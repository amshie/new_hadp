"""interpretation model: runs, per-axis verdicts (CIS + Actionability), verdict-free cells

Adopts the HADP governance interpretation model (ADR-0003): per patient run, six
`domain_axis_interpretations` (one CIS + one Actionability each, two disjoint closed enums) and
eighteen verdict-free `tri_state_cells`. Runs and cells are append-only (trigger + REVOKE); the
per-axis verdict is a mutable review projection. All three tables are tenant-scoped under RLS.

Revision ID: 0003_interpretation_axes
Revises: 0002_security_rls
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_interpretation_axes"
down_revision: str | None = "0002_security_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_TABLES = ["interpretation_runs", "domain_axis_interpretations", "tri_state_cells"]
_APPEND_ONLY_TABLES = ["interpretation_runs", "tri_state_cells"]
_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

_DOMAIN_AXES = (
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
)
_CIS = (
    "CIS_0_INSUFFICIENT_EVIDENCE",
    "CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY",
    "CIS_2_NOT_YET_CREDIBLE",
    "CIS_3_RISK_DOMINANT_OR_CONFLICTING",
    "CIS_4_CREDIBLE_IMPROVEMENT",
    "CIS_5_STABLE_NO_MATERIAL_CHANGE",
)
_ACTIONABILITY = (
    "A_DISCOVERY",
    "B_SUPPORTIVE",
    "C_CLINICALLY_INTERPRETABLE",
    "D_ACTIONABLE_UNDER_GOVERNANCE",
    "E_DO_NOT_ACT",
)
_ADEQUACY = ("adequate", "inadequate", "not_assessed")
_REVIEW = ("draft", "clinician_reviewed")
_TRI_AXES = ("biological", "risk", "functional")
# Union of legal cell states (axis-correctness is enforced at the service layer).
_CELL_STATES = (
    "IMPROVED",
    "STABLE",
    "WORSENED",
    "MIXED",
    "INDETERMINATE",
    "REDUCED",
    "DOMINANT",
    "UNRESOLVED",
    "CONFLICTING",
)


def _enum(*values: str, name: str, length: int = 40) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=length)


def upgrade() -> None:
    op.create_table(
        "interpretation_runs",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_run_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_interpretation_runs_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_run_id"],
            ["interpretation_runs.id"],
            name=op.f("fk_interpretation_runs_supersedes_run_id_interpretation_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_interpretation_runs_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_interpretation_runs_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interpretation_runs")),
        sa.UniqueConstraint(
            "patient_id", "run_number", name=op.f("uq_interpretation_runs_patient_id")
        ),
    )
    op.create_index(
        op.f("ix_interpretation_runs_patient_id"), "interpretation_runs", ["patient_id"]
    )
    op.create_index(
        op.f("ix_interpretation_runs_tenant_id"), "interpretation_runs", ["tenant_id"]
    )

    op.create_table(
        "domain_axis_interpretations",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("interpretation_run_id", sa.UUID(), nullable=False),
        sa.Column("domain_axis", _enum(*_DOMAIN_AXES, name="domainaxis"), nullable=False),
        sa.Column("cis_status", _enum(*_CIS, name="cisstatus", length=60), nullable=False),
        sa.Column(
            "actionability_class",
            _enum(*_ACTIONABILITY, name="actionabilityclass"),
            nullable=False,
        ),
        sa.Column("followup_adequacy", _enum(*_ADEQUACY, name="adequacystatus"), nullable=False),
        sa.Column("rationale", sa.String(length=2000), nullable=True),
        sa.Column(
            "review_status",
            _enum(*_REVIEW, name="interpretationreviewstatus"),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interpretation_run_id"],
            ["interpretation_runs.id"],
            name=op.f("fk_domain_axis_interpretations_interpretation_run_id_interpretation_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name=op.f("fk_domain_axis_interpretations_reviewed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_domain_axis_interpretations_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_domain_axis_interpretations_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domain_axis_interpretations")),
        sa.UniqueConstraint(
            "interpretation_run_id",
            "domain_axis",
            name=op.f("uq_domain_axis_interpretations_interpretation_run_id"),
        ),
    )
    op.create_index(
        op.f("ix_domain_axis_interpretations_interpretation_run_id"),
        "domain_axis_interpretations",
        ["interpretation_run_id"],
    )
    op.create_index(
        op.f("ix_domain_axis_interpretations_tenant_id"),
        "domain_axis_interpretations",
        ["tenant_id"],
    )

    op.create_table(
        "tri_state_cells",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("domain_axis_interpretation_id", sa.UUID(), nullable=False),
        sa.Column("tri_state_axis", _enum(*_TRI_AXES, name="tristateaxis"), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("endpoint_adequacy", _enum(*_ADEQUACY, name="adequacystatus"), nullable=False),
        sa.Column(
            "evidence_refs",
            sa.dialects.postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("rationale", sa.String(length=2000), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{s}'" for s in _CELL_STATES) + ")",
            name=op.f("ck_tri_state_cells_cell_state_vocab"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_axis_interpretation_id"],
            ["domain_axis_interpretations.id"],
            name=op.f("fk_tri_state_cells_domain_axis_interpretation_id_domain_axis_interpretations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tri_state_cells_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tri_state_cells")),
        sa.UniqueConstraint(
            "domain_axis_interpretation_id",
            "tri_state_axis",
            name=op.f("uq_tri_state_cells_domain_axis_interpretation_id"),
        ),
    )
    op.create_index(
        op.f("ix_tri_state_cells_domain_axis_interpretation_id"),
        "tri_state_cells",
        ["domain_axis_interpretation_id"],
    )
    op.create_index(op.f("ix_tri_state_cells_tenant_id"), "tri_state_cells", ["tenant_id"])

    # Grants (explicit; ALTER DEFAULT PRIVILEGES from 0002 also covers future tables).
    for table in _TENANT_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO hadp_app")

    # RLS: ENABLE + FORCE + a single ALL policy scoping reads (USING) and writes (WITH CHECK).
    for table in _TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )

    # Append-only: runs and cells are immutable (corrections create a NEW run). The per-axis
    # verdict (domain_axis_interpretations) stays a mutable review projection.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_interpretation_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in _APPEND_ONLY_TABLES:
        op.execute(f"REVOKE UPDATE, DELETE ON {table} FROM hadp_app")
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION hadp_block_interpretation_mutation()"
        )


def downgrade() -> None:
    for table in _APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS hadp_block_interpretation_mutation()")
    for table in _TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("tri_state_cells")
    op.drop_table("domain_axis_interpretations")
    op.drop_table("interpretation_runs")
