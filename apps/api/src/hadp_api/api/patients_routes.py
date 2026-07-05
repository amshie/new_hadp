"""Patient routes (tenant-scoped, RLS enforced, audited).

Onboarding additions (docs/notes/0011): a pre-create duplicate probe and optional consent
capture in the SAME transaction as the create. The duplicate probe is a POST so identity
details travel in the request body, never in a query string (access logs record
path+query; bodies are never logged).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.errors import DuplicatePatient
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.enums import ConsentPurpose, DuplicateMatchBasis
from hadp_api.modules.patients import service as patients_service
from hadp_api.modules.patients.service import STRONG_MATCH_BASES

router = APIRouter(prefix="/patients", tags=["patients"])

# Earliest accepted birth year; together with "not in the future" this bounds the date of
# birth to a plausible range at the system boundary (the UI enforces the same rule with
# localized messages before submitting).
_MIN_BIRTH_YEAR = 1900


class ConsentGrantIn(BaseModel):
    """A consent granted at onboarding, recorded by the creating staff member.

    Purposes are the existing CLOSED vocabulary (synthetic-Alpha placeholders pending the
    DPO/counsel taxonomy) — onboarding never invents one.
    """

    purpose: ConsentPurpose
    # Bounded free string like the consent routes (e.g. "in_person"); the real channel
    # vocabulary is part of the pending DPO consent taxonomy.
    channel: str = Field(min_length=1, max_length=40)


class CreatePatientRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=120)
    date_of_birth: date | None = None
    # Optional onboarding consents, recorded ATOMICALLY with the create (append-only
    # ConsentEvent stream; each grant separately audited with the purpose only).
    consents: list[ConsentGrantIn] = Field(default_factory=list)
    # Explicit override after the client surfaced strong duplicate candidates to the
    # user. Never the default: a strong match without this flag is a 409.
    allow_duplicate: bool = False

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name must not be blank")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_dob(cls, v: date | None) -> date | None:
        if v is None:
            return None
        if v > datetime.now(UTC).date():
            raise ValueError("date_of_birth must not be in the future")
        if v.year < _MIN_BIRTH_YEAR:
            raise ValueError(f"date_of_birth must be {_MIN_BIRTH_YEAR} or later")
        return v

    @field_validator("consents")
    @classmethod
    def _unique_purposes(cls, v: list[ConsentGrantIn]) -> list[ConsentGrantIn]:
        purposes = [c.purpose for c in v]
        if len(purposes) != len(set(purposes)):
            raise ValueError("consents must not repeat a purpose")
        return v


class PatientOut(BaseModel):
    id: uuid.UUID
    display_name: str
    external_ref: str | None
    date_of_birth: date | None
    is_synthetic: bool


class DuplicateCheckRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date | None = None
    external_ref: str | None = Field(default=None, max_length=120)

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name must not be blank")
        return v


class DuplicateCandidateOut(BaseModel):
    id: uuid.UUID
    display_name: str
    external_ref: str | None
    date_of_birth: date | None
    match_basis: DuplicateMatchBasis


class DuplicateCheckOut(BaseModel):
    candidates: list[DuplicateCandidateOut]
    # True when at least one candidate matched on external_ref or name+date of birth:
    # creating without allow_duplicate would be rejected with 409 `duplicate_patient`.
    has_strong_match: bool


def _to_out(patient: object) -> PatientOut:
    p = patient
    return PatientOut(
        id=p.id,  # type: ignore[attr-defined]
        display_name=p.display_name,  # type: ignore[attr-defined]
        external_ref=p.external_ref,  # type: ignore[attr-defined]
        date_of_birth=p.date_of_birth,  # type: ignore[attr-defined]
        is_synthetic=p.is_synthetic,  # type: ignore[attr-defined]
    )


@router.post("/duplicate-check", response_model=DuplicateCheckOut)
def duplicate_check(
    body: DuplicateCheckRequest,
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> DuplicateCheckOut:
    """Probe THIS tenant for likely-duplicate patients before creating one.

    Read-only and tenant-scoped (explicit filter + RLS): an identical patient in another
    tenant is invisible by construction. Audited with the candidate COUNT only — the
    audit service's forbidden-key guard rejects names outright.
    """
    candidates = patients_service.find_duplicate_candidates(
        ctx.db,
        tenant_id=ctx.tenant_id,
        display_name=body.display_name,
        date_of_birth=body.date_of_birth,
        external_ref=body.external_ref,
    )
    record_audit(
        ctx.db,
        action="patient.duplicate_check",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"candidates": len(candidates)},
    )
    return DuplicateCheckOut(
        candidates=[
            DuplicateCandidateOut(
                id=c.patient.id,
                display_name=c.patient.display_name,
                external_ref=c.patient.external_ref,
                date_of_birth=c.patient.date_of_birth,
                match_basis=c.basis,
            )
            for c in candidates
        ],
        has_strong_match=any(c.basis in STRONG_MATCH_BASES for c in candidates),
    )


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    body: CreatePatientRequest,
    ctx: TenantContext = Depends(require(Action.PATIENT_CREATE)),
) -> PatientOut:
    """Create a synthetic patient; optionally record onboarding consents atomically.

    Duplicate guard: a STRONG candidate (same external_ref, or same normalized name +
    date of birth in this tenant) rejects the create with 409 `duplicate_patient` unless
    the client passes `allow_duplicate=true` after showing the candidates to the user —
    a duplicate can be created deliberately, never silently. Weak (name-only) matches
    never block. The 409 rolls the transaction back; nothing persists for a rejected
    attempt.
    """
    db: Session = ctx.db
    if not body.allow_duplicate:
        candidates = patients_service.find_duplicate_candidates(
            db,
            tenant_id=ctx.tenant_id,
            display_name=body.display_name,
            date_of_birth=body.date_of_birth,
            external_ref=body.external_ref,
        )
        if any(c.basis in STRONG_MATCH_BASES for c in candidates):
            raise DuplicatePatient(
                "a patient with matching identity details already exists in this tenant"
            )
    patient = patients_service.create_patient(
        db,
        tenant_id=ctx.tenant_id,
        display_name=body.display_name,
        external_ref=body.external_ref,
        date_of_birth=body.date_of_birth,
        created_by_user_id=ctx.user.id,
    )
    record_audit(
        db,
        action="patient.create",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient.id,
        correlation_id=ctx.correlation_id,
    )
    for consent in body.consents:
        consents_service.record_consent(
            db,
            tenant_id=ctx.tenant_id,
            patient_id=patient.id,
            purpose=consent.purpose,
            channel=consent.channel,
            recorded_by_user_id=ctx.user.id,
        )
        record_audit(
            db,
            action="consent.granted",
            actor_user_id=ctx.user.id,
            tenant_id=ctx.tenant_id,
            target_type="patient",
            target_id=patient.id,
            correlation_id=ctx.correlation_id,
            detail={"purpose": consent.purpose.value},
        )
    return _to_out(patient)


@router.get("", response_model=list[PatientOut])
def list_patients(
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> list[PatientOut]:
    db: Session = ctx.db
    patients = patients_service.list_patients(db, ctx.tenant_id)
    record_audit(
        db,
        action="patient.list",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"count": len(patients)},
    )
    return [_to_out(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(require(Action.PATIENT_READ)),
) -> PatientOut:
    db: Session = ctx.db
    patient = patients_service.get_patient(db, ctx.tenant_id, patient_id)
    record_audit(
        db,
        action="patient.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="patient",
        target_id=patient.id,
        correlation_id=ctx.correlation_id,
    )
    return _to_out(patient)
