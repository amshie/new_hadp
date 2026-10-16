"""Unit tests of the intake checks, one rule at a time. Exact outputs; "close" is a bug."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from hadp_api.modules.enums import PendingValueStatus
from hadp_api.modules.intake import checks
from hadp_api.modules.kpi.service import seed_terminology
from tests.intake_support import FakeBounds, FakePages, FakeRecord, _Published

TERMS = seed_terminology()
TODAY = date(2026, 10, 16)
DOB = date(1970, 3, 12)
PAGE = "Befund synthetisch\nHbA1c 5,4 % 4,0 - 6,0\nLDL 128 mg/dl 50 - 130\nGlucose 15,2 mmol/L\n"
BOUNDS = FakeBounds(
    {
        "metabolic.hba1c": checks.PlausibilityBound(
            "%", Decimal("2"), Decimal("20"), Decimal("1.0")
        ),
        "cardio.ldl_c": checks.PlausibilityBound(
            "mmol/L", Decimal("0.1"), Decimal("15"), Decimal("1.5")
        ),
    }
)


def value(**over):  # type: ignore[no-untyped-def]
    base: dict = dict(  # noqa: C408 - a literal would need every key spelled twice
        analyte_text="HbA1c",
        value_text="5,4",
        unit_text="%",
        observed_at=datetime(2026, 9, 5, tzinfo=UTC),
        observed_at_is_date_only=True,
        page=1,
        confidence=Decimal("0.95"),
        reference_low="4,0",
        reference_high="6,0",
    )
    base.update(over)
    return checks.ProposedValue(**base)


def run(*values, record=None, issue=date(2026, 9, 6), dob=DOB, pages=(PAGE,), bounds=BOUNDS):  # type: ignore[no-untyped-def]
    batch = checks.ProposedBatch(values=tuple(values), patient_date_of_birth=dob, issue_date=issue)
    return checks.run_checks(
        batch,
        terminology=TERMS,
        bounds=bounds,
        record=record or FakeRecord(DOB, ()),
        pages=FakePages(tuple(pages)),
        today=TODAY,
    )


def reasons(checked, index=0):  # type: ignore[no-untyped-def]
    return [c.reason for c in checked.values[index].checks if c.reason]


# --- vocabulary --------------------------------------------------------------------------------


def test_every_reason_has_a_severity_and_every_check_is_named() -> None:
    assert set(checks.REASONS.values()) == {"red", "yellow"}
    assert len(checks.CHECKS) == 12 and len(set(checks.CHECKS)) == 12
    assert "conflicting_in_batch" in checks.REASONS


def test_a_check_result_cannot_carry_an_unknown_reason() -> None:
    with pytest.raises(AssertionError):
        checks._fail(checks.UNIT, "not_a_reason")


def test_status_precedence_red_over_yellow_over_green() -> None:
    ok = checks._ok(checks.UNIT)
    y = checks._fail(checks.MAPPING, "unmapped_analyte")
    r = checks._fail(checks.UNIT, "unit_unknown")
    assert checks.status_of((ok,)) is PendingValueStatus.GREEN
    assert checks.status_of((ok, y)) is PendingValueStatus.YELLOW
    assert checks.status_of((y, r, ok)) is PendingValueStatus.RED


# --- on the page -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("needle", "found"),
    [("5,4", True), ("15,2", True), ("5,2", False), ("128", True), ("12", False), ("28", False)],
)
def test_a_value_must_stand_on_the_page_as_a_number_of_its_own(needle: str, found: bool) -> None:
    assert checks.value_on_page(needle, PAGE) is found


def test_the_name_is_matched_letter_case_aside_and_the_unit_too() -> None:
    assert checks.text_on_page("hba1c", PAGE)
    assert checks.text_on_page("MG/DL", PAGE)
    assert not checks.text_on_page("Ferritin", PAGE)


def test_a_page_without_text_confirms_nothing() -> None:
    checked = run(value(), pages=("",))
    assert reasons(checked) == ["no_page_text"]
    assert checked.values[0].status is PendingValueStatus.RED


def test_a_page_the_document_does_not_have_is_red_and_the_page_text_check_is_skipped() -> None:
    checked = run(value(page=2))
    assert reasons(checked) == ["page_out_of_range"]
    on_page = next(c for c in checked.values[0].checks if c.check == checks.ON_PAGE)
    assert on_page.result == checks.SKIPPED


# --- mapping, value, unit --------------------------------------------------------------------


def test_an_unmapped_name_is_yellow_and_keeps_the_written_bounds() -> None:
    page = "Kreatinin 78 µmol/L 45 - 84 synthetisch"
    checked = run(
        value(
            analyte_text="Kreatinin",
            value_text="78",
            unit_text="µmol/L",
            reference_low="45",
            reference_high="84",
        ),
        pages=(page,),
    )
    v = checked.values[0]
    assert v.status is PendingValueStatus.YELLOW
    assert reasons(checked) == ["unmapped_analyte"]
    assert v.kpi_code is None and v.normalized_value is None
    assert (v.normalized_reference_low, v.normalized_reference_high) == (
        Decimal("45"),
        Decimal("84"),
    )


@pytest.mark.parametrize("text", ["<0,5", "negativ", "4.000", "5,4 H", "1,234,5"])
def test_a_value_that_is_not_one_plain_number_is_red(text: str) -> None:
    checked = run(value(value_text=text), pages=(f"HbA1c {text} % synthetisch",))
    assert "value_not_a_number" in reasons(checked)
    assert checked.values[0].normalized_value is None


def test_an_approved_conversion_is_exact_and_converts_the_bounds_by_the_same_factor() -> None:
    checked = run(
        value(
            analyte_text="LDL",
            value_text="128",
            unit_text="mg/dl",
            reference_low="50",
            reference_high="130",
        )
    )
    v = checked.values[0]
    assert v.status is PendingValueStatus.GREEN
    assert (v.canonical_unit, v.normalized_value) == (
        "mmol/L",
        Decimal("128") * Decimal("0.0258598"),
    )
    assert v.normalized_value == Decimal("3.3100544")
    assert v.normalized_reference_low == Decimal("50") * Decimal("0.0258598")
    assert v.normalized_reference_high == Decimal("130") * Decimal("0.0258598")


def test_a_different_spelling_of_the_canonical_unit_is_not_a_conversion() -> None:
    checked = run(
        value(analyte_text="LDL", value_text="3,1", unit_text="mmol/l"),
        pages=("LDL 3,1 mmol/l synthetisch",),
    )
    unit = next(c for c in checked.values[0].checks if c.check == checks.UNIT)
    assert unit.result == checks.PASS and "factor" not in unit.detail
    assert checked.values[0].normalized_value == Decimal("3.1")


@pytest.mark.parametrize("unit", ["mg%", "mmol/mol", "µmol/L", None])
def test_an_unknown_or_missing_unit_is_red_and_nothing_is_normalized(unit: str | None) -> None:
    text = f"HbA1c 5,4 {unit or ''} synthetisch"
    checked = run(value(unit_text=unit), pages=(text,))
    expected = "unit_missing" if unit is None else "unit_unknown"
    assert expected in reasons(checked)
    assert checked.values[0].normalized_value is None


# --- reference -------------------------------------------------------------------------------


def test_the_reference_is_held_whole_or_not_at_all() -> None:
    checked = run(value(reference_low="s.o.", reference_high="6,0"))
    v = checked.values[0]
    assert "reference_unreadable" in reasons(checked)
    assert (v.normalized_reference_low, v.normalized_reference_high) == (None, None)
    inverted = run(value(reference_low="6,0", reference_high="4,0"))
    assert "reference_unreadable" in reasons(inverted)


def test_a_one_sided_reference_stays_one_sided() -> None:
    checked = run(value(reference_low=None, reference_high="6,0"))
    v = checked.values[0]
    assert (v.normalized_reference_low, v.normalized_reference_high) == (None, Decimal("6.0"))
    assert reasons(checked) == []


# --- plausibility, delta ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "status"), [("20", "green"), ("20,1", "red"), ("2", "green"), ("1,9", "red")]
)
def test_hard_bounds_are_inclusive(text: str, status: str) -> None:
    checked = run(value(value_text=text), pages=(f"HbA1c {text} % synthetisch",))
    assert checked.values[0].status.value == status


def test_a_kpi_without_signed_bounds_is_yellow_not_green() -> None:
    checked = run(value(), bounds=FakeBounds({}))
    assert reasons(checked) == ["plausibility_not_configured"]
    assert checked.values[0].status is PendingValueStatus.YELLOW


def test_bounds_in_another_unit_than_the_value_do_not_apply() -> None:
    bounds = FakeBounds(
        {
            "metabolic.hba1c": checks.PlausibilityBound(
                "mmol/mol", Decimal("0"), Decimal("200"), None
            )
        }
    )
    checked = run(value(), bounds=bounds)
    assert reasons(checked) == ["plausibility_not_configured"]


def _record_with(kpi: str, held: str, unit: str, day: date = date(2026, 3, 1)) -> FakeRecord:
    return FakeRecord(
        DOB,
        (
            _Published(
                kpi_code=kpi,
                analyte_key="x",
                day=day,
                value_text="x",
                unit_text=unit,
                held_value=Decimal(held),
                held_unit=unit,
            ),
        ),
    )


@pytest.mark.parametrize(("prior", "status"), [("2.7", "green"), ("2,69", "yellow")])
def test_the_delta_threshold_is_relative_to_the_last_value_and_exact(
    prior: str, status: str
) -> None:
    # 5,4 against 2.7 is +100 % = the threshold (1.0) exactly: not beyond it. Against 2.69 it is.
    checked = run(value(), record=_record_with("metabolic.hba1c", prior.replace(",", "."), "%"))
    assert checked.values[0].status.value == status


def test_the_delta_is_skipped_for_another_unit_or_without_a_signed_threshold() -> None:
    other_unit = run(value(), record=_record_with("metabolic.hba1c", "38", "mmol/mol"))
    assert (
        next(c for c in other_unit.values[0].checks if c.check == checks.DELTA).result
        == checks.SKIPPED
    )
    no_threshold = FakeBounds(
        {"metabolic.hba1c": checks.PlausibilityBound("%", Decimal("2"), Decimal("20"), None)}
    )
    checked = run(value(), record=_record_with("metabolic.hba1c", "1", "%"), bounds=no_threshold)
    assert (
        next(c for c in checked.values[0].checks if c.check == checks.DELTA).result
        == checks.SKIPPED
    )
    assert checked.values[0].status is PendingValueStatus.GREEN


# --- date ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "reason"),
    [
        (date(2026, 9, 6), None),
        (date(2026, 6, 8), None),  # issue - 90 days: inside
        (date(2026, 6, 7), "date_outside_window"),
        (date(2026, 9, 7), "date_after_issue"),
        (date(2026, 10, 17), "date_in_future"),
        (date(1970, 3, 11), "date_before_birth"),
    ],
)
def test_the_date_window_boundaries(day: date, reason: str | None) -> None:
    checked = run(value(observed_at=datetime(day.year, day.month, day.day, tzinfo=UTC)))
    assert ([reason] if reason else []) == reasons(checked)


def test_a_value_without_a_date_is_red_and_no_date_is_invented() -> None:
    checked = run(value(observed_at=None))
    assert reasons(checked) == ["date_missing"]


def test_the_future_is_measured_against_today_not_the_issue_date() -> None:
    checked = run(value(observed_at=datetime(2026, 10, 1, tzinfo=UTC)), issue=None)
    assert reasons(checked) == []


# --- duplicate -------------------------------------------------------------------------------


def test_a_published_twin_is_red_and_a_different_day_or_text_is_not() -> None:
    twin = FakeRecord(
        DOB,
        (
            _Published(
                kpi_code="metabolic.hba1c",
                analyte_key="hba1c",
                day=date(2026, 9, 5),
                value_text="5,4",
                unit_text="%",
                held_value=Decimal("5.4"),
                held_unit="%",
            ),
        ),
    )
    assert "duplicate_of_published" in reasons(run(value(), record=twin))
    assert "duplicate_of_published" not in reasons(
        run(value(observed_at=datetime(2026, 9, 6, tzinfo=UTC)), record=twin)
    )
    other_text = run(value(value_text="5.4"), record=twin, pages=("HbA1c 5.4 % synthetisch",))
    assert "duplicate_of_published" not in reasons(other_text)


def test_the_same_value_twice_in_one_batch_marks_the_second() -> None:
    checked = run(value(), value())
    assert reasons(checked, 0) == [] and reasons(checked, 1) == ["duplicate_in_batch"]


def test_two_different_readings_of_one_measurement_mark_both() -> None:
    page = PAGE + "HbA1c 12,0 %\n"
    checked = run(value(), value(value_text="12,0"), pages=(page,))
    assert reasons(checked, 0) == ["conflicting_in_batch"]
    assert reasons(checked, 1) == ["conflicting_in_batch"]
    assert all(v.status is PendingValueStatus.YELLOW for v in checked.values)
    # Another day is another measurement: no conflict.
    other_day = run(
        value(),
        value(value_text="12,0", observed_at=datetime(2026, 9, 4, tzinfo=UTC)),
        pages=(page,),
    )
    assert reasons(other_day, 0) == [] and reasons(other_day, 1) == []


# --- confidence and patient ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("confidence", "status"), [("0.9", "green"), ("0.899", "yellow"), ("0", "yellow")]
)
def test_the_green_threshold_is_0_9_inclusive(confidence: str, status: str) -> None:
    assert run(value(confidence=Decimal(confidence))).values[0].status.value == status


def test_another_patients_document_makes_every_value_red() -> None:
    checked = run(
        value(),
        value(analyte_text="LDL", value_text="128", unit_text="mg/dl"),
        dob=date(1968, 7, 30),
    )
    assert checked.checks[0].reason == "patient_mismatch"
    assert all(v.status is PendingValueStatus.RED for v in checked.values)


def test_no_dob_on_the_document_is_yellow_and_a_record_without_one_cannot_disagree() -> None:
    assert reasons(run(value(), dob=None)) == ["patient_dob_not_proposed"]
    no_record_dob = checks.run_checks(
        checks.ProposedBatch(
            values=(value(),), patient_date_of_birth=DOB, issue_date=date(2026, 9, 6)
        ),
        terminology=TERMS,
        bounds=BOUNDS,
        record=FakeRecord(None, ()),
        pages=FakePages((PAGE,)),
        today=TODAY,
    )
    assert reasons(no_record_dob) == []


# --- the proposal never sets the outcome -------------------------------------------------------


def test_the_output_carries_the_ruleset_version_and_every_check_once() -> None:
    checked = run(value())
    assert [c.check for c in checked.values[0].checks] == list(checks.CHECKS)
    assert checks.CHECKS_VERSION == "intake-checks-1"
