"""Worklist route — the clinician's queue (tenant-scoped, RLS enforced, audited).

Returns STRUCTURED rows (ids, codes, raw fields, timestamps). The frontend formats
display strings (age, relative time) and maps status → badge/label. Attention-summary and
data-quality columns are intentionally omitted until the rules/coverage model exists
(see docs/adr/0002-frontend-backend-wiring.md §6, Gate G1).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import last_reads_by_actor, record_audit
from hadp_api.modules.enums import DomainAxis
from hadp_api.modules.imports import summary as imports_summary
from hadp_api.modules.interpretation import service as interpretation_service
from hadp_api.modules.kpi import service as kpi_service
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


class PreparationRowOut(BaseModel):
    """One record on the practice view (docs/notes/0023): who it is, where its report stands,
    its latest interpretation run, and the counts the page before a visit shows for it —
    workflow and provenance facts, never a rating, a rank or a sum."""

    patient_id: uuid.UUID
    display_name: str
    external_ref: str | None
    report_status: str | None
    updated_at: datetime
    latest_run_number: int | None = None
    latest_run_at: datetime | None = None
    # Published, standing values received after the latest run; of those, outside the
    # laboratory's interval. 0 without a run.
    new_since_run: int = 0
    new_outside: int = 0
    # Markers whose latest standing value lies outside their laboratory's interval.
    outside: int = 0
    # Core markers whose latest value is older than `stale_after_days`; with no value at all.
    stale_core: int = 0
    missing_core: int = 0
    values_pending: int = 0
    unassigned: int = 0
    # Domains the latest run recorded no verdict for; null without a run.
    domains_without_verdict: int | None = None


class PreparationOut(BaseModel):
    stale_after_days: int
    core_markers: int
    rows: list[PreparationRowOut]


class ChangeRowOut(BaseModel):
    """One record with something that arrived or moved after the signed-in person last
    opened it (docs/notes/0024). What the person did themselves is not news to them: a run
    they recorded or a report step they took is left out. Counts and workflow facts only."""

    patient_id: uuid.UUID
    display_name: str
    external_ref: str | None
    last_opened_at: datetime
    # Values received after the opening: published, and awaiting review.
    new_published: int = 0
    new_pending: int = 0
    latest_received_at: datetime | None = None
    # An interpretation run someone else recorded after the opening: its number and moment.
    run_number: int | None = None
    run_at: datetime | None = None
    # The step the latest report took after the opening, by someone else: the status it
    # reached, its version, and when.
    report_status: str | None = None
    report_version_no: int | None = None
    report_status_at: datetime | None = None
    # The latest of the moments above.
    changed_at: datetime


class ChangesOut(BaseModel):
    # Records the person has opened at least once, and records they never opened — the
    # latter can hold no "since", so they are counted, not listed.
    opened: int
    never_opened: int
    rows: list[ChangeRowOut]


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


@router.get("/preparation", response_model=PreparationOut)
def get_preparation(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> PreparationOut:
    """The practice view: the page before a visit, for every record of the clinic at once
    (docs/notes/0023). Rows come in the patient list's order; the page orders by workflow
    and lets a person sort by a column — the API ranks nothing."""
    db = ctx.db
    patients = patients_service.list_patients(db, ctx.tenant_id)
    latest = reports_service.latest_reports_by_patient(db, ctx.tenant_id)
    runs = interpretation_service.latest_runs_by_patient(db, ctx.tenant_id)
    verdicts = interpretation_service.verdict_counts_by_latest_run(db, ctx.tenant_id)
    core = {k.code for k in kpi_service.core_kpis(db)}
    facts = obs_service.preparation_facts_by_patient(
        db,
        ctx.tenant_id,
        {pid: run.recorded_at for pid, run in runs.items()},
        core,
        datetime.now(UTC),
    )
    rows: list[PreparationRowOut] = []
    for p in patients:
        report = latest.get(p.id)
        run = runs.get(p.id)
        f = facts.get(p.id) or obs_service.PatientPreparationFacts(missing_core=len(core))
        rows.append(
            PreparationRowOut(
                patient_id=p.id,
                display_name=p.display_name,
                external_ref=p.external_ref,
                report_status=report.status.value if report else None,
                updated_at=report.created_at if report else p.created_at,
                latest_run_number=run.run_number if run else None,
                latest_run_at=run.recorded_at if run else None,
                new_since_run=f.new_since_run,
                new_outside=f.new_outside,
                outside=f.outside,
                stale_core=f.stale_core,
                missing_core=f.missing_core,
                values_pending=f.pending,
                unassigned=f.unassigned,
                domains_without_verdict=(
                    len(DomainAxis) - verdicts.get(p.id, 0) if run is not None else None
                ),
            )
        )
    record_audit(
        db,
        action="worklist.preparation.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"count": len(rows)},
    )
    return PreparationOut(
        stale_after_days=obs_service.STALE_AFTER_DAYS, core_markers=len(core), rows=rows
    )


@router.get("/changes", response_model=ChangesOut)
def get_changes(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> ChangesOut:
    """What arrived or moved in each record since the signed-in person last opened it
    (docs/notes/0024). The opening is the person's own `patient.read` in the clinic's trail;
    nothing else is stored, and opening the record again is what clears the row. Rows come in
    the patient list's order; the page puts the latest change first."""
    db = ctx.db
    patients = patients_service.list_patients(db, ctx.tenant_id)
    opened_at = last_reads_by_actor(
        db, tenant_id=ctx.tenant_id, actor_user_id=ctx.user.id, action="patient.read"
    )
    cutoffs = {p.id: opened_at[p.id] for p in patients if p.id in opened_at}
    arrivals = obs_service.arrivals_by_patient(db, ctx.tenant_id, cutoffs)
    latest = reports_service.latest_reports_by_patient(db, ctx.tenant_id)
    runs = interpretation_service.latest_runs_by_patient(db, ctx.tenant_id)
    rows: list[ChangeRowOut] = []
    for p in patients:
        since = cutoffs.get(p.id)
        if since is None:
            continue
        moments: list[datetime] = []
        row = ChangeRowOut(
            patient_id=p.id,
            display_name=p.display_name,
            external_ref=p.external_ref,
            last_opened_at=since,
            changed_at=since,
        )
        arrived = arrivals.get(p.id)
        if arrived is not None and arrived.latest_received_at is not None:
            row.new_published = arrived.published
            row.new_pending = arrived.pending
            row.latest_received_at = arrived.latest_received_at
            moments.append(arrived.latest_received_at)
        run = runs.get(p.id)
        if run is not None and run.recorded_at > since and run.recorded_by != ctx.user.id:
            row.run_number = run.run_number
            row.run_at = run.recorded_at
            moments.append(run.recorded_at)
        report = latest.get(p.id)
        version = reports_service.current_version_for(db, report) if report else None
        if version is not None:
            reached = reports_service.status_reached_at(version)
            if reached > since and not reports_service.version_stepped_by(version, ctx.user.id):
                row.report_status = version.status.value
                row.report_version_no = version.version_no
                row.report_status_at = reached
                moments.append(reached)
        if not moments:
            continue
        row.changed_at = max(moments)
        rows.append(row)
    record_audit(
        db,
        action="worklist.changes.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"count": len(rows)},
    )
    return ChangesOut(opened=len(cutoffs), never_opened=len(patients) - len(cutoffs), rows=rows)


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
