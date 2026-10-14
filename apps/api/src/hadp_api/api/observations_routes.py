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


class DerivationInputOut(BaseModel):
    # The input's part in the formula (e.g. "total_cholesterol", "hdl") and the observation.
    role: str
    observation_id: uuid.UUID


class TimelinePointOut(BaseModel):
    observation_id: uuid.UUID
    metric_code: str | None
    original_name: str
    # The source representation, verbatim.
    original_value: str
    original_unit: str | None
    # The number the platform holds (exact decimal as string) and its unit: the normalized value
    # in the catalog's canonical unit when `normalized`, otherwise the source's own number in
    # the source's unit. `converted`: normalizing changed the unit, so `value` and the bounds are
    # the platform's conversion of what the source wrote. The bounds are in the unit of `value`.
    value: str | None
    unit: str | None
    normalized: bool
    converted: bool
    reference_low: str | None
    reference_high: str | None
    observed_at: datetime
    observed_at_is_date_only: bool
    # When the platform received the value (provenance): what could have been seen by a date.
    received_at: datetime
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
    # Correction lineage: the value this one was sent to correct (a proposal until this value
    # is published), and the published correction that has replaced this value.
    supersedes_observation_id: uuid.UUID | None
    superseded_by_observation_id: uuid.UUID | None
    # A derived value computed from an input that a published correction has replaced.
    input_replaced: bool
    # Computed by the platform from other observations of the record (a versioned formula), not
    # reported by any source. `formula_id` names the formula and its version; `derived_from`
    # lists the inputs it was computed from. False / null / empty for a value a source reported.
    derived: bool
    formula_id: str | None
    derived_from: list[DerivationInputOut]


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
            original_value=p.original_value,
            original_unit=p.original_unit,
            value=obs_service.plain(p.value),
            unit=p.unit,
            normalized=p.normalized,
            converted=p.converted,
            reference_low=obs_service.plain(p.reference_low),
            reference_high=obs_service.plain(p.reference_high),
            observed_at=p.observed_at,
            observed_at_is_date_only=p.observed_at_is_date_only,
            received_at=p.received_at,
            review_status=p.review_status.value,
            delta_vs_previous=obs_service.plain(p.delta_vs_previous),
            previous_observation_id=p.previous_observation_id,
            kpi_code=p.kpi_code,
            kpi_primary_domain=p.kpi_primary_domain,
            kpi_secondary_domains=p.kpi_secondary_domains,
            comparability=p.comparability,
            comparability_reason=p.comparability_reason,
            supersedes_observation_id=p.supersedes_observation_id,
            superseded_by_observation_id=p.superseded_by_observation_id,
            input_replaced=p.input_replaced,
            derived=p.derived,
            formula_id=p.formula_id,
            derived_from=[
                DerivationInputOut(role=role, observation_id=input_id)
                for role, input_id in p.derived_from
            ],
        )
        for p in points
    ]
