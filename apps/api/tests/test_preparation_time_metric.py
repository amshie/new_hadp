"""The preparation-time metric, part 1 (go-live plan A6; docs/product/WORKFLOW.md §6).

What the clinic STATES (a median in minutes, per appointment: the baseline and later
follow-ups — append-only, owner-only, tenant-scoped) and what the platform MEASURES (the time
from a report's first draft to its first approval that stood, read from the report rows) are
two quantities and are kept apart. Counts, durations and the recording colleague's name —
nothing about a patient.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import (
    PreparationStatementBasis,
    PreparationStatementKind,
    ReportRejectionReason,
    ReportStatus,
    Role,
)
from hadp_api.modules.metrics import service as metrics_service
from hadp_api.modules.metrics.models import PreparationTimeStatement
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports import timing as report_timing
from hadp_api.modules.reports.models import Report, ReportVersion
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import (
    login,
    login_as,
    make_membership,
    make_tenant,
    make_user,
    select_tenant,
    switch_role,
)

READ = "/api/v1/metrics/preparation-time"
STATE = "/api/v1/metrics/preparation-time/statements"

BASELINE = {"kind": "baseline", "basis": "estimate", "median_minutes": 30}


def _owner(client, admin_session, slug: str = "prep-clinic"):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"owner@{slug}.synthetic.example",
        tenant_name=f"Clinic {slug}",
        tenant_slug=slug,
        role=Role.OWNER,
    )


def _report(
    db: Session,
    tenant: Tenant,
    *,
    drafted: datetime,
    approvals: list[datetime | None],
    refused: frozenset[int] = frozenset(),
    version_gap: timedelta = timedelta(0),
) -> Report:
    """A report as the lifecycle leaves it: created at `drafted`, one version per entry of
    `approvals` — approved at that time, or never (None). A version whose number is in
    `refused` was rejected after its approval and keeps both timestamps, as `reject_report`
    leaves it. Version n is created `version_gap` after version n-1."""
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    db.add(patient)
    db.flush()
    report = Report(
        tenant_id=tenant.id,
        patient_id=patient.id,
        status=ReportStatus.APPROVED,
        created_at=drafted,
    )
    db.add(report)
    db.flush()
    for number, approved_at in enumerate(approvals, start=1):
        rejected = number in refused
        if rejected:
            status = ReportStatus.REJECTED
        elif approved_at:
            status = ReportStatus.APPROVED
        else:
            status = ReportStatus.DRAFT_GENERATED
        db.add(
            ReportVersion(
                tenant_id=tenant.id,
                report_id=report.id,
                version_no=number,
                status=status,
                body={"statements": []},
                narrative_provider="deterministic-test",
                narrative_version="0",
                created_at=drafted + version_gap * (number - 1),
                approved_at=approved_at,
                rejected_at=(approved_at or drafted) + timedelta(minutes=1) if rejected else None,
                rejection_reason=ReportRejectionReason.WORDING if rejected else None,
            )
        )
    db.commit()
    return report


def _approved_after(db: Session, tenant: Tenant, minutes: list[float], *, ago: timedelta) -> None:
    """One report per entry: first approved `ago` before now, `minutes` after its draft."""
    approved = datetime.now(UTC) - ago
    for m in minutes:
        _report(db, tenant, drafted=approved - timedelta(minutes=m), approvals=[approved])


# ---- what the clinic states -------------------------------------------------------------


def test_the_owner_states_a_baseline_and_reads_it_back(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, _ = _owner(client, admin_session)

    before = client.get(READ)
    assert before.status_code == 200, before.text
    assert before.json()["baseline"] is None
    assert before.json()["latest_follow_up"] is None
    assert before.json()["statements"] == []

    stated = client.post(STATE, json=BASELINE)
    assert stated.status_code == 201, stated.text
    statement = stated.json()
    assert statement["kind"] == "baseline"
    assert statement["basis"] == "estimate"
    assert statement["median_minutes"] == 30
    assert statement["sample_size"] is None
    assert statement["recorded_by"] == {"user_id": str(owner.id), "display_name": "Synthetic Staff"}
    assert statement["recorded_at"].endswith(("Z", "+00:00"))

    read = client.get(READ).json()
    assert read["definition"] == "draft-to-approval-1"
    assert read["statements_total"] == 1
    assert read["baseline"] == statement
    assert read["statements"] == [statement]
    assert read["latest_follow_up"] is None


def test_a_correction_is_a_new_statement_and_the_earlier_one_stays(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session)
    first = client.post(STATE, json=BASELINE).json()
    follow_up = client.post(
        STATE,
        json={
            "kind": "follow_up",
            "basis": "timed_sample",
            "median_minutes": 14,
            "sample_size": 20,
        },
    ).json()
    corrected = client.post(
        STATE,
        json={"kind": "baseline", "basis": "timed_sample", "median_minutes": 26, "sample_size": 12},
    ).json()

    read = client.get(READ).json()
    # The newest of each kind stands; nothing was replaced.
    assert read["baseline"] == corrected
    assert read["baseline"]["sample_size"] == 12
    assert read["latest_follow_up"] == follow_up
    assert [s["id"] for s in read["statements"]] == [corrected["id"], follow_up["id"], first["id"]]
    assert len(admin_session.execute(select(PreparationTimeStatement)).scalars().all()) == 3


@pytest.mark.parametrize(
    "body",
    [
        {**BASELINE, "median_minutes": 0},
        {**BASELINE, "median_minutes": -5},
        {**BASELINE, "median_minutes": 601},
        {**BASELINE, "median_minutes": 12.5},
        {**BASELINE, "median_minutes": "about half an hour"},
        # A JSON integer, and nothing that merely converts to one.
        {**BASELINE, "median_minutes": "30"},
        {**BASELINE, "median_minutes": 30.0},
        {**BASELINE, "median_minutes": True},
        {**BASELINE, "basis": "timed_sample", "sample_size": "12"},
        {**BASELINE, "basis": "timed_sample", "sample_size": True},
        {**BASELINE, "median_minutes": None},
        {"kind": "baseline", "basis": "estimate"},
        {**BASELINE, "sample_size": 10},  # an estimate has no sample
        {**BASELINE, "basis": "timed_sample"},  # a timed sample says over how many
        {**BASELINE, "basis": "timed_sample", "sample_size": 0},
        {**BASELINE, "basis": "timed_sample", "sample_size": 100_001},
        {**BASELINE, "kind": "target"},  # not in the closed vocabulary
        {**BASELINE, "basis": "guess"},
        {"basis": "estimate", "median_minutes": 30},
    ],
)
def test_a_statement_outside_the_vocabulary_or_the_range_is_refused(  # type: ignore[no-untyped-def]
    client, admin_session, body: dict[str, Any]
) -> None:
    _owner(client, admin_session)
    resp = client.post(STATE, json=body)
    assert resp.status_code == 422, resp.text
    assert admin_session.execute(select(PreparationTimeStatement)).scalars().all() == []


def test_the_limits_of_the_range_are_accepted(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session)
    for minutes in (1, 600):
        assert client.post(STATE, json={**BASELINE, "median_minutes": minutes}).status_code == 201


def _statement(
    tenant: Tenant,
    user_id: uuid.UUID,
    *,
    kind: PreparationStatementKind,
    minutes: int,
    at: datetime,
) -> PreparationTimeStatement:
    return PreparationTimeStatement(
        tenant_id=tenant.id,
        recorded_by_user_id=user_id,
        kind=kind,
        basis=PreparationStatementBasis.ESTIMATE,
        median_minutes=minutes,
        created_at=at,
    )


def test_the_standing_baseline_is_not_hidden_by_a_long_history(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The history returns the newest 50; the statements that stand are looked up on their
    own — a baseline followed by 51 follow-ups is still the baseline."""
    owner, tenant = _owner(client, admin_session, "prep-long")
    start = datetime.now(UTC) - timedelta(days=100)
    admin_session.add(
        _statement(tenant, owner.id, kind=PreparationStatementKind.BASELINE, minutes=42, at=start)
    )
    for day in range(1, 52):
        admin_session.add(
            _statement(
                tenant,
                owner.id,
                kind=PreparationStatementKind.FOLLOW_UP,
                minutes=20,
                at=start + timedelta(days=day),
            )
        )
    admin_session.commit()

    read = client.get(READ).json()
    assert read["baseline"]["median_minutes"] == 42
    assert read["statements_total"] == 52
    assert len(read["statements"]) == metrics_service.MAX_STATEMENTS == 50
    assert {s["kind"] for s in read["statements"]} == {"follow_up"}
    assert read["latest_follow_up"]["id"] == read["statements"][0]["id"]


def test_the_statement_queries_filter_by_clinic_themselves(admin_session) -> None:  # type: ignore[no-untyped-def]
    """As the admin role, which row-level security does not bind: the filter is in each query."""
    clinic_a = make_tenant(admin_session, name="Clinic prep-q-a", slug="prep-q-a")
    clinic_b = make_tenant(admin_session, name="Clinic prep-q-b", slug="prep-q-b")
    user = make_user(admin_session, email="owner@prep-q.synthetic.example")
    now = datetime.now(UTC)
    admin_session.add_all(
        [
            _statement(
                clinic_a, user.id, kind=PreparationStatementKind.BASELINE, minutes=30, at=now
            ),
            _statement(
                clinic_b, user.id, kind=PreparationStatementKind.BASELINE, minutes=45, at=now
            ),
            _statement(
                clinic_b, user.id, kind=PreparationStatementKind.FOLLOW_UP, minutes=15, at=now
            ),
        ]
    )
    admin_session.commit()

    listed = metrics_service.list_statements(admin_session, tenant_id=clinic_a.id)
    assert [s.median_minutes for s in listed] == [30]
    assert metrics_service.count_statements(admin_session, tenant_id=clinic_a.id) == 1
    assert metrics_service.count_statements(admin_session, tenant_id=clinic_b.id) == 2
    follow_up, baseline = PreparationStatementKind.FOLLOW_UP, PreparationStatementKind.BASELINE
    assert (
        metrics_service.standing_statement(admin_session, tenant_id=clinic_a.id, kind=follow_up)
        is None
    )
    standing = metrics_service.standing_statement(
        admin_session, tenant_id=clinic_b.id, kind=baseline
    )
    assert standing is not None and standing.median_minutes == 45


def test_a_time_is_given_in_utc_whatever_zone_the_database_session_reports(  # type: ignore[no-untyped-def]
    client, admin_session, monkeypatch
) -> None:
    owner, tenant = _owner(client, admin_session, "prep-zone")
    berlin = timezone(timedelta(hours=2))
    statement = _statement(
        tenant,
        owner.id,
        kind=PreparationStatementKind.BASELINE,
        minutes=30,
        at=datetime(2026, 10, 12, 18, 59, 30, tzinfo=berlin),
    )
    statement.id = uuid.uuid4()
    monkeypatch.setattr(metrics_service, "list_statements", lambda *_a, **_k: [statement])

    (listed,) = client.get(READ).json()["statements"]

    assert listed["recorded_at"] in ("2026-10-12T16:59:30Z", "2026-10-12T16:59:30+00:00")


def test_stating_is_throttled_per_account_and_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """A statement is a row nobody can remove: 30 a minute per account and clinic."""
    _owner(client, admin_session, "prep-rl-write")
    for _ in range(30):
        assert client.post(STATE, json=BASELINE).status_code == 201
    blocked = client.post(STATE, json=BASELINE)
    assert blocked.status_code == 429, blocked.text
    assert len(admin_session.execute(select(PreparationTimeStatement)).scalars().all()) == 30
    throttled = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "rate_limited"))
        .scalars()
        .one()
    )
    assert throttled.detail == {"action": "metric.record"}


def test_reading_is_throttled_per_account_and_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Every read writes an audit event: 120 a minute per account and clinic."""
    _owner(client, admin_session, "prep-rl-read")
    for _ in range(120):
        assert client.get(READ).status_code == 200
    assert client.get(READ).status_code == 429
    reads = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "metric.read")
    ).scalars()
    assert len(reads.all()) == 120


# ---- who may ----------------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR])
def test_only_the_owner_reads_and_states(client, admin_session, role: Role) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session)
    assert client.post(STATE, json=BASELINE).status_code == 201
    switch_role(
        client,
        admin_session,
        email=f"{role.value}@prep-clinic.synthetic.example",
        tenant=tenant,
        role=role,
    )
    assert client.get(READ).status_code == 403
    assert client.post(STATE, json=BASELINE).status_code == 403
    denied = (
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == "authz.denied"))
        .scalars()
        .all()
    )
    assert sorted(e.detail["attempted"] for e in denied) == ["metric.read", "metric.record"]
    assert len(admin_session.execute(select(PreparationTimeStatement)).scalars().all()) == 1


def test_the_metric_needs_a_session(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get(READ).status_code == 401
    assert client.post(STATE, json=BASELINE).status_code in (401, 403)


# ---- tenant isolation -------------------------------------------------------------------


def test_another_clinic_sees_neither_the_statements_nor_the_reports(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, clinic_a = _owner(client, admin_session, "prep-a")
    assert client.post(STATE, json=BASELINE).status_code == 201
    _approved_after(admin_session, clinic_a, [10, 20, 30, 40, 50, 60], ago=timedelta(days=1))
    assert client.get(READ).json()["measured_all_time"]["reports"] == 6

    _owner(client, admin_session, "prep-b")
    read = client.get(READ).json()
    assert read["baseline"] is None and read["statements"] == []
    assert read["measured_all_time"]["reports"] == 0
    assert read["measured_last_30_days"]["reports"] == 0


def test_row_level_security_alone_keeps_the_statements_apart(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, clinic_a = _owner(client, admin_session, "prep-rls-a")
    assert client.post(STATE, json=BASELINE).status_code == 201
    clinic_b = make_tenant(admin_session, name="Clinic prep-rls-b", slug="prep-rls-b")
    admin_session.commit()

    count = text("SELECT count(*) FROM preparation_time_statements")
    with get_sessionmaker()() as session:
        # No clinic selected: nothing is visible.
        assert session.execute(count).scalar_one() == 0
        session.rollback()
        set_tenant_context(session, clinic_b.id)
        assert session.execute(count).scalar_one() == 0
        # And a row cannot be written into another clinic from here.
        with pytest.raises(DBAPIError, match="row-level security"):
            session.execute(
                text(
                    "INSERT INTO preparation_time_statements"
                    " (tenant_id, kind, basis, median_minutes, recorded_by_user_id)"
                    " VALUES (:t, 'baseline', 'estimate', 30, :u)"
                ),
                {"t": clinic_a.id, "u": owner.id},
            )
        session.rollback()
        set_tenant_context(session, clinic_a.id)
        assert session.execute(count).scalar_one() == 1


# ---- the table ---------------------------------------------------------------------------


def test_a_statement_is_never_changed_or_removed(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "prep-append")
    assert client.post(STATE, json=BASELINE).status_code == 201

    # The application role holds neither privilege …
    with get_sessionmaker()() as session:
        set_tenant_context(session, tenant.id)
        for statement in (
            "UPDATE preparation_time_statements SET median_minutes = 5",
            "DELETE FROM preparation_time_statements",
        ):
            with pytest.raises(DBAPIError, match="permission denied"):
                session.execute(text(statement))
            session.rollback()
            set_tenant_context(session, tenant.id)
    # … and a role that does is stopped by the trigger.
    for statement in (
        "UPDATE preparation_time_statements SET median_minutes = 5",
        "DELETE FROM preparation_time_statements",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            admin_session.execute(text(statement))
        admin_session.rollback()
    assert (
        admin_session.execute(select(PreparationTimeStatement)).scalars().one().median_minutes == 30
    )


@pytest.mark.parametrize(
    "columns",
    [
        {"kind": "target"},
        {"basis": "guess"},
        {"median_minutes": 0},
        {"median_minutes": 601},
        {"sample_size": 10},  # with basis 'estimate'
        {"basis": "timed_sample"},  # without a sample size
        {"basis": "timed_sample", "sample_size": 0},
        {"basis": "timed_sample", "sample_size": 100_001},
    ],
)
def test_the_database_refuses_what_the_api_refuses(admin_session, columns: dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
    tenant = make_tenant(admin_session, name="Clinic prep-check", slug="prep-check")
    user = make_user(admin_session, email="owner@prep-check.synthetic.example")
    make_membership(admin_session, user_id=user.id, tenant_id=tenant.id, role=Role.OWNER)
    admin_session.commit()
    row = {
        "tenant_id": tenant.id,
        "recorded_by_user_id": user.id,
        "kind": "baseline",
        "basis": "estimate",
        "median_minutes": 30,
        "sample_size": None,
        **columns,
    }
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO preparation_time_statements"
                " (tenant_id, recorded_by_user_id, kind, basis, median_minutes, sample_size)"
                " VALUES (:tenant_id, :recorded_by_user_id, :kind, :basis, :median_minutes,"
                " :sample_size)"
            ),
            row,
        )
    admin_session.rollback()


# ---- what the platform measures ----------------------------------------------------------


def test_no_median_is_given_over_fewer_than_five_reports(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "prep-few")
    _approved_after(admin_session, tenant, [10, 20, 30, 40], ago=timedelta(days=2))

    read = client.get(READ).json()
    assert read["minimum_reports"] == metrics_service.MIN_REPORTS == 5
    for window in ("measured_all_time", "measured_last_30_days"):
        assert read[window]["reports"] == 4
        assert read[window]["median_seconds"] is None
        assert read[window]["q1_seconds"] is None
        assert read[window]["q3_seconds"] is None


def test_the_median_and_quartiles_of_draft_to_first_approval(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "prep-median")
    _approved_after(admin_session, tenant, [100, 10, 40, 20, 30], ago=timedelta(days=2))

    measured = client.get(READ).json()["measured_all_time"]
    assert measured == {
        "since": None,
        "reports": 5,
        "median_seconds": 30 * 60,
        "q1_seconds": 20 * 60,
        "q3_seconds": 40 * 60,
    }


def test_a_report_counts_once_at_its_first_approval_and_not_at_all_without_one(  # type: ignore[no-untyped-def]
    client, admin_session
) -> None:
    _, tenant = _owner(client, admin_session, "prep-once")
    now = datetime.now(UTC)
    day = now - timedelta(days=3)
    # Four plain reports, 60 minutes each.
    for _ in range(4):
        _report(admin_session, tenant, drafted=day, approvals=[day + timedelta(minutes=60)])
    # Approved after 10 minutes, edited, approved again a day later: counted once, at 10.
    _report(
        admin_session,
        tenant,
        drafted=day,
        approvals=[day + timedelta(minutes=10), day + timedelta(days=1)],
    )
    # First version never approved (rejected and reworked), the second after 20 minutes.
    _report(admin_session, tenant, drafted=day, approvals=[None, day + timedelta(minutes=20)])
    # Never approved: not a data point.
    _report(admin_session, tenant, drafted=day, approvals=[None])
    _report(admin_session, tenant, drafted=day, approvals=[None, None])

    measured = client.get(READ).json()["measured_all_time"]
    assert measured["reports"] == 6
    # Sorted minutes: 10, 20, 60, 60, 60, 60.
    assert measured["median_seconds"] == 60 * 60
    assert measured["q1_seconds"] == 30 * 60  # 20 + 0.25 * (60 - 20)
    assert measured["q3_seconds"] == 60 * 60


def test_the_thirty_day_window_takes_the_first_approval_as_its_date(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = _owner(client, admin_session, "prep-window")
    _approved_after(admin_session, tenant, [5, 5, 5, 5, 5], ago=timedelta(days=45))
    _approved_after(admin_session, tenant, [50, 50, 50, 50, 50], ago=timedelta(days=5))
    # Drafted 40 days ago, first approved 5 days ago: inside the window, by its approval.
    now = datetime.now(UTC)
    _report(
        admin_session,
        tenant,
        drafted=now - timedelta(days=40),
        approvals=[now - timedelta(days=5)],
    )

    read = client.get(READ).json()
    assert read["measured_all_time"]["reports"] == 11
    recent = read["measured_last_30_days"]
    assert recent["reports"] == 6
    assert recent["median_seconds"] == 50 * 60
    since = datetime.fromisoformat(recent["since"])
    assert timedelta(days=29, hours=23) < datetime.now(UTC) - since < timedelta(days=30, hours=1)


def test_the_service_measures_one_clinic_and_one_window(admin_session) -> None:  # type: ignore[no-untyped-def]
    """`measure` directly, as the admin role: the tenant filter is in the query itself, not
    only in row-level security."""
    clinic_a = make_tenant(admin_session, name="Clinic prep-svc-a", slug="prep-svc-a")
    clinic_b = make_tenant(admin_session, name="Clinic prep-svc-b", slug="prep-svc-b")
    admin_session.commit()
    _approved_after(admin_session, clinic_a, [10, 10, 10, 10, 10], ago=timedelta(days=1))
    _approved_after(admin_session, clinic_b, [90, 90, 90, 90, 90, 90], ago=timedelta(days=1))
    now = datetime.now(UTC)

    (a,) = metrics_service.measure(admin_session, tenant_id=clinic_a.id, until=now, windows=[None])
    (b,) = metrics_service.measure(admin_session, tenant_id=clinic_b.id, until=now, windows=[None])
    assert (a.reports, a.median_seconds) == (5, 600)
    assert (b.reports, b.median_seconds) == (6, 5400)
    # A window that ends before the approvals is empty.
    (earlier,) = metrics_service.measure(
        admin_session, tenant_id=clinic_a.id, until=now - timedelta(days=2), windows=[None]
    )
    assert earlier.reports == 0 and earlier.median_seconds is None


def test_a_window_includes_its_start_and_excludes_its_end(admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = make_tenant(admin_session, name="Clinic prep-edge", slug="prep-edge")
    admin_session.commit()
    start = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    end = start + timedelta(days=7)
    for approved in (start, start + timedelta(days=3), end):
        _report(
            admin_session, tenant, drafted=approved - timedelta(minutes=15), approvals=[approved]
        )

    whole, from_start = report_timing.draft_to_approval(
        admin_session, tenant_id=tenant.id, until=end, windows=[None, start]
    )
    # The approval exactly at `until` is outside; the one exactly at `since` is inside.
    assert whole.reports == 2 and from_start.reports == 2
    (after_start,) = report_timing.draft_to_approval(
        admin_session,
        tenant_id=tenant.id,
        until=end + timedelta(microseconds=1),
        windows=[start + timedelta(microseconds=1)],
    )
    assert after_start.reports == 2  # the one at `start` left, the one at `end` came in
    assert whole.median_seconds == 15 * 60


def test_an_approval_that_was_refused_does_not_end_the_measurement(admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = make_tenant(admin_session, name="Clinic prep-refused", slug="prep-refused")
    admin_session.commit()
    day = datetime.now(UTC) - timedelta(days=10)
    # Approved after 2 minutes, refused at the release gate, reworked, approved 3 days later.
    _report(
        admin_session,
        tenant,
        drafted=day,
        approvals=[day + timedelta(minutes=2), day + timedelta(days=3)],
        refused=frozenset({1}),
        version_gap=timedelta(days=2),
    )
    # Approved once, and that approval was refused: no approval stands.
    _report(
        admin_session,
        tenant,
        drafted=day,
        approvals=[day + timedelta(minutes=2)],
        refused=frozenset({1}),
    )

    (stats,) = report_timing.draft_to_approval(
        admin_session, tenant_id=tenant.id, until=datetime.now(UTC), windows=[None]
    )
    assert stats.reports == 1
    assert stats.median_seconds == timedelta(days=3).total_seconds()


def test_the_interval_starts_at_the_reports_first_draft_not_at_a_later_version(  # type: ignore[no-untyped-def]
    admin_session,
) -> None:
    tenant = make_tenant(admin_session, name="Clinic prep-start", slug="prep-start")
    admin_session.commit()
    day = datetime.now(UTC) - timedelta(days=10)
    # The second version was created two days after the first and approved ten minutes later.
    _report(
        admin_session,
        tenant,
        drafted=day,
        approvals=[None, day + timedelta(days=2, minutes=10)],
        version_gap=timedelta(days=2),
    )

    (stats,) = report_timing.draft_to_approval(
        admin_session, tenant_id=tenant.id, until=datetime.now(UTC), windows=[None]
    )
    assert stats.median_seconds == timedelta(days=2, minutes=10).total_seconds()


def test_two_clocks_never_give_a_negative_interval(admin_session) -> None:  # type: ignore[no-untyped-def]
    """The draft's time is the database's, the approval's the application's."""
    tenant = make_tenant(admin_session, name="Clinic prep-skew", slug="prep-skew")
    admin_session.commit()
    day = datetime.now(UTC) - timedelta(days=2)
    for _ in range(5):
        _report(admin_session, tenant, drafted=day, approvals=[day - timedelta(seconds=3)])

    (measured,) = metrics_service.measure(
        admin_session, tenant_id=tenant.id, until=datetime.now(UTC), windows=[None]
    )
    assert (measured.reports, measured.q1_seconds, measured.median_seconds) == (5, 0, 0)


def test_the_measure_follows_what_the_lifecycle_writes(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """Through the real services: a draft, an approval, a refusal at the release gate, a
    rework, a second approval. Nothing here inserts a report row."""
    clinician, tenant = login_as(
        client,
        admin_session,
        email="clinician@prep-life.synthetic.example",
        tenant_name="Clinic prep-life",
        tenant_slug="prep-life",
        role=Role.CLINICIAN,
    )

    def stats() -> report_timing.IntervalStats:
        admin_session.expire_all()
        (window,) = report_timing.draft_to_approval(
            admin_session,
            tenant_id=tenant.id,
            until=datetime.now(UTC) + timedelta(minutes=1),
            windows=[None],
        )
        return window

    def version(number: int) -> ReportVersion:
        admin_session.expire_all()
        return admin_session.execute(
            select(ReportVersion).where(ReportVersion.version_no == number)
        ).scalar_one()

    pid = client.post("/api/v1/patients", json={"display_name": "Lifecycle (synthetic)"}).json()[
        "id"
    ]
    imported = client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "values": [
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "2.8",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-06-10T00:00:00Z",
                    "observed_at_is_date_only": True,
                }
            ]
        },
    )
    assert imported.status_code in (200, 201), imported.text
    drafted = client.post(f"/api/v1/patients/{pid}/reports")
    assert drafted.status_code == 201, drafted.text
    report = drafted.json()
    rid = report["report_id"]
    assert stats().reports == 0  # a draft is not a data point

    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    created_at = admin_session.execute(select(Report.created_at)).scalar_one()
    first = stats()
    assert first.reports == 1
    assert first.median_seconds == pytest.approx(
        max((version(1).approved_at - created_at).total_seconds(), 0), abs=1e-3
    )

    # The medical director refuses at the release gate: that approval did not stand.
    switch_role(
        client,
        admin_session,
        email="director@prep-life.synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    refused = client.post(f"/api/v1/reports/{rid}/reject", json={"reason": "wording"})
    assert refused.status_code == 200, refused.text
    assert version(1).approved_at is not None and version(1).rejected_at is not None
    assert stats().reports == 0

    # The clinician reworks it and approves the new version: the report counts again, once,
    # and up to the approval that stands.
    login(client, clinician.email)
    select_tenant(client, tenant.id)
    reworked = client.post(
        f"/api/v1/reports/{rid}/edit",
        json={
            "statements": [
                {
                    "id": s["id"],
                    "text": s["text"] + " (überarbeitet)",
                    "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
                }
                for s in report["statements"]
            ]
        },
    )
    assert reworked.status_code == 200, reworked.text
    assert stats().reports == 0
    assert client.post(f"/api/v1/reports/{rid}/approve").status_code == 200
    final = stats()
    assert final.reports == 1
    assert final.median_seconds == pytest.approx(
        max((version(2).approved_at - created_at).total_seconds(), 0), abs=1e-3
    )
    assert final.median_seconds >= first.median_seconds


# ---- the trail, and what the answer carries -----------------------------------------------


def test_stating_and_reading_are_recorded_without_the_numbers(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    owner, tenant = _owner(client, admin_session, "prep-audit")
    statement = client.post(
        STATE,
        json={"kind": "baseline", "basis": "timed_sample", "median_minutes": 47, "sample_size": 83},
    ).json()
    assert client.get(READ).status_code == 200

    events = {
        e.action: e
        for e in admin_session.execute(
            select(AuditEvent).where(AuditEvent.action.like("metric.%"))
        ).scalars()
    }
    assert set(events) == {"metric.statement_recorded", "metric.read"}
    recorded = events["metric.statement_recorded"]
    assert recorded.tenant_id == tenant.id and recorded.actor_user_id == owner.id
    assert recorded.target_type == "preparation_time_statement"
    assert recorded.target_id == uuid.UUID(statement["id"])
    assert recorded.detail == {"kind": "baseline", "basis": "timed_sample"}
    read = events["metric.read"]
    assert read.tenant_id == tenant.id and read.actor_user_id == owner.id
    assert read.detail == {"metric": "preparation_time", "definition": "draft-to-approval-1"}


def test_the_answer_carries_counts_and_durations_and_nothing_about_a_patient(  # type: ignore[no-untyped-def]
    client, admin_session
) -> None:
    _, tenant = _owner(client, admin_session, "prep-shape")
    client.post(STATE, json=BASELINE)
    _approved_after(admin_session, tenant, [10, 20, 30, 40, 50], ago=timedelta(days=1))

    read = client.get(READ).json()
    assert set(read) == {
        "definition",
        "minimum_reports",
        "baseline",
        "latest_follow_up",
        "statements",
        "statements_total",
        "measured_all_time",
        "measured_last_30_days",
    }
    assert set(read["measured_all_time"]) == {
        "since",
        "reports",
        "median_seconds",
        "q1_seconds",
        "q3_seconds",
    }
    assert set(read["baseline"]) == {
        "id",
        "kind",
        "basis",
        "median_minutes",
        "sample_size",
        "recorded_at",
        "recorded_by",
    }
    # No identifier of a patient or a report anywhere in it.
    ids = {str(i) for i in admin_session.execute(select(Patient.id)).scalars()} | {
        str(i) for i in admin_session.execute(select(Report.id)).scalars()
    }
    assert ids and not any(i in client.get(READ).text for i in ids)
