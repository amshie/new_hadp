"""Source documents. The original file is stored before parsing; a content checksum
supports idempotent re-upload (CLAUDE.md ingestion rules)."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey


class SourceDocument(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "source_documents"
    # Idempotent re-upload: identical content within a tenant maps to one document.
    __table_args__ = (
        UniqueConstraint("tenant_id", "checksum_sha256", name="uq_source_document_tenant_checksum"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Object-storage key (private bucket; short-lived signed access only).
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
