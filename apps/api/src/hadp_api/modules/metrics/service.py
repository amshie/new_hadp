"""The preparation-time metric (go-live plan A6; docs/product/WORKFLOW.md §6).

Two things, kept apart because they are not the same quantity:

- what the CLINIC STATES — its median preparation time per appointment, in minutes: the
  baseline at onboarding and later follow-ups (`PreparationTimeStatement`);
- what the PLATFORM MEASURES — for each report, the time from its first draft to its first
  clinical approval, read from the report rows. That is elapsed time in the workflow: it
  includes every wait, and nothing that happened before the draft existed. It is not minutes
  of work, and it is never set against the clinic's stated minutes as if it were.

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
from hadp_api.modules.reports.models import Report, ReportVersion

# The definition of the measured interval. A change to what is measured gets a new name, so a
# number can always be read with the definition it was produced under.
DEFINITION = "prep-time-1"

# Below this many reports no median is given. A median over two or three reports is the
# turnaround of the one or two clinicians who approved them — a statement about a person, not
# about the clinic's workflow.
MIN_REPORTS = 5

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


def list_statements(db: Session, *, tenant_id: uuid.UUID) -> list[PreparationTimeStatement]:
    """The clinic's statements, newest first. The tenant filter is explicit, as everywhere."""
    return list(
        db.execute(
            select(PreparationTimeStatement)
            .where(PreparationTimeStatement.tenant_id == tenant_id)
            .order_by(
                PreparationTimeStatement.created_at.desc(), PreparationTimeStatement.id.desc()
            )
            .limit(MAX_STATEMENTS)
        ).scalars()
    )


def latest(
    statements: list[PreparationTimeStatement], kind: PreparationStatementKind
) -> PreparationTimeStatement | None:
    """The statement of this kind that stands: the newest (the list is newest first)."""
    return next((s for s in statements if s.kind == kind), None)


def measure(
    db: Session, *, tenant_id: uuid.UUID, since: datetime | None, until: datetime
) -> Measured:
    """Draft-to-approval times of the reports whose FIRST approval falls in [since, until).

    One value per report: from the creation of the report (its first draft) to the earliest
    approval of any of its versions. A report approved again later — after an edit or a
    laboratory correction — is counted once, at its first approval; a report never approved
    is not counted. Read from the report rows, so an erased patient's reports are gone from
    the measure exactly as they are gone from the record.
    """
    first_approval = (
        select(
            Report.created_at.label("drafted_at"),
            func.min(ReportVersion.approved_at).label("approved_at"),
        )
        .join(ReportVersion, ReportVersion.report_id == Report.id)
        .where(
            Report.tenant_id == tenant_id,
            ReportVersion.tenant_id == tenant_id,
            ReportVersion.approved_at.is_not(None),
        )
        .group_by(Report.id, Report.created_at)
        .subquery()
    )
    seconds = func.extract("epoch", first_approval.c.approved_at - first_approval.c.drafted_at)
    query = select(
        func.count(),
        func.percentile_cont(0.25).within_group(seconds),
        func.percentile_cont(0.5).within_group(seconds),
        func.percentile_cont(0.75).within_group(seconds),
    ).where(first_approval.c.approved_at < until)
    if since is not None:
        query = query.where(first_approval.c.approved_at >= since)
    reports, q1, median, q3 = db.execute(query).one()
    if reports < MIN_REPORTS:
        return Measured(
            since=since, reports=reports, median_seconds=None, q1_seconds=None, q3_seconds=None
        )
    return Measured(
        since=since,
        reports=reports,
        median_seconds=round(median),
        q1_seconds=round(q1),
        q3_seconds=round(q3),
    )
