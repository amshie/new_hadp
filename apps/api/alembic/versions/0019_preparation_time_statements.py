"""preparation_time_statements: the clinic's own statements of its preparation time.

Go-live plan A6 (the pilot's primary metric). One row is one statement by a clinic — the
baseline at onboarding or a later follow-up: a median in minutes, how the clinic arrived at it
(an estimate, or a timed sample of so many appointments), who recorded it and when. Timings and
identifiers only.

Tenant-scoped (RLS ENABLE + FORCE, one policy) and APPEND-ONLY like the consent stream
(0008): a wrong statement is corrected by a new one. The measured part of the metric — the
time from a report's first draft to its first approval — is derived from the report rows and
stores nothing here.

Revision ID: 0019_preparation_time_statements
Revises: 0018_observation_source_number
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_preparation_time_statements"
down_revision = "0018_observation_source_number"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

_KINDS = ("baseline", "follow_up")
_BASES = ("estimate", "timed_sample")


def _in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "preparation_time_statements",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("basis", sa.String(length=40), nullable=False),
        sa.Column("median_minutes", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("recorded_by_user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # RESTRICT on both: an append-only table cannot be cascade-deleted, and SET NULL would
        # be an UPDATE the trigger below refuses.
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_preparation_time_statements_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name=op.f("fk_preparation_time_statements_recorded_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preparation_time_statements")),
    )
    op.create_index(
        op.f("ix_preparation_time_statements_tenant_id"),
        "preparation_time_statements",
        ["tenant_id"],
    )
    # Bare names: the metadata naming convention expands them to ck_<table>_<name>.
    op.create_check_constraint("kind", "preparation_time_statements", f"kind IN ({_in(_KINDS)})")
    op.create_check_constraint("basis", "preparation_time_statements", f"basis IN ({_in(_BASES)})")
    op.create_check_constraint(
        "median_minutes_range", "preparation_time_statements", "median_minutes BETWEEN 1 AND 600"
    )
    op.create_check_constraint(
        "sample_size_only_for_timed_sample",
        "preparation_time_statements",
        "(basis = 'timed_sample') = (sample_size IS NOT NULL)",
    )
    op.create_check_constraint(
        "sample_size_range",
        "preparation_time_statements",
        "sample_size IS NULL OR sample_size BETWEEN 1 AND 100000",
    )

    # Read and append, nothing else. The REVOKE is not redundant: the schema's default
    # privileges hand the application role UPDATE and DELETE on every new table.
    op.execute("GRANT SELECT, INSERT ON preparation_time_statements TO hadp_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON preparation_time_statements FROM hadp_app")
    op.execute("ALTER TABLE preparation_time_statements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE preparation_time_statements FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON preparation_time_statements "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_preparation_statement_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER preparation_time_statements_append_only "
        "BEFORE UPDATE OR DELETE ON preparation_time_statements "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_preparation_statement_mutation()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS preparation_time_statements_append_only "
        "ON preparation_time_statements"
    )
    op.execute("DROP FUNCTION IF EXISTS hadp_block_preparation_statement_mutation()")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON preparation_time_statements")
    op.drop_table("preparation_time_statements")
