"""Audit service: append-only event recording, and the clinic's read of its own trail.

Callers pass identifiers, codes, and timings only. Detail must never contain names,
emails, observation values, free text, document contents, or secrets.
"""

from __future__ import annotations

import base64
import binascii
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, not_, or_, select
from sqlalchemy.orm import Session

from hadp_api.errors import ValidationFailed
from hadp_api.modules.audit.models import AuditEvent

logger = logging.getLogger(__name__)

# Keys that must never appear in audit detail (defense-in-depth against PII/health leaks).
_FORBIDDEN_DETAIL_KEYS = {
    "value",
    "numeric_value",
    "name",
    "display_name",
    "email",
    "text",
    "content",
    "token",
    "password",
    "secret",
}


def record_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    detail = detail or {}
    leaked = _FORBIDDEN_DETAIL_KEYS.intersection(k.lower() for k in detail)
    if leaked:
        raise ValueError(f"audit detail must not contain sensitive keys: {sorted(leaked)}")
    event = AuditEvent(
        action=action,
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        detail=detail,
    )
    db.add(event)
    db.flush()
    return event


def record_security_event(
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Record a security event on its OWN committed transaction.

    Used for denied/failed access (e.g. failed authorization, cross-tenant patient-view
    attempts) where the request transaction will roll back — the audit must survive that
    rollback. Audit failures are logged but never propagated, so they cannot mask the
    original denial or turn a 403 into a 500.
    """
    from hadp_api.db.engine import get_sessionmaker, set_tenant_context

    try:
        with get_sessionmaker()() as session:
            if tenant_id is not None:
                set_tenant_context(session, tenant_id)
            record_audit(
                session,
                action=action,
                actor_user_id=actor_user_id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                detail=detail,
            )
            session.commit()
    except Exception as exc:  # noqa: BLE001 - audit must never break the request path
        # ERROR (not silent): a failing security-audit write means the denial trail is
        # being lost — operators must see this. Exception CLASS only (a driver message
        # could carry statement parameters; the trail may involve health-data rows).
        logger.error(
            "failed to record security event action=%s error=%s",
            action,
            type(exc).__name__,
        )


# --- Reading a clinic's trail -------------------------------------------------------------

MAX_PAGE = 200


@dataclass(frozen=True)
class AuditPage:
    events: list[AuditEvent]
    # Opaque position of the last event on this page; None when nothing older is left.
    next_cursor: str | None


def _encode_cursor(event: AuditEvent) -> str:
    raw = f"{event.created_at.isoformat()}|{event.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        stamp, _, ident = raw.partition("|")
        at = datetime.fromisoformat(stamp)
        if at.tzinfo is None:
            raise ValueError("naive timestamp")
        return at, uuid.UUID(ident)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationFailed("invalid cursor") from exc


def is_read_action() -> Any:
    """Staff reads and listings (`*.read`, `*.list`) — the bulk of a trail. A patient opening
    their released report (`report.patient_view`) is not one of them."""
    return or_(
        AuditEvent.action.endswith(".read", autoescape=True),
        AuditEvent.action.endswith(".list", autoescape=True),
    )


def list_tenant_events(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
    cursor: str | None = None,
    category: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    exclude_reads: bool = False,
) -> AuditPage:
    """One page of a clinic's audit events, newest first.

    The tenant filter is explicit and exact. Row-level security alone is NOT enough here: its
    read policy also lets tenant-less events through (sign-ins and denials recorded before a
    clinic is selected — of every user of the platform), and those belong to no clinic.
    """
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if category:
        # "report" selects report.approved, report.released, …; an action without a dot
        # ("rate_limited") is its own category.
        query = query.where(
            or_(
                AuditEvent.action == category,
                AuditEvent.action.startswith(f"{category}.", autoescape=True),
            )
        )
    if actor_user_id is not None:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if target_id is not None:
        query = query.where(AuditEvent.target_id == target_id)
    if since is not None:
        query = query.where(AuditEvent.created_at >= since)
    if until is not None:
        query = query.where(AuditEvent.created_at < until)
    if exclude_reads:
        query = query.where(not_(is_read_action()))
    if cursor:
        at, ident = _decode_cursor(cursor)
        # Keyset: strictly older than the last event already shown. Events written in one
        # transaction share a timestamp; the id breaks the tie, so no event is skipped or shown
        # twice however many are appended while someone pages.
        query = query.where(
            or_(
                AuditEvent.created_at < at,
                and_(AuditEvent.created_at == at, AuditEvent.id < ident),
            )
        )
    size = max(1, min(limit, MAX_PAGE))
    rows = list(
        db.execute(
            query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(size + 1)
        ).scalars()
    )
    page = rows[:size]
    return AuditPage(
        events=page, next_cursor=_encode_cursor(page[-1]) if len(rows) > size else None
    )
