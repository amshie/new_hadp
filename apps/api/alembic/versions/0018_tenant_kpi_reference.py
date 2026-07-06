"""Clinic-defined KPI reference interval (per tenant) — additive, fallback-only, position-only.

Adds an optional clinic-defined reference interval to `tenant_kpi_settings`: `reference_low`,
`reference_high` (exact decimals, in the KPI's canonical unit) and `reference_unit`. This is a
NEUTRAL clinic reference used only as a FALLBACK for the within/above/below position marker when a
laboratory result carries no reference of its own — it never overwrites or hides the lab-provided
reference (which stays immutable on the observation), and it is never an "optimal"/normal target and
never a verdict or score (INTENDED_USE Prohibited: no optimal ranges). It touches clinical meaning,
so it is recorded in the classification register and gated on Regulatory-Lead sign-off before use
with real patient data.

A CHECK enforces the interval invariant at the DB: either all three columns are NULL (no clinic
reference) or all three are set with `reference_low < reference_high` (a meaningful two-sided
interval — a one-sided reference cannot place a value in an interval, so it is disallowed).

Revision ID: 0018_tenant_kpi_reference
Revises: 0017_tenant_kpi_settings
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_tenant_kpi_reference"
down_revision = "0017_tenant_kpi_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_kpi_settings",
        sa.Column("reference_low", sa.Numeric(), nullable=True),
    )
    op.add_column(
        "tenant_kpi_settings",
        sa.Column("reference_high", sa.Numeric(), nullable=True),
    )
    op.add_column(
        "tenant_kpi_settings",
        sa.Column("reference_unit", sa.String(length=40), nullable=True),
    )
    # All-or-nothing + two-sided-and-ordered: a clinic reference is either absent entirely or a
    # complete, meaningful interval. Prevents a one-sided or inverted reference reaching the
    # position marker.
    op.create_check_constraint(
        "reference",
        "tenant_kpi_settings",
        "(reference_low IS NULL AND reference_high IS NULL AND reference_unit IS NULL) "
        "OR (reference_low IS NOT NULL AND reference_high IS NOT NULL "
        "AND reference_unit IS NOT NULL AND reference_low < reference_high)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenant_kpi_settings_reference", "tenant_kpi_settings", type_="check")
    op.drop_column("tenant_kpi_settings", "reference_unit")
    op.drop_column("tenant_kpi_settings", "reference_high")
    op.drop_column("tenant_kpi_settings", "reference_low")
