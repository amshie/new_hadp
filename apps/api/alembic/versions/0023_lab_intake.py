"""Lab intake agent: proposed batches, pending values, plausibility bounds.

docs/product/INTAKE_AGENT.md. A model proposes values from a stored document; deterministic
checks record what they made of each one; a human confirms before anything becomes an
observation. This migration adds the three tables that hold the proposal side:

- `intake_batches` and `pending_values`: tenant-scoped (RLS ENABLE + FORCE, one policy) and
  APPEND-ONLY (trigger + REVOKE), like the consent stream (0008) and the preparation
  statements (0019). A proposal is a record of what a model read; it is never edited. What a
  human decides about it is a separate record in a later migration.
- `kpi_plausibility_bounds`: global reference data like the KPI catalog (0004) — no
  tenant_id, no RLS, read-only for `hadp_app` by explicit REVOKE. It ships EMPTY: a bound is
  a clinical statement, seeded only from a signed entry in `modules/intake/bounds_data.py`.

`pending_values.status` is a closed vocabulary (green / yellow / red), DB-enforced by CHECK
like every enum column (0014).

Revision ID: 0023_lab_intake
Revises: 0022_tenant_address
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0023_lab_intake"
down_revision = "0022_tenant_address"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"
_STATUS = ("green", "yellow", "red")
_APPEND_ONLY = ("intake_batches", "pending_values")


def upgrade() -> None:
    op.create_table(
        "intake_batches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("extraction_provider", sa.String(length=80), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("proposed_patient_date_of_birth", sa.Date(), nullable=True),
        sa.Column("proposed_issue_date", sa.Date(), nullable=True),
        sa.Column("checks", JSONB(), nullable=False),
        sa.Column("value_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_intake_batches_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_intake_batches_patient_id_patients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            name=op.f("fk_intake_batches_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_intake_batches_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intake_batches")),
    )
    op.create_index(op.f("ix_intake_batches_tenant_id"), "intake_batches", ["tenant_id"])
    op.create_index(op.f("ix_intake_batches_patient_id"), "intake_batches", ["patient_id"])
    op.create_index(
        op.f("ix_intake_batches_source_document_id"), "intake_batches", ["source_document_id"]
    )

    op.create_table(
        "pending_values",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("proposed_analyte_text", sa.String(length=200), nullable=False),
        sa.Column("proposed_value_text", sa.String(length=120), nullable=False),
        sa.Column("proposed_unit_text", sa.String(length=60), nullable=True),
        sa.Column("proposed_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_observed_at_is_date_only", sa.Boolean(), nullable=False),
        sa.Column("proposed_reference_low", sa.String(length=60), nullable=True),
        sa.Column("proposed_reference_high", sa.String(length=60), nullable=True),
        sa.Column("proposed_reference_text", sa.String(length=200), nullable=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("bbox", JSONB(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("kpi_code", sa.String(length=80), nullable=True),
        sa.Column("canonical_unit", sa.String(length=40), nullable=True),
        sa.Column("normalized_value", sa.Numeric(), nullable=True),
        sa.Column("normalized_reference_low", sa.Numeric(), nullable=True),
        sa.Column("normalized_reference_high", sa.Numeric(), nullable=True),
        sa.Column("checks", JSONB(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_pending_values_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_pending_values_patient_id_patients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["intake_batches.id"],
            name=op.f("fk_pending_values_batch_id_intake_batches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            name=op.f("fk_pending_values_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_pending_values_kpi_code_kpi_catalog"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pending_values")),
    )
    op.create_index(op.f("ix_pending_values_tenant_id"), "pending_values", ["tenant_id"])
    op.create_index(op.f("ix_pending_values_patient_id"), "pending_values", ["patient_id"])
    op.create_index(op.f("ix_pending_values_batch_id"), "pending_values", ["batch_id"])
    # Bare names: the naming convention expands them to ck_pending_values_<name>.
    op.create_check_constraint(
        "status", "pending_values", "status IN (" + ", ".join(f"'{s}'" for s in _STATUS) + ")"
    )
    op.create_check_constraint(
        "confidence_range", "pending_values", "confidence >= 0 AND confidence <= 1"
    )
    op.create_check_constraint("page_positive", "pending_values", "page >= 1")

    # Tenant isolation + append-only for the proposal tables. The REVOKE is not redundant:
    # the schema's default privileges hand the application role UPDATE and DELETE on every
    # new table (0002).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_intake_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in _APPEND_ONLY:
        op.execute(f"GRANT SELECT, INSERT ON {table} TO hadp_app")
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM hadp_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION hadp_block_intake_mutation()"
        )

    op.create_table(
        "kpi_plausibility_bounds",
        sa.Column("kpi_code", sa.String(length=80), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("hard_low", sa.Numeric(), nullable=True),
        sa.Column("hard_high", sa.Numeric(), nullable=True),
        sa.Column("delta_max_relative", sa.Numeric(), nullable=True),
        sa.Column("source", sa.String(length=500), nullable=False),
        sa.Column("signed_by", sa.String(length=120), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bounds_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_kpi_plausibility_bounds_kpi_code_kpi_catalog"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("kpi_code", name=op.f("pk_kpi_plausibility_bounds")),
    )
    op.create_check_constraint(
        "low_below_high",
        "kpi_plausibility_bounds",
        "hard_low IS NULL OR hard_high IS NULL OR hard_low < hard_high",
    )
    op.create_check_constraint(
        "delta_positive",
        "kpi_plausibility_bounds",
        "delta_max_relative IS NULL OR delta_max_relative > 0",
    )
    # Read-only reference data for the application role, like the catalog (0004 M1).
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON kpi_plausibility_bounds FROM hadp_app")
    op.execute("GRANT SELECT ON kpi_plausibility_bounds TO hadp_app")


def downgrade() -> None:
    op.drop_table("kpi_plausibility_bounds")
    for table in reversed(_APPEND_ONLY):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute("DROP FUNCTION IF EXISTS hadp_block_intake_mutation()")
    op.drop_table("pending_values")
    op.drop_table("intake_batches")
