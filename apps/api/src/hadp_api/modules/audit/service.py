"""Audit service: append-only event recording.

Callers pass identifiers, codes, and timings only. Detail must never contain names,
emails, observation values, free text, document contents, or secrets.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

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
