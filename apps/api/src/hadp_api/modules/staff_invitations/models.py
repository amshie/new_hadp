"""Staff-invitation model — a single-use credential that onboards a colleague into a role.

Mirrors PatientInvitation (only the SHA-256 token hash is stored; the row carries
redeem/revoke/expire lifecycle; the immutable record of every transition is the append-only
audit trail). The difference: the invitation carries the ROLE the owner chose, and redemption
creates a User + Membership (see the service). FKs are RESTRICT/SET NULL — never a cascade.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import InvitationStatus, Role, pg_enum


class StaffInvitation(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "staff_invitations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The role the owner grants. Fixed at invite time; the redeemer never chooses it.
    role: Mapped[Role] = mapped_column(pg_enum(Role), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Set on redemption: the user the colleague created for themselves (provenance link).
    redeemed_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[InvitationStatus] = mapped_column(pg_enum(InvitationStatus), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Whom the owner meant the link for, as they wrote it (migration 0021). Owners only; never
    # sent anything, never in an audit event.
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
