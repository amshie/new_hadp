"""Patient-erasure request (tenant-scoped, RLS-protected).

A `DeletionRequest` is the authorization record for erasing a patient's data. It is a
two-person gate (owner requests → medical director decides → gated execution) and is
operationally MUTABLE through its lifecycle (pending → approved/rejected/cancelled →
executed); the immutable record of each transition is the append-only audit trail, exactly
like `patient_invitations`.

`patient_id` / `tenant_id` are ON DELETE RESTRICT: erasure tombstones the patient row
(anonymizes it) rather than deleting it, so this request keeps pointing at a real,
anonymized patient — and neither a patient nor a tenant can be hard-deleted out from under
an open request. The request row itself carries NO free text (reason is a closed enum) and
NO identity — only IDs, a closed-enum status/reason, actor IDs, timestamps, and a
count-only erasure manifest — so it can never leak PII.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import DeletionReasonCategory, DeletionRequestStatus, pg_enum


class DeletionRequest(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "deletion_requests"
    # At most one NON-TERMINAL request per patient is enforced by a partial unique index in
    # migration 0015 (WHERE status IN ('pending','approved')); this composite index serves the
    # tenant-scoped list + the per-patient lookup.
    __table_args__ = (Index("ix_deletion_requests_tenant_patient", "tenant_id", "patient_id"),)

    # No per-column index: the composite (tenant_id, patient_id) index above serves both the
    # tenant-scoped list and the per-patient lookup (tenant_id is its leading column).
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[DeletionRequestStatus] = mapped_column(
        pg_enum(DeletionRequestStatus), nullable=False, default=DeletionRequestStatus.PENDING
    )
    reason_category: Mapped[DeletionReasonCategory] = mapped_column(
        pg_enum(DeletionReasonCategory), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Count-only summary of what an execution erased (set by the erasure engine, PR B). NEVER
    # contains identifiers or values — only per-artefact-type counts.
    erasure_manifest: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
