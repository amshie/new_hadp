"""Audit events are append-only and reject sensitive detail."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InternalError, ProgrammingError

from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.audit.service import record_audit


def test_audit_detail_rejects_sensitive_keys(admin_session) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        record_audit(admin_session, action="patient.create", detail={"display_name": "Jane"})


def test_audit_rows_cannot_be_updated_or_deleted(admin_session) -> None:  # type: ignore[no-untyped-def]
    event = AuditEvent(action="test.event", detail={})
    admin_session.add(event)
    admin_session.commit()

    # UPDATE is blocked by the append-only trigger (even for the admin/owner).
    with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
        admin_session.execute(
            text("UPDATE audit_events SET action = 'tampered' WHERE id = :i"),
            {"i": event.id},
        )
    admin_session.rollback()

    with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
        admin_session.execute(text("DELETE FROM audit_events WHERE id = :i"), {"i": event.id})
    admin_session.rollback()

    # The row is still present and unchanged.
    still = admin_session.get(AuditEvent, event.id)
    assert still is not None
    assert still.action == "test.event"


def test_audit_event_records_identifiers_only(admin_session) -> None:  # type: ignore[no-untyped-def]
    tid = uuid.uuid4()
    # Insert a tenant so the FK (ON DELETE SET NULL, nullable) is satisfiable; here we
    # just exercise that non-sensitive detail is accepted.
    event = record_audit(
        admin_session,
        action="patient.list",
        correlation_id="corr-123",
        detail={"count": 3, "role": "clinician"},
    )
    admin_session.commit()
    assert event.detail == {"count": 3, "role": "clinician"}
    assert tid != event.id
