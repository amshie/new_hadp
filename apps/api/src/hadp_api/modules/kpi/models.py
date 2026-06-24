"""KPI catalog ORM (ADR-0004) — global, read-only reference data.

Four tables, NO `tenant_id`, NOT in TENANT_TABLES, no RLS. The migration REVOKEs DML from `hadp_app`
and GRANTs SELECT only. Definitions only — no reference/optimal ranges, no scores, no
CIS/Actionability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import (
    DomainAxis,
    KpiCatalogTier,
    KpiComparisonPolicy,
    KpiExternalCodeStatus,
    KpiMeasurementClass,
    KpiReleaseStatus,
    KpiStatus,
    KpiValueKind,
    pg_enum,
)


class KpiCatalogRelease(TimestampCreated, Base):
    __tablename__ = "kpi_catalog_release"

    version: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[KpiReleaseStatus] = mapped_column(pg_enum(KpiReleaseStatus), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class KpiCatalog(TimestampCreated, Base):
    __tablename__ = "kpi_catalog"
    __table_args__ = (
        # is_derived <=> formula_id present.
        CheckConstraint(
            "(is_derived AND formula_id IS NOT NULL) OR (NOT is_derived AND formula_id IS NULL)",
            name="derived_formula",
        ),
        # A panel KPI has no canonical unit.
        CheckConstraint(
            "value_kind IS DISTINCT FROM 'panel' OR canonical_unit_ucum IS NULL",
            name="panel_unit",
        ),
        # Specialist/research KPIs are never patient-visible.
        CheckConstraint(
            "tier NOT IN ('specialist', 'research') OR patient_visible = false",
            name="restricted_not_patient_visible",
        ),
    )

    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_domain_axis: Mapped[DomainAxis] = mapped_column(pg_enum(DomainAxis), nullable=False)
    measurement_class: Mapped[KpiMeasurementClass] = mapped_column(
        pg_enum(KpiMeasurementClass), nullable=False
    )
    # value_kind / comparison_policy are populated in a later slice (ADR-0004 §0).
    value_kind: Mapped[KpiValueKind | None] = mapped_column(pg_enum(KpiValueKind), nullable=True)
    canonical_unit_ucum: Mapped[str | None] = mapped_column(String(40), nullable=True)
    display_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tier: Mapped[KpiCatalogTier] = mapped_column(pg_enum(KpiCatalogTier), nullable=False)
    default_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    formula_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comparison_policy: Mapped[KpiComparisonPolicy | None] = mapped_column(
        pg_enum(KpiComparisonPolicy), nullable=True
    )
    clinician_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    patient_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[KpiStatus] = mapped_column(
        pg_enum(KpiStatus), nullable=False, server_default=text("'active'")
    )
    introduced_in: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("kpi_catalog_release.version", ondelete="RESTRICT"), nullable=True
    )
    deprecated_in: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("kpi_catalog_release.version", ondelete="RESTRICT"), nullable=True
    )


class KpiExternalCode(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "kpi_external_code"
    __table_args__ = (
        UniqueConstraint("code_system", "external_code", "kpi_code", name="system_code_kpi"),
    )

    kpi_code: Mapped[str] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="CASCADE"), nullable=False, index=True
    )
    code_system: Mapped[str] = mapped_column(String(40), nullable=False)
    external_code: Mapped[str] = mapped_column(String(60), nullable=False)
    mapping_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    verification_status: Mapped[KpiExternalCodeStatus] = mapped_column(
        pg_enum(KpiExternalCodeStatus), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


class KpiAlias(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "kpi_alias"
    __table_args__ = (
        # A normalized alias maps to one KPI within a source-system namespace (collision = failure).
        UniqueConstraint("alias_normalized", "source_system", name="alias_namespace"),
    )

    kpi_code: Mapped[str] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="CASCADE"), nullable=False, index=True
    )
    alias_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'und'"))
    # Empty string = the global namespace (lets the unique constraint enforce global uniqueness).
    source_system: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default=text("''")
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class KpiSecondaryDomain(Base):
    """Secondary (non-primary) domain links for a KPI — navigational evidence-visibility only.

    A KPI's primary domain lives on `KpiCatalog`; this table holds only the additional domains where
    the same single Observation is relevant. The link never duplicates the Observation across
    domains (ADR-0004 §3/§15) and never feeds, weights or derives a domain's CIS/Actionability
    (ADR-0003 — verdicts stay per-axis, tri-state stays separate). The (kpi_code, domain_axis) pair
    is unique; `domain_axis != primary_domain_axis` is enforced at seed time (ADR-0004 §13).
    """

    __tablename__ = "kpi_secondary_domain"
    __table_args__ = (Index("ix_kpi_secondary_domain_domain_axis", "domain_axis"),)

    kpi_code: Mapped[str] = mapped_column(
        String(80), ForeignKey("kpi_catalog.code", ondelete="CASCADE"), primary_key=True
    )
    domain_axis: Mapped[DomainAxis] = mapped_column(pg_enum(DomainAxis), primary_key=True)
