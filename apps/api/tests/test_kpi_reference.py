"""Clinic-defined KPI reference interval (fallback-only, position-only).

An owner sets a clinic reference for a KPI (in its canonical unit). Guarantees:
- owner-only, tenant-isolated (RLS);
- a two-sided, ordered interval on a KPI that has a canonical unit (else rejected);
- it is applied to the within/above/below marker ONLY when a lab result carries no reference of
  its own AND the units match — the lab-provided reference always wins;
- it never overwrites the source reference and is opt-in per caller (the clinician timeline uses
  it; the report/evidence path does not).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.kpi.models import KpiCatalog
from hadp_api.modules.kpi_config.service import ClinicReference
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.service import _resolve_reference_source
from hadp_api.modules.patients.models import Patient
from tests.helpers import login_as

HBA1C = "metabolic.hba1c"  # canonical unit "%"
ALT = "metabolic.alt"  # canonical unit "[IU]/L"


# --- Pure logic: which reference backs the marker (the patient-safety-critical decision) ---


def _obs(*, kpi_code, normalized_unit, reference_low=None, reference_high=None) -> Observation:
    return Observation(
        kpi_code=kpi_code,
        normalized_unit=normalized_unit,
        reference_low=reference_low,
        reference_high=reference_high,
    )


def test_resolve_lab_reference_always_wins() -> None:
    refs = {HBA1C: ClinicReference(low=Decimal("4"), high=Decimal("6"), unit="%")}
    obs = _obs(kpi_code=HBA1C, normalized_unit="%", reference_low=Decimal("3"))
    assert _resolve_reference_source(obs, refs) == ("laboratory", None, None)


def test_resolve_clinic_fallback_when_no_lab_reference_and_unit_matches() -> None:
    refs = {HBA1C: ClinicReference(low=Decimal("4"), high=Decimal("6"), unit="%")}
    obs = _obs(kpi_code=HBA1C, normalized_unit="%")
    assert _resolve_reference_source(obs, refs) == ("clinic", Decimal("4"), Decimal("6"))


def test_resolve_no_clinic_fallback_on_unit_mismatch() -> None:
    refs = {HBA1C: ClinicReference(low=Decimal("4"), high=Decimal("6"), unit="%")}
    obs = _obs(kpi_code=HBA1C, normalized_unit="mmol/L")  # unit differs -> never applied
    assert _resolve_reference_source(obs, refs) == (None, None, None)


def test_resolve_none_when_no_refs_at_all() -> None:
    obs = _obs(kpi_code=HBA1C, normalized_unit="%")
    assert _resolve_reference_source(obs, None) == (None, None, None)
    assert _resolve_reference_source(obs, {}) == (None, None, None)


# --- API: set / clear / validate / authz / RLS ---


def test_owner_sets_and_clears_a_clinic_reference(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kr-o@synthetic.example",
        tenant_name="KR",
        tenant_slug="kr",
        role=Role.OWNER,
    )
    r = client.put(
        f"/api/v1/kpi-config/{HBA1C}/reference", json={"reference_low": "4", "reference_high": "6"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reference_low"] == "4" and body["reference_high"] == "6"
    assert body["reference_unit"] == "%" and body["canonical_unit"] == "%"
    assert body["is_overridden"] is True

    # Visible in the list.
    rows = client.get("/api/v1/kpi-config").json()
    hba1c = next(x for x in rows if x["kpi_code"] == HBA1C)
    assert hba1c["reference_low"] == "4"

    # Clear it. The leftover settings row now holds only catalog defaults, so it no longer
    # reads as an override.
    r = client.delete(f"/api/v1/kpi-config/{HBA1C}/reference")
    assert r.status_code == 200, r.text
    assert r.json()["reference_low"] is None and r.json()["reference_unit"] is None
    assert r.json()["is_overridden"] is False


def test_reference_validation(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kr-v@synthetic.example",
        tenant_name="KR V",
        tenant_slug="kr-v",
        role=Role.OWNER,
    )
    # low must be strictly less than high.
    r = client.put(
        f"/api/v1/kpi-config/{HBA1C}/reference", json={"reference_low": "6", "reference_high": "4"}
    )
    assert r.status_code == 422, r.text

    # Unknown KPI -> 404.
    assert (
        client.put(
            "/api/v1/kpi-config/does.not.exist/reference",
            json={"reference_low": "1", "reference_high": "2"},
        ).status_code
        == 404
    )

    # A KPI with no canonical unit (e.g. a panel) cannot carry a numeric reference.
    no_unit = (
        admin_session.execute(
            select(KpiCatalog.code).where(KpiCatalog.canonical_unit_ucum.is_(None))
        )
        .scalars()
        .first()
    )
    if no_unit is not None:
        r = client.put(
            f"/api/v1/kpi-config/{no_unit}/reference",
            json={"reference_low": "1", "reference_high": "2"},
        )
        assert r.status_code == 422, r.text


def test_non_owner_cannot_set_reference(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        slug = f"krn-{role.value}"[:60]
        login_as(
            client,
            admin_session,
            email=f"{role.value}@krn.example",
            tenant_name=slug,
            tenant_slug=slug,
            role=role,
        )
        assert (
            client.put(
                f"/api/v1/kpi-config/{HBA1C}/reference",
                json={"reference_low": "4", "reference_high": "6"},
            ).status_code
            == 403
        )
        assert client.delete(f"/api/v1/kpi-config/{HBA1C}/reference").status_code == 403


def test_reference_is_tenant_isolated(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    login_as(
        client,
        admin_session,
        email="kr-a@synthetic.example",
        tenant_name="KR A",
        tenant_slug="kr-a",
        role=Role.OWNER,
    )
    assert (
        client.put(
            f"/api/v1/kpi-config/{HBA1C}/reference",
            json={"reference_low": "4", "reference_high": "6"},
        ).status_code
        == 200
    )
    login_as(
        client,
        admin_session,
        email="kr-b@synthetic.example",
        tenant_name="KR B",
        tenant_slug="kr-b",
        role=Role.OWNER,
    )
    rows = client.get("/api/v1/kpi-config").json()
    assert next(x for x in rows if x["kpi_code"] == HBA1C)["reference_low"] is None


# --- End-to-end: the clinic fallback drives the timeline marker; the lab reference wins ---


def _add_obs(
    admin_session: Session,
    tenant_id,
    patient_id,
    *,
    kpi_code,
    unit,
    value,
    ref_low=None,
    ref_high=None,
) -> None:
    admin_session.add(
        Observation(
            tenant_id=tenant_id,
            patient_id=patient_id,
            original_name=kpi_code,
            original_value=str(value),
            original_unit=unit,
            kpi_code=kpi_code,
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal(str(value)),
            normalized_value=Decimal(str(value)),
            normalized_unit=unit,
            reference_low=ref_low,
            reference_high=ref_high,
            normalization_version="norm-1",
            observed_at=datetime(2025, 6, 10, tzinfo=UTC),
            received_at=datetime.now(UTC),
            review_status=ReviewStatus.PUBLISHED,
        )
    )


def test_clinic_reference_drives_timeline_marker(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant = login_as(
        client,
        admin_session,
        email="kr-tl@synthetic.example",
        tenant_name="KR TL",
        tenant_slug="kr-tl",
        role=Role.OWNER,
    )
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    pid = patient.id
    # (a) HbA1c with NO lab reference, unit "%" -> eligible for the clinic fallback.
    _add_obs(admin_session, tenant.id, pid, kpi_code=HBA1C, unit="%", value="5.2")
    # (b) HbA1c with NO lab reference but a MISMATCHED unit -> fallback must NOT apply.
    _add_obs(admin_session, tenant.id, pid, kpi_code=HBA1C, unit="mmol/mol", value="33")
    # (c) ALT WITH a lab reference -> lab always wins.
    _add_obs(
        admin_session,
        tenant.id,
        pid,
        kpi_code=ALT,
        unit="[IU]/L",
        value="30",
        ref_low=Decimal("10"),
        ref_high=Decimal("50"),
    )
    admin_session.commit()

    # Owner sets a clinic reference for HbA1c.
    assert (
        client.put(
            f"/api/v1/kpi-config/{HBA1C}/reference",
            json={"reference_low": "4", "reference_high": "6"},
        ).status_code
        == 200
    )

    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    by = {(p["kpi_code"], p["unit"]): p for p in points}

    hba1c_ok = by[(HBA1C, "%")]
    assert hba1c_ok["reference_source"] == "clinic"
    assert hba1c_ok["clinic_reference_low"] == "4" and hba1c_ok["clinic_reference_high"] == "6"
    assert hba1c_ok["reference_low"] is None  # source reference is untouched

    hba1c_mismatch = by[(HBA1C, "mmol/mol")]
    assert hba1c_mismatch["reference_source"] is None  # unit mismatch -> no fallback
    assert hba1c_mismatch["clinic_reference_low"] is None

    alt = by[(ALT, "[IU]/L")]
    assert alt["reference_source"] == "laboratory"  # lab reference wins
    assert alt["clinic_reference_low"] is None
