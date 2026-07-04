"""DB-enforce the closed vocabulary on every remaining native_enum=False enum column.

SQLAlchemy 2.x creates NO CHECK for `native_enum=False` enum columns by default
(`create_constraint=False`), so until now the closed vocabularies were enforced at the
Python layer only — contrary to the `pg_enum` intent. Migration 0009 added the CHECK for
`memberships.role` and 0013 for `staff_invitations.role`; this migration extends the same
treatment to the remaining 28 enum columns, so the database itself rejects any value outside
the closed set (doctrine: vocabularies are closed). Tracked in docs/notes/0006-review-followups.md.

A plain `col IN (...)` CHECK passes on NULL (NULL IN (...) is NULL, not FALSE), so the two
nullable columns (kpi_catalog.value_kind, kpi_catalog.comparison_policy) keep allowing NULL.
Values are hard-coded as of this revision; a future enum value is added by a new migration.

Revision ID: 0014_enum_check_constraints
Revises: 0013_staff_invitations
"""

from __future__ import annotations

from alembic import op

revision = "0014_enum_check_constraints"
down_revision = "0013_staff_invitations"
branch_labels = None
depends_on = None

# (table, column, allowed values). Excludes memberships.role (0009) and
# staff_invitations.role (0013), which already carry the CHECK.
_ENUM_COLUMNS: list[tuple[str, str, list[str]]] = [
    ("kpi_catalog_release", "status", ["draft", "active", "retired"]),
    (
        "kpi_catalog",
        "primary_domain_axis",
        [
            "metabolic",
            "immune_inflammation",
            "cardiovascular",
            "neurocognitive",
            "musculoskeletal",
            "regenerative_capacity",
        ],
    ),
    (
        "kpi_catalog",
        "measurement_class",
        [
            "laboratory",
            "vital_sign",
            "anthropometric",
            "body_composition",
            "functional_test",
            "wearable",
            "imaging",
            "derived",
            "omics",
        ],
    ),
    ("kpi_catalog", "value_kind", ["quantity", "count", "duration", "ratio", "score", "panel"]),
    ("kpi_catalog", "tier", ["core", "extended", "specialist", "research"]),
    (
        "kpi_catalog",
        "comparison_policy",
        [
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
        ],
    ),
    ("kpi_catalog", "status", ["active", "deprecated", "blocked"]),
    ("staff_invitations", "status", ["pending", "redeemed", "revoked", "expired"]),
    ("consent_events", "purpose", ["report_release", "analytics", "data_source_connect"]),
    ("consent_events", "event_type", ["granted", "withdrawn"]),
    ("consent_records", "status", ["active", "withdrawn"]),
    ("kpi_external_code", "verification_status", ["verified", "pending", "rejected"]),
    (
        "kpi_secondary_domain",
        "domain_axis",
        [
            "metabolic",
            "immune_inflammation",
            "cardiovascular",
            "neurocognitive",
            "musculoskeletal",
            "regenerative_capacity",
        ],
    ),
    ("patient_invitations", "status", ["pending", "redeemed", "revoked", "expired"]),
    ("reports", "status", ["draft_generated", "draft_edited", "approved", "released", "rejected"]),
    (
        "domain_axis_interpretations",
        "domain_axis",
        [
            "metabolic",
            "immune_inflammation",
            "cardiovascular",
            "neurocognitive",
            "musculoskeletal",
            "regenerative_capacity",
        ],
    ),
    (
        "domain_axis_interpretations",
        "cis_status",
        [
            "CIS_0_INSUFFICIENT_EVIDENCE",
            "CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY",
            "CIS_2_NOT_YET_CREDIBLE",
            "CIS_3_RISK_DOMINANT_OR_CONFLICTING",
            "CIS_4_CREDIBLE_IMPROVEMENT",
            "CIS_5_STABLE_NO_MATERIAL_CHANGE",
        ],
    ),
    (
        "domain_axis_interpretations",
        "actionability_class",
        [
            "A_DISCOVERY",
            "B_SUPPORTIVE",
            "C_CLINICALLY_INTERPRETABLE",
            "D_ACTIONABLE_UNDER_GOVERNANCE",
            "E_DO_NOT_ACT",
        ],
    ),
    (
        "domain_axis_interpretations",
        "followup_adequacy",
        ["adequate", "inadequate", "not_assessed"],
    ),
    ("domain_axis_interpretations", "review_status", ["draft", "clinician_reviewed"]),
    (
        "import_jobs",
        "status",
        [
            "received",
            "stored",
            "extracted",
            "mapped",
            "validated",
            "review_required",
            "ready",
            "published",
            "rejected",
        ],
    ),
    (
        "observations",
        "source_category",
        [
            "laboratory",
            "vital_sign",
            "anthropometric",
            "body_composition",
            "functional_test",
            "wearable",
            "imaging",
            "derived",
            "omics",
        ],
    ),
    ("observations", "value_type", ["numeric", "text", "coded"]),
    ("observations", "review_status", ["pending", "published", "rejected"]),
    (
        "report_versions",
        "status",
        ["draft_generated", "draft_edited", "approved", "released", "rejected"],
    ),
    (
        "import_rows",
        "status",
        [
            "received",
            "stored",
            "extracted",
            "mapped",
            "validated",
            "review_required",
            "ready",
            "published",
            "rejected",
        ],
    ),
    ("tri_state_cells", "tri_state_axis", ["biological", "risk", "functional"]),
    ("tri_state_cells", "endpoint_adequacy", ["adequate", "inadequate", "not_assessed"]),
]


def upgrade() -> None:
    for table, column, values in _ENUM_COLUMNS:
        allowed = ", ".join(f"'{v}'" for v in values)
        # Bare column name → the metadata naming convention expands it to ck_<table>_<column>.
        op.create_check_constraint(column, table, f"{column} IN ({allowed})")


def downgrade() -> None:
    for table, column, _values in _ENUM_COLUMNS:
        # Bare column name again: the naming convention expands it to ck_<table>_<column>,
        # the same name upgrade() created (passing the full name would double-template it).
        op.drop_constraint(column, table, type_="check")
