"""Report routes: generate draft, view (with inline evidence), approve, release."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.config import get_settings
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.patients import service as patients_service
from hadp_api.modules.reports import service as reports_service
from hadp_api.modules.reports.service import _get_report  # internal lookup (tenant-scoped)

router = APIRouter(tags=["reports"])


class ReleaseOut(BaseModel):
    report_id: uuid.UUID
    status: str
    patient_access_token: str
    patient_view_url: str


class StatementIn(BaseModel):
    id: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1)
    evidence_observation_ids: list[uuid.UUID] = Field(min_length=1)


class EditReportRequest(BaseModel):
    statements: list[StatementIn] = Field(min_length=1)


@router.post("/patients/{patient_id}/reports", status_code=201)
def generate_report(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.REPORT_DRAFT)),
) -> dict[str, Any]:
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    report = reports_service.generate_draft(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        generated_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="report.draft_generated",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="report",
        target_id=report.id,
        correlation_id=ctx.correlation_id,
    )
    return reports_service.assemble_report_view(ctx.db, report)


@router.get("/reports/{report_id}")
def get_report(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> dict[str, Any]:
    report = _get_report(ctx.db, report_id, ctx.tenant_id)
    return reports_service.assemble_report_view(ctx.db, report)


@router.post("/reports/{report_id}/edit")
def edit_report(
    report_id: uuid.UUID,
    body: EditReportRequest,
    ctx: TenantContext = Depends(require(Action.REPORT_EDIT)),
) -> dict[str, Any]:
    statements = [
        {
            "id": s.id,
            "text": s.text,
            "evidence_observation_ids": [str(i) for i in s.evidence_observation_ids],
        }
        for s in body.statements
    ]
    version = reports_service.edit_report(
        ctx.db,
        report_id=report_id,
        tenant_id=ctx.tenant_id,
        statements=statements,
        edited_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="report.draft_edited",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="report_version",
        target_id=version.id,
        correlation_id=ctx.correlation_id,
        detail={"version_no": version.version_no},
    )
    report = _get_report(ctx.db, report_id, ctx.tenant_id)
    return reports_service.assemble_report_view(ctx.db, report)


@router.post("/reports/{report_id}/approve")
def approve_report(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.REPORT_APPROVE)),
) -> dict[str, Any]:
    version = reports_service.approve_report(
        ctx.db, report_id=report_id, tenant_id=ctx.tenant_id, approved_by_user_id=ctx.user.id
    )
    record_audit(
        ctx.db,
        action="report.approved",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="report_version",
        target_id=version.id,
        correlation_id=ctx.correlation_id,
        detail={"version_no": version.version_no},
    )
    report = _get_report(ctx.db, report_id, ctx.tenant_id)
    return reports_service.assemble_report_view(ctx.db, report)


@router.post("/reports/{report_id}/release", response_model=ReleaseOut)
def release_report(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.REPORT_RELEASE)),
) -> ReleaseOut:
    report, raw_token = reports_service.release_report(
        ctx.db, report_id=report_id, tenant_id=ctx.tenant_id, released_by_user_id=ctx.user.id
    )
    record_audit(
        ctx.db,
        action="report.released",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="report",
        target_id=report.id,
        correlation_id=ctx.correlation_id,
    )
    # Link targets the web patient-view page (not the JSON API endpoint).
    base = get_settings().web_base_url
    url = f"{base}/patient-view?tenant={ctx.tenant_id}&token={raw_token}"
    return ReleaseOut(
        report_id=report.id,
        status=report.status.value,
        patient_access_token=raw_token,
        patient_view_url=url,
    )
