"""Worklist route — the clinician's queue (tenant-scoped, RLS enforced, audited).

Returns STRUCTURED rows (ids, codes, raw fields, timestamps). The frontend formats
display strings (age, relative time) and maps status → badge/label. Attention-summary and
data-quality columns are intentionally omitted until the rules/coverage model exists
(see docs/adr/0002-frontend-backend-wiring.md §6, Gate G1).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
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


@router.get("", response_model=list[WorklistRowOut])
def get_worklist(
    status: str | None = None,
    q: str | None = None,
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> list[WorklistRowOut]:
    db = ctx.db
    patients = patients_service.list_patients(db, ctx.tenant_id)
    latest = reports_service.latest_reports_by_patient(db, ctx.tenant_id)

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
        rows.append(
            WorklistRowOut(
                patient_id=p.id,
                report_id=report.id if report else None,
                display_name=p.display_name,
                external_ref=p.external_ref,
                date_of_birth=p.date_of_birth,
                report_status=report_status,
                version_no=reports_service.version_no_for(db, report) if report else None,
                updated_at=report.created_at if report else p.created_at,
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
    )
