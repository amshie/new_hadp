"""Deterministic normalization: conversions, confusable units, review routing."""

from __future__ import annotations

from decimal import Decimal

from hadp_api.modules.imports.normalize import normalize


def test_same_unit_passthrough() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="2.8", original_unit="mmol/L")
    assert r.metric_code == "13457-7"
    assert r.normalized_value == Decimal("2.8")
    assert r.normalized_unit == "mmol/L"
    assert not r.needs_review


def test_mgdl_to_mmoll_exact_conversion_with_reference() -> None:
    r = normalize(
        original_name="LDL Cholesterol",
        original_value="100",
        original_unit="mg/dL",
        reference_low="0",
        reference_high="130",
    )
    # 100 mg/dL * 0.0258598 = 2.58598 mmol/L (exact decimal, same factor for the interval)
    assert r.normalized_value == Decimal("2.58598")
    assert r.reference_high == Decimal("130") * Decimal("0.0258598")
    assert r.normalized_unit == "mmol/L"
    assert not r.needs_review


def test_confusable_units_do_not_collapse() -> None:
    same = normalize(original_name="LDL", original_value="3.0", original_unit="mmol/L")
    converted = normalize(original_name="LDL", original_value="3.0", original_unit="mg/dL")
    # 3.0 mmol/L stays 3.0; 3.0 mg/dL converts to a very different normalized value.
    assert same.normalized_value == Decimal("3.0")
    assert converted.normalized_value == Decimal("3.0") * Decimal("0.0258598")
    assert same.normalized_value != converted.normalized_value


def test_unknown_metric_goes_to_review() -> None:
    r = normalize(original_name="Mystery Marker", original_value="1.0", original_unit="mmol/L")
    assert r.metric_code is None
    assert r.normalized_value is None
    assert "unmapped_metric" in r.review_reasons


def test_unsupported_unit_goes_to_review() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="1.0", original_unit="g/L")
    assert "unsupported_unit" in r.review_reasons
    assert r.normalized_value is None


def test_unparseable_value_goes_to_review() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="abc", original_unit="mmol/L")
    assert "unparseable_value" in r.review_reasons


def test_negative_value_is_flagged_impossible() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="-1", original_unit="mmol/L")
    assert "impossible_value" in r.review_reasons


def test_glucose_uses_its_own_factor_not_cholesterols() -> None:
    # Guards against a factor swap: glucose mg/dL->mmol/L is 0.0555, not 0.0258598.
    glucose = normalize(original_name="Glucose", original_value="100", original_unit="mg/dL")
    cholesterol = normalize(
        original_name="LDL Cholesterol", original_value="100", original_unit="mg/dL"
    )
    assert glucose.normalized_value == Decimal("100") * Decimal("0.0555")
    assert glucose.normalized_value != cholesterol.normalized_value
    assert not glucose.needs_review


def test_hba1c_percent_passthrough() -> None:
    r = normalize(original_name="HbA1c", original_value="5.4", original_unit="%")
    assert r.metric_code == "4548-4"
    assert r.normalized_unit == "%"
    assert r.normalized_value == Decimal("5.4")
    assert not r.needs_review


def test_confusable_units_umoll_and_ngml_route_to_review() -> None:
    # Named confusable units with no approved conversion must NOT be silently accepted.
    for unit in ("µmol/L", "ng/mL"):
        r = normalize(original_name="LDL Cholesterol", original_value="3.0", original_unit=unit)
        assert r.normalized_value is None
        assert "unsupported_unit" in r.review_reasons


def test_one_sided_reference_interval_preserved() -> None:
    r = normalize(
        original_name="LDL Cholesterol",
        original_value="2.0",
        original_unit="mmol/L",
        reference_high="3.0",
    )
    assert r.reference_low is None
    assert r.reference_high == Decimal("3.0")
    assert not r.needs_review


def test_very_large_value_converts_without_false_review() -> None:
    # A large but parseable value is not flagged impossible solely for magnitude.
    r = normalize(original_name="LDL Cholesterol", original_value="9999", original_unit="mmol/L")
    assert r.normalized_value == Decimal("9999")
