"""kpi secondary domains: many-to-many secondary domain links for KPIs (ADR-0004 Slice 2)

A global, NON-tenant-scoped reference table. A KPI's primary domain lives on kpi_catalog; this holds
only the additional (secondary) domains where the same single Observation is relevant — navigational
evidence-visibility only (ADR-0004 §3/§15; ADR-0003). Read-only to the app role `hadp_app` via
explicit REVOKE (the 0002 default-privileges grant DML on all/future tables; M1). The `domain_axis`
CHECK reuses the existing closed DomainAxis value set (native_enum=False -> CHECK, no CREATE TYPE).
`domain_axis != primary` is enforced at seed time. Seeded by
hadp_api.modules.kpi.service.seed_secondary_domains, not inline here.

Revision ID: 0005_kpi_secondary_domain
Revises: 0004_kpi_catalog
Create Date: 2026-06-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_kpi_secondary_domain"
down_revision: str | None = "0004_kpi_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DOMAIN_AXES = (
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
)


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=40)


def upgrade() -> None:
    op.create_table(
        "kpi_secondary_domain",
        sa.Column("kpi_code", sa.String(length=80), nullable=False),
        sa.Column("domain_axis", _enum(*_DOMAIN_AXES, name="domainaxis"), nullable=False),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_kpi_secondary_domain_kpi_code_kpi_catalog"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kpi_code", "domain_axis", name=op.f("pk_kpi_secondary_domain")),
    )
    op.create_index(
        op.f("ix_kpi_secondary_domain_domain_axis"), "kpi_secondary_domain", ["domain_axis"]
    )

    # M1: the table is READ-ONLY to the app role. 0002 granted full DML on all/future tables, so
    # explicitly revoke writes and grant SELECT (mirrors 0004_kpi_catalog).
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON kpi_secondary_domain FROM hadp_app")
    op.execute("GRANT SELECT ON kpi_secondary_domain TO hadp_app")


def downgrade() -> None:
    op.drop_index(op.f("ix_kpi_secondary_domain_domain_axis"), table_name="kpi_secondary_domain")
    op.drop_table("kpi_secondary_domain")
