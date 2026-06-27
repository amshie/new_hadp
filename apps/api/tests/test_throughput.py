"""Worklist throughput endpoint: real per-day report-version counts, isolation, auth.

`created` buckets by ReportVersion.created_at; `signed` buckets by approved_at — both real
persisted timestamps. The tests pin the bucketing and prove cross-tenant isolation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from hadp_api.main import app
from hadp_api.modules.enums import ReportStatus, Role
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports import service as reports_service
from hadp_api.modules.reports.models import Report, ReportVersion
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import login, login_as, provision_staff, select_tenant


def _version(
    admin_session: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: str,
    created_at: datetime,
    approved_at: datetime | None,
) -> None:
    report = Report(
        tenant_id=tenant_id,
        patient_id=uuid.UUID(str(patient_id)),
        status=ReportStatus.APPROVED if approved_at else ReportStatus.DRAFT_GENERATED,
    )
    admin_session.add(report)
    admin_session.flush()
    # created_at is server_default=now(); pass it explicitly to land the version in the test window.
    version = ReportVersion(
        tenant_id=tenant_id,
        report_id=report.id,
        version_no=1,
        status=report.status,
        body={"statements": []},
        narrative_provider="deterministic",
        narrative_version="test",
        created_at=created_at,
        approved_at=approved_at,
    )
    admin_session.add(version)
    admin_session.flush()


def test_throughput_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/worklist/throughput").status_code == 401


def test_throughput_buckets_created_and_signed(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="tp-a@synthetic.example",
        tenant_name="TP A",
        tenant_slug="tp-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "TP Patient"}).json()["id"]
    now = datetime.now(UTC)
    today = now.date()
    yesterday = today - timedelta(days=1)
    # Two versions created today (one of them signed today), one created+signed yesterday.
    _version(admin_session, tenant_id=tenant.id, patient_id=pid, created_at=now, approved_at=now)
    _version(admin_session, tenant_id=tenant.id, patient_id=pid, created_at=now, approved_at=None)
    _version(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        created_at=now - timedelta(days=1),
        approved_at=now - timedelta(days=1),
    )
    admin_session.commit()

    body = client.get("/api/v1/worklist/throughput?days=7").json()
    assert body["days"] == 7
    assert len(body["buckets"]) == 7
    assert body["total_created"] == 3
    assert body["total_signed"] == 2

    by_date = {b["date"]: b for b in body["buckets"]}
    assert by_date[today.isoformat()] == {
        "date": today.isoformat(),
        "created": 2,
        "signed": 1,
    }
    assert by_date[yesterday.isoformat()] == {
        "date": yesterday.isoformat(),
        "created": 1,
        "signed": 1,
    }


def test_throughput_rejects_out_of_range_and_isolates_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, ta = login_as(
        client,
        admin_session,
        email="tp-iso-a@synthetic.example",
        tenant_name="TP ISO A",
        tenant_slug="tp-iso-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "TP Iso"}).json()["id"]
    _version(
        admin_session,
        tenant_id=ta.id,
        patient_id=pid,
        created_at=datetime.now(UTC),
        approved_at=datetime.now(UTC),
    )
    admin_session.commit()

    # days is validated at the boundary — an absurd window is rejected, not silently served.
    assert client.get("/api/v1/worklist/throughput?days=9999").status_code == 422
    assert client.get("/api/v1/worklist/throughput?days=90").json()["days"] == 90

    # A fresh tenant sees an all-zero series — A's versions never leak.
    provision_staff(
        admin_session,
        email="tp-iso-b@synthetic.example",
        tenant_name="TP ISO B",
        tenant_slug="tp-iso-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "tp-iso-b@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        body = cb.get("/api/v1/worklist/throughput?days=14").json()
        assert body["total_created"] == 0
        assert body["total_signed"] == 0
        assert all(b["created"] == 0 and b["signed"] == 0 for b in body["buckets"])


def test_throughput_excludes_out_of_window_and_includes_boundary(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="tp-win@synthetic.example",
        tenant_name="TP WIN",
        tenant_slug="tp-win",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "TP Window"}).json()["id"]
    today = datetime.now(UTC).date()
    # Oldest in-window day for days=7 is today-6 (start = today - (days-1)); midday avoids tz edges.
    boundary = datetime(today.year, today.month, today.day, 12, tzinfo=UTC) - timedelta(days=6)
    out_of_window = datetime.now(UTC) - timedelta(days=10)
    _version(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        created_at=boundary,
        approved_at=boundary,
    )
    _version(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        created_at=out_of_window,
        approved_at=out_of_window,
    )
    admin_session.commit()

    body = client.get("/api/v1/worklist/throughput?days=7").json()
    # Only the boundary version counts; the 10-days-ago version is outside the 7-day window.
    assert body["total_created"] == 1
    assert body["total_signed"] == 1
    by_date = {b["date"]: b for b in body["buckets"]}
    boundary_day = (today - timedelta(days=6)).isoformat()
    assert by_date[boundary_day]["created"] == 1
    assert by_date[boundary_day]["signed"] == 1


def test_throughput_buckets_by_utc_day_regardless_of_session_tz(admin_session) -> None:  # type: ignore[no-untyped-def]
    # A version at 23:30 UTC is the *next* calendar day in Sydney (UTC+10/11). Bucketing is pinned
    # to UTC, so it must key on its UTC day (today) and stay inside the UTC window — even when the
    # DB session time zone is non-UTC. Without the UTC pin it would bucket to the Sydney day
    # (tomorrow), fall outside the window, and vanish from the series.
    tenant = Tenant(name="TP TZ", slug="tp-tz", is_synthetic=True)
    admin_session.add(tenant)
    admin_session.flush()
    patient = Patient(tenant_id=tenant.id, display_name="TZ Patient", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    today = datetime.now(UTC).date()
    at = datetime(today.year, today.month, today.day, 23, 30, tzinfo=UTC)
    _version(
        admin_session,
        tenant_id=tenant.id,
        patient_id=str(patient.id),
        created_at=at,
        approved_at=at,
    )
    admin_session.commit()

    admin_session.execute(text("SET TIME ZONE 'Australia/Sydney'"))
    try:
        summary = reports_service.throughput_daily(admin_session, tenant.id, 7)
    finally:
        admin_session.execute(text("SET TIME ZONE 'UTC'"))

    assert summary.total_created == 1
    assert summary.total_signed == 1
    today_bucket = next(b for b in summary.buckets if b.day == today)
    assert today_bucket.created == 1
    assert today_bucket.signed == 1
