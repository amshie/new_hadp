"""What the overview reads (docs/notes/0015): per-record workflow counts on the worklist, the
day of each release, the share of values linked to a catalog marker, the ways values came in,
and one's own latest actions.

Counts, times and identifiers only — no value, no range, no verdict. Every read is tenant-scoped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from hadp_api.modules.enums import ImportStatus, ReportStatus, Role
from hadp_api.modules.imports.models import ImportJob, ImportRow
from hadp_api.modules.reports.models import Report, ReportVersion
from tests.helpers import login_as, switch_role
from tests.test_interpretation_author_api import _payload

_LDL = {
    "original_name": "LDL Cholesterol",
    "original_value": "2.8",
    "original_unit": "mmol/L",
    "observed_at": "2025-06-10T00:00:00Z",
    "observed_at_is_date_only": True,
}
# A name no terminology maps: it waits for a human decision.
_UNKNOWN = {
    "original_name": "Synthetic Unmapped Analyte",
    "original_value": "65",
    "original_unit": "µg/dL",
    "observed_at": "2025-06-10T00:00:00Z",
    "observed_at_is_date_only": True,
}


def _import(client, pid: str, *values: dict) -> dict:  # type: ignore[no-untyped-def, type-arg]
    resp = client.post(f"/api/v1/patients/{pid}/imports", json={"values": list(values)})
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


def _row(client, pid: str) -> dict:  # type: ignore[no-untyped-def, type-arg]
    rows = client.get("/api/v1/worklist").json()
    return next(r for r in rows if r["patient_id"] == pid)  # type: ignore[no-any-return]


def _released_report(
    admin_session: Session, *, tenant_id: uuid.UUID, patient_id: str, released_at: datetime
) -> None:
    report = Report(
        tenant_id=tenant_id,
        patient_id=uuid.UUID(patient_id),
        status=ReportStatus.RELEASED,
    )
    admin_session.add(report)
    admin_session.flush()
    version = ReportVersion(
        tenant_id=tenant_id,
        report_id=report.id,
        version_no=1,
        status=ReportStatus.RELEASED,
        body={"statements": []},
        narrative_provider="deterministic",
        narrative_version="test",
        created_at=released_at - timedelta(days=2),
        approved_at=released_at - timedelta(days=1),
        released_at=released_at,
    )
    admin_session.add(version)
    admin_session.flush()
    report.current_version_id = version.id
    admin_session.commit()


def test_worklist_counts_what_lies_under_each_record(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="ov-counts@synthetic.example",
        tenant_name="OV Counts",
        tenant_slug="ov-counts",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV Counts"}).json()["id"]

    empty = _row(client, pid)
    assert empty["values_published"] == 0
    assert empty["values_pending"] == 0
    assert empty["pending_since"] is None
    assert empty["latest_received_at"] is None
    assert empty["latest_run_number"] is None
    assert empty["latest_run_at"] is None
    assert empty["values_since_run"] == 0
    assert empty["status_at"] is None

    _import(client, pid, _LDL, _UNKNOWN)
    before_run = _row(client, pid)
    assert before_run["values_published"] == 1
    assert before_run["values_pending"] == 1
    assert before_run["pending_since"] is not None
    # Without a run, nothing arrived "after" one.
    assert before_run["values_since_run"] == 0

    obs_id = next(
        p["observation_id"]
        for p in client.get(f"/api/v1/patients/{pid}/observations").json()
        if p["review_status"] == "published"
    )
    run = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id))
    assert run.status_code == 201, run.text

    after_run = _row(client, pid)
    assert after_run["latest_run_number"] == 1
    assert after_run["latest_run_at"] is not None
    assert after_run["values_since_run"] == 0

    # Two more values arrive: one publishes, one waits. Both count as received after the run.
    second = dict(_LDL, original_value="2.6", observed_at="2026-01-10T00:00:00Z")
    third = dict(_UNKNOWN, original_value="70", observed_at="2026-01-10T00:00:00Z")
    _import(client, pid, second, third)
    later = _row(client, pid)
    assert later["values_published"] == 2
    assert later["values_pending"] == 2
    assert later["values_since_run"] == 2
    assert datetime.fromisoformat(later["latest_received_at"]) > datetime.fromisoformat(
        later["latest_run_at"]
    )
    # The oldest value still waiting is the first one.
    assert later["pending_since"] == before_run["pending_since"]


def test_worklist_says_when_the_report_reached_its_status(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="ov-status@synthetic.example",
        tenant_name="OV Status",
        tenant_slug="ov-status",
        role=Role.MEDICAL_DIRECTOR,
    )
    # The medical director creates no patients; the clinic's assistant does.
    switch_role(
        client,
        admin_session,
        email="ov-status-a@synthetic.example",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV Status"}).json()["id"]
    released_at = datetime.now(UTC) - timedelta(hours=5)
    _released_report(admin_session, tenant_id=tenant.id, patient_id=pid, released_at=released_at)

    row = _row(client, pid)
    assert row["report_status"] == "released"
    assert datetime.fromisoformat(row["status_at"]) == released_at


def test_throughput_counts_releases_by_day(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="ov-released@synthetic.example",
        tenant_name="OV Released",
        tenant_slug="ov-released",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV Released"}).json()["id"]
    now = datetime.now(UTC)
    _released_report(admin_session, tenant_id=tenant.id, patient_id=pid, released_at=now)

    body = client.get("/api/v1/worklist/throughput", params={"days": 7}).json()
    assert body["total_released"] == 1
    today = next(b for b in body["buckets"] if b["date"] == now.date().isoformat())
    assert today["released"] == 1
    assert sum(b["released"] for b in body["buckets"]) == 1


def test_coverage_counts_values_linked_to_a_catalog_marker(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="ov-kpi@synthetic.example",
        tenant_name="OV KPI",
        tenant_slug="ov-kpi",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV KPI"}).json()["id"]
    _import(client, pid, _LDL, _UNKNOWN)
    body = client.get("/api/v1/worklist/coverage").json()
    assert body["total"] == 2
    assert body["with_kpi"] == 1


def test_sources_list_every_reader_and_everything_else(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="ov-sources@synthetic.example",
        tenant_name="OV Sources",
        tenant_slug="ov-sources",
        role=Role.ASSISTANT,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV Sources"}).json()["id"]

    # Nothing read yet: the three readers are listed, with nothing.
    lines = client.get("/api/v1/worklist/sources").json()
    assert [line["parser_name"] for line in lines] == ["hadp-csv", "ldt2-8201", "ldt3-8205", None]
    assert all(line["jobs"] == 0 and line["last_import_at"] is None for line in lines)

    # A value entered through the API, and a laboratory file read by the LDT 3 reader.
    _import(client, pid, _LDL)
    job = ImportJob(
        tenant_id=tenant.id,
        patient_id=uuid.UUID(pid),
        status=ImportStatus.PUBLISHED,
        parser_name="ldt3-8205",
        parser_version="test",
    )
    admin_session.add(job)
    admin_session.flush()
    for index in range(3):
        admin_session.add(
            ImportRow(
                tenant_id=tenant.id,
                import_job_id=job.id,
                row_index=index,
                raw={},
                status=ImportStatus.PUBLISHED,
            )
        )
    admin_session.commit()

    by_name = {line["parser_name"]: line for line in client.get("/api/v1/worklist/sources").json()}
    assert by_name["ldt3-8205"]["jobs"] == 1
    assert by_name["ldt3-8205"]["rows"] == 3
    assert by_name["ldt3-8205"]["last_import_at"] is not None
    assert by_name[None]["jobs"] == 1
    assert by_name["hadp-csv"]["jobs"] == 0
    assert by_name["ldt2-8201"]["jobs"] == 0


def test_sources_are_the_clinics_own(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="ov-src-a@synthetic.example",
        tenant_name="OV Src A",
        tenant_slug="ov-src-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "OV Src A"}).json()["id"]
    _import(client, pid, _LDL)
    login_as(
        client,
        admin_session,
        email="ov-src-b@synthetic.example",
        tenant_name="OV Src B",
        tenant_slug="ov-src-b",
        role=Role.CLINICIAN,
    )
    lines = client.get("/api/v1/worklist/sources").json()
    assert all(line["jobs"] == 0 for line in lines)


def test_own_activity_is_ones_own_and_leaves_reads_out(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    clinician, tenant = login_as(
        client,
        admin_session,
        email="ov-own-c@synthetic.example",
        tenant_name="OV Own",
        tenant_slug="ov-own",
        role=Role.CLINICIAN,
    )
    mine = client.post("/api/v1/patients", json={"display_name": "OV Own Mine"}).json()["id"]
    client.get(f"/api/v1/patients/{mine}")  # a read: not shown

    switch_role(
        client,
        admin_session,
        email="ov-own-a@synthetic.example",
        tenant=tenant,
        role=Role.ASSISTANT,
    )
    theirs = client.post("/api/v1/patients", json={"display_name": "OV Own Theirs"}).json()["id"]

    resp = client.get("/api/v1/audit-events/mine")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    # The assistant's own: entering the clinic, and the record they created.
    assert [i["action"] for i in items][:2] == ["patient.create", "tenant.select"]
    assert {i["target_id"] for i in items if i["action"] == "patient.create"} == {theirs}
    assert all(i["actor"]["email"] == "ov-own-a@synthetic.example" for i in items)
    assert not any(i["action"].endswith((".read", ".list")) for i in items)

    # The clinician sees theirs and not the assistant's.
    switch_role(
        client,
        admin_session,
        email="ov-own-c2@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert client.get("/api/v1/audit-events/mine").json()[0]["action"] == "tenant.select"
    assert all(
        i["actor"]["user_id"] != str(clinician.id)
        for i in client.get("/api/v1/audit-events/mine").json()
    )


def test_own_activity_is_limited_and_never_another_clinics(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="ov-limit@synthetic.example",
        tenant_name="OV Limit A",
        tenant_slug="ov-limit-a",
        role=Role.CLINICIAN,
    )
    for n in range(4):
        client.post("/api/v1/patients", json={"display_name": f"OV Limit {n}"})
    assert len(client.get("/api/v1/audit-events/mine", params={"limit": 3}).json()) == 3
    assert client.get("/api/v1/audit-events/mine", params={"limit": 21}).status_code == 422

    # Someone in a second clinic: none of the first clinic's events.
    login_as(
        client,
        admin_session,
        email="ov-limit-b@synthetic.example",
        tenant_name="OV Limit B",
        tenant_slug="ov-limit-b",
        role=Role.CLINICIAN,
    )
    items = client.get("/api/v1/audit-events/mine").json()
    assert [i["action"] for i in items] == ["tenant.select"]


def test_own_activity_requires_a_clinic(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/audit-events/mine").status_code == 401
