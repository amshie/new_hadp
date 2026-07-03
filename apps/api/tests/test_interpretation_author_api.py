"""API tests for the interpretation authoring endpoint (the governance write path).

POST /patients/{id}/interpretation-runs is clinician-only (two-tier gate: the medical
director reviews/releases but never authors), enforces the closed vocabularies at the
boundary (a CIS value in the Actionability field is a 422), resolves every evidence ref
against the patient's own PUBLISHED observations (fail-closed 409), records required
authorship, is audited without clinical content, and is append-only (a correction is a
new run).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.interpretation.models import InterpretationRun
from tests.helpers import login_as, switch_role

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

_AXES = (
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
)


def _cells(obs_id: str) -> list[dict]:  # type: ignore[type-arg]
    ref = [{"kind": "observation", "id": obs_id}]
    return [
        {
            "tri_state_axis": "biological",
            "state": "STABLE",
            "endpoint_adequacy": "adequate",
            "evidence_refs": ref,
        },
        {
            "tri_state_axis": "risk",
            "state": "REDUCED",
            "endpoint_adequacy": "adequate",
            "evidence_refs": ref,
        },
        {
            "tri_state_axis": "functional",
            "state": "IMPROVED",
            "endpoint_adequacy": "adequate",
            "evidence_refs": ref,
        },
    ]


def _payload(obs_id: str, *, reason: str = "baseline") -> dict:  # type: ignore[type-arg]
    return {
        "reason": reason,
        "domains": [
            {
                "domain_axis": axis,
                "cis_status": "CIS_4_CREDIBLE_IMPROVEMENT",
                "actionability_class": "C_CLINICALLY_INTERPRETABLE",
                "followup_adequacy": "adequate",
                "rationale": "authored note",
                "cells": _cells(obs_id),
            }
            for axis in _AXES
        ],
    }


def _patient_with_observation(client, slug: str) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    """Create a patient and import one auto-publishing observation; return (pid, obs_id)."""
    pid = client.post("/api/v1/patients", json={"display_name": f"P {slug}"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    timeline = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert timeline, "expected the imported observation to publish"
    return pid, timeline[0]["observation_id"]


def test_clinician_authors_a_run_with_required_authorship(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = login_as(
        client,
        admin_session,
        email="author@synthetic.example",
        tenant_name="Author Clinic",
        tenant_slug="author-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "a")

    resp = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["run_number"] == 1
    assert len(body["domains"]) == 6
    # CIS and Actionability come back as TWO separate fields (never merged).
    assert body["domains"][0]["cis_status"].startswith("CIS_")
    assert body["domains"][0]["actionability_class"][0] in "ABCDE"

    # Authorship is recorded and non-null; the run is attributable to the clinician.
    run = admin_session.execute(select(InterpretationRun)).scalars().one()
    assert run.created_by_user_id == user.id

    # Audited, with identifiers/counters only (no clinical content).
    event = (
        admin_session.execute(
            select(AuditEvent).where(AuditEvent.action == "interpretation.authored")
        )
        .scalars()
        .one()
    )
    assert event.detail == {"run_number": 1, "domains": 6}


def test_correction_is_a_new_append_only_run(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="author2@synthetic.example",
        tenant_name="Author Clinic 2",
        tenant_slug="author-clinic-2",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "b")
    assert (
        client.post(
            f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id)
        ).status_code
        == 201
    )
    second = client.post(
        f"/api/v1/patients/{pid}/interpretation-runs",
        json=_payload(obs_id, reason="correction"),
    )
    assert second.status_code == 201, second.text
    assert second.json()["run_number"] == 2
    # Both runs persist (append-only): nothing was overwritten.
    runs = admin_session.execute(select(InterpretationRun)).scalars().all()
    assert sorted(r.run_number for r in runs) == [1, 2]
    # The read path serves the latest run.
    assert client.get(f"/api/v1/patients/{pid}/interpretation").json()["run_number"] == 2


def test_authoring_is_clinician_only(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="author-clin@synthetic.example",
        tenant_name="Role Clinic",
        tenant_slug="role-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "c")

    # The medical director reviews and releases; they do NOT author (two-tier gate).
    switch_role(
        client,
        admin_session,
        email="role-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert (
        client.post(
            f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id)
        ).status_code
        == 403
    )

    switch_role(
        client,
        admin_session,
        email="role-assistant@synthetic.example",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    assert (
        client.post(
            f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id)
        ).status_code
        == 403
    )


def test_unauthenticated_cannot_author(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"/api/v1/patients/{uuid.uuid4()}/interpretation-runs",
        json={"reason": "x", "domains": []},
    )
    assert resp.status_code == 401


def test_cross_tenant_patient_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="xt-a@synthetic.example",
        tenant_name="XT A",
        tenant_slug="xt-a",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "d")
    payload = _payload(obs_id)

    login_as(
        client,
        admin_session,
        email="xt-b@synthetic.example",
        tenant_name="XT B",
        tenant_slug="xt-b",
        role=Role.CLINICIAN,
    )
    assert (
        client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=payload).status_code == 404
    )


def test_wrong_vocabulary_is_rejected_at_the_boundary(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="vocab@synthetic.example",
        tenant_name="Vocab Clinic",
        tenant_slug="vocab-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "e")
    # An Actionability value in the CIS field is structurally impossible (disjoint enums).
    bad = _payload(obs_id)
    bad["domains"][0]["cis_status"] = "B_SUPPORTIVE"
    assert client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=bad).status_code == 422


def test_wrong_shape_is_refused(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="shape@synthetic.example",
        tenant_name="Shape Clinic",
        tenant_slug="shape-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id = _patient_with_observation(client, "f")
    five = _payload(obs_id)
    five["domains"] = five["domains"][:5]  # five domains, not six
    resp = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=five)
    assert resp.status_code == 409, resp.text


def test_unresolvable_evidence_is_refused(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="ev@synthetic.example",
        tenant_name="Evidence Clinic",
        tenant_slug="evidence-clinic",
        role=Role.CLINICIAN,
    )
    pid, _obs_id = _patient_with_observation(client, "g")

    # Nonexistent observation id → fail-closed.
    ghost = _payload(str(uuid.uuid4()))
    assert client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=ghost).status_code == 409

    # Another patient's observation (same tenant) must not back this patient's verdicts.
    _other_pid, other_obs = _patient_with_observation(client, "g2")
    foreign = _payload(other_obs)
    resp = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=foreign)
    assert resp.status_code == 409, resp.text
    # The error names the failure class, not the foreign data.
    assert "observation" in resp.json()["error"]["detail"]
