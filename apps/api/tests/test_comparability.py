"""Longitudinal comparability / §9 non-merge (ADR-0004 Slice 3): the is_comparable rule, read-time
policy resolution per measurement class, and build_timeline withholding an incomparable delta while
keeping a comparable one."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from hadp_api.modules.enums import (
    ComparabilityReason,
    KpiComparisonPolicy,
    KpiMeasurementClass,
    ReviewStatus,
    ValueType,
)
from hadp_api.modules.kpi.service import policy_for_measurement_class, resolve_comparison_policies
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.comparability import POLICY_REQUIRED_COLUMNS, is_comparable
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.tenancy.models import Tenant


def _obs(**context: object) -> Observation:
    o = Observation()
    for key, value in context.items():
        setattr(o, key, value)
    return o


# --- is_comparable (pure) ---


def test_method_aware_needs_no_context() -> None:
    assert is_comparable(_obs(), _obs(), KpiComparisonPolicy.METHOD_AWARE) == (True, None)


def test_instrument_version_match_differ_missing() -> None:
    policy = KpiComparisonPolicy.SAME_INSTRUMENT_VERSION_REQUIRED
    assert is_comparable(_obs(instrument_version="A"), _obs(instrument_version="A"), policy) == (
        True,
        None,
    )
    assert is_comparable(_obs(instrument_version="A"), _obs(instrument_version="B"), policy) == (
        False,
        ComparabilityReason.CONTEXT_DIFFERS,
    )
    assert is_comparable(_obs(instrument_version="A"), _obs(), policy) == (
        False,
        ComparabilityReason.CONTEXT_MISSING,
    )


def test_device_algorithm_requires_both_device_and_version() -> None:
    policy = KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED
    a = _obs(device_model="DXA-A", firmware_or_algorithm_version="1")
    assert is_comparable(
        a, _obs(device_model="DXA-A", firmware_or_algorithm_version="1"), policy
    ) == (True, None)
    # Same device, different algorithm version -> not comparable.
    assert is_comparable(
        a, _obs(device_model="DXA-A", firmware_or_algorithm_version="2"), policy
    ) == (False, ComparabilityReason.CONTEXT_DIFFERS)
    # Missing the version on one side -> not comparable.
    assert is_comparable(a, _obs(device_model="DXA-A"), policy) == (
        False,
        ComparabilityReason.CONTEXT_MISSING,
    )


def test_not_longitudinal_never_merges() -> None:
    assert is_comparable(_obs(), _obs(), KpiComparisonPolicy.NOT_LONGITUDINAL) == (
        False,
        ComparabilityReason.NOT_LONGITUDINAL,
    )


def test_every_policy_value_has_a_required_columns_entry() -> None:
    assert set(POLICY_REQUIRED_COLUMNS) == set(KpiComparisonPolicy)


# --- policy resolution (read-time per-class defaults; catalog stays NULL) ---


def test_policy_for_measurement_class_defaults() -> None:
    assert policy_for_measurement_class(KpiMeasurementClass.LABORATORY) is (
        KpiComparisonPolicy.METHOD_AWARE
    )
    assert policy_for_measurement_class(KpiMeasurementClass.BODY_COMPOSITION) is (
        KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED
    )
    assert policy_for_measurement_class(KpiMeasurementClass.FUNCTIONAL_TEST) is (
        KpiComparisonPolicy.SAME_INSTRUMENT_VERSION_REQUIRED
    )


def test_resolve_comparison_policies_uses_class_defaults(admin_session: Session) -> None:
    resolved = resolve_comparison_policies(
        admin_session,
        {
            "cardio.ldl_c",  # laboratory
            "msk.appendicular_lean_mass",  # body_composition
            "neuro.processing_speed_score",  # functional_test
            "regen.hrv_rmssd",  # wearable
        },
    )
    assert resolved["cardio.ldl_c"] is KpiComparisonPolicy.METHOD_AWARE
    assert resolved["msk.appendicular_lean_mass"] is (
        KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED
    )
    assert resolved["neuro.processing_speed_score"] is (
        KpiComparisonPolicy.SAME_INSTRUMENT_VERSION_REQUIRED
    )
    assert resolved["regen.hrv_rmssd"] is KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED


# --- build_timeline integration ---


def _patient(db: Session) -> tuple[Tenant, Patient]:
    tenant = Tenant(name="Comparability Clinic", slug="cmp-clinic", is_synthetic=True)
    db.add(tenant)
    db.flush()
    patient = Patient(
        tenant_id=tenant.id,
        external_ref="CMP-0001",
        display_name="Comparability Patient",
        date_of_birth=date(1980, 1, 1),
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()
    return tenant, patient


def _add_obs(
    db: Session,
    tenant: Tenant,
    patient: Patient,
    *,
    kpi_code: str,
    value: str,
    unit: str,
    observed_at: datetime,
    **context: object,
) -> None:
    obs = Observation(
        tenant_id=tenant.id,
        patient_id=patient.id,
        original_name=kpi_code,
        original_value=value,
        metric_code=kpi_code,
        code_system="LOINC",
        kpi_code=kpi_code,
        value_type=ValueType.NUMERIC,
        numeric_value=Decimal(value),
        normalized_value=Decimal(value),
        normalized_unit=unit,
        normalization_version="test",
        observed_at=observed_at,
        received_at=datetime.now(UTC),
        review_status=ReviewStatus.PUBLISHED,
    )
    for key, ctx_value in context.items():
        setattr(obs, key, ctx_value)
    db.add(obs)
    db.flush()


def test_timeline_withholds_incomparable_body_composition_delta(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    # Same KPI + unit, but a DXA device + software change between visits (body_composition policy).
    _add_obs(
        admin_session,
        tenant,
        patient,
        kpi_code="msk.appendicular_lean_mass",
        value="21.0",
        unit="kg",
        observed_at=datetime(2025, 1, 20, tzinfo=UTC),
        source_category=KpiMeasurementClass.BODY_COMPOSITION,
        device_model="DXA-A",
        firmware_or_algorithm_version="sw-3.1",
    )
    _add_obs(
        admin_session,
        tenant,
        patient,
        kpi_code="msk.appendicular_lean_mass",
        value="21.6",
        unit="kg",
        observed_at=datetime(2025, 6, 12, tzinfo=UTC),
        source_category=KpiMeasurementClass.BODY_COMPOSITION,
        device_model="DXA-B",
        firmware_or_algorithm_version="sw-4.0",
    )
    latest = obs_service.build_timeline(admin_session, patient.id)[-1]
    assert latest.delta_vs_previous is None  # fabricated change withheld
    assert latest.comparability == "not_comparable"
    assert latest.comparability_reason == "context_differs"


def test_timeline_keeps_comparable_lab_delta_with_null_context(admin_session: Session) -> None:
    tenant, patient = _patient(admin_session)
    # Laboratory KPI -> method_aware: NULL context must NOT suppress the delta (regression guard).
    _add_obs(
        admin_session,
        tenant,
        patient,
        kpi_code="cardio.ldl_c",
        value="3.6",
        unit="mmol/L",
        observed_at=datetime(2025, 1, 15, tzinfo=UTC),
    )
    _add_obs(
        admin_session,
        tenant,
        patient,
        kpi_code="cardio.ldl_c",
        value="2.8",
        unit="mmol/L",
        observed_at=datetime(2025, 6, 10, tzinfo=UTC),
    )
    latest = obs_service.build_timeline(admin_session, patient.id)[-1]
    assert latest.delta_vs_previous == Decimal("-0.8")
    assert latest.comparability == "comparable"
