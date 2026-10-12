"""The preparation-time metric (go-live plan A6; docs/product/WORKFLOW.md §6).

What the clinic STATES (a median in minutes, per appointment: the baseline and later
follow-ups — append-only, owner-only, tenant-scoped) and what the platform MEASURES (the time
from a report's first draft to its first approval, read from the report rows) are two
quantities and are kept apart. Counts, durations and staff identifiers only — nothing about a
patient.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import ReportStatus, Role
from hadp_api.modules.metrics import service as metrics_service
from hadp_api.modules.metrics.models import PreparationTimeStatement
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports.models import Report, ReportVersion
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import login_as, make_membership, make_tenant, make_user, switch_role

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
) -> Report:
    """A report as the lifecycle leaves it: created at `drafted`, one version per entry of
    `approvals` — approved at that time, or never (None)."""
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
        db.add(
            ReportVersion(
                tenant_id=tenant.id,
                report_id=report.id,
                version_no=number,
                status=ReportStatus.APPROVED if approved_at else ReportStatus.DRAFT_GENERATED,
                body={"statements": []},
                narrative_provider="deterministic-test",
                narrative_version="0",
                created_at=drafted,
                approved_at=approved_at,
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
    assert read["definition"] == "prep-time-1"
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

    a = metrics_service.measure(admin_session, tenant_id=clinic_a.id, since=None, until=now)
    b = metrics_service.measure(admin_session, tenant_id=clinic_b.id, since=None, until=now)
    assert (a.reports, a.median_seconds) == (5, 600)
    assert (b.reports, b.median_seconds) == (6, 5400)
    # `until` is exclusive and `since` inclusive: a window that ends before the approvals is empty.
    earlier = metrics_service.measure(
        admin_session, tenant_id=clinic_a.id, since=None, until=now - timedelta(days=2)
    )
    assert earlier.reports == 0 and earlier.median_seconds is None


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
    assert read.detail == {"metric": "preparation_time", "definition": "prep-time-1"}


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
