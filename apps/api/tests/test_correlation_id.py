"""A correlation id is an identifier.

A caller may supply one — in the form of one. Anything else is replaced: it would be text of
the caller's choosing in every audit event of the request, and the surfaces that take no
session would let anyone write it into a clinic's trail, which is append-only.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import select, text

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import Role
from tests.helpers import login_as, provision_staff

_GENERATED = re.compile(r"[0-9a-f]{32}")
FREE_TEXT = "Erika Mustermann, HbA1c 9,1 %, geb. 01.02.1960"


@pytest.mark.parametrize(
    "supplied",
    ["0123456789abcdef0123456789abcdef", "0123ABCD-89ab-4def-8123-456789abcdef"],
)
def test_a_supplied_identifier_is_kept(client, supplied: str) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/health", headers={"x-correlation-id": supplied})
    assert resp.headers["x-correlation-id"] == supplied


@pytest.mark.parametrize(
    "supplied",
    [
        FREE_TEXT,
        "<img src=x onerror=alert(1)>",
        "erika_mustermann_hba1c_9-1",
        "0123456789abcdef0123456789abcde",  # one digit short
        "0123456789abcdef0123456789abcdef0",  # one too many
        "0123456789abcdef-0123456789abcdef",  # hyphens, but not a UUID's
        "0123456789abcdef0123456789abcdeg",  # not hexadecimal
        "a" * 65,
        "",
    ],
)
def test_anything_else_is_replaced(client, supplied: str) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/health", headers={"x-correlation-id": supplied})
    answered = resp.headers["x-correlation-id"]
    assert _GENERATED.fullmatch(answered)
    assert answered != supplied


def test_an_anonymous_caller_cannot_write_text_into_a_clinics_trail(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = provision_staff(
        admin_session,
        email="owner-planted@synthetic.example",
        tenant_name="Audit Planted",
        tenant_slug="audit-planted",
        role=Role.OWNER,
    )

    resp = client.post(
        "/api/v1/invitations/redeem",
        headers={"x-correlation-id": FREE_TEXT},
        json={"tenant": str(tenant.id), "token": "x" * 20},
    )

    assert resp.status_code == 404
    denied = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "invitation.redeem_denied")
    ).scalar_one()
    assert denied.tenant_id == tenant.id
    assert denied.correlation_id and _GENERATED.fullmatch(denied.correlation_id)
    planted = admin_session.execute(
        text("SELECT count(*) FROM audit_events WHERE audit_events::text LIKE '%Mustermann%'")
    ).scalar_one()
    assert planted == 0


def test_a_long_header_does_not_break_an_audited_request(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The column holds 64 characters; a longer id used to fail the audit write, and with it
    the request."""
    login_as(
        client,
        admin_session,
        email="owner-long@synthetic.example",
        tenant_name="Audit Long",
        tenant_slug="audit-long",
        role=Role.OWNER,
    )

    resp = client.get("/api/v1/patients", headers={"x-correlation-id": "a" * 200})

    assert resp.status_code == 200
    listed = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "patient.list")
    ).scalar_one()
    assert listed.correlation_id and _GENERATED.fullmatch(listed.correlation_id)


def test_a_refused_cross_site_request_records_no_caller_text(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="owner-csrf@synthetic.example",
        tenant_name="Audit Csrf",
        tenant_slug="audit-csrf",
        role=Role.OWNER,
    )
    client.headers.pop("x-csrf-token")

    resp = client.post(
        "/api/v1/patients",
        json={"display_name": "Synthetic Cross Site"},
        headers={"x-correlation-id": FREE_TEXT},
    )

    assert resp.status_code == 403
    refused = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "csrf.denied")
    ).scalar_one()
    assert refused.correlation_id is None
