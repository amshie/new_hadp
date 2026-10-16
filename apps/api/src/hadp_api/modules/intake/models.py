"""Lab intake agent — ORM.

Three tables:

- `intake_batches` — one run of the extraction over one stored document: which provider,
  model and prompt proposed the values, and what the document said about the patient. Tenant-
  scoped, append-only.
- `pending_values` — one proposed value each: the text as the model read it, where on the
  page it read it, the model's confidence, what the deterministic checks made of it, and the
  resulting status. Tenant-scoped, append-only. Written only by `intake.service` — the model
  never sets `status`, `kpi_code` or `checks`; the service computes them.
- `kpi_plausibility_bounds` — per KPI, the bounds outside which a value cannot be a reading
  from a living person, and the relative change beyond which a human looks. Global reference
  data like the KPI catalog: NO tenant_id, read-only for the application role, seeded from
  `bounds_data.py`. A bound is a clinical statement and is recorded with who signed it; the
  seed ships EMPTY until a clinician signs bounds (CLASSIFICATION_REGISTER).

What a human later decides about a pending value is a separate append-only record (a later
slice); a pending value is never updated.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import PendingValueStatus, pg_enum


class IntakeBatch(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "intake_batches"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Who ran the extraction (the staff member whose request started it). The model is not an
    # actor: it has no identity the audit trail could carry.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    # The extraction that proposed the values — versioned so every proposal is reproducible
    # and every error rate is attributable (provider, model, prompt).
    extraction_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    # What the document says about itself and its patient, as proposed. Compared by the
    # checks against the record, never trusted.
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_patient_date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    proposed_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Batch-level checks (patient match), same shape as a value's checks.
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    value_count: Mapped[int] = mapped_column(Integer, nullable=False)


class PendingValue(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "pending_values"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("page >= 1", name="page_positive"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- The proposal, as the model read the page (immutable; same limits as observations) ---
    proposed_analyte_text: Mapped[str] = mapped_column(String(200), nullable=False)
    proposed_value_text: Mapped[str] = mapped_column(String(120), nullable=False)
    proposed_unit_text: Mapped[str | None] = mapped_column(String(60), nullable=True)
    proposed_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proposed_observed_at_is_date_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    # The laboratory's reference interval, carried as written — never compared with the value.
    proposed_reference_low: Mapped[str | None] = mapped_column(String(60), nullable=True)
    proposed_reference_high: Mapped[str | None] = mapped_column(String(60), nullable=True)
    proposed_reference_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Provenance on the page: 1-based page, bounding box [x0, y0, x1, y1] in PDF points
    # (origin top-left of the page), when the provider gives one.
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    # --- What the deterministic checks made of it (computed by the service, never proposed) ---
    kpi_code: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="RESTRICT"), nullable=True
    )
    canonical_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_reference_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_reference_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[PendingValueStatus] = mapped_column(pg_enum(PendingValueStatus), nullable=False)


class KpiPlausibilityBound(TimestampCreated, Base):
    """Per KPI: the hard bounds of a reading from a living person and the relative change
    beyond which a human looks. Global, read-only reference data (no tenant_id, no RLS;
    REVOKE DML from hadp_app in the migration). Not a reference interval, not an "optimal"
    range: a value INSIDE the bounds says nothing; a value OUTSIDE cannot be a correct reading.
    """

    __tablename__ = "kpi_plausibility_bounds"
    __table_args__ = (
        CheckConstraint(
            "hard_low IS NULL OR hard_high IS NULL OR hard_low < hard_high", name="low_below_high"
        ),
        CheckConstraint(
            "delta_max_relative IS NULL OR delta_max_relative > 0", name="delta_positive"
        ),
    )

    kpi_code: Mapped[str] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="RESTRICT"), primary_key=True
    )
    # The unit the bounds are stated in — the KPI's canonical unit, checked at seed time.
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    hard_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    hard_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    # |new - last| / |last| above this asks a human to look (yellow). Null: no delta check.
    delta_max_relative: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    signed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bounds_version: Mapped[str] = mapped_column(String(40), nullable=False)
