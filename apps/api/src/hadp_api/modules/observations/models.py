"""Observations.

An observation retains BOTH the source representation (original value/unit/name and
reference text, immutable) and the normalized representation. Corrections create a new
row via `supersedes_observation_id`; provenance is never silently overwritten.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import KpiMeasurementClass, ReviewStatus, ValueType, pg_enum


class Observation(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "observations"
    __table_args__ = (
        # A derived value must carry the formula that produced it (ADR-0004 §8, Slice 4).
        CheckConstraint(
            "source_category <> 'derived' OR formula_id IS NOT NULL",
            name="ck_observations_derived_formula",
        ),
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
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True
    )
    source_record_locator: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Source representation (immutable) ---
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_value: Mapped[str] = mapped_column(String(120), nullable=False)
    original_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Terminology mapping ---
    # `metric_code` stays the SOURCE/LOINC code; `kpi_code` is the canonical KPI-catalog linkage
    # (ADR-0004 M3), set by the normalizer. Additive; readers still use metric_code.
    metric_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    code_system: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kpi_code: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="SET NULL"), nullable=True
    )
    mapping_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Measurement provenance / context (ADR-0004 §5/§8, Slice 3) ---
    # The ACTUAL measured-as class + the source-supplied context. Recorded only when the source
    # provides it, NEVER inferred (§9.8). Nullable = "unknown"; longitudinal comparability is
    # withheld when a context the KPI's comparison policy requires is missing or differs (§9).
    source_category: Mapped[KpiMeasurementClass | None] = mapped_column(
        pg_enum(KpiMeasurementClass), nullable=True
    )
    source_system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    method: Mapped[str | None] = mapped_column(String(120), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    firmware_or_algorithm_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    instrument_version: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # --- Derivation provenance (ADR-0004 §8/§10, Slice 4) ---
    # For a derived value (source_category='derived'): a FROZEN snapshot of the formula that made it
    # (copied at compute time, NOT read live from the mutable catalog). The immutable input IDs
    # live in the append-only `observation_derivation` table. formula_version is the comparability
    # key (two derived values only trend if computed by the same version).
    formula_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    formula_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    algorithm_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Normalized representation ---
    value_type: Mapped[ValueType] = mapped_column(pg_enum(ValueType), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    text_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    coded_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalization_version: Mapped[str] = mapped_column(String(40), nullable=False)

    # --- Timing ---
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # True when the source provided a date only; renderers must not show an invented time.
    observed_at_is_date_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    review_status: Mapped[ReviewStatus] = mapped_column(pg_enum(ReviewStatus), nullable=False)

    # Set when this observation corrects/supersedes a prior one.
    supersedes_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("observations.id", ondelete="SET NULL"), nullable=True
    )
