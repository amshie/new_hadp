"""Lab intake agent: the laboratory on a batch, shadow mode, auto-acceptance rules.

docs/product/INTAKE_AGENT.md, slice 5.

- `intake_batches.source_lab`: the laboratory as the document names it (proposed, like every
  other field of a batch), the stratum of the error-rate report. `intake_batches.shadow`: a
  batch produced to be compared with independently keyed values — never shown on the
  confirmation screen, never decided.
- `intake_auto_accept_rules`: per clinic, laboratory and KPI, whether green values may be
  confirmed without a human, under which measured error rate, over which sample, and with which
  audit sample still routed to a human. Tenant-scoped, append-only: a change is a new row, the
  newest row per stratum counts. A rule is INERT unless the deployment's global switch
  (`INTAKE_AUTO_ACCEPT_ENABLED`) is on — it ships off.
- `intake_decisions.auto_accept_rule_id`: set when a decision was made by a rule, not a person;
  `decided_by_user_id` is then the person who signed the rule.

Revision ID: 0026_intake_governance
Revises: 0025_intake_page_sources
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_intake_governance"
down_revision = "0025_intake_page_sources"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    op.add_column("intake_batches", sa.Column("source_lab", sa.String(length=200), nullable=True))
    op.add_column(
        "intake_batches",
        sa.Column("shadow", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "intake_auto_accept_rules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("source_lab", sa.String(length=200), nullable=False),
        sa.Column("kpi_code", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("max_green_error_rate", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("min_sample", sa.Integer(), nullable=False),
        sa.Column("audit_sample_rate", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("signed_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_intake_auto_accept_rules_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kpi_code"],
            ["kpi_catalog.code"],
            name=op.f("fk_intake_auto_accept_rules_kpi_code_kpi_catalog"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"],
            ["users.id"],
            name=op.f("fk_intake_auto_accept_rules_signed_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intake_auto_accept_rules")),
    )
    op.create_index(
        op.f("ix_intake_auto_accept_rules_tenant_id"), "intake_auto_accept_rules", ["tenant_id"]
    )
    op.create_check_constraint(
        "rates_in_unit_interval",
        "intake_auto_accept_rules",
        "max_green_error_rate BETWEEN 0 AND 1 AND audit_sample_rate BETWEEN 0 AND 1",
    )
    # An audit sample of zero would let a rule run unwatched: never.
    op.create_check_constraint(
        "audit_sample_positive", "intake_auto_accept_rules", "audit_sample_rate > 0"
    )
    op.create_check_constraint("min_sample_positive", "intake_auto_accept_rules", "min_sample >= 1")
    op.execute("GRANT SELECT, INSERT ON intake_auto_accept_rules TO hadp_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON intake_auto_accept_rules FROM hadp_app")
    op.execute("ALTER TABLE intake_auto_accept_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE intake_auto_accept_rules FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON intake_auto_accept_rules "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )
    op.execute(
        "CREATE TRIGGER intake_auto_accept_rules_append_only "
        "BEFORE UPDATE OR DELETE ON intake_auto_accept_rules "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_intake_mutation()"
    )

    op.add_column("intake_decisions", sa.Column("auto_accept_rule_id", sa.UUID(), nullable=True))
    # A short explicit name: the convention's would exceed PostgreSQL's 63 characters.
    op.create_foreign_key(
        op.f("fk_intake_decisions_auto_accept_rule"),
        "intake_decisions",
        "intake_auto_accept_rules",
        ["auto_accept_rule_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # A rule only ever confirms; a correction or a rejection is a person's.
    op.create_check_constraint(
        "rule_only_confirms",
        "intake_decisions",
        "auto_accept_rule_id IS NULL OR decision = 'confirmed'",
    )


def downgrade() -> None:
    op.drop_constraint("rule_only_confirms", "intake_decisions", type_="check")
    op.drop_constraint(
        op.f("fk_intake_decisions_auto_accept_rule"), "intake_decisions", type_="foreignkey"
    )
    op.drop_column("intake_decisions", "auto_accept_rule_id")
    op.execute(
        "DROP TRIGGER IF EXISTS intake_auto_accept_rules_append_only ON intake_auto_accept_rules"
    )
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON intake_auto_accept_rules")
    op.drop_table("intake_auto_accept_rules")
    op.drop_column("intake_batches", "shadow")
    op.drop_column("intake_batches", "source_lab")
