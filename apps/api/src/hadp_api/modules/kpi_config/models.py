"""Per-tenant KPI setting (tenant-scoped, RLS-protected).

One row overrides the global catalog's `default_enabled` and visibility flags for a single KPI
within a single clinic. No patient data and no free text — only IDs, booleans, and timestamps —
so the row can never carry PII. The global `kpi_catalog` is untouched (it stays read-only to the
app role); this is a per-tenant layer on top of it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey


class TenantKpiSetting(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "tenant_kpi_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kpi_code", name="uq_tenant_kpi_settings_tenant_kpi"),
        # A clinic reference is either fully absent or a complete, ordered two-sided interval.
        CheckConstraint(
            "(reference_low IS NULL AND reference_high IS NULL AND reference_unit IS NULL) "
            "OR (reference_low IS NOT NULL AND reference_high IS NOT NULL "
            "AND reference_unit IS NOT NULL AND reference_low < reference_high)",
            name="reference",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    kpi_code: Mapped[str] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="CASCADE"), nullable=False
    )
    # Per-tenant override of the catalog's global default_enabled.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # NULL => inherit the catalog's own visibility flag (no per-tenant change).
    patient_visible_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    clinician_visible_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Clinic-defined reference interval (fallback-only, position-only). Stored in the KPI's
    # canonical unit (reference_unit); applied only when a lab result carries no reference of its
    # own AND the observation's normalized unit matches. Never an "optimal" target, never a verdict.
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reference_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
