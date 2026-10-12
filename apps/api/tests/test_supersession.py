"""Repeated and corrected laboratory values (CLAUDE.md "Corrected reports").

A laboratory sends one measurement more than once: a final report repeats a partial one, a
file is sent again, a result is corrected. Properties under test:

- a value nothing distinguishes from one that stands is recorded, not imported a second time —
  but never when not importing it could lose something a human would want to see;
- a source-marked correction only PROPOSES to replace the one value, sampled at exactly that
  time, it can correct — a human publishing it is what makes the replacement take effect, and
  the earlier value is preserved;
- every other value for an occupied analyte and sampling time is held for review, with the
  held values shown to the reviewer;
- a replaced value is no longer evidence: no change is computed against it, no new draft or
  interpretation run cites it, a report that cites it cannot be approved or released, and a
  new draft from the standing values is the way on (also for a released report);
- matching never crosses patients or tenants.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.derivations.service import compute_derived
from hadp_api.modules.enums import ImportStatus, ReviewStatus, Role, ValueType
from hadp_api.modules.imports import matching
from hadp_api.modules.imports.models import ImportJob, ImportRow, ReviewItem
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports.models import ReportVersion
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import grant_release_consent, login, login_as, select_tenant, switch_role
from tests.ldt_fixtures import TRAILER, header, lab_test, ldt_file, report

_DAY = "2025-06-10T00:00:00Z"


def _clinician(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}@synthetic.example",
        tenant_name=f"{slug} clinic",
        tenant_slug=slug,
        role=Role.CLINICIAN,
    )


def _patient(client, name: str = "Erika Mustermann (synthetic)") -> str:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": name})
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _value(
    value: str = "2.8",
    *,
    name: str = "LDL Cholesterol",
    unit: str = "mmol/L",
    at: str = _DAY,
    date_only: bool = True,
    low: str | None = None,
    high: str | None = None,
) -> dict[str, Any]:
    return {
        "original_name": name,
        "original_value": value,
        "original_unit": unit,
        "observed_at": at,
        "observed_at_is_date_only": date_only,
        "reference_low": low,
        "reference_high": high,
    }


def _enter(client, patient_id: str, *values: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    resp = client.post(f"/api/v1/patients/{patient_id}/imports", json={"values": list(values)})
    assert resp.status_code == 201, resp.text
    return dict(resp.json())


def _import_file(client, patient_id: str, data: bytes, content_type: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    uploaded = client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": ("labs", data, content_type)},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["created"] is True  # a new file, not a re-upload of the same bytes
    resp = client.post(f"/api/v1/patients/{patient_id}/documents/{uploaded.json()['id']}/import")
    assert resp.status_code == 201, resp.text
    return dict(resp.json())


def _ldt(
    client, patient_id: str, *tests: list[tuple[str, str]], **report_fields: Any
) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    data = ldt_file(header(), report(*tests, **report_fields), TRAILER)
    return _import_file(client, patient_id, data, "application/octet-stream")


def _ldl(value: str, **fields: Any) -> list[tuple[str, str]]:
    return lab_test("LDL", "LDL Cholesterol", value=value, unit="mmol/L", **fields)


def _timeline(client, patient_id: str) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    return list(client.get(f"/api/v1/patients/{patient_id}/observations").json())


def _queue(client) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    return list(client.get("/api/v1/review-items").json())


def _decide(client, observation_id: str, decision: str) -> None:  # type: ignore[no-untyped-def]
    """Resolve every open review item of one observation with the same decision."""
    items = [q for q in _queue(client) if q["observation_id"] == observation_id]
    assert items, "expected the observation to be in the review queue"
    for item in items:
        resp = client.post(
            f"/api/v1/review-items/{item['review_item_id']}/resolve", json={"decision": decision}
        )
        assert resp.status_code == 200, resp.text
        if decision == "reject":
            break  # one refusal rejects the observation


def _reasons(client, observation_id: str) -> list[str]:  # type: ignore[no-untyped-def]
    return sorted(q["reason"] for q in _queue(client) if q["observation_id"] == observation_id)


def _values(admin_session) -> list[str]:  # type: ignore[no-untyped-def]
    return sorted(admin_session.execute(select(Observation.original_value)).scalars().all())


# --- repeated values ---


def test_a_final_report_does_not_import_the_partial_reports_values_twice(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "final")
    pid = _patient(client)
    partial = _ldt(
        client,
        pid,
        _ldl("2.8", low="0", high="3.0"),
        lab_test("GLU", "Glucose", value="5.1", unit="mmol/L"),
        lab_test("HBA", "HbA1c", status="F"),
        kind="T",
    )
    assert (partial["published_count"], partial["duplicate_count"]) == (2, 0)

    final = _ldt(
        client,
        pid,
        _ldl("2.8", low="0", high="3.0"),
        # The laboratory may also mark the repeat itself ("bereits berichtet").
        lab_test("GLU", "Glucose", value="5.1", unit="mmol/L", status="B"),
        lab_test("HBA", "HbA1c", value="5.4", unit="%"),
    )
    assert final == {
        **final,
        "published_count": 1,
        "review_count": 0,
        "duplicate_count": 2,
        "not_imported_count": 0,
    }
    assert _values(admin_session) == ["2.8", "5.1", "5.4"]

    # Each repeat is recorded with where it was seen again and which observation it repeats.
    held = {
        o.original_value: str(o.id) for o in admin_session.execute(select(Observation)).scalars()
    }
    repeats = admin_session.execute(
        select(ImportRow).where(ImportRow.status == ImportStatus.REJECTED)
    ).scalars()
    recorded = {r.raw["original_value"]: r.raw for r in repeats if "original_value" in r.raw}
    assert {v: r["duplicate_of_observation_id"] for v, r in recorded.items()} == {
        "2.8": held["2.8"],
        "5.1": held["5.1"],
    }
    assert all(r["not_imported_reason"] == "duplicate_value" for r in recorded.values())
    assert all(r["source_record_locator"].startswith("line ") for r in recorded.values())


def test_the_same_values_in_another_file_import_nothing_new(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "resend")
    pid = _patient(client)
    first = _import_file(
        client,
        pid,
        b"Analyt;Wert;Einheit;Abnahmedatum\nLDL Cholesterol;2,8;mmol/L;10.06.2025\n"
        b"Ferritin;85;ng/mL;10.06.2025\n",
        "text/csv",
    )
    assert (first["published_count"], first["review_count"]) == (1, 1)

    # Other bytes (an extra column the reader ignores), the same values — one of them still
    # waiting in the review queue.
    again = _import_file(
        client,
        pid,
        b"Analyt;Wert;Einheit;Abnahmedatum;Labor\nLDL Cholesterol;2,8;mmol/L;10.06.2025;X\n"
        b"Ferritin;85;ng/mL;10.06.2025;X\n",
        "text/csv",
    )
    assert (again["published_count"], again["review_count"], again["duplicate_count"]) == (0, 0, 2)
    assert _values(admin_session) == ["2,8", "85"]
    assert len(_queue(client)) == 1
    # An import that carried nothing must not read as published.
    job = admin_session.get(ImportJob, uuid.UUID(again["import_job_id"]))
    assert job is not None and job.status == ImportStatus.REJECTED

    # A replay of that import reports the same outcome.
    document_id = admin_session.execute(
        select(ImportJob.source_document_id).where(ImportJob.id == job.id)
    ).scalar_one()
    replay = client.post(f"/api/v1/patients/{pid}/documents/{document_id}/import")
    assert replay.status_code == 200
    assert replay.json() == {**again, "created": False}


def test_a_repeat_inside_one_file_is_a_humans_call(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "infile")
    pid = _patient(client)
    # Twice in one file is more likely a second measurement (another specimen) than a file
    # sent again: nothing is dropped, both later rows wait for a human.
    result = _import_file(
        client,
        pid,
        b"Analyt;Wert;Einheit;Abnahmedatum\n"
        b"LDL Cholesterol;2,8;mmol/L;10.06.2025\n"
        b"LDL Cholesterol;2,8;mmol/L;10.06.2025\n"
        b"LDL Cholesterol;3,1;mmol/L;10.06.2025\n",
        "text/csv",
    )
    assert (result["published_count"], result["review_count"], result["duplicate_count"]) == (
        1,
        2,
        0,
    )
    assert [q["reason"] for q in _queue(client)] == ["possible_duplicate", "possible_duplicate"]


def test_a_marked_repeat_without_a_held_value_is_still_a_humans_call(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "bstatus")
    pid = _patient(client)
    result = _ldt(client, pid, _ldl("2.8", status="B"))
    assert (result["published_count"], result["review_count"], result["duplicate_count"]) == (
        0,
        1,
        0,
    )
    assert [q["reason"] for q in _queue(client)] == ["previously_reported"]


# --- what is NOT a repeat: a human decides ---


def test_another_value_for_the_same_sample_is_held_with_the_held_value_shown(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "conflict")
    pid = _patient(client)
    first = _enter(client, pid, _value("2.8"))["observation_ids"][0]
    second = _enter(client, pid, _value("3.1"))
    assert (second["published_count"], second["review_count"]) == (0, 1)

    (item,) = _queue(client)
    assert item["reason"] == "possible_duplicate"
    assert item["replaces"] is None  # nothing marks it a correction: no replacement is proposed
    assert item["related"] == [
        {
            "observation_id": first,
            "original_name": "LDL Cholesterol",
            "original_value": "2.8",
            "original_unit": "mmol/L",
            "observed_at": _DAY,
            "observed_at_is_date_only": True,
            "review_status": "published",
            "superseded": False,
        }
    ]

    # Publishing it lets both stand; nothing is replaced by an unmarked value.
    _decide(client, second["observation_ids"][0], "publish")
    assert [
        (p["review_status"], p["superseded_by_observation_id"]) for p in _timeline(client, pid)
    ] == [
        ("published", None),
        ("published", None),
    ]


def test_same_number_in_another_notation_unit_or_interval_is_not_dropped(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "notation")
    pid = _patient(client)
    _enter(client, pid, _value("2.8", low="0", high="3.0"))

    for other in (
        _value("2,8", low="0", high="3.0"),  # decimal comma
        _value("108", unit="mg/dL", low="0", high="116"),  # other unit
        _value("2.8", low="0", high="4.1"),  # other reference interval
        _value("2.8", name="LDL", low="0", high="3.0"),  # other name, same metric code
    ):
        result = _enter(client, pid, other)
        assert (result["duplicate_count"], result["review_count"]) == (0, 1), other
        assert "possible_duplicate" in _reasons(client, result["observation_ids"][0])


def test_a_value_with_a_laboratory_note_or_status_is_never_dropped_as_a_repeat(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "status")
    pid = _patient(client)
    # Held: a preliminary value, waiting for review.
    _ldt(client, pid, _ldl("2.8"), kind="V")
    # The final report with the same number must not disappear behind the preliminary one.
    final = _ldt(client, pid, _ldl("2.8"))
    assert (final["duplicate_count"], final["review_count"]) == (0, 1)
    assert _reasons(client, _newest(admin_session)) == ["possible_duplicate"]

    # And a repeat that carries a laboratory note is read by a human, not dropped.
    noted = _ldt(client, pid, _ldl("2.8", text=("Kontrolle empfohlen",)))
    assert (noted["duplicate_count"], noted["review_count"]) == (0, 1)
    assert _reasons(client, _newest(admin_session)) == ["possible_duplicate", "source_comment"]


def _newest(admin_session) -> str:  # type: ignore[no-untyped-def]
    """The observation of the most recent import job."""
    job_id = admin_session.execute(
        select(ImportJob.id).order_by(ImportJob.created_at.desc()).limit(1)
    ).scalar_one()
    return str(
        admin_session.execute(
            select(ReviewItem.observation_id)
            .join(ImportRow, ReviewItem.import_row_id == ImportRow.id)
            .where(ImportRow.import_job_id == job_id)
            .limit(1)
        ).scalar_one()
    )


def test_a_value_a_human_rejected_does_not_come_back_unreviewed(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "rejected")
    pid = _patient(client)
    _enter(client, pid, _value("2.8"))
    refused = _enter(client, pid, _value("3.1"))["observation_ids"][0]
    _decide(client, refused, "reject")

    again = _enter(client, pid, _value("3.1"))
    # Not a repeat of a held value (a rejected value is not held) — and not published either.
    assert (again["duplicate_count"], again["published_count"], again["review_count"]) == (0, 0, 1)
    (item,) = _queue(client)
    assert item["reason"] == "possible_duplicate"
    assert sorted((r["original_value"], r["review_status"]) for r in item["related"]) == [
        ("2.8", "published"),
        ("3.1", "rejected"),
    ]


def test_a_day_only_value_meets_a_timed_value_of_the_same_local_day_in_review(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "dayonly")
    pid = _patient(client)
    # 23:30 UTC on 10 June is 01:30 on 11 June in the laboratory's zone (Europe/Berlin).
    _enter(client, pid, _value("2.8", at="2025-06-10T23:30:00Z", date_only=False))

    other_day = _enter(client, pid, _value("2.8", at="2025-06-10T00:00:00Z"))
    assert (other_day["published_count"], other_day["review_count"]) == (1, 0)

    same_day = _enter(client, pid, _value("2.8", at="2025-06-11T00:00:00Z"))
    # It may be the same sample: never dropped, never published unseen.
    assert (same_day["duplicate_count"], same_day["review_count"]) == (0, 1)
    assert _reasons(client, same_day["observation_ids"][0]) == ["possible_duplicate"]


def test_two_samples_at_different_times_are_two_values(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "twotimes")
    pid = _patient(client)
    result = _enter(
        client,
        pid,
        _value("5.1", name="Glucose", at="2025-06-10T05:30:00Z", date_only=False),
        _value("7.9", name="Glucose", at="2025-06-10T07:30:00Z", date_only=False),
    )
    assert (result["published_count"], result["review_count"], result["duplicate_count"]) == (
        2,
        0,
        0,
    )


def test_matching_never_crosses_patients_or_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "iso-a")
    first = _patient(client, "Patient A (synthetic)")
    second = _patient(client, "Patient B (synthetic)")
    _enter(client, first, _value("2.8"))
    # The same value for another patient is that patient's own first value.
    other = _enter(client, second, _value("2.8"))
    assert (other["published_count"], other["duplicate_count"]) == (1, 0)
    different = _enter(client, second, _value("9.9", at="2025-07-01T00:00:00Z"))
    assert different["review_count"] == 0

    client.cookies.clear()
    _clinician(client, admin_session, "iso-b")
    elsewhere = _patient(client)
    result = _enter(client, elsewhere, _value("2.8"))
    assert (result["published_count"], result["duplicate_count"]) == (1, 0)
    assert _queue(client) == []


# --- corrections ---


def test_a_marked_correction_replaces_the_one_value_only_when_a_human_publishes_it(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "correct")
    pid = _patient(client)
    earlier = _enter(client, pid, _value("2.5", at="2025-01-15T00:00:00Z"))["observation_ids"][0]
    original = _ldt(client, pid, _ldl("2.8"))
    assert original["published_count"] == 1
    original_id = _timeline(client, pid)[1]["observation_id"]

    corrected = _ldt(client, pid, _ldl("3.6", status="K"))
    assert (corrected["published_count"], corrected["review_count"]) == (0, 1)
    (item,) = _queue(client)
    assert item["reason"] == "corrected_result"
    assert item["replaces"] == {
        "observation_id": original_id,
        "original_name": "LDL Cholesterol",
        "original_value": "2.8",
        "original_unit": "mmol/L",
        "observed_at": _DAY,
        "observed_at_is_date_only": True,
        "review_status": "published",
        "superseded": False,
    }
    assert item["related"] == []  # the value it replaces is not listed a second time
    correction_id = item["observation_id"]

    # A proposal only: until a human decides, the original stands and is compared as before.
    by_id = {p["observation_id"]: p for p in _timeline(client, pid)}
    assert by_id[original_id]["superseded_by_observation_id"] is None
    assert by_id[original_id]["previous_observation_id"] == earlier
    assert by_id[correction_id]["supersedes_observation_id"] == original_id
    assert by_id[correction_id]["review_status"] == "pending"

    _decide(client, correction_id, "publish")

    by_id = {p["observation_id"]: p for p in _timeline(client, pid)}
    # The original is preserved, unchanged, and read as replaced.
    assert by_id[original_id]["review_status"] == "published"
    assert by_id[original_id]["value"] == "2.8"
    assert by_id[original_id]["superseded_by_observation_id"] == correction_id
    # A change is only computed between values that stand: 2.5 -> 3.6, never 2.8 -> 3.6.
    assert by_id[original_id]["delta_vs_previous"] is None
    assert by_id[correction_id]["previous_observation_id"] == earlier
    assert Decimal(by_id[correction_id]["delta_vs_previous"]) == Decimal("1.1")

    stored = admin_session.get(Observation, uuid.UUID(original_id))
    assert stored is not None and stored.original_value == "2.8"
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "review_item.resolved")
    ).scalar_one()
    assert audit.detail == {
        "decision": "publish",
        "reason": "corrected_result",
        "superseded_observation_id": original_id,
    }


def test_a_rejected_correction_replaces_nothing(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "norepl")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    _ldt(client, pid, _ldl("3.6", status="K"))
    (item,) = _queue(client)
    _decide(client, item["observation_id"], "reject")

    statuses = {p["value"]: p for p in _timeline(client, pid)}
    assert statuses["2.8"]["superseded_by_observation_id"] is None
    assert statuses["3.6"]["review_status"] == "rejected"
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "review_item.resolved")
    ).scalar_one()
    assert "superseded_observation_id" not in audit.detail


def test_a_correction_of_a_correction_forms_a_chain(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "chain")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    _ldt(client, pid, _ldl("3.6", status="K"))
    _decide(client, _queue(client)[0]["observation_id"], "publish")

    _ldt(client, pid, _ldl("3.4", status="K"))
    (item,) = _queue(client)
    # The value that currently stands is the first correction — that is what is replaced.
    assert item["replaces"]["original_value"] == "3.6"
    assert [(r["original_value"], r["superseded"]) for r in item["related"]] == [("2.8", True)]
    _decide(client, item["observation_id"], "publish")

    standing = [
        p["value"] for p in _timeline(client, pid) if p["superseded_by_observation_id"] is None
    ]
    assert standing == ["3.4"]


def test_a_correction_with_several_candidates_is_never_linked(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "ambig")
    pid = _patient(client)
    _enter(client, pid, _value("2.8"))
    second = _enter(client, pid, _value("3.1"))["observation_ids"][0]
    _decide(client, second, "publish")  # two values now stand for this analyte and day

    _ldt(client, pid, _ldl("3.6", status="K"))
    items = _queue(client)
    assert sorted(q["reason"] for q in items) == ["ambiguous_correction", "corrected_result"]
    assert all(q["replaces"] is None for q in items)
    assert sorted(r["original_value"] for r in items[0]["related"]) == ["2.8", "3.1"]
    correction = admin_session.get(Observation, uuid.UUID(items[0]["observation_id"]))
    assert correction is not None and correction.supersedes_observation_id is None


def test_a_correction_with_nothing_to_correct_is_only_held_for_review(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "lonely")
    pid = _patient(client)
    _enter(client, pid, _value("2.8", at="2025-01-15T00:00:00Z"))  # another sampling day
    _ldt(client, pid, _ldl("3.6", status="K"))
    (item,) = _queue(client)
    assert (item["reason"], item["replaces"], item["related"]) == ("corrected_result", None, [])


def _pending_correction(  # type: ignore[no-untyped-def]
    admin_session,
    tenant: Tenant,
    patient_id: str,
    target: uuid.UUID,
    observed_at: datetime = datetime(2025, 6, 10, tzinfo=UTC),
) -> str:
    correction = Observation(
        tenant_id=tenant.id,
        patient_id=uuid.UUID(patient_id),
        original_name="LDL Cholesterol",
        original_value="3.6",
        original_unit="mmol/L",
        value_type=ValueType.NUMERIC,
        normalization_version="test",
        observed_at=observed_at,
        observed_at_is_date_only=True,
        received_at=datetime.now(UTC),
        review_status=ReviewStatus.PENDING,
        supersedes_observation_id=target,
    )
    admin_session.add(correction)
    admin_session.flush()
    item = ReviewItem(
        tenant_id=tenant.id,
        observation_id=correction.id,
        reason="corrected_result",
        detail={},
        resolved=False,
    )
    admin_session.add(item)
    admin_session.commit()
    return str(item.id)


def test_two_published_corrections_cannot_replace_one_value(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "twice")
    pid = _patient(client)
    target = uuid.UUID(_enter(client, pid, _value("2.8"))["observation_ids"][0])
    # Matching proposes a value for replacement at most once; this is the guard for rows that
    # did not come from it.
    first = _pending_correction(admin_session, tenant, pid, target)
    second = _pending_correction(admin_session, tenant, pid, target)

    ok = client.post(f"/api/v1/review-items/{first}/resolve", json={"decision": "publish"})
    assert ok.status_code == 200, ok.text
    refused = client.post(f"/api/v1/review-items/{second}/resolve", json={"decision": "publish"})
    assert refused.status_code == 409
    assert refused.json()["error"]["detail"].startswith("supersession_conflict")
    # The refused decision changed nothing: the item is still open and can be rejected.
    assert [q["review_item_id"] for q in _queue(client)] == [second]
    assert (
        client.post(
            f"/api/v1/review-items/{second}/resolve", json={"decision": "reject"}
        ).status_code
        == 200
    )


def test_two_imports_of_one_value_side_by_side_create_it_once(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "serial")
    pid = _patient(client)
    # Hold the patient's matching lock so both imports are in flight before either may match.
    matching.lock_patient_record(admin_session, uuid.UUID(pid))
    done: list[dict[str, Any]] = []
    workers = [
        threading.Thread(target=lambda: done.append(_enter(client, pid, _value("2.8"))))
        for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    workers[0].join(0.7)
    assert all(w.is_alive() for w in workers) and not done  # both wait their turn
    admin_session.rollback()  # releases the lock
    for worker in workers:
        worker.join(15)
    # Without the lock each import would miss the other's row and both would publish.
    assert sorted((d["published_count"], d["duplicate_count"]) for d in done) == [(0, 1), (1, 0)]
    assert _values(admin_session) == ["2.8"]


# --- a replaced value is no longer evidence ---


def test_a_draft_that_cites_a_replaced_value_cannot_be_approved(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "report")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    draft = client.post(f"/api/v1/patients/{pid}/reports")
    assert draft.status_code == 201, draft.text
    report_id = draft.json()["report_id"]

    _ldt(client, pid, _ldl("3.6", status="K"))
    (item,) = _queue(client)
    # The reviewer is told that a report cites the value this correction would replace.
    assert item["replaces_cited_in_report_count"] == 1
    _decide(client, item["observation_id"], "publish")

    view = client.get(f"/api/v1/reports/{report_id}").json()
    assert [e["superseded"] for s in view["statements"] for e in s["evidence"]] == [True]
    refused = client.post(f"/api/v1/reports/{report_id}/approve")
    assert refused.status_code == 409
    assert "laboratory correction has replaced" in refused.json()["error"]["detail"]

    # A rework cannot keep the statement either; removing it is the way on.
    kept = client.post(
        f"/api/v1/reports/{report_id}/edit",
        json={
            "statements": [
                {
                    "id": s["id"],
                    "text": s["text"],
                    "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
                }
                for s in view["statements"]
            ]
        },
    )
    assert kept.status_code == 409

    # A new draft is built from the value that stands.
    fresh = client.post(f"/api/v1/patients/{pid}/reports").json()
    cited = [e for s in fresh["statements"] for e in s["evidence"]]
    assert [(e["value"], e["superseded"]) for e in cited] == [("3.6", False)]


def _run_payload(observation_id: str) -> dict[str, Any]:
    ref = [{"kind": "observation", "id": observation_id}]
    cells = [
        {
            "tri_state_axis": axis,
            "state": state,
            "endpoint_adequacy": "adequate",
            "evidence_refs": ref,
        }
        for axis, state in (
            ("biological", "STABLE"),
            ("risk", "REDUCED"),
            ("functional", "IMPROVED"),
        )
    ]
    return {
        "reason": "baseline",
        "domains": [
            {
                "domain_axis": axis,
                "cis_status": "CIS_4_CREDIBLE_IMPROVEMENT",
                "actionability_class": "C_CLINICALLY_INTERPRETABLE",
                "followup_adequacy": "adequate",
                "rationale": "authored note",
                "cells": cells,
            }
            for axis in (
                "metabolic",
                "immune_inflammation",
                "cardiovascular",
                "neurocognitive",
                "musculoskeletal",
                "regenerative_capacity",
            )
        ],
    }


def test_a_new_interpretation_run_cannot_cite_a_replaced_value(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "interp")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    original_id = _timeline(client, pid)[0]["observation_id"]
    run = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_run_payload(original_id))
    assert run.status_code == 201, run.text

    _ldt(client, pid, _ldl("3.6", status="K"))
    correction_id = _queue(client)[0]["observation_id"]
    _decide(client, correction_id, "publish")

    # The existing run is a preserved record; its evidence is marked, not rewritten.
    matrix = client.get(f"/api/v1/patients/{pid}/interpretation").json()
    marks = {e["superseded"] for d in matrix["domains"] for c in d["cells"] for e in c["evidence"]}
    assert marks == {True}

    refused = client.post(
        f"/api/v1/patients/{pid}/interpretation-runs", json=_run_payload(original_id)
    )
    assert refused.status_code == 409
    assert "laboratory correction has replaced" in refused.json()["error"]["detail"]
    accepted = client.post(
        f"/api/v1/patients/{pid}/interpretation-runs", json=_run_payload(correction_id)
    )
    assert accepted.status_code == 201, accepted.text


def test_only_a_published_correction_withdraws_a_derivation_input(admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = Tenant(name="Derivation Clinic", slug="supersede-deriv", is_synthetic=True)
    admin_session.add(tenant)
    admin_session.flush()
    patient = Patient(
        tenant_id=tenant.id,
        display_name="Derivation Patient (synthetic)",
        date_of_birth=date(1980, 1, 1),
        is_synthetic=True,
    )
    admin_session.add(patient)
    admin_session.flush()

    def reading(code: str, value: str, **extra: Any) -> Observation:
        observation = Observation(
            tenant_id=tenant.id,
            patient_id=patient.id,
            original_name=code,
            original_value=value,
            kpi_code=code,
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal(value),
            normalized_value=Decimal(value),
            normalized_unit="mm[Hg]",
            normalization_version="test",
            observed_at=datetime(2025, 6, 10, tzinfo=UTC),
            received_at=datetime.now(UTC),
            **{"review_status": ReviewStatus.PUBLISHED, **extra},
        )
        admin_session.add(observation)
        admin_session.flush()
        return observation

    def pulse_pressure() -> Decimal | None:
        derived = compute_derived(
            admin_session,
            tenant_id=tenant.id,
            patient_id=patient.id,
            formula_id="pulse_pressure.v1",
        )
        return None if derived is None else derived.normalized_value

    systolic = reading("cardio.systolic_bp", "122")
    reading("cardio.diastolic_bp", "78")
    assert pulse_pressure() == Decimal("44")

    correction = reading(
        "cardio.systolic_bp",
        "132",
        review_status=ReviewStatus.PENDING,
        supersedes_observation_id=systolic.id,
    )
    # A correction still in review — or rejected — leaves the original the input.
    assert pulse_pressure() == Decimal("44")
    correction.review_status = ReviewStatus.REJECTED
    admin_session.flush()
    assert pulse_pressure() == Decimal("44")

    correction.review_status = ReviewStatus.PUBLISHED
    admin_session.flush()
    # The value computed from the replaced input no longer stands either — before and after
    # a recomputation — and is marked as such on the timeline.
    stale = {
        p.value: p
        for p in obs_service.build_timeline(admin_session, patient.id)
        if p.input_replaced
    }
    assert list(stale) == [Decimal("44")]
    assert stale[Decimal("44")].observation_id in obs_service.not_standing(
        admin_session, patient.id
    )

    assert pulse_pressure() == Decimal("54")
    points = {p.value: p for p in obs_service.build_timeline(admin_session, patient.id)}
    assert points[Decimal("44")].input_replaced is True
    assert points[Decimal("54")].input_replaced is False
    # A recomputed derived value is lineage, not a laboratory correction.
    assert points[Decimal("44")].superseded_by_observation_id is None
    assert points[Decimal("122")].superseded_by_observation_id == correction.id


def test_an_approved_report_is_not_released_once_its_evidence_was_replaced(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "release")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    report_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)

    # The correction arrives, and is accepted, between approval and release.
    _ldt(client, pid, _ldl("3.6", status="K"))
    _decide(client, _queue(client)[0]["observation_id"], "publish")

    switch_role(
        client,
        admin_session,
        email="director-release@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    refused = client.post(f"/api/v1/reports/{report_id}/release")
    assert refused.status_code == 409
    assert "laboratory correction has replaced" in refused.json()["error"]["detail"]
    # The medical director can send it back; nothing was released.
    assert client.post(f"/api/v1/reports/{report_id}/reject").status_code == 200


# --- cases an independent review found (2026-10-12) ---


def test_a_correction_is_never_linked_to_a_value_that_only_shares_the_day(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "dayfix")
    pid = _patient(client)
    held = _enter(client, pid, _value("5.1", name="Glucose"))["observation_ids"][0]  # day-only

    def glucose(value: str, clock: str) -> list[tuple[str, str]]:
        return lab_test("GLU", "Glucose", value=value, unit="mmol/L", clock=clock, status="K")

    _ldt(client, pid, glucose("6.0", "0800"))
    _ldt(client, pid, glucose("9.9", "1630"))
    items = _queue(client)
    # Two timed corrections of that day: neither can claim the day-only value as THE one it
    # corrects, so nothing is linked and both can be decided.
    assert all(q["replaces"] is None for q in items)
    assert sorted(q["reason"] for q in items) == [
        "ambiguous_correction",
        "ambiguous_correction",
        "corrected_result",
        "corrected_result",
    ]
    for observation_id in {q["observation_id"] for q in items}:
        _decide(client, observation_id, "publish")
    by_id = {p["observation_id"]: p for p in _timeline(client, pid)}
    assert by_id[held]["superseded_by_observation_id"] is None
    assert [p["review_status"] for p in by_id.values()] == ["published"] * 3


def test_the_original_is_not_dropped_behind_a_waiting_already_reported_copy(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "bfirst")
    pid = _patient(client)
    # The cumulative report arrives first: its copy waits as "already reported".
    _ldt(client, pid, _ldl("2.8", status="B"))
    waiting = _queue(client)[0]["observation_id"]

    original = _ldt(client, pid, _ldl("2.8"))
    # Dropping the publishable original here would leave the patient with nothing if the
    # reviewer rejects the waiting copy as a mere repeat.
    assert (original["duplicate_count"], original["review_count"]) == (0, 1)
    item = next(q for q in _queue(client) if q["observation_id"] != waiting)
    assert item["reason"] == "possible_duplicate"
    assert [(r["original_value"], r["review_status"]) for r in item["related"]] == [
        ("2.8", "pending")
    ]

    # Another "already reported" copy shares the waiting copy's fate and is not imported.
    again = _ldt(client, pid, _ldl("2.8", status="B"), lab_test("GLU", "Glucose", value="5.1"))
    assert (again["duplicate_count"], again["published_count"]) == (1, 0)


def test_a_value_identical_to_a_replaced_one_is_a_humans_call(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "revert")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    _ldt(client, pid, _ldl("3.6", status="K"))
    _decide(client, _queue(client)[0]["observation_id"], "publish")

    # It may be the old file sent again — or the laboratory going back. The matcher cannot
    # tell, so the value that contradicts the standing one reaches a human.
    later = _ldt(client, pid, _ldl("2.8"), lab_test("GLU", "Glucose", value="5.1", unit="mmol/L"))
    assert (later["published_count"], later["review_count"], later["duplicate_count"]) == (1, 1, 0)
    (item,) = _queue(client)
    assert item["reason"] == "possible_duplicate"
    assert sorted((r["original_value"], r["superseded"]) for r in item["related"]) == [
        ("2.8", True),
        ("3.6", False),
    ]


def test_the_review_context_is_read_when_the_queue_is_shown(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "live")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    _ldt(client, pid, _ldl("3.6", status="K"))
    (proposal,) = _queue(client)
    assert proposal["related"] == []

    # Another value arrives for that sample and is published before the correction is decided.
    other = _enter(client, pid, _value("3.1"))["observation_ids"][0]
    _decide(client, other, "publish")
    proposal = next(q for q in _queue(client) if q["reason"] == "corrected_result")
    assert proposal["replaces"]["original_value"] == "2.8"
    assert [(r["original_value"], r["review_status"]) for r in proposal["related"]] == [
        ("3.1", "published")
    ]


def test_a_day_only_value_is_stored_as_the_day_as_written(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "pin")
    pid = _patient(client)
    # A client that writes "10 June" with its own offset still means the 10th.
    first = _enter(client, pid, _value("2.8", at="2025-06-10T00:00:00+02:00"))
    stored = admin_session.get(Observation, uuid.UUID(first["observation_ids"][0]))
    assert stored is not None and stored.observed_at == datetime(2025, 6, 10, tzinfo=UTC)

    same = _import_file(
        client,
        pid,
        b"Analyt;Wert;Einheit;Abnahmedatum\nLDL Cholesterol;2.8;mmol/L;10.06.2025\n",
        "text/csv",
    )
    assert (same["published_count"], same["duplicate_count"]) == (0, 1)


def test_two_values_standing_for_one_sample_are_not_a_change_over_time(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "nodelta")
    pid = _patient(client)
    _enter(client, pid, _value("2.5", at="2025-01-15T00:00:00Z"))
    _enter(client, pid, _value("2.8"))
    second = _enter(client, pid, _value("3.1"))["observation_ids"][0]
    _decide(client, second, "publish")

    by_value = {p["value"]: p for p in _timeline(client, pid)}
    assert Decimal(by_value["2.8"]["delta_vs_previous"]) == Decimal("0.3")
    # 2.8 -> 3.1 on the same day is two readings of one sample, not a change.
    assert by_value["3.1"]["delta_vs_previous"] is None
    assert by_value["3.1"]["comparability"] is None


def test_a_released_report_is_withdrawn_by_a_new_draft_from_the_standing_values(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "redraft")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    report_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    # Nothing was replaced: a redraft is not the way to revise this report.
    not_needed = client.post(f"/api/v1/reports/{report_id}/redraft")
    assert not_needed.status_code == 409
    assert not_needed.json()["error"]["detail"].startswith("redraft_not_needed")

    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    switch_role(
        client,
        admin_session,
        email="director-redraft@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    token = client.post(f"/api/v1/reports/{report_id}/release").json()["patient_access_token"]
    access = {"tenant": str(tenant.id), "token": token}
    assert client.post("/api/v1/patient-view", json=access).status_code == 200
    # The gate role does not author: a new draft is care staff's step.
    assert client.post(f"/api/v1/reports/{report_id}/redraft").status_code == 403

    login(client, "redraft@synthetic.example")
    select_tenant(client, tenant.id)
    _ldt(client, pid, _ldl("3.6", status="K"))
    _decide(client, _queue(client)[0]["observation_id"], "publish")

    view = client.get(f"/api/v1/reports/{report_id}").json()
    assert (view["status"], view["cites_replaced_evidence"]) == ("released", True)
    # Until someone acts, the released version is still what the patient sees.
    assert client.post("/api/v1/patient-view", json=access).status_code == 200

    # It discards the current wording and withdraws a released version: the clinician's step.
    switch_role(
        client,
        admin_session,
        email="assistant-redraft@synthetic.example",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    assert client.post(f"/api/v1/reports/{report_id}/redraft").status_code == 403
    assert client.post("/api/v1/patient-view", json=access).status_code == 200
    login(client, "redraft@synthetic.example")
    select_tenant(client, tenant.id)

    redrafted = client.post(f"/api/v1/reports/{report_id}/redraft")
    assert redrafted.status_code == 200, redrafted.text
    body = redrafted.json()
    assert (body["status"], body["version_no"], body["cites_replaced_evidence"]) == (
        "draft_generated",
        2,
        False,
    )
    assert [e["value"] for st in body["statements"] for e in st["evidence"]] == ["3.6"]
    # Patient access is withdrawn until the new version is approved and released again.
    assert client.post("/api/v1/patient-view", json=access).status_code == 404
    # The released version is a preserved record.
    versions = admin_session.execute(
        select(ReportVersion.version_no, ReportVersion.status)
        .where(ReportVersion.report_id == uuid.UUID(report_id))
        .order_by(ReportVersion.version_no)
    ).all()
    assert [(n, st.value) for n, st in versions] == [(1, "released"), (2, "draft_generated")]
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "report.redrafted")
    ).scalar_one()
    assert audit.detail == {"version_no": 2, "patient_access_withdrawn": True}
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200


def test_a_draft_whose_only_statement_was_replaced_has_a_way_on(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "wayon")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    report_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    _ldt(client, pid, _ldl("3.6", status="K"))
    _decide(client, _queue(client)[0]["observation_id"], "publish")

    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 409
    body = client.post(f"/api/v1/reports/{report_id}/redraft").json()
    assert (body["status"], body["version_no"]) == ("draft_generated", 2)
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200


def test_a_day_only_and_a_timed_value_of_one_day_are_not_a_change_either(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "nodelta2")
    pid = _patient(client)
    _enter(client, pid, _value("2.8"))
    timed = _enter(client, pid, _value("3.1", at="2025-06-10T06:00:00Z", date_only=False))
    _decide(client, timed["observation_ids"][0], "publish")
    later = _enter(client, pid, _value("3.4", at="2025-09-01T00:00:00Z"))["observation_ids"][0]

    by_id = {p["observation_id"]: p for p in _timeline(client, pid)}
    # The matcher calls this pair "possibly one sample"; the timeline must not call it a change.
    assert by_id[timed["observation_ids"][0]]["delta_vs_previous"] is None
    assert Decimal(by_id[later]["delta_vs_previous"]) == Decimal("0.3")


def test_a_value_is_proposed_for_replacement_at_most_once(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "once")
    pid = _patient(client)
    _ldt(client, pid, _ldl("2.8"))
    # Two corrections whose names each match the held value but not each other (the first by
    # its spelling, the second by the metric code).
    _ldt(client, pid, lab_test("LDL", "LDL  Cholesterol", value="3.6", unit="mmol/L", status="K"))
    _ldt(client, pid, lab_test("LDL", "LDL", value="3.4", unit="mmol/L", status="K"))
    proposals = {
        q["original_value"]: q for q in _queue(client) if q["reason"] == "corrected_result"
    }
    assert proposals["3.6"]["replaces"]["original_value"] == "2.8"
    assert proposals["3.4"]["replaces"] is None
    assert "ambiguous_correction" in _reasons(client, proposals["3.4"]["observation_id"])


def test_the_queue_shows_the_value_a_decision_will_replace_whatever_it_matches(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "stored")
    pid = _patient(client)
    target = uuid.UUID(_enter(client, pid, _value("2.8"))["observation_ids"][0])
    # A row that did not come from the matcher: its target was sampled on another day.
    item_id = _pending_correction(
        admin_session, tenant, pid, target, observed_at=datetime(2025, 7, 1, tzinfo=UTC)
    )
    (item,) = _queue(client)
    assert item["review_item_id"] == item_id
    # The decision acts on the stored link, so that is what the reviewer is shown.
    assert item["replaces"]["observation_id"] == str(target)
    assert item["related"] == []


def test_two_decisions_on_one_value_take_turns(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "turns")
    pid = _patient(client)
    # Two reasons, two review items, one observation.
    observation = _enter(client, pid, _value("2.8"), _value("2,8", unit="µkat/L"))[
        "observation_ids"
    ][1]
    item_ids = [q["review_item_id"] for q in _queue(client)]
    assert len(item_ids) == 2

    matching.lock_patient_record(admin_session, uuid.UUID(pid))
    codes: list[int] = []

    def publish(item_id: str) -> None:
        resp = client.post(f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"})
        codes.append(resp.status_code)

    workers = [threading.Thread(target=publish, args=(item_id,)) for item_id in item_ids]
    for worker in workers:
        worker.start()
    workers[0].join(0.7)
    assert all(w.is_alive() for w in workers) and not codes  # both wait for the patient's lock
    admin_session.rollback()
    for worker in workers:
        worker.join(15)
    # Side by side, each would see the other's item as still open and leave the value
    # pending with no open item.
    assert codes == [200, 200]
    assert _queue(client) == []
    stored = admin_session.get(Observation, uuid.UUID(observation))
    assert stored is not None and stored.review_status == ReviewStatus.PUBLISHED
