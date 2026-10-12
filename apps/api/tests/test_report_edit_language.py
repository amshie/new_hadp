"""A human edit of report text is held to the intended-use language boundary.

The deterministic provider is guarded by test_forbidden_language.py, but an edit is free text
bound for a patient-facing report. The edit path therefore refuses restricted terms at write
time (fail-closed): nothing is persisted, and the error names the matched term, never the text.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from hadp_api.modules.enums import Role
from hadp_api.modules.reports.language import restricted_terms
from hadp_api.modules.reports.models import ReportVersion
from tests.helpers import login_as

_IMPORT = {
    "values": [
        {
            "original_name": "LDL Cholesterol",
            "original_value": "2.8",
            "original_unit": "mmol/L",
            "observed_at": "2025-06-10T00:00:00Z",
            "observed_at_is_date_only": True,
        }
    ]
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The value suggests a diagnosis.", ["diagnos"]),
        ("Diagnose: LDL erhöht.", ["diagnos"]),  # German inflection of the same stem
        ("Der Wert liegt im optimalen Bereich.", ["optimal"]),
        ("An elevated risk\n score was computed.", ["risk score"]),  # whitespace-normalized
        ("We recommend a supplement.", ["recommend", "supplement"]),
        # Word-start matching: "secure"/"procured" are not "cure".
        ("Stored on a secure server; the sample was procured on 2025-06-10.", []),
        ("LDL Cholesterol was 2.8 mmol/L on 2025-06-10.", []),
    ],
)
def test_restricted_terms(text: str, expected: list[str]) -> None:
    assert restricted_terms([text]) == expected


def _edited(report: dict[str, Any], suffix: str) -> list[dict[str, Any]]:
    return [
        {
            "id": s["id"],
            "text": s["text"] + suffix,
            "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
        }
        for s in report["statements"]
    ]


def test_edit_with_restricted_language_is_refused_and_persists_nothing(  # type: ignore[no-untyped-def]
    client, admin_session
) -> None:
    login_as(
        client,
        admin_session,
        email="lang-edit@synthetic.example",
        tenant_name="Language Clinic",
        tenant_slug="language-clinic",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "R lang"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    report = client.post(f"/api/v1/patients/{pid}/reports").json()
    rid = report["report_id"]
    assert report["edited"] is False  # provider output, untouched
    assert (
        client.post(f"/api/v1/reports/{rid}/reject", json={"reason": "wording"}).status_code == 200
    )

    marker = "ZZ-unique-marker"
    resp = client.post(
        f"/api/v1/reports/{rid}/edit",
        json={"statements": _edited(report, f" {marker} This confirms the diagnosis.")},
    )
    assert resp.status_code == 409, resp.text
    error = resp.json()["error"]
    assert error["code"] == "intended_use_violation"
    assert "diagnos" in error["detail"]
    assert marker not in resp.text  # the submitted text is never echoed

    # Fail-closed: the rejected version is still the only one; no draft was opened.
    versions = admin_session.execute(select(ReportVersion)).scalars().all()
    assert [v.status.value for v in versions] == ["rejected"]
    assert client.get(f"/api/v1/reports/{rid}").json()["status"] == "rejected"

    # The same rework in neutral wording goes through as a new version.
    ok = client.post(
        f"/api/v1/reports/{rid}/edit",
        json={"statements": _edited(report, " Value confirmed against the source document.")},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "draft_edited"
    assert ok.json()["version_no"] == report["version_no"] + 1
    assert ok.json()["edited"] is True  # the view states the text was human-edited
