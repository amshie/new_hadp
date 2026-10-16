"""The intake tables and the one write, against PostgreSQL under the application role.

- `intake_batches` / `pending_values` are tenant-isolated and append-only for `hadp_app`.
- `kpi_plausibility_bounds` is read-only for `hadp_app`; the seed refuses a bound in the wrong
  unit; the shipped seed is empty.
- `create_pending_batch` writes the batch and its values with the status the checks computed,
  records one audit event without values, writes NO observation, and refuses a proposal that
  carries a field the model is not asked for (`status`) — nothing of it is written.
- Without signed bounds every mapped value is yellow; with the golden TEST bounds inserted by
  an admin, the service reproduces the golden case's statuses.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.errors import NotFound
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.documents.service import store_source_document
from hadp_api.modules.enums import PendingValueStatus, Role
from hadp_api.modules.intake import service as intake_service
from hadp_api.modules.intake.models import IntakeBatch, KpiPlausibilityBound, PendingValue
from hadp_api.modules.intake.schemas import ProposedBatchIn
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from tests.helpers import provision_staff
from tests.intake_support import CASES_DIR, load_case

GREEN_CASE = CASES_DIR / "01_a_nord_all_green"
MISMATCH_CASE = CASES_DIR / "11_b_sued_patient_mismatch"


def _setup(admin_session, slug: str):  # type: ignore[no-untyped-def]
    user, tenant = provision_staff(
        admin_session,
        email=f"intake-{slug}@example.test",
        tenant_name=f"Intake {slug}",
        tenant_slug=f"intake-{slug}",
        role=Role.CLINICIAN,
    )
    patient = Patient(
        tenant_id=tenant.id,
        display_name="Synthetic Intake Patient",
        date_of_birth=datetime(1970, 3, 12).date(),
        is_synthetic=True,
    )
    admin_session.add(patient)
    admin_session.commit()
    return user, tenant, patient


def _app_session(tenant_id, user_id):  # type: ignore[no-untyped-def]
    session = get_sessionmaker()()
    set_tenant_context(session, tenant_id, user_id)
    return session


def _store(db, *, tenant_id, patient_id, user_id, case_dir):  # type: ignore[no-untyped-def]
    document, _created = store_source_document(
        db,
        tenant_id=tenant_id,
        patient_id=patient_id,
        filename="report.pdf",
        content_type="application/pdf",
        data=(case_dir / "input" / "report.pdf").read_bytes(),
        uploaded_by_user_id=user_id,
    )
    return document


def _proposal(case_dir) -> ProposedBatchIn:  # type: ignore[no-untyped-def]
    return load_case(case_dir).proposal


def _insert_test_bounds(admin_session, case_dir) -> None:  # type: ignore[no-untyped-def]
    patient = json.loads((case_dir / "input" / "patient.json").read_text(encoding="utf-8"))
    for code, b in patient["test_bounds"].items():
        if code.startswith("_"):
            continue
        admin_session.add(
            KpiPlausibilityBound(
                kpi_code=code,
                unit=b["unit"],
                hard_low=Decimal(b["hard_low"]) if b["hard_low"] is not None else None,
                hard_high=Decimal(b["hard_high"]) if b["hard_high"] is not None else None,
                delta_max_relative=(
                    Decimal(b["delta_max_relative"])
                    if b["delta_max_relative"] is not None
                    else None
                ),
                source="TEST FIXTURE — not clinically signed",
                signed_by="test-fixture",
                signed_at=datetime.now(UTC),
                bounds_version="test",
            )
        )
    admin_session.commit()


# --- the write -------------------------------------------------------------------------------


def test_a_batch_is_written_with_computed_statuses_and_no_observation(admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "write")
    db = _app_session(tenant.id, user.id)
    try:
        document = _store(
            db, tenant_id=tenant.id, patient_id=patient.id, user_id=user.id, case_dir=GREEN_CASE
        )
        observations_before = db.execute(select(func.count()).select_from(Observation)).scalar_one()
        result = intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            document_id=document.id,
            proposal=_proposal(GREEN_CASE),
            created_by_user_id=user.id,
            correlation_id="test-intake",
            today=datetime(2026, 10, 16).date(),
        )
        db.commit()
        set_tenant_context(db, tenant.id, user.id)  # a commit ends the transaction-local binding

        # No observation: the write is a proposal, not a record.
        assert (
            db.execute(select(func.count()).select_from(Observation)).scalar_one()
            == observations_before
        )
        batch = db.get(IntakeBatch, result.batch_id)
        assert batch is not None and batch.value_count == 6 and batch.page_count == 1
        assert batch.model_id == "fixture-proposal" and batch.prompt_version == "fixture-1"
        rows = (
            db.execute(
                select(PendingValue)
                .where(PendingValue.batch_id == batch.id)
                .order_by(PendingValue.row_index)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 6
        # Without signed bounds, nothing mapped is green: every value asks a human to look.
        assert {r.status for r in rows} == {PendingValueStatus.YELLOW}
        assert all(
            any(c.get("reason") == "plausibility_not_configured" for c in r.checks) for r in rows
        )
        assert (result.green, result.yellow, result.red) == (0, 6, 0)
        ldl = next(r for r in rows if r.proposed_analyte_text == "LDL")
        assert (ldl.kpi_code, ldl.canonical_unit, ldl.normalized_value) == (
            "cardio.ldl_c",
            "mmol/L",
            Decimal("3.1"),
        )
        assert (
            ldl.normalized_reference_high == Decimal("3.0") and ldl.normalized_reference_low is None
        )
        assert ldl.bbox is not None and len(ldl.bbox) == 4

        # One audit event: identifiers and counts, no value, no name.
        events = (
            db.execute(select(AuditEvent).where(AuditEvent.action == "intake.batch_proposed"))
            .scalars()
            .all()
        )
        assert len(events) == 1
        event = events[0]
        assert event.target_type == "intake_batch" and event.target_id == batch.id
        assert event.detail["value_count"] == 6 and event.detail["yellow"] == 6
        assert "5,4" not in json.dumps(event.detail) and "LDL" not in json.dumps(event.detail)
    finally:
        db.close()


def test_with_signed_bounds_the_service_reproduces_the_golden_statuses(admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "bounds")
    _insert_test_bounds(admin_session, GREEN_CASE)
    db = _app_session(tenant.id, user.id)
    try:
        document = _store(
            db, tenant_id=tenant.id, patient_id=patient.id, user_id=user.id, case_dir=GREEN_CASE
        )
        result = intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            document_id=document.id,
            proposal=_proposal(GREEN_CASE),
            created_by_user_id=user.id,
            today=datetime(2026, 10, 16).date(),
        )
        db.commit()
        assert (result.green, result.yellow, result.red) == (6, 0, 0)
    finally:
        db.close()


def test_another_patients_report_is_recorded_red_not_dropped(admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "mismatch")
    db = _app_session(tenant.id, user.id)
    try:
        document = _store(
            db, tenant_id=tenant.id, patient_id=patient.id, user_id=user.id, case_dir=MISMATCH_CASE
        )
        result = intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            document_id=document.id,
            proposal=_proposal(MISMATCH_CASE),
            created_by_user_id=user.id,
            today=datetime(2026, 10, 16).date(),
        )
        db.commit()
        set_tenant_context(db, tenant.id, user.id)
        assert (result.green, result.yellow, result.red) == (0, 0, 2)
        batch = db.get(IntakeBatch, result.batch_id)
        assert batch is not None
        assert any(c.get("reason") == "patient_mismatch" for c in batch.checks)
    finally:
        db.close()


def test_a_proposal_that_sets_the_status_itself_is_refused_whole() -> None:
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    raw["values"][0]["status"] = "green"
    with pytest.raises(ValidationError):
        ProposedBatchIn.model_validate(raw)
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    raw["values"][0]["kpi_code"] = "metabolic.hba1c"
    with pytest.raises(ValidationError):
        ProposedBatchIn.model_validate(raw)
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    raw["checks"] = []
    with pytest.raises(ValidationError):
        ProposedBatchIn.model_validate(raw)


def test_a_document_of_another_clinic_or_patient_is_not_found_and_nothing_is_written(
    admin_session,
) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "cross")
    other_user, other_tenant, other_patient = _setup(admin_session, "cross-other")
    other_db = _app_session(other_tenant.id, other_user.id)
    try:
        foreign = _store(
            other_db,
            tenant_id=other_tenant.id,
            patient_id=other_patient.id,
            user_id=other_user.id,
            case_dir=GREEN_CASE,
        )
        other_db.commit()
    finally:
        other_db.close()
    db = _app_session(tenant.id, user.id)
    try:
        with pytest.raises(NotFound):
            intake_service.create_pending_batch(
                db,
                tenant_id=tenant.id,
                patient_id=patient.id,
                document_id=foreign.id,
                proposal=_proposal(GREEN_CASE),
                created_by_user_id=user.id,
            )
        db.rollback()
        with pytest.raises(NotFound):
            intake_service.create_pending_batch(
                db,
                tenant_id=tenant.id,
                patient_id=patient.id,
                document_id=uuid.uuid4(),
                proposal=_proposal(GREEN_CASE),
                created_by_user_id=user.id,
            )
        db.rollback()
    finally:
        db.close()
    assert admin_session.execute(select(func.count()).select_from(IntakeBatch)).scalar_one() == 0
    assert admin_session.execute(select(func.count()).select_from(PendingValue)).scalar_one() == 0


# --- the tables ------------------------------------------------------------------------------


def test_pending_values_are_append_only_for_the_app_role_and_for_the_owner(admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "append")
    db = _app_session(tenant.id, user.id)
    try:
        document = _store(
            db, tenant_id=tenant.id, patient_id=patient.id, user_id=user.id, case_dir=GREEN_CASE
        )
        result = intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            document_id=document.id,
            proposal=_proposal(GREEN_CASE),
            created_by_user_id=user.id,
        )
        db.commit()
        value_id = result.value_ids[0]
        with pytest.raises(ProgrammingError):  # privilege: no UPDATE for hadp_app
            db.execute(
                text("UPDATE pending_values SET status = 'green' WHERE id = :id"), {"id": value_id}
            )
        db.rollback()
        with pytest.raises(ProgrammingError):
            db.execute(text("DELETE FROM pending_values WHERE id = :id"), {"id": value_id})
        db.rollback()
        with pytest.raises(ProgrammingError):
            db.execute(text("DELETE FROM intake_batches WHERE id = :id"), {"id": result.batch_id})
        db.rollback()
    finally:
        db.close()
    # The owner has the privilege; the trigger still refuses.
    with pytest.raises(DBAPIError) as err:
        admin_session.execute(
            text("UPDATE pending_values SET status = 'green' WHERE id = :id"), {"id": value_id}
        )
    assert "append-only" in str(err.value)
    admin_session.rollback()


def test_another_clinic_cannot_read_a_batch(admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant, patient = _setup(admin_session, "rls")
    other_user, other_tenant, _ = _setup(admin_session, "rls-other")
    db = _app_session(tenant.id, user.id)
    try:
        document = _store(
            db, tenant_id=tenant.id, patient_id=patient.id, user_id=user.id, case_dir=GREEN_CASE
        )
        intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            document_id=document.id,
            proposal=_proposal(GREEN_CASE),
            created_by_user_id=user.id,
        )
        db.commit()
    finally:
        db.close()
    other = _app_session(other_tenant.id, other_user.id)
    try:
        assert other.execute(select(func.count()).select_from(PendingValue)).scalar_one() == 0
        assert other.execute(select(func.count()).select_from(IntakeBatch)).scalar_one() == 0
    finally:
        other.close()
    blind = get_sessionmaker()()
    try:
        assert blind.execute(select(func.count()).select_from(PendingValue)).scalar_one() == 0
    finally:
        blind.close()


def test_the_app_role_cannot_write_bounds_and_the_shipped_seed_is_empty(admin_session) -> None:  # type: ignore[no-untyped-def]
    engine = create_engine(os.environ["APP_DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn, pytest.raises(ProgrammingError):
            conn.execute(
                text(
                    "INSERT INTO kpi_plausibility_bounds (kpi_code, unit, source, signed_by, "
                    "signed_at, bounds_version) "
                    "VALUES ('metabolic.hba1c', '%', 'x', 'x', now(), 'x')"
                )
            )
    finally:
        engine.dispose()
    assert intake_service.seed_plausibility_bounds(admin_session) == 0
    assert (
        admin_session.execute(select(func.count()).select_from(KpiPlausibilityBound)).scalar_one()
        == 0
    )


def test_the_seed_refuses_a_bound_in_the_wrong_unit_or_for_an_unknown_kpi(
    admin_session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        intake_service,
        "SIGNED_BOUNDS",
        [("metabolic.hba1c", "mmol/mol", "0", "200", None, "test", "nobody", "2026-10-16")],
    )
    with pytest.raises(ValueError, match="catalog holds it in"):
        intake_service.seed_plausibility_bounds(admin_session)
    admin_session.rollback()
    monkeypatch.setattr(
        intake_service,
        "SIGNED_BOUNDS",
        [("nothing.here", "%", "0", "1", None, "test", "nobody", "2026-10-16")],
    )
    with pytest.raises(ValueError, match="unknown KPI"):
        intake_service.seed_plausibility_bounds(admin_session)
    admin_session.rollback()
    monkeypatch.setattr(
        intake_service,
        "SIGNED_BOUNDS",
        [("metabolic.hba1c", "%", "2", "20", "1.0", "test", "nobody", "2026-10-16")],
    )
    assert intake_service.seed_plausibility_bounds(admin_session) == 1
    assert intake_service.seed_plausibility_bounds(admin_session) == 0  # idempotent
    admin_session.rollback()


def test_a_file_that_is_not_a_pdf_is_refused_before_anything_is_written(admin_session) -> None:  # type: ignore[no-untyped-def]
    from hadp_api.errors import ValidationFailed

    user, tenant, patient = _setup(admin_session, "notpdf")
    db = _app_session(tenant.id, user.id)
    try:
        document, _ = store_source_document(
            db,
            tenant_id=tenant.id,
            patient_id=patient.id,
            filename="values.csv",
            content_type="text/csv",
            data=b"analyte,value\nHbA1c,5.4\n",
            uploaded_by_user_id=user.id,
        )
        with pytest.raises(ValidationFailed, match="document_unreadable"):
            intake_service.create_pending_batch(
                db,
                tenant_id=tenant.id,
                patient_id=patient.id,
                document_id=document.id,
                proposal=_proposal(GREEN_CASE),
                created_by_user_id=user.id,
            )
        db.rollback()
        assert db.execute(select(func.count()).select_from(IntakeBatch)).scalar_one() == 0
    finally:
        db.close()
