"""Per-tenant KPI configuration.

An owner views the global catalog with their clinic's EFFECTIVE settings and adjusts which KPIs
are active/visible for their own clinic. Guarantees exercised here:
- owner-only (deny-by-default matrix);
- effective value = COALESCE(tenant override, catalog default);
- a specialist/research KPI can never be made patient-visible (the catalog rule is not bendable);
- overrides are tenant-isolated (one clinic's change never affects another — RLS);
- the global catalog is never mutated.
"""

from __future__ import annotations

from sqlalchemy import select

from hadp_api.auth.authz import Action, can
from hadp_api.modules.enums import KpiCatalogTier, Role
from hadp_api.modules.kpi.models import KpiCatalog
from tests.helpers import login_as

CORE_ENABLED = "metabolic.hba1c"  # tier core, default_enabled True
EXTENDED_DISABLED = "metabolic.body_fat_percent"  # tier extended, default_enabled False


def _find(rows: list[dict], code: str) -> dict:
    return next(r for r in rows if r["kpi_code"] == code)


def test_kpi_config_authz_matrix() -> None:
    for action in (Action.KPI_CONFIG_READ, Action.KPI_CONFIG_WRITE):
        assert can(Role.OWNER, action) is True
        for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
            assert can(role, action) is False


def test_owner_sees_catalog_with_effective_defaults(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kc-o@synthetic.example",
        tenant_name="KC",
        tenant_slug="kc",
        role=Role.OWNER,
    )
    r = client.get("/api/v1/kpi-config")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) >= 100  # the full active catalog is visible
    core = _find(rows, CORE_ENABLED)
    assert core["effective_enabled"] is True
    assert core["is_overridden"] is False
    assert _find(rows, EXTENDED_DISABLED)["effective_enabled"] is False


def test_owner_disables_core_enables_extended_and_resets(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kc-edit@synthetic.example",
        tenant_name="KC Edit",
        tenant_slug="kc-edit",
        role=Role.OWNER,
    )
    # Disable a core KPI for this clinic.
    r = client.patch(f"/api/v1/kpi-config/{CORE_ENABLED}", json={"enabled": False})
    assert r.status_code == 200, r.text
    assert r.json()["effective_enabled"] is False
    assert r.json()["is_overridden"] is True

    # Enable a normally-off extended KPI for this clinic.
    r = client.patch(f"/api/v1/kpi-config/{EXTENDED_DISABLED}", json={"enabled": True})
    assert r.status_code == 200, r.text
    assert r.json()["effective_enabled"] is True

    rows = client.get("/api/v1/kpi-config").json()
    assert _find(rows, CORE_ENABLED)["effective_enabled"] is False
    assert _find(rows, EXTENDED_DISABLED)["effective_enabled"] is True

    # Reset the core override → back to the catalog default (enabled).
    r = client.delete(f"/api/v1/kpi-config/{CORE_ENABLED}")
    assert r.status_code == 200, r.text
    assert r.json()["effective_enabled"] is True
    assert r.json()["is_overridden"] is False


def test_specialist_research_kpi_cannot_be_patient_visible(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kc-guard@synthetic.example",
        tenant_name="KC Guard",
        tenant_slug="kc-guard",
        role=Role.OWNER,
    )
    restricted = (
        admin_session.execute(
            select(KpiCatalog.code).where(
                KpiCatalog.tier.in_([KpiCatalogTier.SPECIALIST, KpiCatalogTier.RESEARCH])
            )
        )
        .scalars()
        .first()
    )
    assert restricted is not None, "catalog should contain specialist/research KPIs"
    r = client.patch(
        f"/api/v1/kpi-config/{restricted}",
        json={"enabled": True, "patient_visible": True},
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "intended_use_violation"


def test_unknown_kpi_code_is_404(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kc-404@synthetic.example",
        tenant_name="KC 404",
        tenant_slug="kc-404",
        role=Role.OWNER,
    )
    missing = "/api/v1/kpi-config/does.not.exist"
    assert client.patch(missing, json={"enabled": True}).status_code == 404
    assert client.delete(missing).status_code == 404


def test_non_owner_cannot_access_kpi_config(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        slug = f"kcn-{role.value}"[:60]
        login_as(
            client,
            admin_session,
            email=f"{role.value}@kcn.example",
            tenant_name=slug,
            tenant_slug=slug,
            role=role,
        )
        assert client.get("/api/v1/kpi-config").status_code == 403
        assert (
            client.patch(f"/api/v1/kpi-config/{CORE_ENABLED}", json={"enabled": False}).status_code
            == 403
        )
        assert client.delete(f"/api/v1/kpi-config/{CORE_ENABLED}").status_code == 403


def test_overrides_are_tenant_isolated(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # Tenant A disables a core KPI; tenant B still sees the catalog default (RLS + explicit scope).
    login_as(
        client,
        admin_session,
        email="kc-a@synthetic.example",
        tenant_name="KC A",
        tenant_slug="kc-a",
        role=Role.OWNER,
    )
    assert (
        client.patch(f"/api/v1/kpi-config/{CORE_ENABLED}", json={"enabled": False}).status_code
        == 200
    )
    a_rows = client.get("/api/v1/kpi-config").json()
    assert _find(a_rows, CORE_ENABLED)["effective_enabled"] is False

    login_as(
        client,
        admin_session,
        email="kc-b@synthetic.example",
        tenant_name="KC B",
        tenant_slug="kc-b",
        role=Role.OWNER,
    )
    b_rows = client.get("/api/v1/kpi-config").json()
    assert _find(b_rows, CORE_ENABLED)["effective_enabled"] is True
    assert _find(b_rows, CORE_ENABLED)["is_overridden"] is False
