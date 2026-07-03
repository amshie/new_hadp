"""Derived-value computation (ADR-0004 Slice 4): deterministic formulas, fail-closed inputs,
provenance + immutable lineage, idempotency/supersession, formula-version comparability, and the
tenant-RLS + append-only guarantees on observation_derivation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.derivations.models import ObservationDerivation
from hadp_api.modules.derivations.registry import FORMULAS
from hadp_api.modules.derivations.service import compute_derived
from hadp_api.modules.enums import KpiComparisonPolicy, KpiMeasurementClass, ReviewStatus, ValueType
from hadp_api.modules.kpi.catalog_data import FORMULA_IDS
from hadp_api.modules.kpi.service import resolve_comparison_policies
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.comparability import POLICY_REQUIRED_COLUMNS
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.tenancy.models import Tenant

_JAN = datetime(2025, 1, 15, tzinfo=UTC)
_JUN = datetime(2025, 6, 10, tzinfo=UTC)
_JUL = datetime(2025, 7, 1, tzinfo=UTC)


def _patient(db: Session, slug: str = "deriv-clinic") -> tuple[Tenant, Patient]:
    tenant = Tenant(name="Derivations Clinic", slug=slug, is_synthetic=True)
    db.add(tenant)
    db.flush()
    patient = Patient(
        tenant_id=tenant.id,
        external_ref=f"DRV-{slug}",
        display_name="Derivations Patient",
        date_of_birth=date(1980, 1, 1),
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()
    return tenant, patient


def _input(
    db: Session,
    tenant: Tenant,
    patient: Patient,
    *,
    kpi_code: str,
    value: str,
    unit: str,
    observed_at: datetime = _JUN,
    review_status: ReviewStatus = ReviewStatus.PUBLISHED,
) -> Observation:
    obs = Observation(
        tenant_id=tenant.id,
        patient_id=patient.id,
        original_name=kpi_code,
        original_value=value,
        kpi_code=kpi_code,
        value_type=ValueType.NUMERIC,
        numeric_value=Decimal(value),
        normalized_value=Decimal(value),
        normalized_unit=unit,
        normalization_version="test",
        observed_at=observed_at,
        received_at=datetime.now(UTC),
        review_status=review_status,
    )
    db.add(obs)
    db.flush()
    return obs


def _obs(db: Session, t: Tenant, p: Patient, code: str, value: str, unit: str) -> Observation:
    return _input(db, t, p, kpi_code=code, value=value, unit=unit)


def _bp(
    db: Session, t: Tenant, p: Patient, *, sys: str = "122", dia: str = "78", at: datetime = _JUN
) -> None:
    _input(db, t, p, kpi_code="cardio.systolic_bp", value=sys, unit="mm[Hg]", observed_at=at)
    _input(db, t, p, kpi_code="cardio.diastolic_bp", value=dia, unit="mm[Hg]", observed_at=at)


def _compute(db: Session, t: Tenant, p: Patient, formula_id: str = "map.v1") -> Observation | None:
    return compute_derived(db, tenant_id=t.id, patient_id=p.id, formula_id=formula_id)


def _derived_count(db: Session, patient: Patient) -> int:
    return db.execute(
        select(func.count())
        .select_from(Observation)
        .where(
            Observation.patient_id == patient.id,
            Observation.source_category == KpiMeasurementClass.DERIVED,
        )
    ).scalar_one()


# --- registry (pure) ---


def test_formulas_are_correct_quantized_and_match_catalog() -> None:
    assert FORMULAS["non_hdl_c.v1"].fn(
        {"total_cholesterol": Decimal("4.8"), "hdl": Decimal("1.3")}
    ) == Decimal("3.5")
    assert FORMULAS["pulse_pressure.v1"].fn(
        {"systolic": Decimal("122"), "diastolic": Decimal("78")}
    ) == Decimal("44")
    mean = FORMULAS["map.v1"].fn({"systolic": Decimal("122"), "diastolic": Decimal("78")})
    assert Decimal("78") <= mean <= Decimal("122")  # MAP lies within [diastolic, systolic]
    assert FORMULAS["nlr.v1"].fn(
        {"neutrophils": Decimal("3.8"), "lymphocytes": Decimal("1.9")}
    ) == Decimal("2")
    # Every registry formula targets a derived KPI whose catalog formula_id matches (no drift).
    for formula in FORMULAS.values():
        assert FORMULA_IDS[formula.output_kpi_code] == formula.formula_id


# --- compute_derived: value, provenance, lineage ---


def test_compute_writes_value_provenance_and_lineage(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _bp(admin_session, tenant, patient)
    derived = _compute(admin_session, tenant, patient)
    assert derived is not None
    assert derived.kpi_code == "cardio.mean_arterial_pressure"
    assert derived.source_category == KpiMeasurementClass.DERIVED
    assert derived.formula_id == "map.v1"
    assert derived.formula_version == "v1"
    assert derived.algorithm_name == "mean_arterial_pressure"
    assert derived.normalized_value == Decimal("93")  # 78 + (122-78)/3 = 92.67 -> 93
    assert derived.normalized_unit == "mm[Hg]"
    assert derived.metric_code is None  # a derived value has no source code
    links = (
        admin_session.execute(
            select(ObservationDerivation).where(
                ObservationDerivation.derived_observation_id == derived.id
            )
        )
        .scalars()
        .all()
    )
    assert {link.role for link in links} == {"systolic", "diastolic"}


def test_compute_non_hdl_c(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _obs(admin_session, tenant, patient, "cardio.total_cholesterol", "4.8", "mmol/L")
    _obs(admin_session, tenant, patient, "cardio.hdl_c", "1.3", "mmol/L")
    derived = _compute(admin_session, tenant, patient, formula_id="non_hdl_c.v1")
    assert derived is not None
    assert derived.normalized_value == Decimal("3.50")
    assert derived.normalized_unit == "mmol/L"


# --- fail-closed (§9.8) ---


def test_fails_closed_on_missing_input(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _obs(admin_session, tenant, patient, "cardio.systolic_bp", "122", "mm[Hg]")
    # No diastolic input.
    assert _compute(admin_session, tenant, patient) is None
    assert _derived_count(admin_session, patient) == 0


def test_fails_closed_on_unpublished_input(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _obs(admin_session, tenant, patient, "cardio.systolic_bp", "122", "mm[Hg]")
    _input(
        admin_session,
        tenant,
        patient,
        kpi_code="cardio.diastolic_bp",
        value="78",
        unit="mm[Hg]",
        review_status=ReviewStatus.PENDING,
    )
    assert _compute(admin_session, tenant, patient) is None
    assert _derived_count(admin_session, patient) == 0


def test_fails_closed_on_wrong_unit(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _obs(admin_session, tenant, patient, "cardio.systolic_bp", "122", "mm[Hg]")
    _input(admin_session, tenant, patient, kpi_code="cardio.diastolic_bp", value="10.4", unit="kPa")
    assert _compute(admin_session, tenant, patient) is None
    assert _derived_count(admin_session, patient) == 0


# --- idempotency + supersession ---


def test_recompute_same_inputs_is_idempotent(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _bp(admin_session, tenant, patient)
    first = _compute(admin_session, tenant, patient)
    second = _compute(admin_session, tenant, patient)
    assert first is not None and second is not None
    assert first.id == second.id
    assert _derived_count(admin_session, patient) == 1


def test_newer_input_supersedes_prior_derived(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _bp(admin_session, tenant, patient, sys="122", dia="78", at=_JUN)
    first = _compute(admin_session, tenant, patient)
    # A newer systolic reading changes the input set -> a new derived row superseding the prior.
    _input(
        admin_session,
        tenant,
        patient,
        kpi_code="cardio.systolic_bp",
        value="130",
        unit="mm[Hg]",
        observed_at=_JUL,
    )
    second = _compute(admin_session, tenant, patient)
    assert first is not None and second is not None
    assert second.id != first.id
    assert second.supersedes_observation_id == first.id
    assert _derived_count(admin_session, patient) == 2  # prior preserved (append-only)


# --- comparability (formula_version) ---


def test_derived_default_policy_is_same_formula_version(admin_session: Session) -> None:
    resolved = resolve_comparison_policies(admin_session, {"cardio.mean_arterial_pressure"})
    assert resolved["cardio.mean_arterial_pressure"] is (
        KpiComparisonPolicy.SAME_FORMULA_VERSION_REQUIRED
    )
    assert POLICY_REQUIRED_COLUMNS[KpiComparisonPolicy.SAME_FORMULA_VERSION_REQUIRED] == (
        "formula_version",
    )


def _derived_row(
    db: Session, t: Tenant, p: Patient, *, value: str, formula_version: str, at: datetime
) -> None:
    db.add(
        Observation(
            tenant_id=t.id,
            patient_id=p.id,
            original_name="Mean arterial pressure",
            original_value=value,
            kpi_code="cardio.mean_arterial_pressure",
            source_category=KpiMeasurementClass.DERIVED,
            formula_id=f"map.{formula_version}",
            formula_version=formula_version,
            algorithm_name="mean_arterial_pressure",
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal(value),
            normalized_value=Decimal(value),
            normalized_unit="mm[Hg]",
            normalization_version=f"map.{formula_version}",
            observed_at=at,
            received_at=datetime.now(UTC),
            review_status=ReviewStatus.PUBLISHED,
        )
    )
    db.flush()


def test_same_formula_version_trends_different_version_does_not(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session, slug="deriv-cmp")
    _derived_row(admin_session, tenant, patient, value="90", formula_version="v1", at=_JAN)
    _derived_row(admin_session, tenant, patient, value="93", formula_version="v1", at=_JUN)
    latest_same = obs_service.build_timeline(admin_session, patient.id)[-1]
    assert latest_same.comparability == "comparable"
    assert latest_same.delta_vs_previous == Decimal("3")

    tenant2, patient2 = _patient(admin_session, slug="deriv-cmp2")
    _derived_row(admin_session, tenant2, patient2, value="90", formula_version="v1", at=_JAN)
    _derived_row(admin_session, tenant2, patient2, value="93", formula_version="v2", at=_JUN)
    latest_diff = obs_service.build_timeline(admin_session, patient2.id)[-1]
    assert latest_diff.delta_vs_previous is None  # cross-version delta withheld
    assert latest_diff.comparability == "not_comparable"


# --- tenant RLS + append-only on observation_derivation ---


def test_observation_derivation_is_append_only(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    _bp(admin_session, tenant, patient)
    _compute(admin_session, tenant, patient)
    admin_session.commit()
    with pytest.raises(DBAPIError):
        admin_session.execute(text("UPDATE observation_derivation SET role = 'x'"))
    admin_session.rollback()
    with pytest.raises(DBAPIError):
        admin_session.execute(text("DELETE FROM observation_derivation"))
    admin_session.rollback()


def test_rls_scopes_observation_derivation_by_tenant(admin_session: Session) -> None:
    tenant_a, patient_a = _patient(admin_session, slug="deriv-rls-a")
    _bp(admin_session, tenant_a, patient_a)
    _compute(admin_session, tenant_a, patient_a)
    tenant_b, patient_b = _patient(admin_session, slug="deriv-rls-b")
    _bp(admin_session, tenant_b, patient_b)
    _compute(admin_session, tenant_b, patient_b)
    admin_session.commit()

    sessionmaker = get_sessionmaker()
    with sessionmaker() as scoped:
        set_tenant_context(scoped, tenant_a.id)
        tenant_ids = scoped.execute(select(ObservationDerivation.tenant_id)).scalars().all()
        scoped.rollback()
    assert tenant_ids == [tenant_a.id, tenant_a.id]  # only A's two links (systolic, diastolic)

    with sessionmaker() as no_ctx:
        count_none = no_ctx.execute(
            select(func.count()).select_from(ObservationDerivation)
        ).scalar_one()
        no_ctx.rollback()
    assert count_none == 0  # deny-by-default with no tenant context
