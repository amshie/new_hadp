"""Deterministic normalization: terminology resolution, conversions, confusable units, review
routing — and what happens to a value that is NOT normalized: it keeps its number.

The terminology is the KPI catalog (ADR-0004 §13). These tests resolve against the catalog's
seed data, which is what a seeded database resolves (test_kpi_catalog pins that the two agree).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.imports.normalize import (
    NORMALIZATION_VERSION,
    NormalizationResult,
    unit_notation,
)
from hadp_api.modules.kpi.catalog_data import kpi_rows
from hadp_api.modules.kpi.service import seed_terminology

TERMINOLOGY = seed_terminology()


def normalize(**row: Any) -> NormalizationResult:
    return normalize_mod.normalize(terminology=TERMINOLOGY, **row)


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
    assert (r.kpi_code, r.metric_code) == (None, None)
    assert r.normalized_value is None
    assert r.review_reasons == ["unmapped_metric"]
    assert r.mapping_confidence == 0.0


def test_unsupported_unit_goes_to_review() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="1.0", original_unit="g/L")
    assert "unsupported_unit" in r.review_reasons
    assert r.normalized_value is None
    assert r.kpi_code == "cardio.ldl_c"  # the name is known; only the unit is not


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


@pytest.mark.parametrize(
    "raw",
    [
        "NaN",  # crashed the comparison with zero
        "Infinity",
        "-inf",
        "3_4",  # Decimal() reads this as 34
        "1e999",
        "\u0663.\u0664",  # other scripts' digits
        "1.234,5",
        "3,4 mmol",
        "",
    ],
)
def test_only_a_plain_decimal_number_is_a_value(raw: str) -> None:
    r = normalize(original_name="LDL", original_value=raw, original_unit="mmol/L")
    assert r.normalized_value is None
    assert "unparseable_value" in r.review_reasons


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("3.4", "3.4"), ("3,4", "3.4"), (".5", "0.5"), ("+2", "2"), ("5.00E+01", "50.0")],
)
def test_plain_decimal_notations_are_read(raw: str, expected: str) -> None:
    r = normalize(original_name="LDL", original_value=raw, original_unit="mmol/L")
    assert r.normalized_value == Decimal(expected)
    assert r.review_reasons == []


def test_a_reference_bound_that_is_not_a_number_is_never_dropped_silently() -> None:
    # "3_0" used to parse as 30; "<3" used to vanish and leave a one-sided interval.
    for low, high in (("0", "3_0"), ("0", "<3"), ("n/a", "3.0")):
        r = normalize(
            original_name="LDL",
            original_value="2.8",
            original_unit="mmol/L",
            reference_low=low,
            reference_high=high,
        )
        assert r.review_reasons == ["unparseable_reference"]
    # A bound the source simply does not give is not a problem.
    r = normalize(
        original_name="LDL", original_value="2.8", original_unit="mmol/L", reference_high="3.0"
    )
    assert (r.reference_low, r.reference_high, r.review_reasons) == (None, Decimal("3.0"), [])


# ---------------------------------------------------------------------------------------------
# A value that is not normalized keeps its number (norm-2)
# ---------------------------------------------------------------------------------------------


def test_an_unknown_analyte_keeps_its_number_and_its_bounds_in_the_source_unit() -> None:
    r = normalize(
        original_name="Zink",
        original_value="85",
        original_unit="µg/dL",
        reference_low="70",
        reference_high="120",
    )
    assert r.review_reasons == ["unmapped_metric"]
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    # What the source wrote, as numbers — nothing converted, nothing inferred.
    assert r.numeric_value == Decimal("85")
    assert (r.reference_low, r.reference_high) == (Decimal("70"), Decimal("120"))


def test_a_known_analyte_in_a_unit_without_an_approved_conversion_keeps_its_number() -> None:
    # Ferritin's canonical unit is ug/L. ng/mL is the same quantity — and still not converted:
    # only an approved KPI/unit pair is, and this pair is not in the registry.
    r = normalize(
        original_name="Ferritin",
        original_value="85",
        original_unit="ng/mL",
        reference_low="30",
        reference_high="400",
    )
    assert r.kpi_code == "immune.ferritin"
    assert r.review_reasons == ["unsupported_unit"]
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    assert r.numeric_value == Decimal("85")
    assert (r.reference_low, r.reference_high) == (Decimal("30"), Decimal("400"))


def test_an_unreadable_bound_of_an_unknown_analyte_is_a_reason_too() -> None:
    r = normalize(
        original_name="Zink",
        original_value="85",
        original_unit="µg/dL",
        reference_low="70*",
        reference_high="120",
    )
    assert r.review_reasons == ["unmapped_metric", "unparseable_reference"]
    assert (r.reference_low, r.reference_high) == (None, Decimal("120"))


def test_a_text_result_has_no_number() -> None:
    r = normalize(original_name="HIV-1/2 Screening", original_value="reaktiv", original_unit=None)
    assert r.numeric_value is None
    assert r.review_reasons == ["unmapped_metric"]


def test_a_negative_number_of_an_unknown_analyte_is_not_called_impossible() -> None:
    # "Non-negative" is what the catalog knows about ITS quantities; it knows nothing here.
    r = normalize(original_name="Base Excess", original_value="-2.1", original_unit="mmol/L")
    assert r.numeric_value == Decimal("-2.1")
    assert r.review_reasons == ["unmapped_metric"]


def test_a_converted_value_keeps_the_source_number_beside_the_normalized_one() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="130", original_unit="mg/dL")
    assert r.numeric_value == Decimal("130")
    assert r.normalized_value == Decimal("130") * Decimal("0.0258598")
    assert r.normalization_version == NORMALIZATION_VERSION == "norm-2"


# ---------------------------------------------------------------------------------------------
# The terminology is the catalog (ADR-0004 §13)
# ---------------------------------------------------------------------------------------------

_AUTOMATIC_CLASSES = {"laboratory", "vital_sign", "anthropometric"}


@pytest.mark.parametrize(
    "row",
    [r for r in kpi_rows() if r["measurement_class"] in _AUTOMATIC_CLASSES],
    ids=lambda r: str(r["code"]),
)
def test_every_laboratory_vital_and_anthropometric_kpi_normalizes_under_its_own_name(
    row: dict[str, object],
) -> None:
    """ADR-0004 §14: every canonical code imports without `unmapped_metric`."""
    r = normalize(
        original_name=str(row["display_name"]),
        original_value="1.5",
        original_unit=str(row["canonical_unit_ucum"]),
        reference_low="1",
        reference_high="2",
    )
    assert r.review_reasons == []
    assert r.kpi_code == row["code"]
    assert (r.normalized_value, r.normalized_unit) == (Decimal("1.5"), row["canonical_unit_ucum"])
    assert (r.reference_low, r.reference_high) == (Decimal("1"), Decimal("2"))
    assert r.mapping_confidence == 1.0


@pytest.mark.parametrize(
    "row",
    [
        r
        for r in kpi_rows()
        if r["measurement_class"] not in _AUTOMATIC_CLASSES and r["canonical_unit_ucum"]
    ],
    ids=lambda r: str(r["code"]),
)
def test_a_kpi_that_compares_only_with_recorded_context_is_never_normalized_from_a_bare_row(
    row: dict[str, object],
) -> None:
    """Body composition, functional tests, wearables, imaging, omics and derived values need the
    device, the instrument version, the protocol or the formula to mean one measurement. A
    name and a number carry none of that: the row waits for a human, with its number kept."""
    r = normalize(
        original_name=str(row["display_name"]),
        original_value="1.5",
        original_unit=str(row["canonical_unit_ucum"]),
    )
    assert r.review_reasons == ["unmapped_metric"]
    assert r.kpi_code == row["code"]  # the catalog link is still recorded
    assert r.normalized_value is None
    assert r.numeric_value == Decimal("1.5")


def test_only_the_six_names_of_norm_1_carry_a_source_code() -> None:
    """A code from an external terminology is stamped only where norm-1 stamped it; the
    catalog-resolved rest carries the KPI code and no LOINC code on a guess."""
    stamped = {
        "LDL": "13457-7",
        "LDL Cholesterol": "13457-7",
        "Total cholesterol": "2093-3",
        "HDL cholesterol": "2085-9",
        "Glucose": "2345-7",
        "HbA1c": "4548-4",
    }
    for name, code in stamped.items():
        unit = "%" if name == "HbA1c" else "mmol/L"
        r = normalize(original_name=name, original_value="1", original_unit=unit)
        assert (r.metric_code, r.code_system) == (code, "LOINC"), name
    for name, unit in (("Creatinine", "umol/L"), ("Triglycerides", "mmol/L"), ("Ferritin", "ug/L")):
        r = normalize(original_name=name, original_value="1", original_unit=unit)
        assert r.review_reasons == []
        assert (r.metric_code, r.code_system) == (None, None), name


def test_an_alias_resolves_like_the_canonical_name() -> None:
    r = normalize(original_name="Nüchternglukose", original_value="95", original_unit="mg/dL")
    assert r.kpi_code == "metabolic.fasting_plasma_glucose"
    assert r.normalized_value == Decimal("95") * Decimal("0.0555")
    assert r.review_reasons == []


def test_a_name_resolves_exactly_or_not_at_all() -> None:
    for name in ("Creatinine (urine)", "Creatinin", "Serum creatinine", "Creatinine ratio"):
        r = normalize(original_name=name, original_value="80", original_unit="umol/L")
        assert (r.kpi_code, r.review_reasons) == (None, ["unmapped_metric"]), name
    r = normalize(original_name="  CREATININE ", original_value="80", original_unit="umol/L")
    assert (r.kpi_code, r.review_reasons) == ("regen.creatinine", [])


def test_generic_crp_never_becomes_hs_crp() -> None:
    """ADR-0004 §9: the two are different KPIs; neither name resolves to the other."""
    generic = normalize(
        original_name="C-reactive protein", original_value="4", original_unit="mg/L"
    )
    sensitive = normalize(original_name="hs-CRP", original_value="1.8", original_unit="mg/L")
    assert (generic.kpi_code, sensitive.kpi_code) == ("immune.crp", "immune.hs_crp")
    bare = normalize(original_name="CRP", original_value="4", original_unit="mg/L")
    assert (bare.kpi_code, bare.review_reasons) == (None, ["unmapped_metric"])


def test_lipoprotein_a_is_never_converted_between_mass_and_molar_units() -> None:
    """ADR-0004 §9: Lp(a) mg/dL and nmol/L are not interconvertible by a fixed factor."""
    molar = normalize(original_name="Lipoprotein(a)", original_value="75", original_unit="nmol/L")
    mass = normalize(original_name="Lipoprotein(a)", original_value="30", original_unit="mg/dL")
    assert (molar.normalized_value, molar.review_reasons) == (Decimal("75"), [])
    assert (mass.normalized_value, mass.review_reasons) == (None, ["unsupported_unit"])
    assert mass.numeric_value == Decimal("30")


def test_every_approved_conversion_names_a_catalog_kpi_and_a_unit_other_than_its_own() -> None:
    units = {str(r["code"]): r["canonical_unit_ucum"] for r in kpi_rows()}
    for (kpi_code, source_unit), factor in normalize_mod._CONVERSIONS.items():
        assert kpi_code in units, kpi_code
        assert source_unit != units[kpi_code], (kpi_code, source_unit)
        assert source_unit == unit_notation(source_unit), "registry keys are in catalog notation"
        assert factor > 0


# ---------------------------------------------------------------------------------------------
# Unit notation is not conversion
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("written", "notation"),
    [
        ("mmol/l", "mmol/L"),
        ("µmol/l", "umol/L"),  # micro sign U+00B5
        ("μmol/L", "umol/L"),  # Greek mu U+03BC
        ("µg/l", "ug/L"),
        ("ng/ml", "ng/mL"),
        ("pg/ml", "pg/mL"),
        ("mg/dl", "mg/dL"),
        ("MG/DL", "mg/dL"),  # norm-1 accepted these three in any letter case
        ("10*9/l", "10*9/L"),
        ("/nl", "/nL"),
        ("fl", "fL"),
        ("ml/min", "mL/min"),
        (" mmol/L ", "mmol/L"),
        ("%", "%"),
        ("mm/h", "mm/h"),
        # Left exactly as written: nothing here is a litre, and case carries meaning.
        ("mol", "mol"),
        ("G/l", "G/L"),
        ("g/l", "g/L"),
        ("U/l", "U/L"),
        ("mU/l", "mU/L"),
        ("MU/l", "MU/L"),
        ("Tsd/µl", "Tsd/uL"),
        ("", ""),
    ],
)
def test_a_unit_is_brought_into_catalog_notation_without_changing_it(
    written: str, notation: str
) -> None:
    assert unit_notation(written) == notation


def test_notation_never_folds_two_different_units_into_one() -> None:
    """Giga per litre and gram per litre differ only in the case of one letter."""
    assert unit_notation("G/l") != unit_notation("g/l")
    assert unit_notation("mU/L") != unit_notation("MU/L")
    assert unit_notation("mg/L") != unit_notation("Mg/L")
    # And so a cell count written in giga per litre is not read as grams per litre.
    r = normalize(original_name="Albumin", original_value="45", original_unit="G/l")
    assert r.review_reasons == ["unsupported_unit"]


@pytest.mark.parametrize("unit", ["umol/L", "µmol/L", "µmol/l", "μmol/l", "umol/l"])
def test_a_canonical_unit_is_recognized_in_its_usual_spellings(unit: str) -> None:
    r = normalize(original_name="Creatinine", original_value="80", original_unit=unit)
    assert (r.normalized_value, r.normalized_unit, r.review_reasons) == (
        Decimal("80"),
        "umol/L",
        [],
    )


@pytest.mark.parametrize("unit", ["U/L", "IU/L", "U/l", "µkat/L"])
def test_an_enzyme_unit_other_than_the_canonical_one_is_not_assumed_equal(unit: str) -> None:
    # U/L and [IU]/L are numerically equal for enzymes by convention — a convention is an
    # approval, and no such pair is in the registry yet.
    r = normalize(original_name="Alanine aminotransferase", original_value="30", original_unit=unit)
    assert (r.normalized_value, r.review_reasons) == (None, ["unsupported_unit"])
    assert r.numeric_value == Decimal("30")


def test_a_missing_unit_is_never_read_as_the_canonical_one() -> None:
    for unit in (None, "", "  "):
        r = normalize(original_name="Creatinine", original_value="80", original_unit=unit)
        assert (r.normalized_value, r.review_reasons) == (None, ["unsupported_unit"])
