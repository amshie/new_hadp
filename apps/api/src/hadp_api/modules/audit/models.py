"""Append-only audit events.

Append-only is enforced at the database level (a trigger blocks UPDATE/DELETE and the
app role lacks UPDATE/DELETE privileges). Audit detail must contain only identifiers,
codes, and timings — never names, emails, observation values, or document contents.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey


class AuditEvent(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "audit_events"

    # Null for pre-tenant-selection events (e.g. login). Tenant-scoped reads use RLS.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Non-sensitive structured context only (no PII / no health values).
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
