"""Milestone 0.5 exit criteria — the thin end-to-end vertical spike.

One synthetic lab value travels: upload -> normalized observation -> clinician timeline
-> source-grounded draft -> clinician approval -> patient view, on synthetic data, with
NO patient release of unapproved content. Every module is crossed once.
"""

from __future__ import annotations

from hadp_api.modules.enums import Role
from tests.helpers import grant_release_consent, login_as


def test_full_happy_path_crosses_every_module(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="spike@synthetic.example",
        tenant_name="Spike Clinic",
        tenant_slug="spike-clinic",
        role=Role.CLINICIAN,
    )

    # 1) create a synthetic patient
    patient_id = client.post("/api/v1/patients", json={"display_name": "Spike Patient"}).json()[
        "id"
    ]

    # 2) upload a source document (stored before parsing; idempotent)
    csv = b"name,value,unit,date\nLDL Cholesterol,2.8,mmol/L,2025-06-10\n"
    up = client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": ("labs.csv", csv, "text/csv")},
    )
    assert up.status_code == 201, up.text
    document = up.json()
    assert document["created"] is True
    # re-upload identical content -> idempotent (not created again)
    up2 = client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": ("labs.csv", csv, "text/csv")},
    )
    assert up2.json()["created"] is False

    # 3) import two values -> normalized, published observations
    imp = client.post(
        f"/api/v1/patients/{patient_id}/imports",
        json={
            "source_document_id": document["id"],
            "values": [
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "3.6",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-01-15T00:00:00Z",
                    "observed_at_is_date_only": True,
                    "reference_low": "0",
                    "reference_high": "3.0",
                },
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "2.8",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-06-10T00:00:00Z",
                    "observed_at_is_date_only": True,
                    "reference_low": "0",
                    "reference_high": "3.0",
                },
            ],
        },
    )
    assert imp.status_code == 201, imp.text
    assert imp.json()["published_count"] == 2
    assert imp.json()["review_count"] == 0

    # 4) clinician timeline shows provenance + deterministic delta
    timeline = client.get(f"/api/v1/patients/{patient_id}/observations").json()
    assert len(timeline) == 2
    latest = timeline[-1]
    assert latest["value"] == "2.8"
    assert latest["unit"] == "mmol/L"
    assert latest["delta_vs_previous"] == "-0.8"  # 2.8 - 3.6
    # Catalog linkage (Slice 2b): the normalizer resolved the canonical KPI + its domains.
    assert latest["kpi_code"] == "cardio.ldl_c"
    assert latest["kpi_primary_domain"] == "cardiovascular"
    assert latest["kpi_secondary_domains"] == []  # LDL-C has no secondary links
    # Comparability (Slice 3): laboratory KPI is method_aware, so the two LDL points are comparable.
    assert latest["comparability"] == "comparable"

    # 5) source-grounded draft: every statement is evidence-linked
    draft = client.post(f"/api/v1/patients/{patient_id}/reports")
    assert draft.status_code == 201, draft.text
    report = draft.json()
    report_id = report["report_id"]
    assert report["status"] == "draft_generated"
    assert len(report["statements"]) >= 1
    for stmt in report["statements"]:
        assert len(stmt["evidence"]) >= 1  # evidence viewable inline

    # 6) SAFETY: a patient cannot receive unapproved content — release before approve fails
    early_release = client.post(f"/api/v1/reports/{report_id}/release")
    assert early_release.status_code == 409

    # 7) clinician approval (attributable), then release
    approve = client.post(f"/api/v1/reports/{report_id}/approve")
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    # Release is consent-gated (fail-closed): grant report_release consent for this patient.
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=patient_id)
    release = client.post(f"/api/v1/reports/{report_id}/release")
    assert release.status_code == 200, release.text
    token = release.json()["patient_access_token"]

    # 8) patient view: RELEASED content only, via the scoped link
    view = client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}")
    assert view.status_code == 200, view.text
    assert view.json()["status"] == "released"
    assert view.json()["synthetic"] is True
    assert len(view.json()["statements"]) >= 1

    # 9) a wrong token reveals nothing
    bad = client.get(f"/api/v1/patient-view?tenant={tenant.id}&token=not-a-real-token")
    assert bad.status_code == 404


def test_editing_a_released_report_revokes_patient_access(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="edit@synthetic.example",
        tenant_name="Edit Clinic",
        tenant_slug="edit-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "Edit Patient"}).json()["id"]
    client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "values": [
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "2.8",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-06-10T00:00:00Z",
                    "observed_at_is_date_only": True,
                }
            ]
        },
    )
    report = client.post(f"/api/v1/patients/{pid}/reports").json()
    rid = report["report_id"]
    client.post(f"/api/v1/reports/{rid}/approve")
    grant_release_consent(admin_session, tenant_id=tenant.id, patient_id=pid)
    token = client.post(f"/api/v1/reports/{rid}/release").json()["patient_access_token"]

    # The released report is viewable by the patient.
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 200

    # Edit after release -> new draft version, prior approval invalidated, access retracted.
    statements = [
        {
            "id": s["id"],
            "text": s["text"] + " (edited)",
            "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
        }
        for s in report["statements"]
    ]
    edited = client.post(f"/api/v1/reports/{rid}/edit", json={"statements": statements})
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "draft_edited"

    # The previously valid patient link no longer works.
    assert client.get(f"/api/v1/patient-view?tenant={tenant.id}&token={token}").status_code == 404
