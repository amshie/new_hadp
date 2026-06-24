"""Observation timeline route (provenance + deterministic deltas)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.patients import service as patients_service

router = APIRouter(tags=["observations"])


class TimelinePointOut(BaseModel):
    observation_id: uuid.UUID
    metric_code: str | None
    original_name: str
    value: str | None  # exact decimal as string (no false precision)
    unit: str | None
    reference_low: str | None
    reference_high: str | None
    observed_at: datetime
    observed_at_is_date_only: bool
    review_status: str
    delta_vs_previous: str | None
    previous_observation_id: uuid.UUID | None
    # Catalog linkage (ADR-0004 Slice 2b): canonical KPI + its navigational domains.
    kpi_code: str | None
    kpi_primary_domain: str | None
    kpi_secondary_domains: list[str]
    # Comparability marker (ADR-0004 Slice 3, §9): verdict-free; "not_comparable" means the delta
    # was withheld because required measurement context is missing/differs.
    comparability: str | None
    comparability_reason: str | None


@router.get("/patients/{patient_id}/observations", response_model=list[TimelinePointOut])
def timeline(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> list[TimelinePointOut]:
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    points = obs_service.build_timeline(ctx.db, patient_id)
    record_audit(
        ctx.db,
        action="observation.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
        detail={"count": len(points)},
    )
    return [
        TimelinePointOut(
            observation_id=p.observation_id,
            metric_code=p.metric_code,
            original_name=p.original_name,
            value=None if p.value is None else str(p.value),
            unit=p.unit,
            reference_low=None if p.reference_low is None else str(p.reference_low),
            reference_high=None if p.reference_high is None else str(p.reference_high),
            observed_at=p.observed_at,
            observed_at_is_date_only=p.observed_at_is_date_only,
            review_status=p.review_status.value,
            delta_vs_previous=None if p.delta_vs_previous is None else str(p.delta_vs_previous),
            previous_observation_id=p.previous_observation_id,
            kpi_code=p.kpi_code,
            kpi_primary_domain=p.kpi_primary_domain,
            kpi_secondary_domains=p.kpi_secondary_domains,
            comparability=p.comparability,
            comparability_reason=p.comparability_reason,
        )
        for p in points
    ]
