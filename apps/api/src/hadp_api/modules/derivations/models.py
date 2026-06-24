"""Immutable input lineage for derived Observations (ADR-0004 §8, Slice 4).

One row per (derived value, input Observation, role). Tenant-scoped under RLS and APPEND-ONLY (the
migration adds the policy + trigger + REVOKE UPDATE/DELETE): a recompute creates a NEW derived
Observation with NEW links, never mutates existing lineage. The derived value itself is a normal
`observations` row (source_category='derived') carrying the frozen formula provenance.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey


class ObservationDerivation(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "observation_derivation"
    __table_args__ = (
        UniqueConstraint(
            "derived_observation_id",
            "input_observation_id",
            "role",
            name="uq_observation_derivation_derived_observation_id",
        ),
        Index("ix_observation_derivation_derived_observation_id", "derived_observation_id"),
        Index("ix_observation_derivation_input_observation_id", "input_observation_id"),
        Index("ix_observation_derivation_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    derived_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("observations.id", ondelete="CASCADE"), nullable=False
    )
    input_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("observations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(60), nullable=False)
