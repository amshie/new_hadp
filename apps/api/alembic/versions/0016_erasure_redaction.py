"""Gated erasure redaction: the ONE immutability-adjacent change (docs/notes/0012, PR B).

A GDPR Art. 17 erasure must remove a patient's PII. Most PII lives in mutable tables the app
can delete directly (observations, source_documents, imports, reports). But three append-only
tables hold patient PII that a delete/redact would otherwise be blocked from touching:

  - interpretation_runs.reason (NOT NULL free text) + tri_state_cells.rationale (free text) —
    append-only (REVOKE UPDATE/DELETE + trigger). Erasure must REDACT this free text in place.
  - observation_derivation — append-only lineage that CASCADES from observations; deleting a
    patient's observations would fire its trigger and abort. Erasure must DELETE the lineage.

This migration adds the ONLY sanctioned exception, narrowly and audibly:

  1. The two append-only trigger functions gain a single guarded branch: permit exactly the
     erasure operation (interpretation → UPDATE only; derivation → DELETE only) when a
     TRANSACTION-LOCAL GUC `app.erasure` is 'on'. Everything else still RAISEs — verdicts are
     never altered, interpretation rows are never deleted, and nothing is mutable outside an
     erasure. **consent_events and audit_events triggers are NOT touched.**
  2. A SECURITY DEFINER function `hadp_execute_patient_erasure(tenant, patient)` (owned by the
     migration superuser, so it clears the REVOKE) sets that GUC transaction-locally and performs
     ONLY the redaction/lineage-delete, every statement scoped by tenant_id AND patient_id
     (SECURITY DEFINER bypasses RLS, so explicit scoping is mandatory). EXECUTE is granted to the
     app role and to nobody else; the GUC is set nowhere else.

Revision ID: 0016_erasure_redaction
Revises: 0015_deletion_requests
"""

from __future__ import annotations

from alembic import op

revision = "0016_erasure_redaction"
down_revision = "0015_deletion_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1a. Interpretation: allow ONLY an in-place UPDATE (free-text redaction) under the erasure
    #     GUC. DELETE and any non-erasure UPDATE still RAISE (verdicts stay immutable).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_interpretation_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'UPDATE' AND current_setting('app.erasure', true) = 'on' THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    # 1b. Derivation: allow ONLY a DELETE (lineage pointing at erased observations) under the
    #     erasure GUC. UPDATE and any non-erasure DELETE still RAISE.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_derivation_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND current_setting('app.erasure', true) = 'on' THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # 2. The gated erasure primitive. SECURITY DEFINER (owner = migration superuser) so it holds
    #    UPDATE/DELETE despite the app-role REVOKE; every statement is scoped by tenant AND patient
    #    because SECURITY DEFINER runs with RLS bypassed. It sets the GUC transaction-locally, does
    #    the append-only-touching work, and resets the GUC.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_execute_patient_erasure(p_tenant_id uuid, p_patient_id uuid)
        RETURNS void AS $$
        BEGIN
          PERFORM set_config('app.erasure', 'on', true);

          -- Delete derivation lineage that references any of the patient's observations
          -- (append-only; the gated DELETE branch permits this).
          DELETE FROM observation_derivation
           WHERE tenant_id = p_tenant_id
             AND (derived_observation_id IN
                    (SELECT id FROM observations
                      WHERE patient_id = p_patient_id AND tenant_id = p_tenant_id)
                  OR input_observation_id IN
                    (SELECT id FROM observations
                      WHERE patient_id = p_patient_id AND tenant_id = p_tenant_id));

          -- Redact free text on the append-only interpretation tables (gated UPDATE).
          UPDATE interpretation_runs
             SET reason = '[erased]'
           WHERE tenant_id = p_tenant_id AND patient_id = p_patient_id;

          UPDATE tri_state_cells c
             SET rationale = NULL
            FROM domain_axis_interpretations d, interpretation_runs r
           WHERE c.domain_axis_interpretation_id = d.id
             AND d.interpretation_run_id = r.id
             AND r.patient_id = p_patient_id
             AND r.tenant_id = p_tenant_id
             AND d.tenant_id = p_tenant_id
             AND c.tenant_id = p_tenant_id;

          -- domain_axis_interpretations is mutable, but scrub its rationale here so all
          -- interpretation free-text redaction lives in one audited primitive.
          UPDATE domain_axis_interpretations d
             SET rationale = NULL
            FROM interpretation_runs r
           WHERE d.interpretation_run_id = r.id
             AND r.patient_id = p_patient_id
             AND r.tenant_id = p_tenant_id
             AND d.tenant_id = p_tenant_id;

          PERFORM set_config('app.erasure', 'off', true);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION hadp_execute_patient_erasure(uuid, uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION hadp_execute_patient_erasure(uuid, uuid) TO hadp_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS hadp_execute_patient_erasure(uuid, uuid)")
    # Restore the original unconditional append-only guards.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_interpretation_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION hadp_block_derivation_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
