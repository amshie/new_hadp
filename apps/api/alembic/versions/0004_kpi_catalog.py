"""kpi catalog: global read-only KPI terminology layer (ADR-0004 Slice 1)

Four global, NON-tenant-scoped reference tables (kpi_catalog_release, kpi_catalog, kpi_external_code,
kpi_alias) + an additive nullable observations.kpi_code FK. The app role `hadp_app` is made
READ-ONLY on these tables via explicit REVOKE (the 0002 default-privileges grant DML on all/future
tables; M1). Data is seeded by hadp_api.modules.kpi.service.seed_kpi_catalog, not inline here.

Revision ID: 0004_kpi_catalog
Revises: 0003_interpretation_axes
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_kpi_catalog"
down_revision: str | None = "0003_interpretation_axes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATALOG_TABLES = ["kpi_catalog_release", "kpi_catalog", "kpi_external_code", "kpi_alias"]

_DOMAIN_AXES = (
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
)
_MEASUREMENT_CLASS = (
    "laboratory",
    "vital_sign",
    "anthropometric",
    "body_composition",
    "functional_test",
    "wearable",
    "imaging",
    "derived",
    "omics",
)
_VALUE_KIND = ("quantity", "count", "duration", "ratio", "score", "panel")
_TIER = ("core", "extended", "specialist", "research")
_COMPARISON_POLICY = (
    "method_aware",
    "same_method_required",
    "same_protocol_required",
    "same_device_protocol_required",
    "same_device_algorithm_required",
    "same_instrument_version_required",
    "same_imaging_protocol_required",
    "same_formula_version_required",
    "same_omics_platform_required",
    "not_longitudinal",
)
_STATUS = ("active", "deprecated", "blocked")
_EXT_STATUS = ("verified", "pending", "rejected")
_RELEASE_STATUS = ("draft", "active", "retired")


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=40)


def upgrade() -> None:
    op.create_table(
        "kpi_catalog_release",
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", _enum(*_RELEASE_STATUS, name="kpireleasestatus"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("version", name=op.f("pk_kpi_catalog_release")),
    )

    op.create_table(
        "kpi_catalog",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("primary_domain_axis", _enum(*_DOMAIN_AXES, name="domainaxis"), nullable=False),
        sa.Column(
            "measurement_class",
            _enum(*_MEASUREMENT_CLASS, name="kpimeasurementclass"),
            nullable=False,
        ),
        sa.Column("value_kind", _enum(*_VALUE_KIND, name="kpivaluekind"), nullable=True),
        sa.Column("canonical_unit_ucum", sa.String(length=40), nullable=True),
        sa.Column("display_unit", sa.String(length=40), nullable=True),
        sa.Column("tier", _enum(*_TIER, name="kpicatalogtier"), nullable=False),
        sa.Column("default_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_derived", sa.Boolean(), nullable=False),
        sa.Column("formula_id", sa.String(length=80), nullable=True),
        sa.Column(
            "comparison_policy",
            _enum(*_COMPARISON_POLICY, name="kpicomparisonpolicy"),
            nullable=True,
        ),
        sa.Column("clinician_visible", sa.Boolean(), nullable=False),
        sa.Column("patient_visible", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            _enum(*_STATUS, name="kpistatus"),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("introduced_in", sa.String(length=40), nullable=True),
        sa.Column("deprecated_in", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(is_derived AND formula_id IS NOT NULL) OR (NOT is_derived AND formula_id IS NULL)",
            name=op.f("ck_kpi_catalog_derived_formula"),
        ),
        sa.CheckConstraint(
            "value_kind IS DISTINCT FROM 'panel' OR canonical_unit_ucum IS NULL",
            name=op.f("ck_kpi_catalog_panel_unit"),
        ),
        sa.CheckConstraint(
            "tier NOT IN ('specialist', 'research') OR patient_visible = false",
            name=op.f("ck_kpi_catalog_restricted_not_patient_visible"),
        ),
        sa.ForeignKeyConstraint(
            ["introduced_in"],
            ["kpi_catalog_release.version"],
            name=op.f("fk_kpi_catalog_introduced_in_kpi_catalog_release"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["deprecated_in"],
            ["kpi_catalog_release.version"],
            name=op.f("fk_kpi_catalog_deprecated_in_kpi_catalog_release"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_kpi_catalog")),
    )

    op.create_table(
        "kpi_external_code",
        sa.Column("kpi_code", sa.String(length=80), nullable=False),
        sa.Column("code_system", sa.String(length=40), nullable=False),
        sa.Column("external_code", sa.String(length=60), nullable=False),
        sa.Column("mapping_context", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "verification_status",
            _enum(*_EXT_STATUS, name="kpiexternalcodestatus"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(length=120), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_kpi_external_code_kpi_code_kpi_catalog"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpi_external_code")),
        sa.UniqueConstraint(
            "code_system",
            "external_code",
            "kpi_code",
            name=op.f("uq_kpi_external_code_code_system"),
        ),
    )
    op.create_index(op.f("ix_kpi_external_code_kpi_code"), "kpi_external_code", ["kpi_code"])

    op.create_table(
        "kpi_alias",
        sa.Column("kpi_code", sa.String(length=80), nullable=False),
        sa.Column("alias_normalized", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=8), server_default=sa.text("'und'"), nullable=False),
        sa.Column(
            "source_system", sa.String(length=60), server_default=sa.text("''"), nullable=False
        ),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_kpi_alias_kpi_code_kpi_catalog"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpi_alias")),
        sa.UniqueConstraint(
            "alias_normalized", "source_system", name=op.f("uq_kpi_alias_alias_normalized")
        ),
    )
    op.create_index(op.f("ix_kpi_alias_kpi_code"), "kpi_alias", ["kpi_code"])

    # Additive linkage: observations.kpi_code -> kpi_catalog.code (M3). metric_code is unchanged.
    op.add_column("observations", sa.Column("kpi_code", sa.String(length=80), nullable=True))
    op.create_foreign_key(
        op.f("fk_observations_kpi_code_kpi_catalog"),
        "observations",
        "kpi_catalog",
        ["kpi_code"],
        ["code"],
        ondelete="SET NULL",
    )

    # M1: the catalog is READ-ONLY to the app role. 0002 granted full DML on all/future tables, so
    # explicitly revoke writes and (re)grant SELECT.
    for table in _CATALOG_TABLES:
        op.execute(f"REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON {table} FROM hadp_app")
        op.execute(f"GRANT SELECT ON {table} TO hadp_app")


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_observations_kpi_code_kpi_catalog"), "observations", type_="foreignkey"
    )
    op.drop_column("observations", "kpi_code")
    op.drop_index(op.f("ix_kpi_alias_kpi_code"), table_name="kpi_alias")
    op.drop_table("kpi_alias")
    op.drop_index(op.f("ix_kpi_external_code_kpi_code"), table_name="kpi_external_code")
    op.drop_table("kpi_external_code")
    op.drop_table("kpi_catalog")
    op.drop_table("kpi_catalog_release")
