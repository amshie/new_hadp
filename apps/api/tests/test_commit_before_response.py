"""A response is sent only after the request's transaction is committed.

Answering "saved" before the save is durable is a false success: the client (and the audit
trail it relies on) believes a write that a failing commit would silently drop, and a request
issued right after — select the clinic straight after logging in — can miss it. FastAPI ends a
`yield` dependency AFTER the response by default, so the request session must be declared with
the function scope; these tests pin the ordering from the outside, at the ASGI boundary.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from hadp_api.db.engine import reset_engine
from hadp_api.main import app
from hadp_api.modules.enums import Role
from tests.helpers import login_as, provision_staff

_SRC = Path(__file__).resolve().parents[1] / "src" / "hadp_api"


class _CommitProbe:
    """ASGI wrapper: the instant a response STARTS, ask an independent connection what is
    committed. That connection cannot see another transaction's uncommitted rows."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.query: str | None = None
        self.seen: list[int] = []

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        async def probing_send(message: Any) -> None:
            if message["type"] == "http.response.start" and self.query is not None:
                with self.engine.connect() as conn:
                    self.seen.append(conn.execute(text(self.query)).scalar_one())
            await send(message)

        await app(scope, receive, probing_send if scope["type"] == "http" else send)


def test_a_write_and_its_audit_event_are_committed_before_the_response(  # type: ignore[no-untyped-def]
    admin_engine, admin_session
) -> None:
    reset_engine()
    probe = _CommitProbe(admin_engine)
    with TestClient(probe) as client:
        login_as(
            client,
            admin_session,
            email="commit-order@synthetic.example",
            tenant_name="Commit Order Clinic",
            tenant_slug="commit-order",
            role=Role.CLINICIAN,
        )
        probe.query = (
            "select (select count(*) from patients)"
            " + (select count(*) from audit_events where action = 'patient.create')"
        )
        resp = client.post("/api/v1/patients", json={"display_name": "Commit Probe (synthetic)"})
        assert resp.status_code == 201, resp.text
    # Both the row and the audit event were already durable when the 201 started.
    assert probe.seen == [2]


def test_a_session_is_usable_the_moment_login_answers(admin_engine, admin_session) -> None:  # type: ignore[no-untyped-def]
    reset_engine()
    provision_staff(
        admin_session,
        email="login-order@synthetic.example",
        tenant_name="Login Order Clinic",
        tenant_slug="login-order",
        role=Role.CLINICIAN,
    )
    probe = _CommitProbe(admin_engine)
    with TestClient(probe) as client:
        probe.query = "select count(*) from auth_sessions"
        resp = client.post(
            "/api/v1/auth/dev-login", json={"email": "login-order@synthetic.example"}
        )
        assert resp.status_code == 200, resp.text
    assert probe.seen == [1]


def test_a_failed_commit_is_never_reported_as_success(monkeypatch, admin_session) -> None:  # type: ignore[no-untyped-def]
    reset_engine()
    with TestClient(app, raise_server_exceptions=False) as client:
        login_as(
            client,
            admin_session,
            email="commit-fail@synthetic.example",
            tenant_name="Commit Fail Clinic",
            tenant_slug="commit-fail",
            role=Role.CLINICIAN,
        )

        def failing_commit(self: Session) -> None:
            raise OperationalError("COMMIT", {}, Exception("synthetic commit failure"))

        monkeypatch.setattr(Session, "commit", failing_commit)
        resp = client.post("/api/v1/patients", json={"display_name": "Never Saved (synthetic)"})
        monkeypatch.undo()
    assert resp.status_code == 500
    assert admin_session.execute(text("select count(*) from patients")).scalar_one() == 0


def test_every_route_uses_the_shared_request_session() -> None:
    # Two declarations with different scopes would be two sessions in one request. The scope
    # is therefore stated once (db/session.py) and nothing else may declare the dependency.
    offenders = [
        str(path.relative_to(_SRC))
        for path in sorted(_SRC.rglob("*.py"))
        if path.name != "session.py" and re.search(r"Depends\(\s*get_db", path.read_text())
    ]
    assert offenders == []
