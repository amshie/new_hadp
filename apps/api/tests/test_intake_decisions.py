"""The human side of the gate, over HTTP: propose from a stored PDF, read the batch and the page
region, decide — and only a decision makes a value an observation.

Covers: the text-layer provider proposing from the golden PDFs (everything yellow: low
confidence, no signed bounds); the role matrix (assistant proposes and reads, cannot decide;
medical director reads only); confirm → a PUBLISHED observation with provenance and lineage;
correct → the clinician's reading enters, the proposal is kept, the checks still refuse an
impossible correction; reject → nothing enters; red cannot be confirmed; one decision per
value; confirm-all-green; cross-tenant isolation; the audit trail.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.intake.models import IntakeDecision, KpiPlausibilityBound, PendingValue
from hadp_api.modules.observations.models import Observation
from tests.helpers import login_as, switch_role
from tests.intake_support import CASES_DIR

API = "/api/v1"
GREEN_CASE = CASES_DIR / "01_a_nord_all_green"
HALLUCINATION_CASE = CASES_DIR / "10_a_nord_hallucination"


def _patient(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"{API}/patients",
        json={"display_name": "Synthetic Intake Patient", "date_of_birth": "1970-03-12"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _upload(client, patient_id: str, case_dir, name: str = "report.pdf") -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"{API}/patients/{patient_id}/documents",
        files={"file": (name, (case_dir / "input" / "report.pdf").read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _propose(client, patient_id: str, document_id: str) -> dict:  # type: ignore[no-untyped-def, type-arg]
    resp = client.post(f"{API}/patients/{patient_id}/documents/{document_id}/intake")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _batch(client, batch_id: str) -> dict:  # type: ignore[no-untyped-def, type-arg]
    resp = client.get(f"{API}/intake/batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _sign_test_bounds(admin_session) -> None:  # type: ignore[no-untyped-def]
    patient = json.loads((GREEN_CASE / "input" / "patient.json").read_text(encoding="utf-8"))
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
                    Decimal(b["delta_max_relative"]) if b["delta_max_relative"] else None
                ),
                source="TEST FIXTURE — not clinically signed",
                signed_by="test-fixture",
                signed_at=datetime.now().astimezone(),
                bounds_version="test",
            )
        )
    admin_session.commit()


def _clinician(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"intake-{slug}@example.test",
        tenant_name=f"Intake HTTP {slug}",
        tenant_slug=f"intake-http-{slug}",
        role=Role.CLINICIAN,
    )


def _observations(admin_session, patient_id: str) -> list[Observation]:  # type: ignore[no-untyped-def]
    return list(
        admin_session.execute(
            select(Observation).where(Observation.patient_id == uuid.UUID(patient_id))
        ).scalars()
    )


# --- proposing ---------------------------------------------------------------------------------


def test_the_text_layer_provider_proposes_every_line_yellow_and_publishes_nothing(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "propose")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    out = _propose(client, pid, did)
    assert out["extraction_provider"] == "text-layer"
    assert out["value_count"] == 6 and (out["green"], out["yellow"], out["red"]) == (0, 6, 0)
    batch = _batch(client, out["batch_id"])
    assert batch["filename"] == "report.pdf" and batch["page_count"] == 1
    assert batch["proposed_patient_date_of_birth"] == "1970-03-12"
    assert batch["proposed_issue_date"] == "2026-09-06"
    names = [v["analyte_text"] for v in batch["values"]]
    assert names == [
        "HbA1c",
        "LDL",
        "HDL cholesterol",
        "Total cholesterol",
        "Glucose",
        "Triglycerides",
    ]
    ldl = batch["values"][1]
    assert (ldl["value_text"], ldl["unit_text"], ldl["reference_high"]) == ("3,1", "mmol/L", "3,0")
    assert ldl["kpi_code"] == "cardio.ldl_c" and ldl["has_region"] is True
    assert set(ldl["reasons"]) == {"plausibility_not_configured", "low_confidence"}
    assert batch["open_count"] == 6 and all(v["decision"] is None for v in batch["values"])
    assert _observations(admin_session, pid) == []

    listed = client.get(f"{API}/patients/{pid}/intake-batches").json()
    assert len(listed) == 1 and listed[0]["open_count"] == 6 and listed[0]["yellow"] == 6

    region = client.get(f"{API}/intake/values/{ldl['pending_value_id']}/region")
    assert region.status_code == 200 and region.headers["content-type"] == "image/png"
    assert region.content[:8] == b"\x89PNG\r\n\x1a\n" and len(region.content) > 500


def test_a_structured_file_is_not_a_document_the_intake_reads(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "csv")
    pid = _patient(client)
    resp = client.post(
        f"{API}/patients/{pid}/documents",
        files={"file": ("values.csv", b"analyte,value\nHbA1c,5.4\n", "text/csv")},
    )
    did = resp.json()["id"]
    resp = client.post(f"{API}/patients/{pid}/documents/{did}/intake")
    assert resp.status_code == 422 and "document_unreadable" in resp.text


# --- deciding -----------------------------------------------------------------------------------


def test_confirming_a_value_makes_it_a_published_observation_with_provenance(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = _clinician(client, admin_session, "confirm")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    batch_id = _propose(client, pid, did)["batch_id"]
    batch = _batch(client, batch_id)
    ldl = next(v for v in batch["values"] if v["analyte_text"] == "LDL")

    resp = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={
            "pending_value_id": ldl["pending_value_id"],
            "decision": "confirmed",
            "review_seconds": 4,
            "screen_seconds": 20,
        },
    )
    assert resp.status_code == 201, resp.text
    out = resp.json()
    assert out["decision"] == "confirmed" and out["observation_id"]

    [obs] = _observations(admin_session, pid)
    assert str(obs.id) == out["observation_id"]
    assert obs.review_status.value == "published"
    assert (obs.original_name, obs.original_value, obs.original_unit) == ("LDL", "3,1", "mmol/L")
    assert obs.reference_text == "< 3,0"  # the source's own wording, as the page prints it
    assert (obs.kpi_code, obs.normalized_value, obs.normalized_unit) == (
        "cardio.ldl_c",
        Decimal("3.1"),
        "mmol/L",
    )
    assert (obs.reference_low, obs.reference_high) == (None, Decimal("3.0"))
    assert obs.observed_at.date().isoformat() == "2026-09-05" and obs.observed_at_is_date_only
    assert obs.source_document_id == uuid.UUID(did)
    assert obs.source_record_locator is not None and obs.source_record_locator.startswith(
        "page 1 bbox "
    )
    assert obs.normalization_version == "intake-checks-1"

    # Visible on the timeline like any other published value.
    points = client.get(f"{API}/patients/{pid}/observations").json()
    assert any(p["observation_id"] == out["observation_id"] for p in points)

    # The decision is one row, attributable, with its timings; the batch shows it.
    [row] = admin_session.execute(select(IntakeDecision)).scalars().all()
    assert (
        row.decided_by_user_id == user.id and row.review_seconds == 4 and row.screen_seconds == 20
    )
    after = _batch(client, batch_id)
    done = next(v for v in after["values"] if v["analyte_text"] == "LDL")
    assert done["decision"] == "confirmed" and done["observation_id"] == out["observation_id"]
    assert after["open_count"] == 5

    # One decision per value.
    again = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={"pending_value_id": ldl["pending_value_id"], "decision": "confirmed"},
    )
    assert again.status_code == 409 and "already_decided" in again.text
    assert len(_observations(admin_session, pid)) == 1

    actions = [
        a
        for a in admin_session.execute(select(AuditEvent.action)).scalars()
        if a.startswith("intake.")
    ]
    assert actions.count("intake.batch_proposed") == 1
    assert actions.count("intake.value_confirmed") == 1
    assert actions.count("intake.batch_read") >= 2


def test_a_correction_enters_the_clinicians_reading_and_keeps_the_proposal(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "correct")
    pid = _patient(client)
    did = _upload(client, pid, HALLUCINATION_CASE)
    batch_id = _propose(client, pid, did)["batch_id"]
    glucose = next(v for v in _batch(client, batch_id)["values"] if v["analyte_text"] == "Glucose")
    # The provider read the page correctly ("5,1"); the clinician corrects the unit spelling —
    # a change that does not alter the number — and it is recorded as a correction.
    resp = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={
            "pending_value_id": glucose["pending_value_id"],
            "decision": "corrected",
            "correction": {"unit_text": "mmol/l"},
        },
    )
    assert resp.status_code == 201, resp.text
    [obs] = _observations(admin_session, pid)
    assert (obs.original_value, obs.original_unit, obs.normalized_value) == (
        "5,1",
        "mmol/l",
        Decimal("5.1"),
    )
    [row] = admin_session.execute(select(IntakeDecision)).scalars().all()
    assert row.correction is not None
    assert row.correction["original"]["unit_text"] == "mmol/L"
    assert row.correction["final"]["unit_text"] == "mmol/l"
    assert row.correction["page_check"] == []
    shown = next(v for v in _batch(client, batch_id)["values"] if v["analyte_text"] == "Glucose")
    assert shown["decision"] == "corrected" and shown["corrected_to"]["unit_text"] == "mmol/l"

    # A correction that changes nothing is not a decision.
    hba1c = next(v for v in _batch(client, batch_id)["values"] if v["analyte_text"] == "HbA1c")
    same = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={
            "pending_value_id": hba1c["pending_value_id"],
            "decision": "corrected",
            "correction": {"value_text": "5,4"},
        },
    )
    assert same.status_code == 409 and "no_change" in same.text
    # A correction to an impossible reading is refused by the checks.
    _sign_test_bounds(admin_session)
    impossible = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={
            "pending_value_id": hba1c["pending_value_id"],
            "decision": "corrected",
            "correction": {"value_text": "54"},
        },
    )
    assert impossible.status_code == 409 and "outside_hard_bounds" in impossible.text
    # A correction to an unknown unit is refused too.
    unknown = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={
            "pending_value_id": hba1c["pending_value_id"],
            "decision": "corrected",
            "correction": {"unit_text": "mmol/mol"},
        },
    )
    assert unknown.status_code == 409 and "unit_unknown" in unknown.text
    assert len(_observations(admin_session, pid)) == 1


def test_a_red_value_cannot_be_confirmed_and_a_rejection_enters_nothing(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "red")
    pid = _patient(client)
    did = _upload(client, pid, HALLUCINATION_CASE)
    # The text-layer provider reads the page as it is; to get a red value, a batch proposed
    # through the agent's write is used (the golden proposal with the misread "51").
    from hadp_api.modules.intake.schemas import ProposedBatchIn
    from hadp_api.modules.intake.tools import IntakeScope, IntakeTools

    me = client.get(f"{API}/auth/me").json()
    tools = IntakeTools(
        IntakeScope(
            tenant_id=uuid.UUID(me["active_tenant_id"]),
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            actor_user_id=uuid.UUID(me["user"]["id"]),
            extraction_provider="golden-fixture",
            model_id="fixture-proposal",
            prompt_version="fixture-1",
        ),
        today=datetime(2026, 10, 16).date(),
    )
    raw = json.loads((HALLUCINATION_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    ProposedBatchIn.model_validate(raw)
    outcome = tools.create_pending_batch(
        did,
        raw["values"],
        patient_date_of_birth=raw["patient_date_of_birth"],
        issue_date=raw["issue_date"],
    )
    assert outcome.red == 3
    red = next(
        v for v in _batch(client, str(outcome.batch_id))["values"] if v["value_text"] == "51"
    )
    assert red["status"] == "red" and "value_not_on_page" in red["reasons"]

    confirm = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/decisions",
        json={"pending_value_id": red["pending_value_id"], "decision": "confirmed"},
    )
    assert confirm.status_code == 409 and "red_value" in confirm.text

    missing_reason = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/decisions",
        json={"pending_value_id": red["pending_value_id"], "decision": "rejected"},
    )
    assert missing_reason.status_code == 422

    reject = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/decisions",
        json={
            "pending_value_id": red["pending_value_id"],
            "decision": "rejected",
            "rejection_reason": "misread",
            "review_seconds": 9,
        },
    )
    assert reject.status_code == 201 and reject.json()["observation_id"] is None
    assert _observations(admin_session, pid) == []
    # A correction of the misread value to what the page says enters the record.
    correct = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/decisions",
        json={
            "pending_value_id": red["pending_value_id"],
            "decision": "corrected",
            "correction": {"value_text": "5,1"},
        },
    )
    assert correct.status_code == 409 and "already_decided" in correct.text  # it was rejected
    other_red = next(
        v
        for v in _batch(client, str(outcome.batch_id))["values"]
        if v["analyte_text"] == "Ferritin"
    )
    # Ferritin is not on the page at all and its unit is unknown: a correction cannot save it
    # unless the unit is fixed too; with the unit fixed, the page check is advisory only.
    fixed = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/decisions",
        json={
            "pending_value_id": other_red["pending_value_id"],
            "decision": "corrected",
            "correction": {"unit_text": "ug/L"},
        },
    )
    assert fixed.status_code == 201, fixed.text
    [row] = [
        d
        for d in admin_session.execute(select(IntakeDecision)).scalars()
        if d.decision.value == "corrected"
    ]
    assert row.correction is not None and row.correction["page_check"] == ["analyte_not_on_page"]
    assert len(_observations(admin_session, pid)) == 1
    # The batch holds the decided value in the open count's complement, red values included.
    view = _batch(client, str(outcome.batch_id))
    assert view["open_count"] == len(view["values"]) - 2


def test_confirm_all_green_confirms_only_green_and_only_once(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "green")
    _sign_test_bounds(admin_session)
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    from hadp_api.modules.intake.tools import IntakeScope, IntakeTools

    me = client.get(f"{API}/auth/me").json()
    tools = IntakeTools(
        IntakeScope(
            tenant_id=uuid.UUID(me["active_tenant_id"]),
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            actor_user_id=uuid.UUID(me["user"]["id"]),
            extraction_provider="golden-fixture",
            model_id="fixture-proposal",
            prompt_version="fixture-1",
        ),
        today=datetime(2026, 10, 16).date(),
    )
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    # Five green values and one yellow (confidence lowered on the last).
    raw["values"][-1]["confidence"] = "0.5"
    outcome = tools.create_pending_batch(
        did,
        raw["values"],
        patient_date_of_birth=raw["patient_date_of_birth"],
        issue_date=raw["issue_date"],
    )
    assert (outcome.green, outcome.yellow, outcome.red) == (5, 1, 0)

    resp = client.post(
        f"{API}/intake/batches/{outcome.batch_id}/confirm-green", json={"screen_seconds": 31}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["confirmed"] == 5 and len(resp.json()["observation_ids"]) == 5
    assert len(_observations(admin_session, pid)) == 5
    view = _batch(client, str(outcome.batch_id))
    assert view["open_count"] == 1
    assert next(v for v in view["values"] if v["decision"] is None)["status"] == "yellow"
    # Again: nothing left to confirm.
    again = client.post(f"{API}/intake/batches/{outcome.batch_id}/confirm-green", json={})
    assert again.status_code == 200 and again.json()["confirmed"] == 0
    assert len(_observations(admin_session, pid)) == 5


# --- who may do what ------------------------------------------------------------------------------


def test_the_role_matrix_over_http(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "roles")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    batch_id = _propose(client, pid, did)["batch_id"]
    value_id = _batch(client, batch_id)["values"][0]["pending_value_id"]

    switch_role(
        client,
        admin_session,
        email="assistant-roles@example.test",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    assert client.get(f"{API}/intake/batches/{batch_id}").status_code == 200
    assert client.post(f"{API}/patients/{pid}/documents/{did}/intake").status_code == 201
    denied = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={"pending_value_id": value_id, "decision": "confirmed"},
    )
    assert denied.status_code == 403
    assert client.post(f"{API}/intake/batches/{batch_id}/confirm-green", json={}).status_code == 403

    switch_role(
        client,
        admin_session,
        email="md-roles@example.test",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.get(f"{API}/intake/batches/{batch_id}").status_code == 200
    assert client.get(f"{API}/intake/values/{value_id}/region").status_code == 200
    assert client.post(f"{API}/patients/{pid}/documents/{did}/intake").status_code == 403
    assert (
        client.post(
            f"{API}/intake/batches/{batch_id}/decisions",
            json={"pending_value_id": value_id, "decision": "confirmed"},
        ).status_code
        == 403
    )
    assert _observations(admin_session, pid) == []


def test_another_clinic_sees_no_batch_no_value_no_region(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "iso-a")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    batch_id = _propose(client, pid, did)["batch_id"]
    value_id = _batch(client, batch_id)["values"][0]["pending_value_id"]

    _clinician(client, admin_session, "iso-b")
    assert client.get(f"{API}/intake/batches/{batch_id}").status_code == 404
    assert client.get(f"{API}/intake/values/{value_id}/region").status_code == 404
    assert client.get(f"{API}/patients/{pid}/intake-batches").status_code == 404
    assert (
        client.post(
            f"{API}/intake/batches/{batch_id}/decisions",
            json={"pending_value_id": value_id, "decision": "confirmed"},
        ).status_code
        == 404
    )
    assert client.post(f"{API}/intake/batches/{batch_id}/confirm-green", json={}).status_code == 404
    assert admin_session.execute(select(IntakeDecision)).first() is None
    assert admin_session.execute(select(PendingValue)).scalars().all() != []
