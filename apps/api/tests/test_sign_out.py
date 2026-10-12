"""Sign-out: the session is revoked, and both cookies leave the device.

The session cookie and the CSRF cookie are issued together at sign-in. Sign-out removed only
the first, and removed it without the attributes it was set with — which a browser does not
accept for a `__Host-` name (the production names): the deletion would have removed nothing.
"""

from __future__ import annotations

from http.cookies import SimpleCookie

import pytest
from fastapi import Response
from sqlalchemy import select

from hadp_api.api import auth_routes
from hadp_api.config import Settings
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from hadp_api.modules.identity.models import AuthSession
from tests.helpers import login_as


def _cookies(response) -> dict[str, dict[str, str | bool]]:  # type: ignore[no-untyped-def]
    """Every Set-Cookie of a response: name -> its value and attributes."""
    out: dict[str, dict[str, str | bool]] = {}
    headers = response.headers
    # An httpx response (from the test client) and a Starlette one spell it differently.
    lines = (
        headers.get_list("set-cookie")
        if hasattr(headers, "get_list")
        else headers.getlist("set-cookie")
    )
    for header in lines:
        jar: SimpleCookie = SimpleCookie()
        jar.load(header)
        for name, morsel in jar.items():
            out[name] = {
                "value": morsel.value,
                "max_age": morsel["max-age"],
                "path": morsel["path"],
                "secure": bool(morsel["secure"]),
                "httponly": bool(morsel["httponly"]),
                "samesite": morsel["samesite"].lower(),
            }
    return out


def test_sign_out_revokes_the_session_and_removes_both_cookies(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _ = login_as(
        client,
        admin_session,
        email="sign-out@synthetic.example",
        tenant_name="Sign Out Clinic",
        tenant_slug="sign-out",
        role=Role.CLINICIAN,
    )
    assert client.cookies.get("hadp_session") and client.cookies.get("hadp_csrf")

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204, resp.text

    removed = _cookies(resp)
    assert set(removed) == {"hadp_session", "hadp_csrf"}
    for name, cookie in removed.items():
        assert cookie["max_age"] == "0", name
        assert cookie["value"] == "", name
        assert cookie["path"] == "/", name
    # The client did what a browser does with them.
    assert client.cookies.get("hadp_session") is None
    assert client.cookies.get("hadp_csrf") is None

    # Revoked server-side — the cookie value is worthless even if a copy survives.
    session = admin_session.execute(select(AuthSession)).scalars().one()
    assert session.revoked_at is not None
    assert client.get("/api/v1/auth/me").status_code == 401
    event = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "auth.logout"))
        .scalars()
        .one()
    )
    assert event.actor_user_id == user.id


def test_a_copied_session_cookie_is_refused_after_sign_out(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="sign-out-copy@synthetic.example",
        tenant_name="Sign Out Copy Clinic",
        tenant_slug="sign-out-copy",
        role=Role.CLINICIAN,
    )
    copied = client.cookies.get("hadp_session")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("hadp_session", copied)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_each_cookie_is_removed_with_the_attributes_it_was_set_with(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In production the names carry `__Host-`: a browser takes a Set-Cookie for such a name
    only with `Secure` and `Path=/` — for the deletion exactly as for the cookie itself."""
    production = Settings(
        app_env="production",
        database_url="postgresql+psycopg://postgres:postgres@db:5432/hadp",
        app_database_url="postgresql+psycopg://hadp_app:hadp_app@db:5432/hadp",
        session_secret="x" * 40,
        s3_access_key_id="synthetic-key",
        s3_secret_access_key="synthetic-secret",
        session_cookie_name="__Host-hadp_session",
        csrf_cookie_name="__Host-hadp_csrf",
    )
    monkeypatch.setattr(auth_routes, "get_settings", lambda: production)

    issued = Response()
    auth_routes._set_session_cookie(issued, "synthetic-session-token")
    auth_routes._set_csrf_cookie(issued, "synthetic-csrf-token")
    cleared = Response()
    auth_routes._clear_auth_cookies(cleared)

    set_with, removed = _cookies(issued), _cookies(cleared)
    assert set(removed) == set(set_with) == {"__Host-hadp_session", "__Host-hadp_csrf"}
    for name in removed:
        assert removed[name]["max_age"] == "0" and removed[name]["value"] == "", name
        assert removed[name]["secure"] is True, name
        assert removed[name]["path"] == "/", name
        for attribute in ("secure", "path", "httponly", "samesite"):
            assert removed[name][attribute] == set_with[name][attribute], (name, attribute)
    assert removed["__Host-hadp_session"]["httponly"] is True
    assert removed["__Host-hadp_csrf"]["httponly"] is False
