"""Which values an import publishes without a human.

The import normalizes — and so publishes unseen — six names, as norm-1 did. Every other value
waits for a clinician, whatever the catalog knows about its name. The catalog says what a
name may mean; it does not know the specimen, the method, whether the number is plausible, or
who typed it. An assistant may enter values and may not resolve the review queue: what the
import publishes by itself is what reaches a report with no clinician having looked at it.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from hadp_api.modules.enums import ReviewStatus, Role
from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.kpi.service import seed_terminology
from hadp_api.modules.observations.models import Observation
from tests.helpers import login_as
from tests.ldt_fixtures import TRAILER, header, lab_test, ldt_file, report

SIX = set(normalize_mod._AUTOMATIC)


def _staff(client, admin_session, slug: str, role: Role):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}@synthetic.example",
        tenant_name=f"Gate {slug}",
        tenant_slug=f"gate-{slug}",
        role=role,
    )


def _patient(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": "Synthetic Gate"})
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def test_an_assistant_typing_any_catalog_name_publishes_only_the_six(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Every alias the catalog holds, typed in the catalog's own unit — the best case for the
    import — on a day of its own, so nothing is held back as a duplicate."""
    _staff(client, admin_session, "assistant", Role.ASSISTANT)
    pid = _patient(client)
    terminology = seed_terminology()
    first = date(2025, 1, 1)
    values = [
        {
            "original_name": alias,
            "original_value": "4.2",
            "original_unit": terminology.resolve(alias).canonical_unit,  # type: ignore[union-attr]
            "reference_low": "1",
            "reference_high": "9",
            "observed_at": f"{first + timedelta(days=index)}T00:00:00Z",
            "observed_at_is_date_only": True,
        }
        for index, alias in enumerate(sorted(terminology._terms))
    ]
    assert len(values) > 100

    result = client.post(f"/api/v1/patients/{pid}/imports", json={"values": values})

    assert result.status_code == 201, result.text
    stored = admin_session.execute(select(Observation)).scalars().all()
    published = {o.original_name for o in stored if o.review_status == ReviewStatus.PUBLISHED}
    assert published == SIX
    assert result.json()["published_count"] == len(SIX)
    assert result.json()["review_count"] == len(values) - len(SIX)
    for o in stored:
        if o.original_name not in SIX:
            assert o.review_status == ReviewStatus.PENDING, o.original_name
            assert (o.normalized_value, o.metric_code) == (None, None), o.original_name
            assert o.kpi_code == terminology.resolve(o.original_name).kpi_code  # type: ignore[union-attr]
    # The assistant cannot be the human who looks: the queue is the clinician's to resolve.
    item_id = result.json()["review_item_ids"][0]
    refused = client.post(f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"})
    assert refused.status_code == 403


def test_implausible_and_specimen_bound_values_wait_for_a_clinician(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Values a human would stop at: a body weight of 820 kg, a creatinine that can only be
    urine, a research assay. All are catalog names in catalog units."""
    _staff(client, admin_session, "implausible", Role.ASSISTANT)
    pid = _patient(client)
    day = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}
    rows = [
        ("Body weight", "820", "kg"),
        ("Creatinine", "9500", "umol/L"),
        ("Albumin", "12", "g/L"),
        ("Interleukin-6", "7.2", "pg/mL"),
        ("Plasma phosphorylated tau 217", "0.9", "pg/mL"),
        ("Calcium", "2.4", "mmol/L"),
    ]

    result = client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "values": [
                {"original_name": n, "original_value": v, "original_unit": u, **day}
                for n, v, u in rows
            ]
        },
    )

    assert result.status_code == 201, result.text
    assert (result.json()["published_count"], result.json()["review_count"]) == (0, len(rows))
    timeline = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert {p["review_status"] for p in timeline} == {"pending"}
    # Nothing that is not published can be drafted into a report.
    assert client.post(f"/api/v1/patients/{pid}/reports").status_code == 422


def test_a_file_that_names_the_specimen_publishes_nothing_but_the_six(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """The CSV reader knows a closed list of columns and ignores the rest — a "Material" column
    among them. A calcium from spot urine is therefore just "Calcium" to the import."""
    _staff(client, admin_session, "specimen", Role.CLINICIAN)
    pid = _patient(client)
    csv = (
        "Analyt;Material;Wert;Einheit;Abnahmedatum\n"
        "Calcium;Spontanurin;2,4;mmol/l;10.06.2025\n"
        "Creatinine;Urin;9500;µmol/l;10.06.2025\n"
        "Albumin;Aszites;12;g/l;10.06.2025\n"
        "Folate;Erythrozyten;890;nmol/l;10.06.2025\n"
        "LDL Cholesterol;Serum;2,8;mmol/l;10.06.2025\n"
    ).encode()
    uploaded = client.post(
        f"/api/v1/patients/{pid}/documents", files={"file": ("labs", csv, "text/csv")}
    )
    assert uploaded.status_code == 201, uploaded.text

    result = client.post(f"/api/v1/patients/{pid}/documents/{uploaded.json()['id']}/import")

    assert result.status_code == 201, result.text
    stored = admin_session.execute(select(Observation)).scalars().all()
    assert {o.original_name for o in stored if o.review_status == ReviewStatus.PUBLISHED} == {
        "LDL Cholesterol"
    }
    assert len(stored) == 5


def test_the_review_queue_shows_the_bounds_publishing_puts_into_effect(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """Publishing a value puts its reference bounds into effect: a position against them is
    stated in the tables and in a report. The reviewer sees the bounds the platform holds —
    and sees that it holds none where the source's could not be read."""
    _staff(client, admin_session, "queue", Role.CLINICIAN)
    pid = _patient(client)
    day = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}
    values = [
        ("Ferritin", "85", "ng/mL", "30", "400"),
        ("Leukozyten", "950", "/µl", "4.000", "10.000"),
        ("LDL Cholesterol", "-1", "mg/dL", "0", "116"),
    ]
    result = client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "values": [
                {
                    "original_name": name,
                    "original_value": value,
                    "original_unit": unit,
                    "reference_low": low,
                    "reference_high": high,
                    **day,
                }
                for name, value, unit, low, high in values
            ]
        },
    )
    assert result.status_code == 201, result.text

    items = client.get("/api/v1/review-items").json()

    def held(item: dict) -> tuple:  # type: ignore[type-arg]
        return (
            item["reference_low"],
            item["reference_high"],
            item["reference_unit"],
            item["reference_converted"],
        )

    by_reason = {(i["original_name"], i["reason"]): held(i) for i in items}
    assert by_reason == {
        ("Ferritin", "unmapped_metric"): ("30", "400", "ng/mL", False),
        # "4.000 – 10.000" reads two ways: no bound is held, and the reason says why.
        ("Leukozyten", "unmapped_metric"): (None, None, "/µl", False),
        ("Leukozyten", "unparseable_reference"): (None, None, "/µl", False),
        # Normalized: the bounds are the source's, converted with the value's own factor.
        ("LDL Cholesterol", "impossible_value"): ("0.0000000", "2.9997368", "mmol/L", True),
    }


def test_a_laboratory_file_publishes_nothing_but_the_six(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """An LDT 2 report with names the catalog knows (they are spelled the same in German) and
    one of the six. The reader carries no specimen; the catalog's knowing a name is not a
    reason to publish a value unread."""
    _staff(client, admin_session, "ldt", Role.CLINICIAN)
    resp = client.post(
        "/api/v1/patients",
        json={"display_name": "Erika Mustermann (synthetic)", "date_of_birth": "1980-01-15"},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    data = ldt_file(
        header(),
        report(
            lab_test("CA", "Calcium", value="2.4", unit="mmol/L"),
            lab_test("ALB", "Albumin", value="12", unit="g/L"),
            lab_test("FERR", "Ferritin", value="85", unit="ug/L", low="30", high="400"),
            lab_test("B12", "Vitamin B12", value="310", unit="pmol/L"),
            lab_test("CYSC", "Cystatin C", value="0.9", unit="mg/L"),
            lab_test("IL6", "Interleukin-6", value="7.2", unit="pg/mL"),
            lab_test("LDL", "LDL Cholesterol", value="2.8", unit="mmol/L", low="0", high="3.0"),
        ),
        TRAILER,
    )
    uploaded = client.post(
        f"/api/v1/patients/{pid}/documents",
        files={"file": ("befund.ldt", data, "application/octet-stream")},
    )
    assert uploaded.status_code == 201, uploaded.text

    result = client.post(f"/api/v1/patients/{pid}/documents/{uploaded.json()['id']}/import")

    assert result.status_code == 201, result.text
    assert (result.json()["published_count"], result.json()["review_count"]) == (1, 6)
    stored = admin_session.execute(select(Observation)).scalars().all()
    assert {o.original_name for o in stored if o.review_status == ReviewStatus.PUBLISHED} == {
        "LDL Cholesterol"
    }


def test_the_same_values_sent_again_are_not_stored_again(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A file that arrives twice adds nothing — also for a value whose reference could not be
    read, or whose number reads two ways. (The reason the normalizer gives for an unreadable
    reference is its own; the readers' reason for several ranges in a source would make each
    copy a new value.)"""
    _staff(client, admin_session, "again", Role.CLINICIAN)
    pid = _patient(client)
    day = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}
    values = [
        {"original_name": n, "original_value": v, "original_unit": u, **bounds, **day}
        for n, v, u, bounds in (
            ("LDL Cholesterol", "2.8", "mmol/L", {"reference_low": "0", "reference_high": "3.0"}),
            ("Ferritin", "85", "ng/mL", {"reference_low": "30", "reference_high": "400"}),
            (
                "Leukozyten",
                "950",
                "/µl",
                {"reference_low": "4.000", "reference_high": "10.000"},
            ),
            ("Cystatin C", "0.9", "mg/l", {"reference_low": "1.2", "reference_high": "0.6"}),
            ("Thrombozyten", "98.000", "/µl", {}),
            ("TSH", "1.250", "mU/l", {"reference_low": "0.270", "reference_high": "4.200"}),
        )
    ]

    first = client.post(f"/api/v1/patients/{pid}/imports", json={"values": values}).json()
    stored = len(admin_session.execute(select(Observation)).scalars().all())
    open_items = len(client.get("/api/v1/review-items").json())
    for _ in range(2):
        again = client.post(f"/api/v1/patients/{pid}/imports", json={"values": values})
        assert again.status_code == 201, again.text
        assert again.json()["duplicate_count"] == len(values), again.json()
        assert (again.json()["published_count"], again.json()["review_count"]) == (0, 0)

    assert (first["published_count"], first["review_count"]) == (1, 5)
    assert stored == len(values)
    admin_session.expire_all()
    assert len(admin_session.execute(select(Observation)).scalars().all()) == stored
    assert len(client.get("/api/v1/review-items").json()) == open_items


def test_a_catalog_that_does_not_confirm_a_name_holds_its_values_and_says_so(  # type: ignore[no-untyped-def]
    client, admin_session, caplog: pytest.LogCaptureFixture
) -> None:
    """Through the import, against the database: with LDL retired in the catalog, an LDL value
    waits for a human, HbA1c is untouched — and the operator's log names the two names. The
    review queue alone would only say "not mapped"."""
    _staff(client, admin_session, "catalog", Role.CLINICIAN)
    pid = _patient(client)
    day = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}
    values = [
        {"original_name": "LDL Cholesterol", "original_value": "2.8", "original_unit": "mmol/L"},
        {"original_name": "HbA1c", "original_value": "5.4", "original_unit": "%"},
    ]
    admin_session.execute(
        text("UPDATE kpi_catalog SET status = 'deprecated' WHERE code = 'cardio.ldl_c'")
    )
    admin_session.commit()
    try:
        with caplog.at_level(logging.ERROR, logger="hadp_api.modules.imports.service"):
            result = client.post(
                f"/api/v1/patients/{pid}/imports",
                json={"values": [{**value, **day} for value in values]},
            )
    finally:
        admin_session.execute(
            text("UPDATE kpi_catalog SET status = 'active' WHERE code = 'cardio.ldl_c'")
        )
        admin_session.commit()

    assert result.status_code == 201, result.text
    stored = {
        o.original_name: o for o in admin_session.execute(select(Observation)).scalars().all()
    }
    ldl, hba1c = stored["LDL Cholesterol"], stored["HbA1c"]
    assert (ldl.review_status, ldl.normalized_value, ldl.kpi_code) == (
        ReviewStatus.PENDING,
        None,
        None,
    )
    assert ldl.numeric_value is not None
    assert (hba1c.review_status, hba1c.kpi_code) == (ReviewStatus.PUBLISHED, "metabolic.hba1c")
    (said,) = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert "2 of the import's 6 automatic names (ldl, ldl cholesterol)" in said
    # With the catalog as seeded nothing is said.
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="hadp_api.modules.imports.service"):
        client.post(
            f"/api/v1/patients/{pid}/imports",
            json={
                "values": [
                    {
                        **values[0],
                        "observed_at": "2025-07-01T00:00:00Z",
                        **{"observed_at_is_date_only": True},
                    }
                ]
            },
        )
    assert [r for r in caplog.records if r.levelno == logging.ERROR] == []
