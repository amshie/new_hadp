"""observation measurement context: provenance fields for §8/§9 non-merge (ADR-0004 Slice 3)

Seven additive, nullable columns on the tenant-scoped `observations` table — the actual measured-as
source category/system plus the comparability-relevant context (method, protocol, device, firmware/
algorithm version, instrument version). Recorded only when a source supplies them, never inferred
(§9.8). `observations` is a TENANT table under RLS with app DML already granted (0002), so there is
NO REVOKE here (that pattern is for the global read-only catalog only). `source_category` reuses the
closed KpiMeasurementClass value set as a CHECK enum (native_enum=False), same as the model.

Revision ID: 0006_observation_context
Revises: 0005_kpi_secondary_domain
Create Date: 2026-06-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_observation_context"
down_revision: str | None = "0005_kpi_secondary_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEASUREMENT_CLASS = (
    "laboratory",
    "vital_sign",
    "anthropometric",
    "body_composition",
    "functional_test",
    "wearable",
    "imaging",
    "derived",
    "omics",
)

_CONTEXT_COLUMNS = (
    "source_system",
    "method",
    "protocol",
    "device_model",
    "firmware_or_algorithm_version",
    "instrument_version",
)


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=40)


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column(
            "source_category",
            _enum(*_MEASUREMENT_CLASS, name="kpimeasurementclass"),
            nullable=True,
        ),
    )
    op.add_column("observations", sa.Column("source_system", sa.String(length=120), nullable=True))
    op.add_column("observations", sa.Column("method", sa.String(length=120), nullable=True))
    op.add_column("observations", sa.Column("protocol", sa.String(length=120), nullable=True))
    op.add_column("observations", sa.Column("device_model", sa.String(length=120), nullable=True))
    op.add_column(
        "observations",
        sa.Column("firmware_or_algorithm_version", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "observations", sa.Column("instrument_version", sa.String(length=80), nullable=True)
    )


def downgrade() -> None:
    for column in _CONTEXT_COLUMNS:
        op.drop_column("observations", column)
    op.drop_column("observations", "source_category")
