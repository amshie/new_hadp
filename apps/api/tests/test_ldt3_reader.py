"""The LDT 3 reader follows the KBV object tree exactly and refuses or records the rest.

Synthetic files only (tests/ldt3_fixtures.py). What a wrong reading would turn into a wrong
clinical value is pinned here: which sample a result belongs to (and so WHEN it was taken),
which of several written values is carried, the time zone, the result's status, and the file's
own checksum.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.imports.parsers import SourceParseError, parse_source_document
from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    AMBIGUOUS_REFERENCE,
    CORRECTED_RESULT,
    MULTIPLE_RESULT_VALUES,
    NO_RESULT,
    NO_SAMPLING_DATE,
    PRELIMINARY_REPORT,
    PREVIOUSLY_REPORTED,
    RESULT_PENDING,
    SOURCE_COMMENT,
    TEXT_RESULT,
    UNSUPPORTED_RESULT_TYPE,
    ParsedDocument,
)
from tests.ldt3_fixtures import (
    chemistry,
    fields,
    header,
    ldt3_file,
    material,
    microbiology,
    note,
    obj,
    reference,
    report,
    timestamp,
    value,
)
from tests.ldt_fixtures import ldt_line

BERLIN = ZoneInfo("Europe/Berlin")
LDL = chemistry("LDL", "LDL Cholesterol", value("2.8", references=(reference("0", "3.0"),)))


def _read(*parts: list, **kwargs) -> ParsedDocument:  # type: ignore[type-arg, no-untyped-def]
    return parse_source_document(ldt3_file(header(), report(*parts, **kwargs)), zone=BERLIN)


def _error(data: bytes) -> SourceParseError:
    with pytest.raises(SourceParseError) as caught:
        parse_source_document(data, zone=BERLIN)
    return caught.value


def test_a_report_is_read_through_its_object_tree() -> None:
    data = ldt3_file(
        header(),
        report(
            material("S1", sampled=timestamp("8219", "Abnahme", "20250610", "081500", "UTC+2")),
            material("S2", sampled=timestamp("8219", "Abnahme", "20250610", "093000", "UTC+2")),
            LDL,
            chemistry(
                "GLUC",
                "Glukose im Plasma",
                value("101", "mg/dl", system="2", references=(reference("60.0", "125.0"),)),
                value("5.6", "mmol/l", system="1", references=(reference("3.3", "6.9"),)),
                samples=("S2",),
            ),
            chemistry("HB", "Hämoglobin", value("14.2", "g/dl", system="2")),
            chemistry("URIN", "Urinstatus", value("unauffällig", None, system="9", shape="04")),
            chemistry("TSH", "TSH basal", status="02"),
            microbiology(),
        ),
    )
    doc = parse_source_document(data, zone=BERLIN)

    assert (doc.parser_name, doc.parser_version) == ("ldt3-8205", "1")
    assert doc.patient_date_of_birth == date(1980, 1, 15)
    ldl, glucose, hb = doc.values

    assert (ldl.original_name, ldl.original_value, ldl.original_unit) == (
        "LDL Cholesterol",
        "2.8",
        "mmol/l",
    )
    assert (ldl.reference_low, ldl.reference_high) == ("0", "3.0")
    # WHEN: the sampling time of the material the result names (S1) — an exact instant, because
    # LDT 3 states the zone. Never the measurement time (14:30) that sits next to the value.
    assert ldl.observed_at == datetime(2025, 6, 10, 6, 15, tzinfo=UTC)
    assert ldl.observed_at_is_date_only is False
    assert ldl.review_reasons == ()

    # One measurement written in two unit systems: the SI one is carried, with ITS range.
    assert (glucose.original_value, glucose.original_unit) == ("5.6", "mmol/l")
    assert (glucose.reference_low, glucose.reference_high) == ("3.3", "6.9")
    assert glucose.observed_at == datetime(2025, 6, 10, 7, 30, tzinfo=UTC)  # sample S2

    assert hb.original_name == "Hämoglobin"  # ISO 8859-15

    # The locator is the line of the value (8420) that was carried.
    lines = data.split(b"\r\n")
    for row in doc.values:
        number = int(row.source_record_locator.removeprefix("line "))
        assert lines[number - 1][3:7] == b"8420"
        assert lines[number - 1][7:].decode("iso-8859-15") == row.original_value

    assert [n.reason for n in doc.not_imported] == [
        TEXT_RESULT,
        RESULT_PENDING,
        UNSUPPORTED_RESULT_TYPE,
    ]


@pytest.mark.parametrize(
    ("clock", "zone", "expected", "date_only"),
    [
        ("081500", "UTC+2", datetime(2025, 6, 10, 6, 15, tzinfo=UTC), False),
        ("081500123", "UTC+2", datetime(2025, 6, 10, 6, 15, tzinfo=UTC), False),  # milliseconds
        ("081500", "UTC", datetime(2025, 6, 10, 8, 15, tzinfo=UTC), False),
        ("081500", "UTC+5:30", datetime(2025, 6, 10, 2, 45, tzinfo=UTC), False),
        ("081500", "UTC-3", datetime(2025, 6, 10, 11, 15, tzinfo=UTC), False),
        # A zone is required with a time; without one the laboratory's zone is assumed.
        ("081500", None, datetime(2025, 6, 10, 6, 15, tzinfo=UTC), False),
        (None, None, datetime(2025, 6, 10, tzinfo=UTC), True),  # a date stays a date
    ],
)
def test_sampling_timestamps(
    clock: str | None, zone: str | None, expected: datetime, date_only: bool
) -> None:
    stamp = timestamp("8219", "Abnahme", "20250610", clock, zone)
    doc = _read(material("S1", sampled=stamp), LDL)
    assert doc.values[0].observed_at == expected
    assert doc.values[0].observed_at_is_date_only is date_only


def test_a_local_time_without_zone_that_is_not_one_instant_is_held_for_review() -> None:
    stamp = timestamp("8219", "Abnahme", "20251026", "023000", None)
    assert _read(material("S1", sampled=stamp), LDL).values[0].review_reasons == (
        AMBIGUOUS_LOCAL_TIME,
    )


@pytest.mark.parametrize(
    ("samples", "materials"),
    [
        (("S9",), [material("S1")]),  # the result names a sample the file does not describe
        (("S1",), [material("S1", with_time=False)]),  # the material names no sampling time
        (  # two samples taken at different times: which one is the result's?
            ("S1", "S2"),
            [material("S1"), material("S2", sampled=timestamp("8219", "Abnahme", "20250611"))],
        ),
        ((), [material("S1")]),  # the result names no sample at all
    ],
)
def test_without_one_sampling_time_the_result_is_not_imported(
    samples: tuple[str, ...], materials: list
) -> None:  # type: ignore[type-arg]
    result = chemistry("LDL", "LDL Cholesterol", value("2.8"), samples=samples)
    doc = _read(*materials, result)
    assert doc.values == []
    assert [n.reason for n in doc.not_imported] == [NO_SAMPLING_DATE]


def test_two_samples_taken_at_the_same_time_are_not_ambiguous() -> None:
    result = chemistry("LDL", "LDL Cholesterol", value("2.8"), samples=("S1", "S2"))
    assert len(_read(material("S1"), material("S2"), result).values) == 1


@pytest.mark.parametrize(
    ("status", "reasons"),
    [
        ("06", ()),
        ("05", ()),
        ("03", (PRELIMINARY_REPORT,)),
        ("10", (PRELIMINARY_REPORT,)),
        ("04", (CORRECTED_RESULT,)),
        ("08", (CORRECTED_RESULT,)),
        ("07", (PREVIOUSLY_REPORTED,)),
    ],
)
def test_the_result_status_decides_whether_a_human_must_look(
    status: str, reasons: tuple[str, ...]
) -> None:
    result = chemistry("LDL", "LDL Cholesterol", value("2.8"), status=status)
    assert _read(material(), result).values[0].review_reasons == reasons


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("02", RESULT_PENDING),
        ("01", NO_RESULT),
        ("09", NO_RESULT),
        ("11", NO_RESULT),
        ("12", NO_RESULT),
    ],
)
def test_a_status_without_a_result_is_recorded_not_imported(status: str, reason: str) -> None:
    # Even if a value is written, a cancelled or missing result is not a measurement.
    result = chemistry("LDL", "LDL Cholesterol", value("2.8"), status=status)
    doc = _read(material(), result)
    assert doc.values == []
    assert [n.reason for n in doc.not_imported] == [reason]


def test_how_a_value_is_written_decides_whether_it_is_carried() -> None:
    doc = _read(
        material(),
        chemistry("CRP", "CRP", value("<0.5", "mg/l", system="2", shape="02")),
        chemistry("HBS", "HBs-Antigen", value("negativ", None, system="9", shape="04")),
        chemistry("TIT", "Titer", value("1:64", None, system="9", shape="05")),
        chemistry(
            "LDL",
            "LDL Cholesterol",
            value("2.8"),
            value("im Zielbereich", None, system="9", shape="04"),
        ),
    )
    below_limit, with_text = doc.values
    # A value with a measuring limit is carried verbatim; the pipeline will not publish it as a
    # number on its own.
    assert below_limit.original_value == "<0.5"
    # A text written next to the number may qualify it and is not carried.
    assert (with_text.original_value, with_text.review_reasons) == ("2.8", (SOURCE_COMMENT,))
    assert [n.reason for n in doc.not_imported] == [TEXT_RESULT, TEXT_RESULT]


def test_several_values_without_a_single_si_one_all_go_to_review() -> None:
    doc = _read(
        material(),
        chemistry(
            "LEUK",
            "Leukozyten",
            value("6.1", "/nl", system="2"),
            value("6100", "/µl", system="2"),
        ),
    )
    assert [(v.original_value, v.review_reasons) for v in doc.values] == [
        ("6.1", (MULTIPLE_RESULT_VALUES,)),
        ("6100", (MULTIPLE_RESULT_VALUES,)),
    ]


def test_reference_ranges() -> None:
    doc = _read(
        material(),
        chemistry("A", "A", value("1", references=(reference(text=("< 5.7", "(NGSP)")),))),
        chemistry("B", "B", value("1", references=(reference("0", "3"), reference("0", "4")))),
        chemistry(
            "C", "C", value("1", "mmol/l", references=(reference("60", "125", unit="mg/dl"),))
        ),
        chemistry("D", "D", value("1", "mmol/l", references=(reference("0", "3", unit="mmol/l"),))),
        chemistry("E", "E", value("1", references=(reference(high="3"),))),
    )
    text_only, several, other_unit, same_unit, one_sided = doc.values
    assert (text_only.reference_low, text_only.reference_text) == (None, "< 5.7 (NGSP)")
    # Several ranges, or a range in another unit than the value: none is chosen or rescaled.
    for row in (several, other_unit):
        assert (row.reference_low, row.reference_high) == (None, None)
        assert row.review_reasons == (AMBIGUOUS_REFERENCE,)
    assert (same_unit.reference_low, same_unit.reference_high) == ("0", "3")
    assert same_unit.review_reasons == ()
    assert (one_sided.reference_low, one_sided.reference_high) == (None, "3")


def test_a_laboratory_note_anywhere_on_the_result_holds_it_for_review() -> None:
    doc = _read(
        material(),
        chemistry("K", "Kalium", value("5.9"), extra=note()),
        chemistry("Q", "Quick", value("2.5", references=(reference("8", "15", note="Achtung"),))),
        LDL,
    )
    assert [v.review_reasons for v in doc.values] == [(SOURCE_COMMENT,), (SOURCE_COMMENT,), ()]


def test_the_ident_is_the_name_when_no_designation_is_given() -> None:
    assert (
        _read(material(), chemistry("GLUC", None, value("5.1"))).values[0].original_name == "GLUC"
    )


def test_several_reports_for_the_same_patient_are_read_together() -> None:
    data = ldt3_file(header(), report(material(), LDL), report(material(), LDL))
    assert len(parse_source_document(data, zone=BERLIN).values) == 2


def test_the_checksum_guards_every_byte() -> None:
    good = ldt3_file(header(), report(material(), LDL))
    assert parse_source_document(good, zone=BERLIN).values[0].original_value == "2.8"
    # One changed digit, every line still well-formed: only the checksum can notice.
    tampered = good.replace(ldt_line("8420", "2.8"), ldt_line("8420", "9.8"))
    assert tampered != good
    assert _error(tampered).code == "checksum_mismatch"
    assert _error(ldt3_file(header(), report(material(), LDL), checksum=False)).code == (
        "malformed_record"
    )


def _unclosed() -> list:  # type: ignore[type-arg]
    broken = report(material(), LDL)
    broken.remove(("8003", "Obj_0060"))
    return broken


def _deep(levels: int) -> list:  # type: ignore[type-arg]
    inner = fields(("3564", "x"))
    for _ in range(levels):
        inner = obj("8167", "Zusaetzliche_Informationen", "Obj_0068", inner)
    return report(material(), chemistry("LDL", "LDL", value("2.8"), extra=inner))


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (ldt3_file(header("LDT3.1.0"), report(material(), LDL)), "unsupported_ldt_version"),
        (
            ldt3_file(header(), report(material(), LDL, record_type="8215")),
            "unsupported_record_type",
        ),
        (
            ldt3_file(header(), report(material(), LDL), report(material(), LDL, first_name="Max")),
            "multiple_patients",
        ),
        (
            ldt3_file(header(), report(material(), LDL), report(material(), LDL, born="19790101")),
            "multiple_patients",
        ),
        (ldt3_file(header(), _unclosed()), "malformed_object"),
        (
            ldt3_file(
                header(),
                [("8000", "8205"), ("8002", "Obj_0035"), ("8003", "Obj_0035"), ("8001", "8205")],
            ),
            "malformed_object",
        ),
        (ldt3_file(header(), _deep(60)), "malformed_object"),
        (ldt3_file(report(material(), LDL)), "malformed_record"),  # no header
        (
            ldt3_file(
                header(), report(material(), chemistry("LDL", "LDL", value("2.8"), status="77"))
            ),
            "unsupported_test_status",
        ),
        (
            ldt3_file(
                header(),
                report(
                    material("S1", sampled=timestamp("8219", "A", "20250610", "081500", "CEST")),
                    LDL,
                ),
            ),
            "unsupported_time",
        ),
        (
            ldt3_file(
                header(),
                report(
                    material("S1", sampled=timestamp("8219", "A", "20250610", "256100", "UTC+2")),
                    LDL,
                ),
            ),
            "unsupported_time",
        ),
        (
            ldt3_file(
                header(), report(material("S1", sampled=timestamp("8219", "A", "20990101")), LDL)
            ),
            "implausible_date",
        ),
        (ldt3_file(header(), report(material())), "empty_document"),
        (ldt3_file(header()), "empty_document"),
    ],
)
def test_anything_outside_the_description_refuses_the_whole_file(data: bytes, code: str) -> None:
    assert _error(data).code == code


def test_an_order_package_is_named_as_such() -> None:
    order = [("8000", "8230"), *header()[1:-1], ("8001", "8230")]
    error = _error(ldt3_file(order, report(material(), LDL, record_type="8215")))
    assert error.code == "unsupported_record_type"
    assert "order packages" in error.detail


def test_an_incomplete_date_of_birth_is_unknown_not_guessed() -> None:
    assert _read(material(), LDL, born="19800000").patient_date_of_birth is None
    assert _read(material(), LDL, born=None).patient_date_of_birth is None


def test_errors_and_output_never_carry_the_patient_name() -> None:
    bad = ldt3_file(
        header(),
        report(
            material(), chemistry("X", "ZZ-secret", value("1"), status="77"), last_name="ZZ-secret"
        ),
    )
    assert "ZZ-secret" not in _error(bad).detail
    assert "ZZ-secret" not in repr(_read(material(), LDL, last_name="ZZ-secret"))
