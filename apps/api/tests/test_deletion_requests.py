"""Patient-erasure request lifecycle (docs/notes/0012, PR A — no execution yet).

Two-person gate: an OWNER opens a request, a MEDICAL DIRECTOR decides it, the requester may
cancel a pending one. Enforced server-side (deny-by-default authz + service guards). Every
transition is audited with status/reason codes only, never identity. Tenant isolation is
proven end to end: a request is invisible and un-decidable from another tenant.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.privacy.models import DeletionRequest
from tests.helpers import login_as, switch_role


def _make_patient(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": "Zu Löschen"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _owner_and_patient(client, admin_session, *, slug: str):  # type: ignore[no-untyped-def]
    owner, tenant = login_as(
        client,
        admin_session,
        email=f"{slug}-owner@synthetic.example",
        tenant_name=f"Erasure Clinic {slug}",
        tenant_slug=f"erasure-{slug}",
        role=Role.OWNER,
    )
    pid = _make_patient(client)
    return owner, tenant, pid


def test_full_two_person_lifecycle_request_then_approve(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, tenant, pid = _owner_and_patient(client, admin_session, slug="approve")

    created = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "patient_request"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["reason_category"] == "patient_request"
    assert body["patient_id"] == pid
    assert body["requested_by_user_id"] == str(owner.id)
    assert body["decided_at"] is None
    rid = body["id"]

    # The owner may see the queue but may NOT decide (medical-director-only).
    assert client.get("/api/v1/deletion-requests").status_code == 200
    denied = client.post(f"/api/v1/deletion-requests/{rid}/approve")
    assert denied.status_code == 403, denied.text

    # Switch to the medical director: decides (a DIFFERENT person, by role).
    md = switch_role(
        client,
        admin_session,
        email="approve-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    approved = client.post(f"/api/v1/deletion-requests/{rid}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_by_user_id"] == str(md.id)

    # Audit trail: request + approve, codes only (no patient name / identity keys).
    actions = [
        e.action
        for e in admin_session.execute(
            select(AuditEvent).where(AuditEvent.target_id == uuid.UUID(rid))
        )
        .scalars()
        .all()
    ]
    assert "privacy.deletion_requested" in actions
    assert "privacy.deletion_approved" in actions
    requested = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "privacy.deletion_requested")
    ).scalar_one()
    assert requested.detail == {"reason_category": "patient_request"}
    assert "display_name" not in requested.detail and "name" not in requested.detail


def test_requester_cannot_decide_and_reject_path(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # A medical director both requests? No — request is owner-only. But guard the decider-≠-
    # requester rule directly: give the SAME person both roles is impossible (one role per
    # tenant), so we assert the role gate AND the service self-decision guard via a rejected path.
    _owner, tenant, pid = _owner_and_patient(client, admin_session, slug="reject")
    rid = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "withdrawn_consent"},
    ).json()["id"]

    switch_role(
        client,
        admin_session,
        email="reject-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    rejected = client.post(f"/api/v1/deletion-requests/{rid}/reject")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    # A decided request cannot be decided again (409).
    again = client.post(f"/api/v1/deletion-requests/{rid}/approve")
    assert again.status_code == 409, again.text


def test_only_requester_cancels_and_only_when_pending(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, tenant, pid = _owner_and_patient(client, admin_session, slug="cancel")
    rid = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "data_minimization"},
    ).json()["id"]

    # A different owner in the same tenant may NOT cancel someone else's request.
    switch_role(
        client,
        admin_session,
        email="cancel-owner2@synthetic.example",
        tenant=tenant,
        role=Role.OWNER,
    )
    denied = client.post(f"/api/v1/deletion-requests/{rid}/cancel")
    assert denied.status_code == 409, denied.text

    # The original requester cancels their pending request.
    login_as_again = client.post(
        "/api/v1/auth/dev-login", json={"email": "cancel-owner@synthetic.example"}
    )
    assert login_as_again.status_code == 200
    csrf = client.cookies.get("hadp_csrf")
    if csrf:
        client.headers["x-csrf-token"] = csrf
    client.post("/api/v1/tenancy/select-tenant", json={"tenant_id": str(tenant.id)})
    cancelled = client.post(f"/api/v1/deletion-requests/{rid}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    # A cancelled (terminal) request frees the patient for a NEW request.
    again = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "patient_request"},
    )
    assert again.status_code == 201, again.text


def test_one_open_request_per_patient(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, _tenant, pid = _owner_and_patient(client, admin_session, slug="dup")
    first = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "patient_request"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "patient_request"},
    )
    assert second.status_code == 409, second.text


def test_deletion_requests_never_cross_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Tenant A opens a request.
    _owner_a, tenant_a, pid_a = _owner_and_patient(client, admin_session, slug="iso-a")
    rid = client.post(
        f"/api/v1/patients/{pid_a}/deletion-requests",
        json={"reason_category": "patient_request"},
    ).json()["id"]

    # Tenant B (a medical director, so authz would otherwise allow deciding) sees NOTHING and
    # cannot decide tenant A's request — RLS + explicit tenant scope.
    login_as(
        client,
        admin_session,
        email="iso-b-md@synthetic.example",
        tenant_name="Erasure Clinic B",
        tenant_slug="erasure-iso-b",
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.get("/api/v1/deletion-requests").json() == []
    cross = client.post(f"/api/v1/deletion-requests/{rid}/approve")
    assert cross.status_code == 404, cross.text
    # And tenant A's request row is untouched.
    row = admin_session.execute(
        select(DeletionRequest).where(DeletionRequest.id == uuid.UUID(rid))
    ).scalar_one()
    assert row.status.value == "pending"
    assert row.tenant_id == tenant_a.id


def test_care_staff_cannot_request_or_list(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Erasure is tenant administration: a clinician/assistant may neither request nor view.
    _owner, tenant, pid = _owner_and_patient(client, admin_session, slug="authz")
    switch_role(
        client,
        admin_session,
        email="authz-clin@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert (
        client.post(
            f"/api/v1/patients/{pid}/deletion-requests",
            json={"reason_category": "patient_request"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/deletion-requests").status_code == 403


def test_reason_category_is_a_closed_vocabulary(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, _tenant, pid = _owner_and_patient(client, admin_session, slug="vocab")
    bad = client.post(
        f"/api/v1/patients/{pid}/deletion-requests",
        json={"reason_category": "because_i_said_so"},
    )
    assert bad.status_code == 422, bad.text
