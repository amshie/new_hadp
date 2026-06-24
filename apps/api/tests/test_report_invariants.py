"""Report safety invariants (service/DB level, RLS-scoped app session)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.errors import Conflict, IntendedUseViolation
from hadp_api.modules.enums import ReportStatus, ReviewStatus, Role, ValueType
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports import service as reports_service
from hadp_api.modules.reports.evidence import validate_statements
from hadp_api.modules.reports.models import ReportVersion
from tests.helpers import provision_staff


def _published_obs(admin_session: Session, tenant_id, patient_id) -> uuid.UUID:
    obs = Observation(
        tenant_id=tenant_id,
        patient_id=patient_id,
        original_name="LDL Cholesterol",
        original_value="2.8",
        original_unit="mmol/L",
        metric_code="13457-7",
        code_system="LOINC",
        value_type=ValueType.NUMERIC,
        numeric_value=Decimal("2.8"),
        normalized_value=Decimal("2.8"),
        normalized_unit="mmol/L",
        reference_low=Decimal("0"),
        reference_high=Decimal("3.0"),
        normalization_version="norm-1",
        observed_at=datetime(2025, 6, 10, tzinfo=UTC),
        observed_at_is_date_only=True,
        received_at=datetime.now(UTC),
        review_status=ReviewStatus.PUBLISHED,
    )
    admin_session.add(obs)
    admin_session.flush()
    return obs.id


@pytest.fixture()
def scoped(admin_session) -> Iterator[tuple[Session, uuid.UUID, uuid.UUID, uuid.UUID]]:  # type: ignore[no-untyped-def]
    user, tenant = provision_staff(
        admin_session,
        email="rep@synthetic.example",
        tenant_name="Report Clinic",
        tenant_slug="report-clinic",
        role=Role.CLINICIAN,
    )
    from hadp_api.modules.patients.models import Patient

    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    _published_obs(admin_session, tenant.id, patient.id)
    admin_session.commit()

    session = get_sessionmaker()()
    set_tenant_context(session, tenant.id, user.id)
    try:
        yield session, tenant.id, patient.id, user.id
    finally:
        session.rollback()
        session.close()


def test_validate_statements_requires_viewable_evidence(scoped) -> None:  # type: ignore[no-untyped-def]
    session, _tenant, patient_id, _user = scoped
    published = list(reports_service.build_evidence_payload(session, patient_id))
    good_id = str(published[0].observation_id)

    validate_statements(session, patient_id, [{"id": "s1", "evidence_observation_ids": [good_id]}])

    with pytest.raises(ValueError):
        validate_statements(session, patient_id, [{"id": "s1", "evidence_observation_ids": []}])

    with pytest.raises(ValueError):
        validate_statements(
            session, patient_id, [{"id": "s1", "evidence_observation_ids": [str(uuid.uuid4())]}]
        )


def test_cannot_release_before_approval(scoped) -> None:  # type: ignore[no-untyped-def]
    session, tenant_id, patient_id, user_id = scoped
    report = reports_service.generate_draft(
        session, tenant_id=tenant_id, patient_id=patient_id, generated_by_user_id=user_id
    )
    with pytest.raises(Conflict):
        reports_service.release_report(
            session, report_id=report.id, tenant_id=tenant_id, released_by_user_id=user_id
        )


def test_approve_rejects_statement_without_viewable_evidence(scoped) -> None:  # type: ignore[no-untyped-def]
    session, tenant_id, patient_id, user_id = scoped
    report = reports_service.generate_draft(
        session, tenant_id=tenant_id, patient_id=patient_id, generated_by_user_id=user_id
    )
    # Tamper the draft body to reference a non-existent observation, then attempt approval.
    version = session.get(ReportVersion, report.current_version_id)
    assert version is not None
    version.body = {
        "statements": [{"id": "s1", "text": "x", "evidence_observation_ids": [str(uuid.uuid4())]}]
    }
    session.flush()
    with pytest.raises(IntendedUseViolation):
        reports_service.approve_report(
            session, report_id=report.id, tenant_id=tenant_id, approved_by_user_id=user_id
        )


def test_edit_after_approval_creates_new_version_and_invalidates_approval(scoped) -> None:  # type: ignore[no-untyped-def]
    session, tenant_id, patient_id, user_id = scoped
    report = reports_service.generate_draft(
        session, tenant_id=tenant_id, patient_id=patient_id, generated_by_user_id=user_id
    )
    approved = reports_service.approve_report(
        session, report_id=report.id, tenant_id=tenant_id, approved_by_user_id=user_id
    )
    assert approved.status == ReportStatus.APPROVED
    statements = approved.body["statements"]

    new_version = reports_service.edit_report(
        session,
        report_id=report.id,
        tenant_id=tenant_id,
        statements=statements,
        edited_by_user_id=user_id,
    )
    assert new_version.version_no == approved.version_no + 1
    assert new_version.status == ReportStatus.DRAFT_EDITED
    assert report.current_version_id == new_version.id
    assert report.status == ReportStatus.DRAFT_EDITED
    # The prior approved version is preserved (not overwritten).
    old = session.get(ReportVersion, approved.id)
    assert old is not None and old.status == ReportStatus.APPROVED
