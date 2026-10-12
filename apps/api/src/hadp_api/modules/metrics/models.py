"""The clinic's own statements of its appointment-preparation time.

One row is one statement by the clinic: a median, in minutes, of how long preparing one
appointment takes — the baseline at onboarding, or a later follow-up. Timings and identifiers
only; nothing about any patient. APPEND-ONLY (migration 0019: REVOKE UPDATE/DELETE + trigger):
a wrong statement is corrected by a new one, and the earlier one stays on record.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import PreparationStatementBasis, PreparationStatementKind, pg_enum

MIN_MINUTES = 1
MAX_MINUTES = 600
MAX_SAMPLE_SIZE = 100_000


class PreparationTimeStatement(UUIDPrimaryKey, TimestampCreated, Base):
    __tablename__ = "preparation_time_statements"
    __table_args__ = (
        CheckConstraint(
            f"median_minutes BETWEEN {MIN_MINUTES} AND {MAX_MINUTES}", name="median_minutes_range"
        ),
        # A timed sample says over how many appointments; an estimate has no sample.
        CheckConstraint(
            "(basis = 'timed_sample') = (sample_size IS NOT NULL)",
            name="sample_size_iff_timed_sample",
        ),
        CheckConstraint(
            f"sample_size IS NULL OR sample_size BETWEEN 1 AND {MAX_SAMPLE_SIZE}",
            name="sample_size_range",
        ),
    )

    # ON DELETE RESTRICT on both references: the trigger that blocks row changes would turn a
    # cascade — or a SET NULL, which is an UPDATE — into a confusing abort, so the constraint
    # says what actually happens. Consequence: an account that recorded a statement cannot be
    # hard-deleted while the statement exists (a retention question for the DPO; register row).
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[PreparationStatementKind] = mapped_column(
        pg_enum(PreparationStatementKind), nullable=False
    )
    basis: Mapped[PreparationStatementBasis] = mapped_column(
        pg_enum(PreparationStatementBasis), nullable=False
    )
    median_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
