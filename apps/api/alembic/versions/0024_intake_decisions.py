"""Lab intake agent: the clinician's decisions on pending values.

docs/product/INTAKE_AGENT.md, slice 3. One row per decided pending value (UNIQUE), append-only
(trigger + REVOKE), tenant-scoped (RLS ENABLE + FORCE). A confirmed or corrected value points
at the observation it became; a rejected one carries its reason from a closed vocabulary.
Closed vocabularies are CHECK-enforced (0014).

Revision ID: 0024_intake_decisions
Revises: 0023_lab_intake
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0024_intake_decisions"
down_revision = "0023_lab_intake"
branch_labels = None
depends_on = None

_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"
_DECISIONS = ("confirmed", "corrected", "rejected")
_REASONS = ("not_on_document", "misread", "wrong_patient", "already_recorded", "other")


def _in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "intake_decisions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("pending_value_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=True),
        sa.Column("correction", JSONB(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=40), nullable=True),
        sa.Column("decided_by_user_id", sa.UUID(), nullable=False),
        sa.Column("review_seconds", sa.Integer(), nullable=True),
        sa.Column("screen_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_intake_decisions_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_intake_decisions_patient_id_patients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["intake_batches.id"],
            name=op.f("fk_intake_decisions_batch_id_intake_batches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pending_value_id"],
            ["pending_values.id"],
            name=op.f("fk_intake_decisions_pending_value_id_pending_values"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observations.id"],
            name=op.f("fk_intake_decisions_observation_id_observations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name=op.f("fk_intake_decisions_decided_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intake_decisions")),
        sa.UniqueConstraint("pending_value_id", name="uq_intake_decisions_pending_value_id"),
    )
    op.create_index(op.f("ix_intake_decisions_tenant_id"), "intake_decisions", ["tenant_id"])
    op.create_index(op.f("ix_intake_decisions_patient_id"), "intake_decisions", ["patient_id"])
    op.create_index(op.f("ix_intake_decisions_batch_id"), "intake_decisions", ["batch_id"])
    op.create_check_constraint("decision", "intake_decisions", f"decision IN ({_in(_DECISIONS)})")
    op.create_check_constraint(
        "rejection_reason",
        "intake_decisions",
        f"rejection_reason IS NULL OR rejection_reason IN ({_in(_REASONS)})",
    )
    op.create_check_constraint(
        "observation_iff_accepted",
        "intake_decisions",
        "(decision = 'rejected') = (observation_id IS NULL)",
    )
    op.create_check_constraint(
        "reason_iff_rejected",
        "intake_decisions",
        "(decision = 'rejected') = (rejection_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        "correction_iff_corrected",
        "intake_decisions",
        "(decision = 'corrected') = (correction IS NOT NULL)",
    )
    op.create_check_constraint(
        "seconds_range",
        "intake_decisions",
        "(review_seconds IS NULL OR review_seconds BETWEEN 0 AND 86400) AND "
        "(screen_seconds IS NULL OR screen_seconds BETWEEN 0 AND 86400)",
    )

    op.execute("GRANT SELECT, INSERT ON intake_decisions TO hadp_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON intake_decisions FROM hadp_app")
    op.execute("ALTER TABLE intake_decisions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE intake_decisions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON intake_decisions "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )
    # Reuses the trigger function of 0023.
    op.execute(
        "CREATE TRIGGER intake_decisions_append_only BEFORE UPDATE OR DELETE ON intake_decisions "
        "FOR EACH ROW EXECUTE FUNCTION hadp_block_intake_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS intake_decisions_append_only ON intake_decisions")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON intake_decisions")
    op.drop_table("intake_decisions")
