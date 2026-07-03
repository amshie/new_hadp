"""Review-queue resolution (Phase 1C): the human-in-the-loop half of the pipeline.

A pending observation can now be resolved through the product: a clinician publishes or
rejects it, attributably and audited. REJECT is immediate and fail-closed; PUBLISH takes
effect only with the LAST open item for the observation. Resolution is a clinical
judgement — the assistant (triage) and the medical director (gate) get 403.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.imports.models import ReviewItem
from tests.helpers import login_as, switch_role

# An unsupported unit routes the value into the review queue (normalize.py).
_REVIEW_IMPORT = {
    "values": [
        {
            "original_name": "LDL Cholesterol",
            "original_value": "2.8",
            "original_unit": "µkat/L",
            "observed_at": "2025-06-10T00:00:00Z",
            "observed_at_is_date_only": True,
        }
    ]
}


def _pending_item(client, slug: str) -> tuple[str, str, str]:  # type: ignore[no-untyped-def]
    """Create a patient + one review-required observation; return (pid, obs_id, item_id)."""
    pid = client.post("/api/v1/patients", json={"display_name": f"RQ {slug}"}).json()["id"]
    result = client.post(f"/api/v1/patients/{pid}/imports", json=_REVIEW_IMPORT).json()
    assert result["review_count"] == 1, result
    return pid, result["observation_ids"][0], result["review_item_ids"][0]


def test_clinician_publishes_a_pending_observation(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = login_as(
        client,
        admin_session,
        email="rq@synthetic.example",
        tenant_name="RQ Clinic",
        tenant_slug="rq-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id, item_id = _pending_item(client, "a")

    # The clinician timeline shows the value with its review status visible (pending),
    # and computes no delta for it (published-only arithmetic).
    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert [(p["observation_id"], p["review_status"]) for p in points] == [(obs_id, "pending")]
    assert points[0]["delta_vs_previous"] is None
    # The queue lists the item with the source representation.
    queue = client.get("/api/v1/review-items").json()
    assert [q["review_item_id"] for q in queue] == [item_id]
    assert queue[0]["original_unit"] == "µkat/L"

    resolved = client.post(f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["observation_review_status"] == "published"

    # Published on the timeline; queue is empty; resolution is attributable and audited.
    timeline = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert [(p["observation_id"], p["review_status"]) for p in timeline] == [(obs_id, "published")]
    assert client.get("/api/v1/review-items").json() == []
    item = admin_session.execute(
        select(ReviewItem).where(ReviewItem.id == uuid.UUID(item_id))
    ).scalar_one()
    assert item.resolved is True
    assert item.resolved_by_user_id == user.id
    assert item.resolved_at is not None
    audit = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "review_item.resolved"))
        .scalars()
        .one()
    )
    assert audit.detail == {"decision": "publish", "reason": "unsupported_unit"}

    # A resolved item cannot be resolved again.
    assert (
        client.post(
            f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"}
        ).status_code
        == 409
    )


def test_reject_keeps_the_value_out_of_the_timeline(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rq-rej@synthetic.example",
        tenant_name="RQ Reject Clinic",
        tenant_slug="rq-reject-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id, item_id = _pending_item(client, "b")
    resolved = client.post(f"/api/v1/review-items/{item_id}/resolve", json={"decision": "reject"})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["observation_review_status"] == "rejected"
    # Never published: the timeline shows it as rejected (status visible); queue is clear.
    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert [(p["observation_id"], p["review_status"]) for p in points] == [(obs_id, "rejected")]
    assert client.get("/api/v1/review-items").json() == []


def test_publish_waits_for_the_last_open_item(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rq-multi@synthetic.example",
        tenant_name="RQ Multi Clinic",
        tenant_slug="rq-multi-clinic",
        role=Role.CLINICIAN,
    )
    pid, obs_id, item_id = _pending_item(client, "c")
    # A second open item on the SAME observation (e.g. a second conflict).
    second = ReviewItem(
        tenant_id=admin_session.execute(
            select(ReviewItem.tenant_id).where(ReviewItem.id == uuid.UUID(item_id))
        ).scalar_one(),
        observation_id=uuid.UUID(obs_id),
        reason="impossible_value",
        detail={},
        resolved=False,
    )
    admin_session.add(second)
    admin_session.commit()

    # Resolving the first item publishes NOTHING while the second stays open.
    first = client.post(f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"})
    assert first.status_code == 200, first.text
    assert first.json()["observation_review_status"] == "pending"
    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    assert [(p["observation_id"], p["review_status"]) for p in points] == [(obs_id, "pending")]

    # Resolving the LAST open item publishes the observation.
    last = client.post(f"/api/v1/review-items/{second.id}/resolve", json={"decision": "publish"})
    assert last.status_code == 200, last.text
    assert last.json()["observation_review_status"] == "published"
    assert [
        (p["observation_id"], p["review_status"])
        for p in client.get(f"/api/v1/patients/{pid}/observations").json()
    ] == [(obs_id, "published")]


def test_resolution_is_clinician_only(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = login_as(
        client,
        admin_session,
        email="rq-clin@synthetic.example",
        tenant_name="RQ Role Clinic",
        tenant_slug="rq-role-clinic",
        role=Role.CLINICIAN,
    )
    _pid, _obs_id, item_id = _pending_item(client, "d")
    for email, role in (
        ("rq-assistant@synthetic.example", Role.ASSISTANT),
        ("rq-md@synthetic.example", Role.MEDICAL_DIRECTOR),
    ):
        switch_role(client, admin_session, email=email, tenant=tenant, role=role)
        assert (
            client.post(
                f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"}
            ).status_code
            == 403
        )


def test_cross_tenant_item_is_404_and_queue_is_tenant_scoped(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="rq-xa@synthetic.example",
        tenant_name="RQ XA",
        tenant_slug="rq-xa",
        role=Role.CLINICIAN,
    )
    _pid, _obs_id, item_id = _pending_item(client, "e")

    login_as(
        client,
        admin_session,
        email="rq-xb@synthetic.example",
        tenant_name="RQ XB",
        tenant_slug="rq-xb",
        role=Role.CLINICIAN,
    )
    # Tenant B sees an empty queue and cannot resolve A's item.
    assert client.get("/api/v1/review-items").json() == []
    assert (
        client.post(
            f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"}
        ).status_code
        == 404
    )


def test_unauthenticated_and_bad_decision(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    assert (
        client.post(
            f"/api/v1/review-items/{uuid.uuid4()}/resolve", json={"decision": "publish"}
        ).status_code
        == 401
    )
    login_as(
        client,
        admin_session,
        email="rq-bad@synthetic.example",
        tenant_name="RQ Bad",
        tenant_slug="rq-bad",
        role=Role.CLINICIAN,
    )
    _pid, _obs_id, item_id = _pending_item(client, "f")
    # Closed decision vocabulary: an invented value is rejected at the boundary.
    assert (
        client.post(
            f"/api/v1/review-items/{item_id}/resolve", json={"decision": "escalate"}
        ).status_code
        == 422
    )
