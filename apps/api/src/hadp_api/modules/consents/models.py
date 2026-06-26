"""Consent: an append-only, purpose-scoped event stream that gates patient-facing release.

`ConsentEvent` is the authoritative, APPEND-ONLY record (one purpose per row): a grant or an
attributable withdrawal is a NEW row, never an in-place mutation (mirrors the audit / interpretation
/ derivation streams). Current state for a (patient, purpose) is the latest event by `recorded_at`.
The legacy `ConsentRecord` (mutable) is retained inert for now and read by nothing; the gate reads
`ConsentEvent`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import ConsentEventType, ConsentPurpose, ConsentStatus, pg_enum


class ConsentRecord(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "consent_records"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_text_version: Mapped[str] = mapped_column(String(40), nullable=False)
    purposes: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[ConsentStatus] = mapped_column(
        pg_enum(ConsentStatus), nullable=False, default=ConsentStatus.ACTIVE
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ConsentEvent(UUIDPrimaryKey, TimestampCreated, Base):
    """Append-only consent state change, one purpose per row. DB-enforced immutable (migration 0008:
    REVOKE UPDATE/DELETE + BEFORE UPDATE OR DELETE trigger). A withdrawal is a new WITHDRAWN row."""

    __tablename__ = "consent_events"
    __table_args__ = (Index("ix_consent_events_patient_purpose", "patient_id", "purpose"),)

    # ON DELETE RESTRICT, not CASCADE: an append-only ledger must not be cascade-deleted (the
    # immutability trigger would turn a parent delete into a confusing abort). A patient/tenant
    # cannot be hard-deleted while consent events exist; real erasure is a gated DPO/counsel
    # process.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    purpose: Mapped[ConsentPurpose] = mapped_column(pg_enum(ConsentPurpose), nullable=False)
    event_type: Mapped[ConsentEventType] = mapped_column(pg_enum(ConsentEventType), nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(40), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
