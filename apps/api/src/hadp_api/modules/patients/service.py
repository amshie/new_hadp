"""Patients application service. All reads/writes are tenant-scoped (RLS enforced)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.errors import NotFound
from hadp_api.modules.patients.models import Patient


def create_patient(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    display_name: str,
    external_ref: str | None,
    date_of_birth: date | None,
    created_by_user_id: uuid.UUID,
) -> Patient:
    patient = Patient(
        tenant_id=tenant_id,
        display_name=display_name,
        external_ref=external_ref,
        date_of_birth=date_of_birth,
        created_by_user_id=created_by_user_id,
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()
    return patient


def list_patients(db: Session, tenant_id: uuid.UUID) -> list[Patient]:
    # tenant_id is redundant with RLS but kept explicit so the scope is obvious at call sites.
    return list(
        db.execute(
            select(Patient).where(Patient.tenant_id == tenant_id).order_by(Patient.created_at)
        )
        .scalars()
        .all()
    )


def get_patient(db: Session, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
    patient = db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if patient is None:
        raise NotFound("patient not found")
    return patient
