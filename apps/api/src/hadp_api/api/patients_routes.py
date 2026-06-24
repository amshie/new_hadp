"""Patient routes (tenant-scoped, RLS enforced, audited)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.patients import service as patients_service

router = APIRouter(prefix="/patients", tags=["patients"])


class CreatePatientRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    external_ref: str | None = Field(default=None, max_length=120)
    date_of_birth: date | None = None


class PatientOut(BaseModel):
    id: uuid.UUID
    display_name: str
    external_ref: str | None
    date_of_birth: date | None
    is_synthetic: bool


def _to_out(patient: object) -> PatientOut:
    p = patient
    return PatientOut(
        id=p.id,  # type: ignore[attr-defined]
        display_name=p.display_name,  # type: ignore[attr-defined]
        external_ref=p.external_ref,  # type: ignore[attr-defined]
        date_of_birth=p.date_of_birth,  # type: ignore[attr-defined]
        is_synthetic=p.is_synthetic,  # type: ignore[attr-defined]
    )


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    body: CreatePatientRequest,
    ctx: TenantContext = Depends(require(Action.PATIENT_CREATE)),
) -> PatientOut:
    db: Session = ctx.db
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
