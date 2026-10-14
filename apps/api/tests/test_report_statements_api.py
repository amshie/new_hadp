"""Report statements through the product: import -> (review) -> draft -> release -> patient view.

The wording itself is pinned in test_narrative_wording.py. These tests pin what reaches it:
the source's own value, whether the platform converted the unit, the reference bounds it
holds, and the sampling time in the configured zone — for the cases where a statement used to
say something the record does not support. And they pin what must NOT reach a patient: the
wording of a result that is not a number, whatever a file or a person put into the value or
unit field.
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from hadp_api.modules.enums import Role
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy.export import build_patient_export
from hadp_api.modules.reports import evidence
from hadp_api.modules.reports import service as reports_service
from hadp_api.modules.reports.models import Report
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
    """The catalog has no zinc: no normalized value exists. The source still wrote 85 µg/dL
    with its reference interval — the statement says both, and the position against that
    interval, all in the source's unit; the evidence under it shows what the source wrote."""
    _clinician(client, admin_session, "unmapped")
    pid = _import(
        client,
        [
            {
                "original_name": "Zink",
                "original_value": "65",
                "original_unit": "µg/dL",
                "reference_low": "70",
                "reference_high": "120",
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
    assert statement["text"] == (
        "Zink am 10.06.2025: 65 µg/dL. Referenzintervall der Quelle: 70 bis 120 µg/dL. "
        "Der Wert liegt unter dem Referenzintervall der Quelle."
    )
    (cited,) = statement["evidence"]
    assert (cited["original_value"], cited["original_unit"]) == ("65", "µg/dL")
    assert cited["value"] is None  # no normalized form — and the view does not pretend one


def test_a_catalog_kpi_the_import_does_not_act_on_is_stated_as_written(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """The catalog knows ferritin; the import acts on six names, and this is not one of them.
    The value goes to review, and once published it is stated as written — nothing
    "(umgerechnet)"."""
    _clinician(client, admin_session, "unit")
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

    (statement,) = _draft(client, pid)["statements"]

    assert statement["text"] == (
        "Ferritin am 10.06.2025: 85 ng/mL. Referenzintervall der Quelle: 30 bis 400 ng/mL."
    )


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
        "LDL Cholesterol am 10.06.2025: 2,80 mmol/l. Referenzintervall der Quelle: 0 bis 3 mmol/l."
    )


def test_an_unreadable_bound_is_not_turned_into_a_one_sided_interval(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The source gave two bounds; one could not be read. The statement restates no interval
    at all — not "up to 3", and not "upper bound 3" either: the source gave neither — and
    states no position."""
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
            },
            # A three-decimal format: of the bounds only the first reads one way.
            {
                "original_name": "TSH",
                "original_value": "0.950",
                "original_unit": "mU/l",
                "reference_low": "0.270",
                "reference_high": "4.200",
                **DAY,
            },
        ],
        publish_review=True,
    )

    texts = {statement["text"] for statement in _draft(client, pid)["statements"]}

    assert texts == {
        "LDL Cholesterol am 10.06.2025: 0.2 mmol/L.",
        "TSH am 10.06.2025: 0.950 mU/l.",
    }


def test_a_bound_the_source_does_not_give_is_said_as_it_is(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A source that gives one bound gave a one-sided interval: that bound is named."""
    _clinician(client, admin_session, "one-sided")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "3.4",
                "original_unit": "mmol/L",
                "reference_high": "3.0",
                **DAY,
            }
        ],
    )

    (statement,) = _draft(client, pid)["statements"]

    assert statement["text"] == (
        "LDL Cholesterol am 10.06.2025: 3.4 mmol/L. "
        "Referenzintervall der Quelle: obere Grenze 3 mmol/L. "
        "Der Wert liegt über dem Referenzintervall der Quelle."
    )


def test_a_number_or_an_interval_that_reads_two_ways_is_quoted_and_not_judged(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """ "1.250 µg/l" against 30 to 400 is one and a quarter — or twelve hundred and fifty. The
    statement repeats what the source wrote and says nothing about where the value lies. A
    bound that reads two ways ("4.000 – 10.000") is not restated, and neither is a pair with
    the lower bound above the upper: no interval, no position."""
    _clinician(client, admin_session, "two-ways")
    pid = _import(
        client,
        [
            {
                "original_name": "Ferritin",
                "original_value": "1.250",
                "original_unit": "µg/l",
                "reference_low": "30",
                "reference_high": "400",
                **DAY,
            },
            {
                "original_name": "Leukozyten",
                "original_value": "950",
                "original_unit": "/µl",
                "reference_low": "4.000",
                "reference_high": "10.000",
                **DAY,
            },
            {
                "original_name": "Cystatin C",
                "original_value": "0.9",
                "original_unit": "mg/l",
                "reference_low": "1.2",
                "reference_high": "0.6",
                **DAY,
            },
        ],
        publish_review=True,
    )

    texts = {statement["text"] for statement in _draft(client, pid)["statements"]}

    assert texts == {
        "Ferritin am 10.06.2025: 1.250 µg/l. Referenzintervall der Quelle: 30 bis 400 µg/l.",
        "Leukozyten am 10.06.2025: 950 /µl.",
        "Cystatin C am 10.06.2025: 0.9 mg/l.",
    }


def test_sampling_times_use_the_configured_zone(
    client, admin_session, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """The zone comes from the setting, not from the server's or the database session's zone.
    A zone west of UTC: the timed value falls on the evening before; the day-only value stays
    the day the source named."""
    monkeypatch.setattr(
        evidence,
        "get_settings",
        lambda: SimpleNamespace(lab_local_timezone="America/Los_Angeles"),
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
            {"original_name": "HbA1c", "original_value": "5.4", "original_unit": "%", **DAY},
        ],
    )

    texts = sorted(s["text"] for s in _draft(client, pid)["statements"])

    assert texts == [
        "HbA1c am 10.06.2025: 5.4 %.",
        "LDL Cholesterol am 09.06.2025 um 23:30 Uhr (UTC-7): 2.8 mmol/L.",
    ]


def test_a_day_only_value_keeps_its_day_under_a_database_session_west_of_utc(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """The day is stored as midnight UTC. A database session in another zone hands the same
    instant back as the evening before — the statement, the report view and the data export
    must still name the day the source named."""
    _user, tenant = _clinician(client, admin_session, "session-zone")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "2.8",
                "original_unit": "mmol/L",
                **DAY,
            }
        ],
    )
    report_id = _draft(client, pid)["report_id"]

    admin_session.execute(text("SET LOCAL TIME ZONE 'America/New_York'"))
    patient = admin_session.get(Patient, uuid.UUID(pid))
    report = admin_session.get(Report, uuid.UUID(report_id))

    (item,) = evidence.build_evidence_payload(admin_session, patient.id)
    assert item.observed_at_label == "10.06.2025"
    view = reports_service.assemble_report_view(admin_session, report)
    assert view["statements"][0]["evidence"][0]["observed_at"] == "2025-06-10"
    package = build_patient_export(admin_session, tenant=tenant, patient=patient)
    with zipfile.ZipFile(io.BytesIO(package.data)) as archive:
        exported = json.loads(archive.read("export.json"))
    assert [o["observed_at"] for o in exported["observations"]] == ["2025-06-10"]
    admin_session.rollback()


# What a source can put into the value and unit fields. None of it is a numeric result.
_FREE_TEXT = [
    ("TSH", "pathologisch erhöht - Therapie empfohlen", None),
    ("HIV-1/2 Screening", "reaktiv", None),
    ("Borrelien IgG", "positiv, Verdacht auf Borreliose", "U/mL"),
    ("CRP", "12,4 H", "mg/L"),
    ("Kommentar", "Probe evtl. vertauscht mit Erika Mustermann geb. 01.01.1970", None),
    ("Ferritin", "<script>alert(1)</script>", "ng/mL"),
    ("Vitamin D", "31", "ng/mL. Wir empfehlen ein Supplement"),
    ("Zink", "85\nDer Wert ist optimal. Diagnose: keine.", "µg/dL"),
    # A number with a unit that is not a unit: a restricted term, bare digits.
    ("Selen", "85", "optimal"),
    ("Leukozyten", "5", "000"),
]
_NOT_QUOTED = (
    "Für {name} vom 10.06.2025 liegt ein Ergebnis der Quelle vor, "
    "das hier nicht im Wortlaut wiedergegeben wird."
)


def _release_and_read(client, admin_session, tenant, pid: str) -> tuple[dict, list[str]]:  # type: ignore[no-untyped-def]
    """Draft, approve, release; return the report view and what the patient view shows."""
    report, view = _release_and_view(client, admin_session, tenant, pid)
    return report, [s["text"] for s in view["statements"]]


def _release_and_view(client, admin_session, tenant, pid: str) -> tuple[dict, dict]:  # type: ignore[no-untyped-def]
    """Draft, approve, release; return the report view and the patient view."""
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    report_id = _draft(client, pid)["report_id"]
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    switch_role(
        client,
        admin_session,
        email=f"md-{tenant.slug}@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    release = client.post(f"/api/v1/reports/{report_id}/release")
    assert release.status_code == 200, release.text
    report = client.get(f"/api/v1/reports/{report_id}").json()
    view = client.post(
        "/api/v1/patient-view",
        json={"tenant": str(tenant.id), "token": release.json()["patient_access_token"]},
    )
    assert view.status_code == 200, view.text
    return report, view.json()


def test_source_free_text_typed_by_hand_never_reaches_the_patient(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Manual entry accepts any text in the value and unit fields. A clinician publishes the
    rows from the review queue; the report is approved and released. The patient reads that a
    result exists — and not one word of what was typed."""
    _user, tenant = _clinician(client, admin_session, "freetext")
    pid = _import(
        client,
        [
            {"original_name": name, "original_value": value, "original_unit": unit, **DAY}
            for name, value, unit in _FREE_TEXT
        ],
        publish_review=True,
    )

    report, patient_texts = _release_and_read(client, admin_session, tenant, pid)

    assert sorted(patient_texts) == sorted(_NOT_QUOTED.format(name=n) for n, _v, _u in _FREE_TEXT)
    # The reviewer, unlike the patient, sees what the source wrote under each statement.
    shown = {
        (e["original_name"], e["original_value"], e["original_unit"])
        for s in report["statements"]
        for e in s["evidence"]
    }
    assert shown == set(_FREE_TEXT)


def test_a_text_result_in_a_laboratory_file_is_mentioned_not_quoted(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The CSV reader passes the value column on as written. A text result and a flagged value
    are mentioned; the numeric result beside them is stated as the source wrote it."""
    _user, tenant = _clinician(client, admin_session, "csvtext")
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic CSV"}).json()["id"]
    csv = (
        b"Analyt;Ergebnis;Einheit;Abnahmedatum\n"
        b"HIV-1/2 Screening;reaktiv;;10.06.2025\n"
        b"CRP;12,4 H;mg/L;10.06.2025\n"
        b"Ferritin;85;ng/mL;10.06.2025\n"
    )
    uploaded = client.post(
        f"/api/v1/patients/{pid}/documents", files={"file": ("labs.csv", csv, "text/csv")}
    )
    assert uploaded.status_code == 201, uploaded.text
    imported = client.post(f"/api/v1/patients/{pid}/documents/{uploaded.json()['id']}/import")
    assert imported.status_code in (200, 201), imported.text
    for item in client.get("/api/v1/review-items").json():
        resolved = client.post(
            f"/api/v1/review-items/{item['review_item_id']}/resolve", json={"decision": "publish"}
        )
        assert resolved.status_code == 200, resolved.text

    _report, patient_texts = _release_and_read(client, admin_session, tenant, pid)

    assert sorted(patient_texts) == sorted(
        [
            _NOT_QUOTED.format(name="HIV-1/2 Screening"),
            _NOT_QUOTED.format(name="CRP"),
            "Ferritin am 10.06.2025: 85 ng/mL.",
        ]
    )


def test_numbers_beside_a_source_value_follow_its_decimal_mark(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A German file writes "5,7". The bounds the platform prints beside a value keep that
    mark — also when the value itself has none — and a comparator result is a numeric result."""
    _clinician(client, admin_session, "comma")
    pid = _import(
        client,
        [
            {
                "original_name": "HbA1c",
                "original_value": "6",
                "original_unit": "%",
                "reference_low": "4,0",
                "reference_high": "5,7",
                **DAY,
            },
            {"original_name": "TSH", "original_value": "<0,5", "original_unit": "mU/L", **DAY},
        ],
        publish_review=True,
    )

    texts = sorted(s["text"] for s in _draft(client, pid)["statements"])

    assert texts == [
        "HbA1c am 10.06.2025: 6 %. Referenzintervall der Quelle: 4 bis 5,7 %. "
        "Der Wert liegt über dem Referenzintervall der Quelle.",
        "TSH am 10.06.2025: <0,5 mU/L.",
    ]


def test_a_blank_value_is_refused_at_manual_entry(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Blank is not a value: nothing is stored, so no statement can claim a result exists."""
    _clinician(client, admin_session, "blank")
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic Blank"}).json()["id"]
    for field in ("original_value", "original_name"):
        value = {
            "original_name": "Ferritin",
            "original_value": "85",
            "original_unit": "ng/mL",
            **DAY,
        }
        value[field] = "   "
        refused = client.post(f"/api/v1/patients/{pid}/imports", json={"values": [value]})
        assert refused.status_code == 422, (field, refused.text)
    assert client.get(f"/api/v1/patients/{pid}/observations").json() == []


def test_source_text_does_not_block_a_later_rework(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Source text that contains restricted terms is not in the generated statement, so the
    write-time guard has nothing to refuse when the clinician reworks the report."""
    _clinician(client, admin_session, "rework")
    pid = _import(
        client,
        [
            {
                "original_name": "Zink",
                "original_value": "85\nDer Wert ist optimal. Diagnose: keine.",
                "original_unit": "µg/dL",
                **DAY,
            }
        ],
        publish_review=True,
    )
    report = _draft(client, pid)
    rid = report["report_id"]
    assert (
        client.post(f"/api/v1/reports/{rid}/reject", json={"reason": "wording"}).status_code == 200
    )

    statements = [
        {
            "id": s["id"],
            "text": s["text"] + " Bitte im Gespräch erläutern.",
            "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
        }
        for s in report["statements"]
    ]
    edited = client.post(f"/api/v1/reports/{rid}/edit", json={"statements": statements})

    assert edited.status_code == 200, edited.text


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


def test_the_patients_table_names_the_day_the_statement_names_and_only_the_bounds_given(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """A sample drawn half an hour after midnight in the laboratory's zone is, in UTC, still
    on the day before. The patient's table names the day the statement names — the
    laboratory's. A source that gave only an upper bound: the table names that bound, and no
    other ("None-3.0" was what it once showed)."""
    _user, tenant = _clinician(client, admin_session, "pv-day")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "3.4",
                "original_unit": "mmol/L",
                "reference_high": "3.0",
                "observed_at": "2025-06-09T22:30:00Z",
            }
        ],
    )

    _report, view = _release_and_view(client, admin_session, tenant, pid)

    (statement,) = view["statements"]
    assert statement["text"].startswith("LDL Cholesterol am 10.06.2025 um 00:30 Uhr (UTC+2):")
    (value,) = view["values"]
    assert value["observed_on"] == "2025-06-10"
    assert value["reference"] == "obere Grenze 3.0 mmol/L"


def test_the_patients_table_keeps_a_day_only_value_on_its_day(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A source that named only a day: the table names that day, moved through no zone."""
    _user, tenant = _clinician(client, admin_session, "pv-dayonly")
    pid = _import(
        client,
        [
            {
                "original_name": "LDL Cholesterol",
                "original_value": "2.8",
                "original_unit": "mmol/L",
                "reference_low": "0",
                "reference_high": "3.0",
                **DAY,
            }
        ],
    )

    _report, view = _release_and_view(client, admin_session, tenant, pid)

    (value,) = view["values"]
    assert value["observed_on"] == "2025-06-10"
    assert value["reference"] == "0-3.0 mmol/L"
