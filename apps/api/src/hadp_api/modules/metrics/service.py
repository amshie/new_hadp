"""The preparation-time metric, part 1 (go-live plan A6; docs/product/WORKFLOW.md §6).

Two things, kept apart because they are not the same quantity:

- what the CLINIC STATES — its median preparation time per appointment, in minutes: the
  baseline at onboarding and later follow-ups (`PreparationTimeStatement`);
- what the PLATFORM MEASURES — for each report, the time from its first draft to the first
  approval that stood, read from the report rows (`reports.timing`). That is elapsed time in
  the workflow: it includes every wait, and nothing that happened before the draft existed.
  It is not minutes of work, and it is never set against the clinic's stated minutes as if it
  were.

A measure that CAN be set against the baseline — preparation from its start — does not exist
yet: the product records no "preparation started" moment (WORKFLOW §6.4).

Nothing here reads or returns anything about a patient: counts and durations only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import PreparationStatementBasis, PreparationStatementKind
from hadp_api.modules.metrics.models import PreparationTimeStatement
from hadp_api.modules.reports import timing as report_timing

# The definition of the measured interval, named for what it measures. A change to what is
# measured gets a new name, so a number can always be read with the definition it was produced
# under.
DEFINITION = "draft-to-approval-1"

# Below this many reports no median is given: over so few, each figure is close to a single
# report's own time. This is a small-sample guard, NOT a protection of persons — it counts
# reports, not the people who approved them, and in a clinic with one approving clinician
# every figure describes that one person's turnaround however many reports there are.
MIN_REPORTS = 5

# How many statements the history returns (the newest). The statements that STAND are looked
# up on their own and do not depend on this.
MAX_STATEMENTS = 50


@dataclass(frozen=True)
class Measured:
    """Draft-to-approval times of the reports first approved in a window."""

    since: datetime | None
    reports: int
    # None while fewer than MIN_REPORTS reports are in the window.
    median_seconds: int | None
    q1_seconds: int | None
    q3_seconds: int | None


def record_statement(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    recorded_by_user_id: uuid.UUID,
    kind: PreparationStatementKind,
    basis: PreparationStatementBasis,
    median_minutes: int,
    sample_size: int | None,
) -> PreparationTimeStatement:
    statement = PreparationTimeStatement(
        tenant_id=tenant_id,
        recorded_by_user_id=recorded_by_user_id,
        kind=kind,
        basis=basis,
        median_minutes=median_minutes,
        sample_size=sample_size,
    )
    db.add(statement)
    db.flush()
    db.refresh(statement)
    return statement


_NEWEST_FIRST = (PreparationTimeStatement.created_at.desc(), PreparationTimeStatement.id.desc())


def list_statements(db: Session, *, tenant_id: uuid.UUID) -> list[PreparationTimeStatement]:
    """The clinic's newest statements, newest first — at most MAX_STATEMENTS of them. The
    tenant filter is explicit, as everywhere."""
    return list(
        db.execute(
            select(PreparationTimeStatement)
            .where(PreparationTimeStatement.tenant_id == tenant_id)
            .order_by(*_NEWEST_FIRST)
            .limit(MAX_STATEMENTS)
        ).scalars()
    )


def count_statements(db: Session, *, tenant_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(PreparationTimeStatement)
        .where(PreparationTimeStatement.tenant_id == tenant_id)
    ).scalar_one()


def standing_statement(
    db: Session, *, tenant_id: uuid.UUID, kind: PreparationStatementKind
) -> PreparationTimeStatement | None:
    """The statement of this kind that stands: the newest one, however many came after it of
    the other kind."""
    return db.execute(
        select(PreparationTimeStatement)
        .where(
            PreparationTimeStatement.tenant_id == tenant_id,
            PreparationTimeStatement.kind == kind,
        )
        .order_by(*_NEWEST_FIRST)
        .limit(1)
    ).scalar_one_or_none()


def measure(
    db: Session, *, tenant_id: uuid.UUID, until: datetime, windows: list[datetime | None]
) -> list[Measured]:
    """Per window, the draft-to-approval times of the reports first approved in it — see
    `reports.timing.draft_to_approval` for what counts. Below MIN_REPORTS reports the count is
    given and the figures are withheld."""
    measured = []
    stats = report_timing.draft_to_approval(db, tenant_id=tenant_id, until=until, windows=windows)
    for since, window in zip(windows, stats, strict=True):
        figures = [window.q1_seconds, window.median_seconds, window.q3_seconds]
        shown = [round(f) for f in figures if f is not None]
        if window.reports < MIN_REPORTS or len(shown) != len(figures):
            shown_q1 = shown_median = shown_q3 = None
        else:
            shown_q1, shown_median, shown_q3 = shown
        measured.append(
            Measured(
                since=since,
                reports=window.reports,
                median_seconds=shown_median,
                q1_seconds=shown_q1,
                q3_seconds=shown_q3,
            )
        )
    return measured
