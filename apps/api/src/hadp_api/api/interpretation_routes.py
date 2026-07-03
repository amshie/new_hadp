"""Interpretation read route — the per-axis matrix for a patient (tenant-scoped, audited).

Returns the latest interpretation run as six domain verdicts (CIS + Actionability as TWO separate
fields) plus their three verdict-free tri-state cells. No unified score, no derived rollup.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import (
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    TriStateAxis,
)
from hadp_api.modules.interpretation import service as interpretation_service
from hadp_api.modules.interpretation.run_shape import (
    CellInput,
    DomainInput,
    EvidenceRef,
    RunInput,
)
from hadp_api.modules.patients import service as patients_service

router = APIRouter(tags=["interpretation"])


class EvidenceObsOut(BaseModel):
    observation_id: str
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


# ---- Authoring (write path) ---------------------------------------------------------
# The clinician authors a WHOLE run; the engine validates and records; it never derives.
# Pydantic enforces the closed vocabularies at the boundary (422 on any non-member
# value — a CIS value in the actionability field is structurally impossible);
# run_shape re-checks the doctrine shape and the service resolves every evidence ref
# against this patient's own published observations (fail-closed).


class EvidenceRefIn(BaseModel):
    kind: str = Field(max_length=40)
    id: str = Field(max_length=64)


class TriStateCellIn(BaseModel):
    tri_state_axis: TriStateAxis
    state: str = Field(max_length=40)
    endpoint_adequacy: AdequacyStatus
    evidence_refs: list[EvidenceRefIn] = Field(default_factory=list, max_length=50)
    rationale: str | None = Field(default=None, max_length=2000)


class DomainVerdictIn(BaseModel):
    domain_axis: DomainAxis
    cis_status: CisStatus
    actionability_class: ActionabilityClass
    followup_adequacy: AdequacyStatus
    cells: list[TriStateCellIn] = Field(max_length=10)
    rationale: str | None = Field(default=None, max_length=2000)


class RunAuthorIn(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    domains: list[DomainVerdictIn] = Field(max_length=10)


@router.post(
    "/patients/{patient_id}/interpretation-runs",
    response_model=DomainMatrixOut,
    status_code=201,
)
def author_interpretation_run(
    patient_id: uuid.UUID,
    body: RunAuthorIn,
    ctx: TenantContext = Depends(require(Action.INTERPRETATION_AUTHOR)),
) -> DomainMatrixOut:
    # Tenant-scoped existence check: a cross-tenant patient_id is a 404 (no info leak).
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    run_input = RunInput(
        domains=[
            DomainInput(
                domain_axis=d.domain_axis,
                cis_status=d.cis_status,
                actionability_class=d.actionability_class,
                followup_adequacy=d.followup_adequacy,
                rationale=d.rationale,
                cells=[
                    CellInput(
                        tri_state_axis=c.tri_state_axis,
                        state=c.state,
                        endpoint_adequacy=c.endpoint_adequacy,
                        evidence_refs=[EvidenceRef(kind=r.kind, id=r.id) for r in c.evidence_refs],
                        rationale=c.rationale,
                    )
                    for c in d.cells
                ],
            )
            for d in body.domains
        ]
    )
    run = interpretation_service.create_run(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        created_by_user_id=ctx.user.id,
        run=run_input,
        reason=body.reason,
    )
    record_audit(
        ctx.db,
        action="interpretation.authored",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="interpretation_run",
        target_id=run.id,
        correlation_id=ctx.correlation_id,
        detail={"run_number": run.run_number, "domains": len(body.domains)},
    )
    matrix = interpretation_service.latest_matrix(ctx.db, ctx.tenant_id, patient_id)
    assert matrix is not None  # the run was just recorded
    return DomainMatrixOut(**matrix)
