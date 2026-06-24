"""Worklist + single-patient read endpoints: tenant isolation and auth."""

from __future__ import annotations

from fastapi.testclient import TestClient

from hadp_api.main import app
from hadp_api.modules.enums import Role
from tests.helpers import login, login_as, provision_staff, select_tenant


def test_worklist_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/worklist").status_code == 401


def test_worklist_is_tenant_scoped(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Clinic A clinician creates a patient; it appears in A's worklist.
    login_as(
        client,
        admin_session,
        email="wla@synthetic.example",
        tenant_name="WL A",
        tenant_slug="wl-a",
        role=Role.CLINICIAN,
    )
    client.post("/api/v1/patients", json={"display_name": "WL Patient A"})
    a_rows = client.get("/api/v1/worklist").json()
    assert any(r["display_name"] == "WL Patient A" for r in a_rows)

    # Clinic B clinician sees none of clinic A's rows.
    provision_staff(
        admin_session,
        email="wlb@synthetic.example",
        tenant_name="WL B",
        tenant_slug="wl-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "wlb@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        b_rows = cb.get("/api/v1/worklist").json()
        assert b_rows == []


def test_get_patient_cross_tenant_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="gpa@synthetic.example",
        tenant_name="GP A",
        tenant_slug="gp-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "GP Patient"}).json()["id"]

    provision_staff(
        admin_session,
        email="gpb@synthetic.example",
        tenant_name="GP B",
        tenant_slug="gp-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "gpb@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        # RLS hides A's patient -> tenant-scoped get returns 404, not another tenant's data.
        assert cb.get(f"/api/v1/patients/{pid}").status_code == 404
