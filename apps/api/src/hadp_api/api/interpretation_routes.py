"""Interpretation read route — the per-axis matrix for a patient (tenant-scoped, audited).

Returns the latest interpretation run as six domain verdicts (CIS + Actionability as TWO separate
fields) plus their three verdict-free tri-state cells. No unified score, no derived rollup.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.interpretation import service as interpretation_service
from hadp_api.modules.patients import service as patients_service

router = APIRouter(tags=["interpretation"])


class EvidenceObsOut(BaseModel):
    original_name: str
    value: str | None
    unit: str | None
    reference: str | None
    observed_at: str
    review_status: str
    metric_code: str | None


class TriStateCellOut(BaseModel):
    tri_state_axis: str
    state: str
    endpoint_adequacy: str
    evidence_count: int
    evidence: list[EvidenceObsOut]
    rationale: str | None


class DomainVerdictOut(BaseModel):
    domain_axis: str
    cis_status: str
    actionability_class: str
    followup_adequacy: str
    review_status: str
    rationale: str | None
    cells: list[TriStateCellOut]


class DomainMatrixOut(BaseModel):
    run_id: str | None
    run_number: int | None
    domains: list[DomainVerdictOut]


@router.get("/patients/{patient_id}/interpretation", response_model=DomainMatrixOut)
def get_interpretation(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> DomainMatrixOut:
    # Tenant-scoped existence check: a cross-tenant patient_id is a 404 (no info leak).
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    matrix = interpretation_service.latest_matrix(ctx.db, ctx.tenant_id, patient_id)
    record_audit(
        ctx.db,
        action="interpretation.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
        detail={"domains": 0 if matrix is None else len(matrix["domains"])},
    )
    if matrix is None:
        return DomainMatrixOut(run_id=None, run_number=None, domains=[])
    return DomainMatrixOut(**matrix)
