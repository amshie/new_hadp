"""derived observations: formula provenance + immutable input lineage (ADR-0004 Slice 4)

Additive nullable provenance columns on the tenant `observations` table (formula_id, formula_version,
algorithm_name) — a frozen snapshot of the formula that produced a derived value — plus a CHECK that a
`source_category='derived'` row carries a formula_id. A new tenant-scoped, RLS, APPEND-ONLY join table
`observation_derivation` pins the immutable input Observation IDs (M:N + role) per ADR-0004 §8.
`observations` keeps app DML (tenant table, no REVOKE); the join table is append-only (recompute =
new derived row + new links), mirroring the 0003 interpretation pattern.

Revision ID: 0007_derived_observations
Revises: 0006_observation_context
Create Date: 2026-06-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_derived_observations"
down_revision: str | None = "0006_observation_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    # 1) Additive nullable provenance on the tenant observations table (no REVOKE — app keeps DML).
    op.add_column("observations", sa.Column("formula_id", sa.String(length=80), nullable=True))
    op.add_column("observations", sa.Column("formula_version", sa.String(length=40), nullable=True))
    op.add_column("observations", sa.Column("algorithm_name", sa.String(length=120), nullable=True))
    op.create_check_constraint(
        op.f("ck_observations_derived_formula"),
        "observations",
        "source_category <> 'derived' OR formula_id IS NOT NULL",
    )

    # 2) Immutable input lineage for derived values (tenant-scoped, RLS, append-only).
    op.create_table(
        "observation_derivation",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("derived_observation_id", sa.UUID(), nullable=False),
        sa.Column("input_observation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=60), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_observation_derivation_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["derived_observation_id"],
            ["observations.id"],
            name=op.f("fk_observation_derivation_derived_observation_id_observations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["input_observation_id"],
            ["observations.id"],
            name=op.f("fk_observation_derivation_input_observation_id_observations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observation_derivation")),
        sa.UniqueConstraint(
            "derived_observation_id",
            "input_observation_id",
            "role",
            name=op.f("uq_observation_derivation_derived_observation_id"),
        ),
    )
    op.create_index(
        op.f("ix_observation_derivation_derived_observation_id"),
        "observation_derivation",
        ["derived_observation_id"],
    )
    op.create_index(
        op.f("ix_observation_derivation_input_observation_id"),
        "observation_derivation",
        ["input_observation_id"],
    )
    op.create_index(
        op.f("ix_observation_derivation_tenant_id"), "observation_derivation", ["tenant_id"]
    )

    # Grants + RLS (ENABLE + FORCE + one ALL policy), mirroring 0003.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON observation_derivation TO hadp_app")
    op.execute("ALTER TABLE observation_derivation ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE observation_derivation FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON observation_derivation "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )

    # Append-only: derivation lineage is immutable (recompute = new derived row + new links).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_derivation_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON observation_derivation FROM hadp_app")
    op.execute(
        "CREATE TRIGGER observation_derivation_append_only "
        "BEFORE UPDATE OR DELETE ON observation_derivation "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_derivation_mutation()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS observation_derivation_append_only ON observation_derivation"
    )
    op.execute("DROP FUNCTION IF EXISTS hadp_block_derivation_mutation()")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON observation_derivation")
    op.execute("ALTER TABLE observation_derivation NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE observation_derivation DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        op.f("ix_observation_derivation_tenant_id"), table_name="observation_derivation"
    )
    op.drop_index(
        op.f("ix_observation_derivation_input_observation_id"), table_name="observation_derivation"
    )
    op.drop_index(
        op.f("ix_observation_derivation_derived_observation_id"),
        table_name="observation_derivation",
    )
    op.drop_table("observation_derivation")
    op.drop_constraint(op.f("ck_observations_derived_formula"), "observations", type_="check")
    op.drop_column("observations", "algorithm_name")
    op.drop_column("observations", "formula_version")
    op.drop_column("observations", "formula_id")
