"""Deterministic normalization: which names the import acts on by itself, conversions,
confusable units, review routing — and what happens to a value that is NOT normalized: it
keeps its number, when that number reads one way only.

A name is looked up in the KPI catalog (ADR-0004 §13). These tests resolve against the
catalog's seed data, which is what a seeded database resolves (test_kpi_catalog pins that the
two agree).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from hadp_api.modules.imports import normalize as normalize_mod
from hadp_api.modules.imports.normalize import (
    NORMALIZATION_VERSION,
    NormalizationResult,
    is_one_number,
    is_plain_number,
    unit_was_converted,
)
from hadp_api.modules.kpi.service import CatalogTerminology, seed_terminology
from hadp_api.modules.kpi.terms import CatalogTerm

TERMINOLOGY = seed_terminology()


def normalize(**row: Any) -> NormalizationResult:
    return normalize_mod.normalize(terminology=TERMINOLOGY, **row)


def test_same_unit_passthrough() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="2.8", original_unit="mmol/L")
    assert (r.kpi_code, r.metric_code, r.code_system) == ("cardio.ldl_c", "13457-7", "LOINC")
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
        "٣.٤",  # other scripts' digits
        "1.234,5",
        "12.345.678",
        "1,234,567",
        "3,4 mmol",
        "",
    ],
)
def test_only_a_plain_decimal_number_is_a_value(raw: str) -> None:
    r = normalize(original_name="LDL", original_value=raw, original_unit="mmol/L")
    assert (r.numeric_value, r.normalized_value) == (None, None)
    assert "unparseable_value" in r.review_reasons


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("3.4", "3.4"), ("3,4", "3.4"), (".5", "0.5"), ("+2", "2"), ("5.00E+01", "50.0")],
)
def test_plain_decimal_notations_are_read(raw: str, expected: str) -> None:
    r = normalize(original_name="LDL", original_value=raw, original_unit="mmol/L")
    assert r.normalized_value == Decimal(expected)
    assert r.review_reasons == []


# ---------------------------------------------------------------------------------------------
# A number that reads two ways is not read
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["4.000", "1,250", "150.000", "98.000", "-1.250", "+4.000", " 4.000 ", "04.000", "012.345"],
)
def test_a_number_that_groups_digits_in_threes_is_not_read(raw: str) -> None:
    """ "4.000" is four — or four thousand; "1,250" is one and a quarter — or twelve hundred
    and fifty. Nothing in the value says which, and its size must not decide."""
    assert is_plain_number(raw)  # written like a number: a statement may repeat it as written
    assert not is_one_number(raw)  # but the platform does not read a number from it
    # For a name the import acts on by itself: no number, and a human looks.
    automatic = normalize(original_name="LDL", original_value=raw, original_unit="mmol/L")
    assert (automatic.numeric_value, automatic.normalized_value) == (None, None)
    assert automatic.review_reasons == ["unparseable_value"]
    # For any other name: the source's wording stays, no number is held.
    other = normalize(original_name="Leukozyten", original_value=raw, original_unit="/µl")
    assert other.numeric_value is None
    assert other.review_reasons == ["unmapped_metric"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0.005", "0.005"),  # an integer part of zeros groups nothing
        ("0,125", "0.125"),
        ("00.500", "0.500"),
        ("1000.000", "1000.000"),  # four digits lead: not a group of thousands
        ("1.25", "1.25"),
        ("1.0000", "1.0000"),
        ("12.5", "12.5"),
        ("950", "950"),
        ("1.234e2", "123.4"),  # an exponent says the mark is a decimal mark
    ],
)
def test_a_number_that_reads_one_way_is_read(raw: str, expected: str) -> None:
    assert is_one_number(raw)
    r = normalize(original_name="Leukozyten", original_value=raw, original_unit="/µl")
    assert r.numeric_value == Decimal(expected)


# ---------------------------------------------------------------------------------------------
# A reference interval is held whole or not at all
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["LDL", "Leukozyten"])
@pytest.mark.parametrize(
    ("low", "high"),
    [
        # "3_0" used to parse as 30; "<3" used to vanish and leave a one-sided interval.
        ("0", "3_0"),
        ("0", "<3"),
        ("n/a", "3.0"),
        ("70*", "120"),
        # A bound that reads two ways: "4.000 – 10.000" per microlitre is 4 to 10, or
        # 4000 to 10000. A three-decimal format: of "0.270 – 4.200" only the first reads one way.
        ("4.000", "10.000"),
        ("150", "400.000"),
        ("1,250", "5"),
        ("0.270", "4.200"),
        # The lower bound above the upper: not an interval.
        ("1.2", "0.6"),
        ("400", "30"),
        ("0.5", "-0.5"),
    ],
)
def test_an_interval_that_cannot_be_read_whole_is_not_held(name: str, low: str, high: str) -> None:
    """Keeping the readable half would show a one-sided interval the source did not give."""
    r = normalize(
        original_name=name,
        original_value="2.8",
        original_unit="mmol/L",
        reference_low=low,
        reference_high=high,
    )
    assert (r.reference_low, r.reference_high) == (None, None)
    # One reason, the normalizer's own. The readers' `ambiguous_reference` means something
    # else (several ranges in the source) and changes how a repeated value is recognized.
    assert [reason for reason in r.review_reasons if "reference" in reason] == [
        "unparseable_reference"
    ]
    assert r.needs_review
    # The value itself is untouched by a problem with its interval.
    assert r.numeric_value == Decimal("2.8")


def test_an_interval_the_source_gives_is_held_as_given() -> None:
    both = normalize(
        original_name="LDL",
        original_value="2.8",
        original_unit="mmol/L",
        reference_low="0",
        reference_high="3.0",
    )
    assert (both.reference_low, both.reference_high, both.review_reasons) == (
        Decimal("0"),
        Decimal("3.0"),
        [],
    )
    # A bound the source simply does not give is not a problem: the other one is held.
    upper = normalize(
        original_name="LDL", original_value="2.8", original_unit="mmol/L", reference_high="3.0"
    )
    assert (upper.reference_low, upper.reference_high, upper.review_reasons) == (
        None,
        Decimal("3.0"),
        [],
    )
    lower = normalize(
        original_name="LDL",
        original_value="2.8",
        original_unit="mmol/L",
        reference_low="1.0",
        reference_high="  ",
    )
    assert (lower.reference_low, lower.reference_high, lower.review_reasons) == (
        Decimal("1.0"),
        None,
        [],
    )
    # Equal bounds are an interval (of one point).
    point = normalize(
        original_name="LDL",
        original_value="2.8",
        original_unit="mmol/L",
        reference_low="3.0",
        reference_high="3.0",
    )
    assert (point.reference_low, point.reference_high) == (Decimal("3.0"), Decimal("3.0"))
    assert point.review_reasons == []


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


def test_a_catalog_kpi_the_import_does_not_act_on_keeps_its_number_and_names_its_kpi() -> None:
    # Ferritin is a catalog KPI, written here in the catalog's own unit. It is still held for a
    # human: the import acts on six names, and this is not one of them.
    r = normalize(
        original_name="Ferritin",
        original_value="85",
        original_unit="ug/L",
        reference_low="30",
        reference_high="400",
    )
    assert r.kpi_code == "immune.ferritin"
    assert (r.metric_code, r.code_system) == (None, None)
    assert r.review_reasons == ["unmapped_metric"]
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    assert r.numeric_value == Decimal("85")
    assert (r.reference_low, r.reference_high) == (Decimal("30"), Decimal("400"))


def test_a_text_result_has_no_number() -> None:
    r = normalize(original_name="HIV-1/2 Screening", original_value="reaktiv", original_unit=None)
    assert r.numeric_value is None
    assert r.review_reasons == ["unmapped_metric"]


def test_a_negative_number_of_another_analyte_is_not_called_impossible() -> None:
    # "Non-negative" is what this module knows about ITS six quantities; it knows nothing here.
    r = normalize(original_name="Base Excess", original_value="-2.1", original_unit="mmol/L")
    assert r.numeric_value == Decimal("-2.1")
    assert r.review_reasons == ["unmapped_metric"]


def test_a_converted_value_keeps_the_source_number_beside_the_normalized_one() -> None:
    r = normalize(original_name="LDL Cholesterol", original_value="130", original_unit="mg/dL")
    assert r.numeric_value == Decimal("130")
    assert r.normalized_value == Decimal("130") * Decimal("0.0258598")
    assert r.normalization_version == NORMALIZATION_VERSION == "norm-2"


def test_a_value_in_an_unsupported_unit_keeps_its_number_and_its_interval() -> None:
    r = normalize(
        original_name="LDL Cholesterol",
        original_value="9.9",
        original_unit="µkat/L",
        reference_low="1",
        reference_high="12",
    )
    assert r.review_reasons == ["unsupported_unit"]
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    assert r.numeric_value == Decimal("9.9")
    assert (r.reference_low, r.reference_high) == (Decimal("1"), Decimal("12"))


# ---------------------------------------------------------------------------------------------
# What the import acts on without a human: six names, and the catalog has to agree
# ---------------------------------------------------------------------------------------------

# norm-1's terminology, as it stood: name -> (source code, unit). Which names publish unseen is
# a clinical decision; this list changes when someone has made one.
NORM_1 = {
    "ldl cholesterol": ("13457-7", "mmol/L"),
    "ldl": ("13457-7", "mmol/L"),
    "total cholesterol": ("2093-3", "mmol/L"),
    "hdl cholesterol": ("2085-9", "mmol/L"),
    "glucose": ("2345-7", "mmol/L"),
    "hba1c": ("4548-4", "%"),
}
ALIASES = sorted(TERMINOLOGY._terms)


def test_the_names_the_import_acts_on_are_exactly_those_of_norm_1() -> None:
    assert {
        name: (automatic.legacy_code, automatic.unit)
        for name, automatic in normalize_mod._AUTOMATIC.items()
    } == NORM_1


@pytest.mark.parametrize("name", sorted(NORM_1))
def test_each_of_the_six_names_normalizes_in_its_unit(name: str) -> None:
    code, unit = NORM_1[name]
    r = normalize(original_name=name.upper(), original_value="4.2", original_unit=unit)
    assert (r.metric_code, r.normalized_value, r.normalized_unit) == (code, Decimal("4.2"), unit)
    assert r.kpi_code == TERMINOLOGY.resolve(name).kpi_code  # type: ignore[union-attr]
    assert r.review_reasons == []


@pytest.mark.parametrize("name", ["  LDL  ", "\tLDL \n", "ldl", "Ldl", "LDL\u00a0"])
def test_a_six_name_is_matched_without_case_and_outer_white_space(name: str) -> None:
    """As norm-1 matched it. Whatever is inside the name must be exactly the name."""
    r = normalize(original_name=name, original_value="3.0", original_unit="mmol/L")
    assert (r.kpi_code, r.normalized_value, r.review_reasons) == (
        "cardio.ldl_c",
        Decimal("3.0"),
        [],
    )


@pytest.mark.parametrize("name", ["L DL", "LDL\u200b", "\uff2c\uff24\uff2c", "LDL.", "LDL-C"])
def test_a_name_that_only_looks_like_one_of_the_six_is_not_one(name: str) -> None:
    r = normalize(original_name=name, original_value="3.0", original_unit="mmol/L")
    assert r.normalized_value is None
    assert r.review_reasons == ["unmapped_metric"]


def test_the_catalog_as_seeded_confirms_all_six_names() -> None:
    assert normalize_mod.automatic_names() == set(NORM_1)
    assert normalize_mod.unconfirmed_names(TERMINOLOGY) == []
    # A catalog that was never seeded confirms none of them — and says which.
    assert normalize_mod.unconfirmed_names(_catalog()) == sorted(NORM_1)
    drifted = _catalog(**{**TERMINOLOGY._terms, "ldl": CatalogTerm("cardio.ldl_c", "g/L")})
    assert normalize_mod.unconfirmed_names(drifted) == ["ldl"]


@pytest.mark.parametrize("alias", [a for a in ALIASES if a not in NORM_1])
def test_no_other_catalog_name_is_acted_on_without_a_human(alias: str) -> None:
    """Every alias the catalog holds, in the catalog's own unit — the best case a source could
    offer. The catalog says what the name may mean; that is not a decision that a value under
    it may be published unread (specimen, method, plausibility, and who typed it are all
    unknown to the import)."""
    term = TERMINOLOGY.resolve(alias)
    assert term is not None

    r = normalize(original_name=alias, original_value="4.2", original_unit=term.canonical_unit)

    assert r.needs_review and r.review_reasons == ["unmapped_metric"]
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    assert (r.metric_code, r.code_system) == (None, None)
    # Where the value belongs is recorded; the number stays the source's.
    assert r.kpi_code == term.kpi_code
    assert r.numeric_value == Decimal("4.2")


def _catalog(**terms: CatalogTerm) -> CatalogTerminology:
    return CatalogTerminology(dict(terms))


@pytest.mark.parametrize(
    "catalog",
    [
        _catalog(),  # the catalog does not know the name (an unseeded or retired entry)
        _catalog(ldl=CatalogTerm("cardio.ldl_particle_number", "mmol/L")),  # another KPI
        _catalog(ldl=CatalogTerm("cardio.ldl_c", "g/L")),  # another unit
        _catalog(ldl=CatalogTerm("cardio.ldl_c", None)),
    ],
    ids=["unknown", "other-kpi", "other-unit", "no-unit"],
)
def test_where_the_catalog_disagrees_nothing_is_acted_on(catalog: CatalogTerminology) -> None:
    """The six names are bound to a KPI and a unit here AND in the catalog. A catalog edit can
    take a name out of automatic handling; it cannot put one in, or change what a name
    converts to."""
    for unit in ("mmol/L", "mg/dL", "g/L"):
        r = normalize_mod.normalize(
            terminology=catalog, original_name="LDL", original_value="3.0", original_unit=unit
        )
        assert r.review_reasons == ["unmapped_metric"]
        assert (r.normalized_value, r.normalized_unit, r.metric_code) == (None, None, None)
        assert r.numeric_value == Decimal("3.0")


def test_generic_crp_never_becomes_hs_crp() -> None:
    """ADR-0004 §9: the two are different KPIs; neither name resolves to the other, and the
    bare abbreviation resolves to neither."""
    generic = normalize(
        original_name="C-reactive protein", original_value="4", original_unit="mg/L"
    )
    sensitive = normalize(original_name="hs-CRP", original_value="1.8", original_unit="mg/L")
    assert (generic.kpi_code, sensitive.kpi_code) == ("immune.crp", "immune.hs_crp")
    bare = normalize(original_name="CRP", original_value="4", original_unit="mg/L")
    assert (bare.kpi_code, bare.review_reasons) == (None, ["unmapped_metric"])


def test_a_name_resolves_exactly_or_not_at_all() -> None:
    assert TERMINOLOGY.resolve("  LDL  ") == TERMINOLOGY.resolve("ldl")
    for near in ("LDL-C direct", "LDL Cholesterol (calc.)", "Cholesterol"):
        r = normalize(original_name=near, original_value="3.0", original_unit="mmol/L")
        assert r.normalized_value is None, near


# ---------------------------------------------------------------------------------------------
# Conversions and units
# ---------------------------------------------------------------------------------------------


def test_the_approved_conversions_are_these_four_and_no_other() -> None:
    """The factors as approved: a changed digit is a changed value on every converted row."""
    assert {
        ("cardio.ldl_c", "mg/dL", "mmol/L"): Decimal("0.0258598"),
        ("cardio.total_cholesterol", "mg/dL", "mmol/L"): Decimal("0.0258598"),
        ("cardio.hdl_c", "mg/dL", "mmol/L"): Decimal("0.0258598"),
        ("metabolic.fasting_plasma_glucose", "mg/dL", "mmol/L"): Decimal("0.0555"),
    } == normalize_mod._CONVERSIONS
    for name, factor in (
        ("Total cholesterol", "0.0258598"),
        ("HDL cholesterol", "0.0258598"),
        ("LDL", "0.0258598"),
        ("Glucose", "0.0555"),
    ):
        r = normalize(original_name=name, original_value="100", original_unit="mg/dL")
        assert r.normalized_value == Decimal("100") * Decimal(factor), name


def test_every_approved_conversion_belongs_to_one_of_the_six_and_names_its_target() -> None:
    held_in = {a.kpi_code: a.unit for a in normalize_mod._AUTOMATIC.values()}
    assert normalize_mod._CONVERSIONS
    for (kpi_code, source_unit, target_unit), factor in normalize_mod._CONVERSIONS.items():
        assert held_in[kpi_code] == target_unit
        assert source_unit != target_unit
        assert factor > 0


def test_a_conversion_is_to_the_unit_it_names_and_to_no_other() -> None:
    """If the catalog's unit for HDL changed, 55 mg/dL would not become "1.42 g/L"."""
    drifted = _catalog(**{"hdl cholesterol": CatalogTerm("cardio.hdl_c", "g/L")})
    r = normalize_mod.normalize(
        terminology=drifted,
        original_name="HDL cholesterol",
        original_value="55",
        original_unit="mg/dL",
        reference_low="40",
        reference_high="60",
    )
    assert (r.normalized_value, r.normalized_unit) == (None, None)
    assert (r.numeric_value, r.reference_low, r.reference_high) == (
        Decimal("55"),
        Decimal("40"),
        Decimal("60"),
    )
    assert r.needs_review


@pytest.mark.parametrize("unit", ["mmol/L", "mmol/l", "MMOL/L", "Mmol/L", " mmol/L "])
def test_three_spellings_are_accepted_in_any_letter_case(unit: str) -> None:
    r = normalize(original_name="LDL", original_value="3.0", original_unit=unit)
    assert (r.normalized_value, r.normalized_unit, r.review_reasons) == (
        Decimal("3.0"),
        "mmol/L",
        [],
    )
    assert not unit_was_converted(unit, "mmol/L")


@pytest.mark.parametrize("unit", ["umol/L", "µmol/L", "nmol/L", "mmol/dL", "mmol", "g/L", "mM"])
def test_any_other_unit_is_compared_as_written(unit: str) -> None:
    r = normalize(original_name="LDL", original_value="3.0", original_unit=unit)
    assert r.normalized_value is None
    assert r.review_reasons == ["unsupported_unit"]


def test_a_missing_unit_is_never_read_as_the_canonical_one() -> None:
    for unit in (None, "", "   "):
        r = normalize(original_name="LDL", original_value="3.0", original_unit=unit)
        assert r.normalized_value is None
        assert r.review_reasons == ["unsupported_unit"]
