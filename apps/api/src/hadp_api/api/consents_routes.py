"""Consent routes — the API surface of the P0 consent gate (append-only).

A grant and a withdrawal are each a NEW event (never an in-place edit); withdrawal of
`report_release` revokes live patient access links in the same transaction (service).
Purposes remain the closed synthetic-Alpha placeholders — the real taxonomy, per-purpose
lawful basis, and counsel-authored consent text are a pending DPO/counsel deliverable.
The write routes are audited with the purpose only (never names, text, or values); the read
route gives the current state per purpose to every staff role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.enums import ConsentEventType, ConsentPurpose
from hadp_api.modules.patients import service as patients_service

router = APIRouter(tags=["consents"])


class ConsentIn(BaseModel):
    purpose: ConsentPurpose
    # Channel stays a bounded free string for the synthetic Alpha (e.g. "in_person");
    # the real channel vocabulary is part of the pending DPO consent taxonomy.
    channel: str = Field(min_length=1, max_length=40)


class ConsentEventOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    purpose: str
    event_type: str
    consent_text_version: str
    channel: str
    recorded_at: str


def _out(event) -> ConsentEventOut:  # type: ignore[no-untyped-def]
    return ConsentEventOut(
        id=event.id,
        patient_id=event.patient_id,
        purpose=event.purpose.value,
        event_type=event.event_type.value,
        consent_text_version=event.consent_text_version,
        channel=event.channel,
        recorded_at=event.recorded_at.isoformat(),
    )


class ConsentStateOut(BaseModel):
    purpose: str
    # True iff the latest event for this purpose is a grant (the rule the release gate applies).
    active: bool
    # The latest event; None if nothing was ever recorded for this purpose.
    last_event: ConsentEventOut | None


@router.get("/patients/{patient_id}/consents", response_model=list[ConsentStateOut])
def list_consents(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> list[ConsentStateOut]:
    """Current consent state for every purpose of the closed vocabulary (read staff)."""
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    states = consents_service.current_consents(
        ctx.db, tenant_id=ctx.tenant_id, patient_id=patient_id
    )
    record_audit(
        ctx.db,
        action="consent.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
    )
    return [
        ConsentStateOut(
            purpose=purpose.value,
            active=event is not None and event.event_type == ConsentEventType.GRANTED,
            last_event=_out(event) if event is not None else None,
        )
        for purpose, event in states.items()
    ]


@router.post("/patients/{patient_id}/consents", response_model=ConsentEventOut, status_code=201)
def grant_consent(
    patient_id: uuid.UUID,
    body: ConsentIn,
    ctx: TenantContext = Depends(require(Action.CONSENT_RECORD)),
) -> ConsentEventOut:
    # Tenant-scoped existence check: a cross-tenant patient_id is a 404 (no info leak).
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    event = consents_service.record_consent(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        purpose=body.purpose,
        channel=body.channel,
        recorded_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="consent.granted",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
        detail={"purpose": body.purpose.value},
    )
    return _out(event)


@router.post(
    "/patients/{patient_id}/consents/withdraw",
    response_model=ConsentEventOut,
    status_code=201,
)
def withdraw_consent(
    patient_id: uuid.UUID,
    body: ConsentIn,
    ctx: TenantContext = Depends(require(Action.CONSENT_RECORD)),
) -> ConsentEventOut:
    patients_service.get_patient(ctx.db, ctx.tenant_id, patient_id)
    event = consents_service.withdraw_consent(
        ctx.db,
        tenant_id=ctx.tenant_id,
        patient_id=patient_id,
        purpose=body.purpose,
        channel=body.channel,
        recorded_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="consent.withdrawn",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient_id,
        correlation_id=ctx.correlation_id,
        detail={"purpose": body.purpose.value},
    )
    return _out(event)
