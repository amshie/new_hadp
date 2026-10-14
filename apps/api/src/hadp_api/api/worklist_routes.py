"""Worklist route — the clinician's queue (tenant-scoped, RLS enforced, audited).

Returns STRUCTURED rows (ids, codes, raw fields, timestamps). The frontend formats
display strings (age, relative time) and maps status → badge/label. Attention-summary and
data-quality columns are intentionally omitted until the rules/coverage model exists
(see docs/adr/0002-frontend-backend-wiring.md §6, Gate G1).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.imports import summary as imports_summary
from hadp_api.modules.interpretation import service as interpretation_service
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.patients import service as patients_service
from hadp_api.modules.reports import service as reports_service

router = APIRouter(prefix="/worklist", tags=["worklist"])


class WorklistRowOut(BaseModel):
    patient_id: uuid.UUID
    report_id: uuid.UUID | None
    display_name: str
    external_ref: str | None
    date_of_birth: date | None
    report_status: str | None
    version_no: int | None
    updated_at: datetime
    # When the latest report reached its status: released, approved or rejected at that
    # moment; a draft when its version was written. Null without a report.
    status_at: datetime | None = None
    # What lies under the record — workflow counts, never a statement about a value.
    values_published: int = 0
    values_pending: int = 0
    # When the oldest value still awaiting a human decision arrived.
    pending_since: datetime | None = None
    latest_received_at: datetime | None = None
    # The latest interpretation run (its number and when it was recorded), and how many
    # values arrived after it (rejected ones not counted). Null and 0 without a run.
    latest_run_number: int | None = None
    latest_run_at: datetime | None = None
    values_since_run: int = 0


class ThroughputBucketOut(BaseModel):
    date: date
    created: int
    signed: int
    released: int = 0


class ThroughputOut(BaseModel):
    """Real per-day report-version throughput for the dashboard "Review-Durchsatz" chart.

    `created` = versions created that day; `signed` = versions approved (signed off) that day —
    both from persisted `ReportVersion` timestamps, tenant-scoped. A real rate over time, NOT a
    fabricated trend; zero-activity days are included so the series has no gaps.
    """

    days: int
    buckets: list[ThroughputBucketOut]
    total_created: int
    total_signed: int
    total_released: int = 0


class CoverageOut(BaseModel):
    """Tenant-wide observation coverage counts for the dashboard "Datenlage" tile (ADR-0006).

    Plain counts + freshness over real observations — NOT a clinical data-quality score. The
    quality/rules model that the comp's "94 %" gauge implied does not exist (Gate G1); these are
    the honest coverage figures the UI renders instead of a fabricated percentage.
    """

    total: int
    published: int
    with_reference: int
    latest_observed_at: datetime | None
    # Linked to a marker of the KPI catalog (a mapping, not a judgement of the value).
    with_kpi: int = 0


class SourceOut(BaseModel):
    """One way values came in: a laboratory file reader by its name, or (`parser_name` null)
    every other way — entered by hand or sent through the API. Counts and times only."""

    parser_name: str | None
    jobs: int
    rows: int
    last_import_at: datetime | None


@router.get("", response_model=list[WorklistRowOut])
def get_worklist(
    status: str | None = None,
    q: str | None = None,
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> list[WorklistRowOut]:
    db = ctx.db
    patients = patients_service.list_patients(db, ctx.tenant_id)
    latest = reports_service.latest_reports_by_patient(db, ctx.tenant_id)
    runs = interpretation_service.latest_runs_by_patient(db, ctx.tenant_id)
    counts = obs_service.value_counts_by_patient(
        db, ctx.tenant_id, {pid: run.recorded_at for pid, run in runs.items()}
    )

    rows: list[WorklistRowOut] = []
    for p in patients:
        report = latest.get(p.id)
        report_status = report.status.value if report else None
        if status and report_status != status:
            continue
        if q:
            haystack = f"{p.display_name} {p.external_ref or ''}".lower()
            if q.lower() not in haystack:
                continue
        version = reports_service.current_version_for(db, report) if report else None
        run = runs.get(p.id)
        value_counts = counts.get(p.id) or obs_service.PatientValueCounts()
        rows.append(
            WorklistRowOut(
                patient_id=p.id,
                report_id=report.id if report else None,
                display_name=p.display_name,
                external_ref=p.external_ref,
                date_of_birth=p.date_of_birth,
                report_status=report_status,
                version_no=version.version_no if version else None,
                updated_at=report.created_at if report else p.created_at,
                status_at=reports_service.status_reached_at(version) if version else None,
                values_published=value_counts.published,
                values_pending=value_counts.pending,
                pending_since=value_counts.pending_since,
                latest_received_at=value_counts.latest_received_at,
                latest_run_number=run.run_number if run else None,
                latest_run_at=run.recorded_at if run else None,
                values_since_run=value_counts.received_after_cutoff,
            )
        )

    record_audit(
        db,
        action="worklist.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"count": len(rows)},
    )
    return rows


@router.get("/coverage", response_model=CoverageOut)
def get_coverage(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> CoverageOut:
    summary = obs_service.coverage_summary(ctx.db, ctx.tenant_id)
    record_audit(
        ctx.db,
        action="worklist.coverage.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"total": summary.total},
    )
    return CoverageOut(
        total=summary.total,
        published=summary.published,
        with_reference=summary.with_reference,
        latest_observed_at=summary.latest_observed_at,
        with_kpi=summary.with_kpi,
    )


@router.get("/sources", response_model=list[SourceOut])
def get_sources(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> list[SourceOut]:
    lines = imports_summary.source_summary(ctx.db, ctx.tenant_id)
    record_audit(
        ctx.db,
        action="worklist.sources.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"jobs": sum(line.jobs for line in lines)},
    )
    return [
        SourceOut(
            parser_name=line.parser_name,
            jobs=line.jobs,
            rows=line.rows,
            last_import_at=line.last_import_at,
        )
        for line in lines
    ]


@router.get("/throughput", response_model=ThroughputOut)
def get_throughput(
    days: int = Query(default=30, ge=1, le=90),
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> ThroughputOut:
    summary = reports_service.throughput_daily(ctx.db, ctx.tenant_id, days)
    record_audit(
        ctx.db,
        action="worklist.throughput.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"days": summary.days},
    )
    return ThroughputOut(
        days=summary.days,
        buckets=[
            ThroughputBucketOut(date=b.day, created=b.created, signed=b.signed, released=b.released)
            for b in summary.buckets
        ],
        total_created=summary.total_created,
        total_signed=summary.total_signed,
        total_released=summary.total_released,
    )
