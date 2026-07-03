"""DB-backed tests for the interpretation service: create_run records a whole run; latest_matrix
returns 6 verdicts x 3 cells; reads are tenant-filtered; an invalid run shape is refused; evidence
refs must resolve to the patient's own PUBLISHED observations; authorship is required."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from hadp_api.errors import IntendedUseViolation
from hadp_api.modules.enums import (
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    ReviewStatus,
    TriStateAxis,
    ValueType,
)
from hadp_api.modules.identity.models import User
from hadp_api.modules.interpretation import service
from hadp_api.modules.interpretation.run_shape import (
    CellInput,
    DomainInput,
    EvidenceRef,
    RunInput,
)
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.tenancy.models import Tenant


def _domain(axis: DomainAxis, ref: EvidenceRef) -> DomainInput:
    return DomainInput(
        domain_axis=axis,
        cis_status=CisStatus.CIS_4_CREDIBLE_IMPROVEMENT,
        actionability_class=ActionabilityClass.C_CLINICALLY_INTERPRETABLE,
        followup_adequacy=AdequacyStatus.ADEQUATE,
        rationale="note",
        cells=[
            CellInput(TriStateAxis.BIOLOGICAL, "STABLE", AdequacyStatus.ADEQUATE, [ref]),
            CellInput(TriStateAxis.RISK, "REDUCED", AdequacyStatus.ADEQUATE, [ref]),
            CellInput(TriStateAxis.FUNCTIONAL, "IMPROVED", AdequacyStatus.ADEQUATE, [ref]),
        ],
    )


def _full_run(ref: EvidenceRef) -> RunInput:
    return RunInput(domains=[_domain(a, ref) for a in DomainAxis])


def _published_observation(
    db: Session,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    review_status: ReviewStatus = ReviewStatus.PUBLISHED,
) -> uuid.UUID:
    obs = Observation(
        tenant_id=tenant_id,
        patient_id=patient_id,
        original_name="LDL Cholesterol",
        original_value="2.8",
        value_type=ValueType.NUMERIC,
        normalization_version="test-v1",
        observed_at=datetime(2025, 6, 10, tzinfo=UTC),
        observed_at_is_date_only=True,
        received_at=datetime(2025, 6, 11, tzinfo=UTC),
        review_status=review_status,
    )
    db.add(obs)
    db.flush()
    return obs.id


def _patient(db: Session, slug: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, EvidenceRef]:
    """Tenant + patient + authoring user + a ref to the patient's own PUBLISHED observation."""
    tenant = Tenant(name="T", slug=slug, is_synthetic=True)
    db.add(tenant)
    db.flush()
    patient = Patient(
        tenant_id=tenant.id,
        external_ref=f"SYN-{slug}",
        display_name="Synthetic Patient",
        date_of_birth=date(1980, 1, 1),
        is_synthetic=True,
    )
    user = User(email=f"author-{slug}@synthetic.example", display_name="A", is_synthetic=True)
    db.add_all([patient, user])
    db.flush()
    obs_id = _published_observation(db, tenant.id, patient.id)
    return tenant.id, patient.id, user.id, EvidenceRef(kind="observation", id=str(obs_id))


def test_create_run_records_six_verdicts_and_eighteen_cells(admin_session: Session) -> None:
    tenant_id, patient_id, user_id, ref = _patient(admin_session, "run-a")
    run = service.create_run(
        admin_session,
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=user_id,
        run=_full_run(ref),
        reason="baseline",
    )
    # Authorship is recorded, never null ("a clinician authors" is enforced).
    assert run.created_by_user_id == user_id
    matrix = service.latest_matrix(admin_session, tenant_id, patient_id)
    assert matrix is not None
    assert len(matrix["domains"]) == 6
    assert all(len(d["cells"]) == 3 for d in matrix["domains"])
    # CIS and Actionability are present as TWO separate fields (never merged).
    first = matrix["domains"][0]
    assert first["cis_status"].startswith("CIS_")
    assert first["actionability_class"][0] in "ABCDE"


def test_latest_matrix_is_tenant_filtered(admin_session: Session) -> None:
    tenant_id, patient_id, user_id, ref = _patient(admin_session, "run-b")
    service.create_run(
        admin_session,
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=user_id,
        run=_full_run(ref),
        reason="baseline",
    )
    # A different tenant id must not see this patient's run.
    assert service.latest_matrix(admin_session, uuid.uuid4(), patient_id) is None


def test_create_run_rejects_an_incomplete_run(admin_session: Session) -> None:
    tenant_id, patient_id, user_id, ref = _patient(admin_session, "run-c")
    bad = _full_run(ref)
    bad.domains.pop()  # five domains, not six
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=user_id,
            run=bad,
            reason="bad",
        )


def test_create_run_rejects_unresolvable_evidence(admin_session: Session) -> None:
    """Fail-closed evidence resolution: nonexistent, foreign-patient, and unreviewed
    observations, and non-observation kinds, are all refused."""
    tenant_id, patient_id, user_id, _ = _patient(admin_session, "run-d")

    # Nonexistent observation id.
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=user_id,
            run=_full_run(EvidenceRef(kind="observation", id=str(uuid.uuid4()))),
            reason="bad-ref",
        )

    # Another patient's observation (same tenant) must not back this patient's verdicts.
    other = Patient(
        tenant_id=tenant_id,
        external_ref="SYN-run-d-other",
        display_name="Other Patient",
        date_of_birth=date(1981, 1, 1),
        is_synthetic=True,
    )
    admin_session.add(other)
    admin_session.flush()
    foreign_obs = _published_observation(admin_session, tenant_id, other.id)
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=user_id,
            run=_full_run(EvidenceRef(kind="observation", id=str(foreign_obs))),
            reason="foreign-ref",
        )

    # An unreviewed (PENDING) observation must not back a verdict.
    pending_obs = _published_observation(
        admin_session, tenant_id, patient_id, review_status=ReviewStatus.PENDING
    )
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=user_id,
            run=_full_run(EvidenceRef(kind="observation", id=str(pending_obs))),
            reason="pending-ref",
        )

    # A non-observation kind is unresolvable today and refused.
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=user_id,
            run=_full_run(EvidenceRef(kind="measurement", id=str(uuid.uuid4()))),
            reason="bad-kind",
        )
