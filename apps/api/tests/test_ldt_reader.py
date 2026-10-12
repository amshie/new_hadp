"""The LDT 2 reader reads exactly what the KBV record description fixes, and refuses the rest.

Synthetic files only (tests/ldt_fixtures.py). The properties under test are the ones a wrong
reading would turn into a wrong clinical value: line framing, the version-dependent date order,
the character set, which test a field belongs to, and one-file-one-patient.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.documents.xdt import is_wellformed_xdt
from hadp_api.modules.imports.parsers import SourceParseError, parse_source_document
from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    CORRECTED_RESULT,
    NO_SAMPLING_DATE,
    PRELIMINARY_REPORT,
    PREVIOUSLY_REPORTED,
    RESULT_PENDING,
    SOURCE_COMMENT,
    TEXT_RESULT,
)
from hadp_api.modules.imports.parsers.detect import parse_ldt
from tests.ldt_fixtures import TRAILER, header, lab_test, ldt_file, ldt_line, report

BERLIN = ZoneInfo("Europe/Berlin")

LDL = lab_test("LDL", "LDL Cholesterol", value="2.8", unit="mmol/L", low="0", high="3.0")


def _error(data: bytes) -> SourceParseError:
    with pytest.raises(SourceParseError) as caught:
        parse_ldt(data, zone=BERLIN)
    return caught.value


def test_the_specification_example_line_pins_the_length_rule() -> None:
    # KBV record description: the line for record type 8220 is "01380008220" — 4 characters of
    # content plus 9.
    assert ldt_line("8000", "8220") == b"01380008220\r\n"
    assert is_wellformed_xdt(b"01380008220\r\n") is True
    assert is_wellformed_xdt(b"01480008220\r\n") is False  # wrong declared length
    assert is_wellformed_xdt(b"01380008220") is False  # the last line must end too
    assert is_wellformed_xdt(b"name;value;date\r\n") is False
    # Digits of another script are not a length: int() would happily convert them.
    assert is_wellformed_xdt("٠١٣8000".encode() + b"8220\r\n") is False


def test_a_report_is_read_test_by_test_with_verbatim_values() -> None:
    data = ldt_file(
        header(),
        report(
            lab_test(
                "LDL",
                "LDL Cholesterol",
                value="2.8",
                unit="mmol/L",
                low="0",
                high="3.0",
                clock="0815",
            ),
            lab_test("HBA1C", "HbA1c", value="5.4", unit="%", reference=("< 5.7", "(NGSP)")),
            lab_test("HB", "Hämoglobin", value="14.2", unit="g/dl", low="12.0", high="16.0"),
            lab_test("URIN", "Urinstatus", text=("unauffällig",)),
            lab_test("TSH", "TSH basal", status="F"),
        ),
        TRAILER,
    )
    doc = parse_source_document(data, zone=BERLIN)  # detected by content, not by a file name

    assert (doc.parser_name, doc.parser_version) == ("ldt2-8201", "1")
    assert doc.patient_date_of_birth == date(1980, 1, 15)
    ldl, hba1c, hb = doc.values

    assert (ldl.original_name, ldl.original_value, ldl.original_unit) == (
        "LDL Cholesterol",
        "2.8",
        "mmol/L",
    )
    assert (ldl.reference_low, ldl.reference_high, ldl.reference_text) == ("0", "3.0", None)
    assert ldl.observed_at == datetime(2025, 6, 10, 6, 15, tzinfo=UTC)  # 08:15 CEST
    assert ldl.observed_at_is_date_only is False
    assert ldl.review_reasons == ()

    # Each field belongs to the test whose 8410 precedes it — nothing leaks to a neighbour.
    assert (hba1c.original_value, hba1c.original_unit) == ("5.4", "%")
    assert (hba1c.reference_low, hba1c.reference_high) == (None, None)
    assert hba1c.reference_text == "< 5.7 (NGSP)"
    assert hba1c.observed_at == datetime(2025, 6, 10, tzinfo=UTC)
    assert hba1c.observed_at_is_date_only is True

    assert hb.original_name == "Hämoglobin"  # ISO 8859-15, as declared in 9106
    assert (hb.reference_low, hb.reference_high) == ("12.0", "16.0")

    # The locator is the line of the test's 8410 in the source file.
    lines = data.split(b"\r\n")
    for value in doc.values:
        number = int(value.source_record_locator.removeprefix("line "))
        assert lines[number - 1][3:7] == b"8410"

    # Results without a numeric value are reported, never dropped silently.
    assert [n.reason for n in doc.not_imported] == [TEXT_RESULT, RESULT_PENDING]


def test_the_test_ident_is_the_name_when_no_designation_is_given() -> None:
    doc = parse_ldt(ldt_file(header(), report(lab_test("GLUC", value="5.1")), TRAILER), zone=BERLIN)
    assert doc.values[0].original_name == "GLUC"


def test_the_date_order_follows_the_declared_ldt_version() -> None:
    old = ldt_file(
        header(version="LDT1001.02"),
        report(lab_test("LDL", value="2.8", day="10062025"), born="15011980"),
        TRAILER,
    )
    doc = parse_ldt(old, zone=BERLIN)
    assert doc.values[0].observed_at == datetime(2025, 6, 10, tzinfo=UTC)
    assert doc.patient_date_of_birth == date(1980, 1, 15)

    # The same day-first date under the year-first version is not silently reinterpreted.
    mixed = ldt_file(header(), report(lab_test("LDL", value="2.8", day="10062025")), TRAILER)
    assert _error(mixed).code in {"unsupported_date", "implausible_date"}


@pytest.mark.parametrize("born", ["19800000", "19800100", "00000000", None])
def test_an_incomplete_date_of_birth_is_unknown_not_guessed(born: str | None) -> None:
    doc = parse_ldt(ldt_file(header(), report(LDL, born=born), TRAILER), zone=BERLIN)
    assert doc.patient_date_of_birth is None


def test_character_sets() -> None:
    cp437 = ldt_file(
        header(charset="2"),
        report(lab_test("HB", "Hämoglobin", value="14.2"), last_name="Müller"),
        TRAILER,
        encoding="cp437",
    )
    assert parse_ldt(cp437, zone=BERLIN).values[0].original_name == "Hämoglobin"

    ascii_only = ldt_file(header(charset=None), report(LDL), TRAILER)
    assert parse_ldt(ascii_only, zone=BERLIN).values[0].original_name == "LDL Cholesterol"

    # Undeclared, or the 7-bit national variant: a non-ASCII byte cannot be read safely.
    undeclared = ldt_file(
        header(charset=None), report(lab_test("HB", "Hämoglobin", value="14.2")), TRAILER
    )
    assert _error(undeclared).code == "unsupported_charset"
    assert _error(ldt_file(header(charset="1"), report(LDL), TRAILER)).code == "unsupported_charset"


def test_the_source_status_of_a_result_sends_it_to_review() -> None:
    doc = parse_ldt(
        ldt_file(
            header(),
            report(
                lab_test("A", value="1.0"),
                lab_test("B", value="2.0", status="B"),
                lab_test("K", value="3.0", status="K"),
                kind="V",
            ),
            TRAILER,
        ),
        zone=BERLIN,
    )
    assert [v.review_reasons for v in doc.values] == [
        (PRELIMINARY_REPORT,),
        (PRELIMINARY_REPORT, PREVIOUSLY_REPORTED),
        (PRELIMINARY_REPORT, CORRECTED_RESULT),
    ]

    partial = parse_ldt(ldt_file(header(), report(LDL, kind="T"), TRAILER), zone=BERLIN)
    assert partial.values[0].review_reasons == ()  # a partial report's values are final


def test_a_value_with_a_laboratory_note_is_held_for_review() -> None:
    # The note may qualify the value ("haemolytic sample") and is not carried by the pipeline.
    noted = [*lab_test("K", "Kalium", value="5.9", unit="mmol/l"), ("8470", "Probe hämolytisch")]
    with_text = lab_test("CRP", value="3.1", text=("siehe Kommentar",))
    doc = parse_ldt(ldt_file(header(), report(noted, with_text, LDL), TRAILER), zone=BERLIN)
    assert [v.review_reasons for v in doc.values] == [(SOURCE_COMMENT,), (SOURCE_COMMENT,), ()]


def test_a_local_time_that_is_not_one_instant_is_held_for_review() -> None:
    data = ldt_file(
        header(), report(lab_test("LDL", value="2.8", day="20251026", clock="0230")), TRAILER
    )
    assert parse_ldt(data, zone=BERLIN).values[0].review_reasons == (AMBIGUOUS_LOCAL_TIME,)


def test_a_file_cut_off_in_transit_imports_nothing() -> None:
    whole = ldt_file(
        header(),
        report(
            [*lab_test("K", "Kalium", value="5.9", low="3.5", high="5.1"), ("8470", "hämolytisch")]
        ),
        TRAILER,
    )
    # Cut right after the value: what is left is line-perfect, but the bounds and the
    # laboratory's note never arrived. Without the trailer nothing of it may be imported.
    cut = whole[: whole.index(ldt_line("8420", "5.9")) + len(ldt_line("8420", "5.9"))]
    assert parse_ldt(whole, zone=BERLIN).values[0].review_reasons == (SOURCE_COMMENT,)
    assert _error(cut).code == "malformed_record"
    assert _error(ldt_file(header(), report(LDL))).code == "malformed_record"  # no trailer
    assert _error(ldt_file(header(), TRAILER, report(LDL))).code == "malformed_record"
    assert _error(ldt_file(header(), header(), report(LDL), TRAILER)).code == "malformed_record"


def test_a_note_on_the_whole_report_holds_all_its_values_for_review() -> None:
    doc = parse_ldt(
        ldt_file(
            header(),
            report(LDL, lab_test("HB", value="14.2"), note="Probe hämolytisch"),
            TRAILER,
        ),
        zone=BERLIN,
    )
    assert [v.review_reasons for v in doc.values] == [(SOURCE_COMMENT,), (SOURCE_COMMENT,)]


def test_result_fields_outside_a_test_are_not_silently_dropped() -> None:
    stray = report(LDL)
    stray.insert(2, ("8420", "9.9"))  # a value before any test (8410)
    assert _error(ldt_file(header(), stray, TRAILER)).code == "malformed_record"


def test_reports_that_name_nobody_cannot_be_merged() -> None:
    # One anonymous report is importable (there is nothing to compare); two are not — nothing
    # shows they are one person's.
    one = ldt_file(header(), report(LDL, named=False, born=None), TRAILER)
    assert len(parse_ldt(one, zone=BERLIN).values) == 1
    two = ldt_file(
        header(),
        report(LDL, named=False, born=None),
        report(LDL, named=False, born=None),
        TRAILER,
    )
    assert _error(two).code == "unidentified_patient"
    mixed = ldt_file(header(), report(LDL), report(LDL, named=False, born=None), TRAILER)
    assert _error(mixed).code == "multiple_patients"


@pytest.mark.parametrize(
    ("test", "code"),
    [
        (lab_test("LDL", value="3.4\x00"), "unsupported_character"),
        (lab_test("LDL", "LDL\x07", value="3.4"), "unsupported_character"),
        (lab_test("LDL", value="3.4", low="9" * 61), "field_too_long"),
        (lab_test("LDL", value="3.4", high="9" * 61), "field_too_long"),
    ],
)
def test_a_field_that_cannot_be_stored_verbatim_refuses_the_file(test: list, code: str) -> None:  # type: ignore[type-arg]
    assert _error(ldt_file(header(), report(test), TRAILER)).code == code


def test_a_value_without_a_sampling_date_is_recorded_not_imported() -> None:
    # The report date (8302) is in the file, but it is not when the sample was taken.
    doc = parse_ldt(
        ldt_file(header(), report(lab_test("LDL", value="2.8", day=None), LDL), TRAILER),
        zone=BERLIN,
    )
    assert [v.original_name for v in doc.values] == ["LDL Cholesterol"]
    assert [n.reason for n in doc.not_imported] == [NO_SAMPLING_DATE]


def test_several_reports_for_the_same_patient_are_read_together() -> None:
    data = ldt_file(
        header(),
        report(lab_test("LDL", value="3.6", day="20250115")),
        report(lab_test("LDL", value="2.8", day="20250610")),
        TRAILER,
    )
    assert [v.original_value for v in parse_ldt(data, zone=BERLIN).values] == ["3.6", "2.8"]


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (
            ldt_file(header(), report(LDL), report(LDL, first_name="Max"), TRAILER),
            "multiple_patients",
        ),
        (
            ldt_file(header(), report(LDL), report(LDL, born="19790101"), TRAILER),
            "multiple_patients",
        ),
        (ldt_file(header(), report(LDL, record_type="8203"), TRAILER), "unsupported_record_type"),
        (ldt_file(header(version="LDT1015.00"), report(LDL), TRAILER), "unsupported_ldt_version"),
        (ldt_file(report(LDL), TRAILER), "malformed_record"),  # no package header
        (
            ldt_file(header(), report([*LDL, ("8420", "9.9")]), TRAILER),
            "duplicate_field",
        ),
        (
            ldt_file(header(), report(lab_test("LDL", value="2.8", status="X")), TRAILER),
            "unsupported_test_status",
        ),
        (ldt_file(header(), report(LDL, kind="Q"), TRAILER), "unsupported_report_kind"),
        (
            ldt_file(header(), report(lab_test("LDL", value="2.8", clock="2575")), TRAILER),
            "unsupported_time",
        ),
        (
            ldt_file(header(), report(lab_test("LDL", value="2.8", day="20990101")), TRAILER),
            "implausible_date",
        ),
        (ldt_file(header(), report(), TRAILER), "empty_document"),
        (ldt_file(header(), report(LDL), TRAILER).replace(b"\r\n", b"\n"), "malformed_line"),
    ],
)
def test_anything_outside_the_description_refuses_the_whole_file(data: bytes, code: str) -> None:
    assert _error(data).code == code


def test_a_wrong_line_length_is_refused_with_its_line_number() -> None:
    good = ldt_file(header(), report(LDL), TRAILER)
    lines = good.split(b"\r\n")
    target = next(i for i, line in enumerate(lines) if line[3:7] == b"8420")
    lines[target] = b"099" + lines[target][3:]
    error = _error(b"\r\n".join(lines))
    assert error.code == "malformed_line"
    assert f"line {target + 1}:" in error.detail


def test_errors_and_output_never_carry_the_patient_name() -> None:
    data = ldt_file(
        header(),
        report(
            lab_test("LDL", "ZZ-secret-analyte", value="2.8", status="X"), last_name="ZZ-secret"
        ),
        TRAILER,
    )
    assert "ZZ-secret" not in _error(data).detail

    doc = parse_ldt(ldt_file(header(), report(LDL, last_name="ZZ-secret"), TRAILER), zone=BERLIN)
    assert "ZZ-secret" not in repr(doc)
