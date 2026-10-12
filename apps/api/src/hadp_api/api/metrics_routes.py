"""The preparation-time metric, read and fed by the clinic (go-live plan A6).

The pilot's criterion is the clinic's preparation time per appointment against a baseline the
clinic stated at onboarding. This surface holds both halves and keeps them apart: what the
clinic states (minutes, as a median, with how it arrived at them) and what the platform
measures from the report lifecycle (elapsed time from a report's first draft to its first
approval). See `modules/metrics/service.py` for what the measured number is and is not.

OWNER only: the numbers show how quickly the clinic's clinicians work through their reports.
Counts, durations and identifiers of the clinic's own staff — nothing about any patient.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import PreparationStatementBasis, PreparationStatementKind
from hadp_api.modules.identity.models import User
from hadp_api.modules.metrics import service as metrics_service
from hadp_api.modules.metrics.models import (
    MAX_MINUTES,
    MAX_SAMPLE_SIZE,
    MIN_MINUTES,
    PreparationTimeStatement,
)

router = APIRouter(tags=["metrics"])


class PreparationRecorderOut(BaseModel):
    user_id: uuid.UUID
    display_name: str


class PreparationStatementOut(BaseModel):
    id: uuid.UUID
    kind: PreparationStatementKind
    basis: PreparationStatementBasis
    # The clinic's own number: a median, per appointment.
    median_minutes: int
    # Over how many appointments the clinic timed it; null for an estimate.
    sample_size: int | None
    # In UTC.
    recorded_at: datetime
    recorded_by: PreparationRecorderOut | None


class PreparationMeasuredOut(BaseModel):
    # Start of the window (UTC); null: every report the clinic holds.
    since: datetime | None
    # Reports whose first approval falls in the window.
    reports: int
    # From a report's first draft to its first approval — elapsed time, not minutes of work.
    # All three are null while `reports` is below `minimum_reports`.
    median_seconds: int | None
    q1_seconds: int | None
    q3_seconds: int | None


class PreparationTimeOut(BaseModel):
    # The definition the measured numbers were produced under.
    definition: str
    minimum_reports: int
    # The statements that stand: the newest of each kind.
    baseline: PreparationStatementOut | None
    latest_follow_up: PreparationStatementOut | None
    # Every statement, newest first (a correction is a new statement; nothing is replaced).
    statements: list[PreparationStatementOut]
    measured_all_time: PreparationMeasuredOut
    measured_last_30_days: PreparationMeasuredOut


class RecordPreparationStatementRequest(BaseModel):
    kind: PreparationStatementKind
    basis: PreparationStatementBasis
    median_minutes: int = Field(ge=MIN_MINUTES, le=MAX_MINUTES)
    sample_size: int | None = Field(default=None, ge=1, le=MAX_SAMPLE_SIZE)

    @model_validator(mode="after")
    def _a_sample_has_a_size_and_an_estimate_has_none(self) -> RecordPreparationStatementRequest:
        timed = self.basis is PreparationStatementBasis.TIMED_SAMPLE
        if timed != (self.sample_size is not None):
            raise ValueError("sample_size is given for a timed sample, and only for one")
        return self


def _out(
    statement: PreparationTimeStatement, names: dict[uuid.UUID, str]
) -> PreparationStatementOut:
    name = names.get(statement.recorded_by_user_id)
    return PreparationStatementOut(
        id=statement.id,
        kind=statement.kind,
        basis=statement.basis,
        median_minutes=statement.median_minutes,
        sample_size=statement.sample_size,
        recorded_at=statement.created_at.astimezone(UTC),
        recorded_by=(
            PreparationRecorderOut(user_id=statement.recorded_by_user_id, display_name=name)
            if name is not None
            else None
        ),
    )


def _names(ctx: TenantContext, statements: list[PreparationTimeStatement]) -> dict[uuid.UUID, str]:
    ids = {s.recorded_by_user_id for s in statements}
    if not ids:
        return {}
    rows = ctx.db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(rows.tuples().all())


def _measured(measured: metrics_service.Measured) -> PreparationMeasuredOut:
    return PreparationMeasuredOut(
        since=measured.since,
        reports=measured.reports,
        median_seconds=measured.median_seconds,
        q1_seconds=measured.q1_seconds,
        q3_seconds=measured.q3_seconds,
    )


@router.get("/metrics/preparation-time", response_model=PreparationTimeOut)
def read_preparation_time(
    ctx: TenantContext = Depends(require(Action.METRIC_READ)),
) -> PreparationTimeOut:
    statements = metrics_service.list_statements(ctx.db, tenant_id=ctx.tenant_id)
    names = _names(ctx, statements)
    baseline = metrics_service.latest(statements, PreparationStatementKind.BASELINE)
    follow_up = metrics_service.latest(statements, PreparationStatementKind.FOLLOW_UP)
    now = datetime.now(UTC)
    all_time = metrics_service.measure(ctx.db, tenant_id=ctx.tenant_id, since=None, until=now)
    recent = metrics_service.measure(
        ctx.db, tenant_id=ctx.tenant_id, since=now - timedelta(days=30), until=now
    )
    record_audit(
        ctx.db,
        action="metric.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={"metric": "preparation_time", "definition": metrics_service.DEFINITION},
    )
    return PreparationTimeOut(
        definition=metrics_service.DEFINITION,
        minimum_reports=metrics_service.MIN_REPORTS,
        baseline=_out(baseline, names) if baseline else None,
        latest_follow_up=_out(follow_up, names) if follow_up else None,
        statements=[_out(s, names) for s in statements],
        measured_all_time=_measured(all_time),
        measured_last_30_days=_measured(recent),
    )


@router.post(
    "/metrics/preparation-time/statements", response_model=PreparationStatementOut, status_code=201
)
def record_preparation_time_statement(
    body: RecordPreparationStatementRequest,
    ctx: TenantContext = Depends(require(Action.METRIC_RECORD)),
) -> PreparationStatementOut:
    statement = metrics_service.record_statement(
        ctx.db,
        tenant_id=ctx.tenant_id,
        recorded_by_user_id=ctx.user.id,
        kind=body.kind,
        basis=body.basis,
        median_minutes=body.median_minutes,
        sample_size=body.sample_size,
    )
    # Codes only: which kind of statement and on what basis — the number itself is on the row.
    record_audit(
        ctx.db,
        action="metric.statement_recorded",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="preparation_time_statement",
        target_id=statement.id,
        correlation_id=ctx.correlation_id,
        detail={"kind": body.kind.value, "basis": body.basis.value},
    )
    return _out(statement, {ctx.user.id: ctx.user.display_name})
