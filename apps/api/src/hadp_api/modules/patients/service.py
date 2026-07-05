"""Patients application service. All reads/writes are tenant-scoped (RLS enforced)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.errors import NotFound
from hadp_api.modules.enums import DuplicateMatchBasis
from hadp_api.modules.patients.models import Patient

# Bases that block an un-flagged create (route raises DuplicatePatient). A name-only match is
# surfaced to the user but never blocks — same-name/different-person is routine in a clinic.
STRONG_MATCH_BASES = frozenset({DuplicateMatchBasis.EXTERNAL_REF, DuplicateMatchBasis.NAME_DOB})


@dataclass(frozen=True)
class DuplicateCandidate:
    patient: Patient
    basis: DuplicateMatchBasis


def _normalize_name(name: str) -> str:
    # Case-insensitive with internal whitespace collapsed. Deliberately NOT transliterated
    # (Müller != Mueller) and NOT fuzzy — conservative and documented (docs/notes/0011).
    return " ".join(name.split()).lower()


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


def find_duplicate_candidates(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    display_name: str,
    date_of_birth: date | None,
    external_ref: str | None,
) -> list[DuplicateCandidate]:
    """Existing patients in THIS tenant that likely match the given identity details.

    Matching walks the tenant's patients in Python so input and column go through the
    exact same normalization (one code path, no SQL/Python casing drift) — fine at Alpha
    scale, where the directory endpoint already loads the same rows. Tenant scoping is
    explicit AND RLS-enforced; a cross-tenant twin is invisible by construction.
    Strongest basis wins per candidate: external_ref > name_dob > name.
    """
    name_norm = _normalize_name(display_name)
    ref_norm = external_ref.strip() if external_ref and external_ref.strip() else None
    candidates: list[DuplicateCandidate] = []
    # Tombstoned (erased) patients carry no identity and must never match a new patient.
    rows = db.execute(
        select(Patient)
        .where(Patient.tenant_id == tenant_id, Patient.erased_at.is_(None))
        .order_by(Patient.created_at)
    ).scalars()
    for row in rows:
        basis: DuplicateMatchBasis | None = None
        if (
            ref_norm is not None
            and row.external_ref is not None
            and row.external_ref.strip() == ref_norm
        ):
            basis = DuplicateMatchBasis.EXTERNAL_REF
        if basis is None and _normalize_name(row.display_name) == name_norm:
            if (
                date_of_birth is not None
                and row.date_of_birth is not None
                and row.date_of_birth == date_of_birth
            ):
                basis = DuplicateMatchBasis.NAME_DOB
            else:
                basis = DuplicateMatchBasis.NAME
        if basis is not None:
            candidates.append(DuplicateCandidate(patient=row, basis=basis))

    rank = {
        DuplicateMatchBasis.EXTERNAL_REF: 0,
        DuplicateMatchBasis.NAME_DOB: 1,
        DuplicateMatchBasis.NAME: 2,
    }
    candidates.sort(key=lambda c: (rank[c.basis], c.patient.created_at))
    return candidates


def list_patients(db: Session, tenant_id: uuid.UUID) -> list[Patient]:
    # tenant_id is redundant with RLS but kept explicit so the scope is obvious at call sites.
    # Erased (tombstoned) patients are hidden from the directory listing.
    return list(
        db.execute(
            select(Patient)
            .where(Patient.tenant_id == tenant_id, Patient.erased_at.is_(None))
            .order_by(Patient.created_at)
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
