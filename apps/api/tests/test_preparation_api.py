"""The practice view (docs/notes/0023): the page before a visit for every record at once.

GET /worklist/preparation is tenant-scoped (RLS beneath an explicit filter), open to every
staff role that may read observations, audited with a count only, and says per record what
the patient page's own card says: values received after the latest run, markers outside the
laboratory's interval, core markers old or missing, values awaiting review, domains the run
left without a verdict. Counts of what stands — never a rating, a rank or a sum.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.main import app
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.service import STALE_AFTER_DAYS
from tests.helpers import login, login_as, provision_staff, select_tenant
from tests.test_interpretation_author_api import _IMPORT, _payload

URL = "/api/v1/worklist/preparation"


def _obs(
    admin_session: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: str,
    kpi_code: str | None,
    value: str,
    observed_at: datetime,
    received_at: datetime,
    reference_low: str | None = None,
    reference_high: str | None = None,
    review_status: ReviewStatus = ReviewStatus.PUBLISHED,
) -> None:
    admin_session.add(
        Observation(
            tenant_id=tenant_id,
            patient_id=uuid.UUID(str(patient_id)),
            original_name=kpi_code or "Synthetic value",
            original_value=value,
            original_unit="mmol/L",
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal(value),
            normalized_value=Decimal(value),
            normalized_unit="mmol/L",
            reference_low=Decimal(reference_low) if reference_low is not None else None,
            reference_high=Decimal(reference_high) if reference_high is not None else None,
            normalization_version="test",
            observed_at=observed_at,
            received_at=received_at,
            review_status=review_status,
            kpi_code=kpi_code,
        )
    )


def test_preparation_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get(URL).status_code == 401


def test_preparation_counts_what_stands_in_each_record(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="prep-a@synthetic.example",
        tenant_name="Prep A",
        tenant_slug="prep-a",
        role=Role.CLINICIAN,
    )
    now = datetime.now(UTC)

    # Record 1: one imported value, a run over it, then two values after the run — one of them
    # outside its interval — and one old core marker, one value no catalog marker names.
    pid = client.post("/api/v1/patients", json={"display_name": "Prep One"}).json()["id"]
    client.post(f"/api/v1/patients/{pid}/imports", json=_IMPORT)
    obs_id = client.get(f"/api/v1/patients/{pid}/observations").json()[0]["observation_id"]
    authored = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id))
    assert authored.status_code == 201, authored.text
    after = now + timedelta(seconds=1)
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        kpi_code="metabolic.hba1c",
        value="7.1",
        reference_low="4.0",
        reference_high="6.0",
        observed_at=now - timedelta(days=2),
        received_at=after,
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        kpi_code="immune.hs_crp",
        value="1.0",
        reference_low="0",
        reference_high="3.0",
        observed_at=now - timedelta(days=2),
        received_at=after,
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        kpi_code="cardio.apob",
        value="1.0",
        observed_at=now - timedelta(days=STALE_AFTER_DAYS + 30),
        received_at=now - timedelta(days=STALE_AFTER_DAYS + 29),
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        kpi_code=None,
        value="5",
        observed_at=now - timedelta(days=1),
        received_at=after,
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        kpi_code="metabolic.hba1c",
        value="9.9",
        observed_at=now,
        received_at=after,
        review_status=ReviewStatus.PENDING,
    )
    # Record 2: nothing at all.
    empty = client.post("/api/v1/patients", json={"display_name": "Prep Two"}).json()["id"]
    admin_session.commit()

    resp = client.get(URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stale_after_days"] == STALE_AFTER_DAYS
    assert body["core_markers"] == 43
    rows = {r["patient_id"]: r for r in body["rows"]}
    assert set(rows) == {pid, empty}

    one = rows[pid]
    assert one["latest_run_number"] == 1
    # Three standing values arrived after the run (HbA1c, hs-CRP and the unnamed one); the
    # pending value is not among them, and one of the three lies above its interval.
    assert one["new_since_run"] == 3
    assert one["new_outside"] == 1
    assert one["outside"] == 1
    # Two core markers' latest values are older than the stated days: ApoB, and the LDL the
    # import brought (its sample is from 2025).
    assert one["stale_core"] == 2
    # Of 43 core markers, the record holds LDL (from the import), HbA1c, hs-CRP and ApoB.
    assert one["missing_core"] == 39
    assert one["values_pending"] == 1
    assert one["unassigned"] == 1
    # The run recorded all six verdicts.
    assert one["domains_without_verdict"] == 0

    two = rows[empty]
    assert two["latest_run_number"] is None
    assert two["domains_without_verdict"] is None
    assert two["new_since_run"] == 0
    assert two["missing_core"] == 43
    assert two["report_status"] is None

    # Audited with a count only.
    event = (
        admin_session.execute(
            select(AuditEvent).where(AuditEvent.action == "worklist.preparation.read")
        )
        .scalars()
        .one()
    )
    assert event.tenant_id == tenant.id
    assert event.detail == {"count": 2}


def test_preparation_is_open_to_every_staff_role(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="prep-assistant@synthetic.example",
        tenant_name="Prep Roles",
        tenant_slug="prep-roles",
        role=Role.ASSISTANT,
    )
    resp = client.get(URL)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows"] == []


def test_preparation_excludes_other_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="prep-iso-a@synthetic.example",
        tenant_name="Prep Iso A",
        tenant_slug="prep-iso-a",
        role=Role.CLINICIAN,
    )
    client.post("/api/v1/patients", json={"display_name": "Iso A Patient"})
    assert len(client.get(URL).json()["rows"]) == 1

    provision_staff(
        admin_session,
        email="prep-iso-b@synthetic.example",
        tenant_name="Prep Iso B",
        tenant_slug="prep-iso-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "prep-iso-b@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        assert cb.get(URL).json()["rows"] == []
