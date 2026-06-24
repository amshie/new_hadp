"""HADP interpretation model (ADR-0003).

The domain axis is the canonical unit: ONE CIS + ONE Actionability per axis per run, with three
verdict-free tri-state cells per axis (6 verdicts + 18 cells per run). Runs are append-only;
corrections create a NEW run. CIS and Actionability are two DISJOINT closed enums stored as separate
columns — never merged, never derived from each other or from the cells. A tri-state cell carries
NO CIS/Actionability column: it is supporting evidence only.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hadp_api.db.base import Base, TimestampCreated, UUIDPrimaryKey
from hadp_api.modules.enums import (
    CELL_STATES,
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    InterpretationReviewStatus,
    TriStateAxis,
    pg_enum,
)


class InterpretationRun(UUIDPrimaryKey, TimestampCreated, Base):
    """An immutable, append-only interpretation run for a patient. 6 verdicts + 18 cells."""

    __tablename__ = "interpretation_runs"
    __table_args__ = (UniqueConstraint("patient_id", "run_number"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Null for the first run; otherwise the run this one supersedes.
    supersedes_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interpretation_runs.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class DomainAxisInterpretation(UUIDPrimaryKey, TimestampCreated, Base):
    """ONE CIS + ONE Actionability verdict per domain axis per run (six rows per run).

    `review_status`/`reviewed_by_user_id` are a mutable review projection; the verdict values are
    set at run creation and corrected only via a NEW run.
    """

    __tablename__ = "domain_axis_interpretations"
    __table_args__ = (UniqueConstraint("interpretation_run_id", "domain_axis"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interpretation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interpretation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_axis: Mapped[DomainAxis] = mapped_column(pg_enum(DomainAxis), nullable=False)
    # CIS and Actionability: two disjoint closed enums, separate columns, never merged/derived.
    cis_status: Mapped[CisStatus] = mapped_column(pg_enum(CisStatus, length=60), nullable=False)
    actionability_class: Mapped[ActionabilityClass] = mapped_column(
        pg_enum(ActionabilityClass), nullable=False
    )
    followup_adequacy: Mapped[AdequacyStatus] = mapped_column(
        pg_enum(AdequacyStatus), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    review_status: Mapped[InterpretationReviewStatus] = mapped_column(
        pg_enum(InterpretationReviewStatus), nullable=False, server_default=text("'draft'")
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class TriStateCell(UUIDPrimaryKey, TimestampCreated, Base):
    """Verdict-FREE supporting cell — three per domain verdict (eighteen per run).

    Carries NO `cis_status` / `actionability_class` column. `state` is validated against the cell's
    OWN axis vocabulary at the service layer; the DB CHECK admits the union of all legal states.
    """

    __tablename__ = "tri_state_cells"
    __table_args__ = (
        UniqueConstraint("domain_axis_interpretation_id", "tri_state_axis"),
        CheckConstraint(
            "state IN (" + ", ".join(f"'{s}'" for s in CELL_STATES) + ")",
            name="cell_state_vocab",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain_axis_interpretation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domain_axis_interpretations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tri_state_axis: Mapped[TriStateAxis] = mapped_column(pg_enum(TriStateAxis), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    endpoint_adequacy: Mapped[AdequacyStatus] = mapped_column(
        pg_enum(AdequacyStatus), nullable=False
    )
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    rationale: Mapped[str | None] = mapped_column(String(2000), nullable=True)
