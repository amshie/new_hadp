"""Report statements through the product: import -> (review) -> draft -> release -> patient view.

The wording itself is pinned in test_narrative_wording.py. These tests pin what reaches it:
the source's own value, whether the platform converted the unit, the reference bounds it
holds, and the sampling time in the configured zone — for the cases where a statement used to
say something the record does not support.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hadp_api.modules.enums import Role
from hadp_api.modules.reports import evidence
from tests.helpers import grant_release_consent, login_as, switch_role

DAY = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}


def _clinician(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}@synthetic.example",
        tenant_name=f"Statements {slug}",
        tenant_slug=f"statements-{slug}",
        role=Role.CLINICIAN,
    )


def _import(client, values: list[dict], *, publish_review: bool = False) -> str:  # type: ignore[no-untyped-def]
    """Create a patient, import the values, optionally publish what went to review."""
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic Statements"}).json()[
        "id"
    ]
    result = client.post(f"/api/v1/patients/{pid}/imports", json={"values": values})
    assert result.status_code == 201, result.text
    for item_id in result.json()["review_item_ids"]:
        assert publish_review, "value went to review unexpectedly"
        resolved = client.post(
            f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"}
        )
        assert resolved.status_code == 200, resolved.text
    return pid


def _draft(client, pid: str) -> dict:  # type: ignore[no-untyped-def]
    draft = client.post(f"/api/v1/patients/{pid}/reports")
    assert draft.status_code == 201, draft.text
    return draft.json()


def test_an_analyte_the_terminology_does_not_know_is_stated_as_the_source_wrote_it(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """Ferritin is not in the terminology: no normalized value exists. The source still wrote
    85 ng/mL — the statement says that, and the evidence under it shows it."""
    _clinician(client, admin_session, "unmapped")
    pid = _import(
        client,
        [
            {
                "original_name": "Ferritin",
                "original_value": "85",
                "original_unit": "ng/mL",
                "reference_low": "30",
                "reference_high": "400",
                **DAY,
            }
        ],
        publish_review=True,
    )

    report = _draft(client, pid)

    assert (report["narrative_provider"], report["narrative_version"]) == (
        "deterministic",
        "narr-2",
    )
    (statement,) = report["statements"]
    assert statement["text"] == "Ferritin am 10.06.2025: 85 ng/mL."
    (cited,) = statement["evidence"]
    assert (cited["original_value"], cited["original_unit"]) == ("85", "ng/mL")
    assert cited["value"] is None  # no normalized form — and the view does not pretend one


def test_a_converted_unit_shows_the_source_value_and_names_the_conversion(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "converted")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "130",
                "original_unit": "mg/dL",
                "reference_low": "0",
                "reference_high": "116",
                **DAY,
            }
        ],
    )

    (statement,) = _draft(client, pid)["statements"]

    assert statement["text"] == (
        "LDL Cholesterol am 10.06.2025: 130 mg/dL (umgerechnet: 3.361774 mmol/L). "
        "Referenzintervall der Quelle (umgerechnet): 0 bis 2.9997368 mmol/L. "
        "Der Wert liegt über dem Referenzintervall der Quelle."
    )


def test_the_same_unit_in_another_spelling_is_not_a_conversion(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "spelling")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "2,80",
                "original_unit": "mmol/l",
                "reference_low": "0",
                "reference_high": "3,0",
                **DAY,
            }
        ],
    )

    (statement,) = _draft(client, pid)["statements"]

    assert statement["text"] == (
        "LDL Cholesterol am 10.06.2025: 2,80 mmol/l. Referenzintervall der Quelle: 0 bis 3 mmol/L."
    )


def test_an_unreadable_bound_is_not_turned_into_a_one_sided_interval(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The source gave two bounds; one could not be read. The statement names the bound the
    platform holds and claims neither an interval "up to 3" nor a position against it."""
    _clinician(client, admin_session, "bound")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "0.2",
                "original_unit": "mmol/L",
                "reference_low": "0.5*",
                "reference_high": "3.0",
                **DAY,
            }
        ],
        publish_review=True,
    )

    (statement,) = _draft(client, pid)["statements"]

    assert statement["text"] == (
        "LDL Cholesterol am 10.06.2025: 0.2 mmol/L. "
        "Referenzintervall der Quelle: obere Grenze 3 mmol/L."
    )


def test_a_timed_sample_is_written_in_the_configured_zone(
    client, admin_session, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """The zone comes from the setting, not from the server's or the database session's zone."""
    monkeypatch.setattr(
        evidence, "get_settings", lambda: SimpleNamespace(lab_local_timezone="Asia/Tokyo")
    )
    _clinician(client, admin_session, "zone")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "2.8",
                "original_unit": "mmol/L",
                "observed_at": "2025-06-10T06:30:00Z",
            },
            {
                "original_name": "HbA1c",
                "original_value": "5.4",
                "original_unit": "%",
                # Late evening in UTC: a day-only value stays the day the source named.
                "observed_at": "2025-06-10T23:00:00Z",
                "observed_at_is_date_only": True,
            },
        ],
    )

    texts = sorted(s["text"] for s in _draft(client, pid)["statements"])

    assert texts == [
        "HbA1c am 10.06.2025: 5.4 %.",
        "LDL Cholesterol am 10.06.2025 um 15:30 Uhr (JST): 2.8 mmol/L.",
    ]


def test_the_patient_reads_the_statement_as_generated(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Approve, release, open the patient view: the German statement, and nothing English."""
    _user, tenant = _clinician(client, admin_session, "patient")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "3.6",
                "original_unit": "mmol/L",
                "reference_low": "0",
                "reference_high": "3.0",
                **DAY,
            }
        ],
    )
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    report_id = _draft(client, pid)["report_id"]
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email="md-patient@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    release = client.post(f"/api/v1/reports/{report_id}/release")
    assert release.status_code == 200, release.text

    view = client.post(
        "/api/v1/patient-view",
        json={"tenant": str(tenant.id), "token": release.json()["patient_access_token"]},
    )

    assert view.status_code == 200, view.text
    assert [s["text"] for s in view.json()["statements"]] == [
        "LDL Cholesterol am 10.06.2025: 3.6 mmol/L. "
        "Referenzintervall der Quelle: 0 bis 3 mmol/L. "
        "Der Wert liegt über dem Referenzintervall der Quelle."
    ]
