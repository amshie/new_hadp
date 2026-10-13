"""What the patient page's domain overview reads (docs/notes/0006, the domain timelines).

The catalog's core markers per domain, when each value was received, and when the latest
interpretation run was recorded. Each is provenance or reference data: no range, no score,
no verdict.
"""

from __future__ import annotations

from datetime import datetime

from hadp_api.modules.enums import Role
from tests.helpers import login_as
from tests.test_interpretation_author_api import _patient_with_observation, _payload

_AXES = {
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
}


def test_core_catalog_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/kpi-catalog/core").status_code == 401


def test_core_catalog_names_the_expected_markers_of_every_domain(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="catalog-core@synthetic.example",
        tenant_name="Catalog Core",
        tenant_slug="catalog-core",
        role=Role.ASSISTANT,
    )
    resp = client.get("/api/v1/kpi-catalog/core")
    assert resp.status_code == 200, resp.text
    rows = resp.json()

    # The 43 core rows of kpi-cat-2.0.0, each once, ordered by code, in all six domains.
    codes = [r["code"] for r in rows]
    assert len(codes) == 43
    assert codes == sorted(codes)
    assert {r["primary_domain_axis"] for r in rows} == _AXES
    neuro = [r["code"] for r in rows if r["primary_domain_axis"] == "neurocognitive"]
    assert len(neuro) == 4

    ldl = next(r for r in rows if r["code"] == "cardio.ldl_c")
    assert ldl == {
        "code": "cardio.ldl_c",
        "display_name": "LDL cholesterol",
        "primary_domain_axis": "cardiovascular",
        "measurement_class": "laboratory",
    }
    # Definitions only: nothing that ranks or judges a value.
    for row in rows:
        assert set(row) == {
            "code",
            "display_name",
            "primary_domain_axis",
            "measurement_class",
        }


def test_timeline_says_when_each_value_was_received(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="received-at@synthetic.example",
        tenant_name="Received At",
        tenant_slug="received-at",
        role=Role.CLINICIAN,
    )
    pid, _ = _patient_with_observation(client, "received")
    point = client.get(f"/api/v1/patients/{pid}/observations").json()[0]
    # The sample is from 2025; the platform received it now. Both are stated, apart.
    assert point["observed_at"].startswith("2025-06-10")
    received = datetime.fromisoformat(point["received_at"])
    assert received.tzinfo is not None
    assert received > datetime.fromisoformat(point["observed_at"])


def test_interpretation_says_when_its_run_was_recorded(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="recorded-at@synthetic.example",
        tenant_name="Recorded At",
        tenant_slug="recorded-at",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "recorded")

    # No run yet: nothing was recorded, so there is no time either.
    empty = client.get(f"/api/v1/patients/{pid}/interpretation").json()
    assert empty["run_number"] is None
    assert empty["recorded_at"] is None

    authored = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id))
    assert authored.status_code == 201, authored.text
    assert authored.json()["recorded_at"] is not None

    latest = client.get(f"/api/v1/patients/{pid}/interpretation").json()
    recorded = datetime.fromisoformat(latest["recorded_at"])
    assert recorded.tzinfo is not None
    # The value it interprets was received before the run was recorded.
    point = client.get(f"/api/v1/patients/{pid}/observations").json()[0]
    assert datetime.fromisoformat(point["received_at"]) <= recorded
