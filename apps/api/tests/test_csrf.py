"""CSRF guard (P-pre-2, docs/notes/0010): double-submit + Origin allowlist.

Unsafe methods on cookie-authenticated requests must prove same-origin: an allow-listed
Origin/Referer or the x-csrf-token header matching the csrf cookie issued at login.
A rejected request is a 403 and emits an audited `csrf.denied` security event.
"""

from __future__ import annotations

from sqlalchemy import select

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login_as


def test_cookie_post_without_proof_is_rejected(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="csrf@synthetic.example",
        tenant_name="CSRF Clinic",
        tenant_slug="csrf-clinic",
        role=Role.CLINICIAN,
    )
    # Strip the double-submit header the helper installed: a forged cross-site request
    # carries the cookie but neither the header nor an allow-listed Origin.
    del client.headers["x-csrf-token"]
    resp = client.post("/api/v1/patients", json={"display_name": "Forged"})
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "csrf_rejected"
    event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "csrf.denied"))
        .scalars()
        .one()
    )
    assert event.detail == {"method": "POST"}


def test_cross_origin_post_is_rejected_even_with_origin_header(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="csrf2@synthetic.example",
        tenant_name="CSRF Clinic 2",
        tenant_slug="csrf-clinic-2",
        role=Role.CLINICIAN,
    )
    del client.headers["x-csrf-token"]
    resp = client.post(
        "/api/v1/patients",
        json={"display_name": "Forged"},
        headers={"origin": "https://evil.example"},
    )
    assert resp.status_code == 403, resp.text


def test_double_submit_header_allows_the_request(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # helpers.login installs the header from the csrf cookie — the legitimate-client path.
    login_as(
        client,
        admin_session,
        email="csrf3@synthetic.example",
        tenant_name="CSRF Clinic 3",
        tenant_slug="csrf-clinic-3",
        role=Role.CLINICIAN,
    )
    assert client.headers["x-csrf-token"] == client.cookies.get("hadp_csrf")
    resp = client.post("/api/v1/patients", json={"display_name": "Legit Patient"})
    assert resp.status_code == 201, resp.text


def test_allowed_origin_allows_the_request_without_header(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="csrf4@synthetic.example",
        tenant_name="CSRF Clinic 4",
        tenant_slug="csrf-clinic-4",
        role=Role.CLINICIAN,
    )
    del client.headers["x-csrf-token"]
    resp = client.post(
        "/api/v1/patients",
        json={"display_name": "Same Origin"},
        headers={"origin": "http://127.0.0.1:3000"},
    )
    assert resp.status_code == 201, resp.text


def test_wrong_double_submit_token_is_rejected(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="csrf5@synthetic.example",
        tenant_name="CSRF Clinic 5",
        tenant_slug="csrf-clinic-5",
        role=Role.CLINICIAN,
    )
    client.headers["x-csrf-token"] = "not-the-cookie-value"
    resp = client.post("/api/v1/patients", json={"display_name": "Forged"})
    assert resp.status_code == 403, resp.text


def test_unauthenticated_and_safe_requests_are_untouched(client) -> None:  # type: ignore[no-untyped-def]
    # No session cookie: the guard does not apply (401 comes from authn, not CSRF).
    resp = client.post("/api/v1/patients", json={"display_name": "X"})
    assert resp.status_code == 401
    # Safe method with no cookie: untouched.
    assert client.get("/api/v1/health").status_code == 200
