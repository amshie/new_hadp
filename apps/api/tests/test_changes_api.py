"""What changed in a record since the person last opened it (docs/notes/0024).

GET /worklist/changes is tenant-scoped (RLS beneath an explicit filter), open to every staff
role that may read observations, audited with a count only. The person's last opening is
their own `patient.read` in the clinic's trail; opening the record again is what clears the
row. A step the person took themselves — a run they recorded, a draft they generated — is
not news to them and is left out. Counts and workflow facts only, never a rating.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.main import app
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import ReviewStatus, Role
from tests.helpers import login, login_as, provision_staff, select_tenant, switch_role
from tests.test_interpretation_author_api import _IMPORT, _payload
from tests.test_preparation_api import _obs

URL = "/api/v1/worklist/changes"


def _audited_counts(admin_session: Session, tenant_id: uuid.UUID) -> list[int]:
    events = (
        admin_session.execute(
            select(AuditEvent)
            .where(AuditEvent.action == "worklist.changes.read", AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        )
        .scalars()
        .all()
    )
    return [e.detail["count"] for e in events]


def test_changes_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get(URL).status_code == 401


def test_changes_names_what_moved_since_the_person_opened_the_record(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    me, tenant = login_as(
        client,
        admin_session,
        email="changes-a@synthetic.example",
        tenant_name="Changes A",
        tenant_slug="changes-a",
        role=Role.CLINICIAN,
    )
    opened = client.post("/api/v1/patients", json={"display_name": "Opened Record"}).json()["id"]
    never = client.post("/api/v1/patients", json={"display_name": "Never Opened"}).json()["id"]

    # Nothing opened yet: both records are only counted.
    body = client.get(URL).json()
    assert body == {"opened": 0, "never_opened": 2, "rows": []}

    # The person opens one record; nothing has happened in it since.
    assert client.get(f"/api/v1/patients/{opened}").status_code == 200
    body = client.get(URL).json()
    assert (body["opened"], body["never_opened"], body["rows"]) == (1, 1, [])

    # Then a colleague imports a value, records a run and generates a draft; a value awaiting
    # review arrives too. The never-opened record gets a value as well — still only counted.
    colleague = switch_role(
        client,
        admin_session,
        email="changes-colleague@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert client.post(f"/api/v1/patients/{opened}/imports", json=_IMPORT).status_code == 201
    assert client.post(f"/api/v1/patients/{never}/imports", json=_IMPORT).status_code == 201
    obs_id = client.get(f"/api/v1/patients/{opened}/observations").json()[0]["observation_id"]
    authored = client.post(f"/api/v1/patients/{opened}/interpretation-runs", json=_payload(obs_id))
    assert authored.status_code == 201, authored.text
    drafted = client.post(f"/api/v1/patients/{opened}/reports")
    assert drafted.status_code == 201, drafted.text
    now = datetime.now(UTC)
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=opened,
        kpi_code="metabolic.hba1c",
        value="9.9",
        observed_at=now,
        received_at=now,
        review_status=ReviewStatus.PENDING,
    )
    admin_session.commit()

    login(client, "changes-a@synthetic.example")
    select_tenant(client, tenant.id)
    body = client.get(URL).json()
    assert (body["opened"], body["never_opened"]) == (1, 1)
    assert [r["patient_id"] for r in body["rows"]] == [opened]
    row = body["rows"][0]
    assert row["display_name"] == "Opened Record"
    assert row["new_published"] == 1
    assert row["new_pending"] == 1
    assert row["run_number"] == 1
    assert row["report_status"] == "draft_generated"
    assert row["report_version_no"] == 1
    assert row["run_at"] is not None and row["report_status_at"] is not None
    assert row["changed_at"] == max(
        row["latest_received_at"], row["run_at"], row["report_status_at"]
    )
    assert row["changed_at"] > row["last_opened_at"]

    # Opening the record again clears it.
    assert client.get(f"/api/v1/patients/{opened}").status_code == 200
    assert client.get(URL).json()["rows"] == []

    # A step the person takes themselves is not news to them: their own run stays out.
    pending_id = client.get(f"/api/v1/patients/{opened}/observations").json()
    own = client.post(f"/api/v1/patients/{opened}/interpretation-runs", json=_payload(obs_id))
    assert own.status_code == 201, own.text
    assert client.get(URL).json()["rows"] == []
    assert colleague.id != me.id and len(pending_id) >= 2

    # Audited with a count only, once per read.
    assert _audited_counts(admin_session, tenant.id) == [0, 0, 1, 0, 0]


def test_changes_is_open_to_every_staff_role(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="changes-assistant@synthetic.example",
        tenant_name="Changes Roles",
        tenant_slug="changes-roles",
        role=Role.ASSISTANT,
    )
    resp = client.get(URL)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"opened": 0, "never_opened": 0, "rows": []}


def test_changes_excludes_other_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="changes-iso-a@synthetic.example",
        tenant_name="Changes Iso A",
        tenant_slug="changes-iso-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "Iso A Patient"}).json()["id"]
    assert client.get(f"/api/v1/patients/{pid}").status_code == 200
    assert client.get(URL).json()["opened"] == 1

    provision_staff(
        admin_session,
        email="changes-iso-b@synthetic.example",
        tenant_name="Changes Iso B",
        tenant_slug="changes-iso-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "changes-iso-b@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        assert cb.get(URL).json() == {"opened": 0, "never_opened": 0, "rows": []}
