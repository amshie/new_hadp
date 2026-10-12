"""The CSV reader transports source values verbatim and refuses what it cannot read exactly.

Synthetic rows only. The reader never converts a value, never guesses a date, and never returns
part of a file: a structural problem refuses the whole document with a position, not content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.imports.parsers import SourceParseError, parse_source_document
from hadp_api.modules.imports.parsers.base import AMBIGUOUS_LOCAL_TIME, MAX_VALUES
from hadp_api.modules.imports.parsers.csv_reader import parse_csv

BERLIN = ZoneInfo("Europe/Berlin")


def _error(text: str) -> SourceParseError:
    with pytest.raises(SourceParseError) as caught:
        parse_csv(text, zone=BERLIN)
    return caught.value


def test_german_layout_keeps_source_values_verbatim() -> None:
    doc = parse_csv(
        "Analyt;Wert;Einheit;Referenz_von;Referenz_bis;Abnahmedatum\n"
        "LDL Cholesterol;2,8;mmol/L;0;3,0;10.06.2025\n"
        "HbA1c;5,4;%;;5,6;10.06.2025\n",
        zone=BERLIN,
    )
    assert (doc.parser_name, doc.parser_version) == ("hadp-csv", "1")
    ldl, hba1c = doc.values
    # The decimal comma is NOT rewritten here: the original stays the original.
    assert (ldl.original_name, ldl.original_value, ldl.original_unit) == (
        "LDL Cholesterol",
        "2,8",
        "mmol/L",
    )
    assert (ldl.reference_low, ldl.reference_high) == ("0", "3,0")
    assert ldl.observed_at == datetime(2025, 6, 10, tzinfo=UTC)
    assert ldl.observed_at_is_date_only is True
    assert ldl.source_record_locator == "line 2"
    # One-sided interval: the missing bound stays missing.
    assert (hba1c.reference_low, hba1c.reference_high) == (None, "5,6")
    assert hba1c.source_record_locator == "line 3"


def test_english_layout_ignores_unknown_columns_and_header_case() -> None:
    doc = parse_csv(
        ' NAME , Value ,Unit,Comment,Date\n"Glucose",5.1,mmol/L,"fasting, morning",2025-06-10\n',
        zone=BERLIN,
    )
    (glucose,) = doc.values
    assert (glucose.original_name, glucose.original_value) == ("Glucose", "5.1")
    assert glucose.observed_at == datetime(2025, 6, 10, tzinfo=UTC)


def test_tab_delimiter_and_reference_text() -> None:
    doc = parse_csv(
        "Parameter\tErgebnis\tReferenzbereich\tDatum\nHbA1c\t5,4\t< 5,7 %\t10.06.2025\n",
        zone=BERLIN,
    )
    assert doc.values[0].reference_text == "< 5,7 %"
    assert doc.values[0].original_unit is None


def test_blank_lines_are_skipped_but_keep_their_line_numbers() -> None:
    doc = parse_csv(
        "\nname,value,date\n\nGlucose,5.1,2025-06-10\n\nHbA1c,5.4,2025-06-10\n", zone=BERLIN
    )
    assert [v.source_record_locator for v in doc.values] == ["line 4", "line 6"]


@pytest.mark.parametrize(
    ("day", "clock", "expected_utc"),
    [
        ("10.06.2025", "08:15", datetime(2025, 6, 10, 6, 15, tzinfo=UTC)),  # CEST, UTC+2
        ("10.01.2025", "08:15:30", datetime(2025, 1, 10, 7, 15, 30, tzinfo=UTC)),  # CET, UTC+1
        # Just after local midnight belongs to the previous UTC day.
        ("10.06.2025", "00:30", datetime(2025, 6, 9, 22, 30, tzinfo=UTC)),
    ],
)
def test_local_time_is_resolved_in_the_laboratory_zone(
    day: str, clock: str, expected_utc: datetime
) -> None:
    doc = parse_csv(f"name;value;date;time\nGlucose;5,1;{day};{clock}\n", zone=BERLIN)
    (row,) = doc.values
    assert row.observed_at == expected_utc
    assert row.observed_at_is_date_only is False
    assert row.review_reasons == ()


@pytest.mark.parametrize(
    "day",
    [
        "30.03.2025",  # 02:30 does not exist: clocks jump from 02:00 to 03:00
        "26.10.2025",  # 02:30 happens twice: clocks fall back from 03:00 to 02:00
    ],
)
def test_a_local_time_that_is_not_one_instant_is_held_for_review(day: str) -> None:
    doc = parse_csv(f"name;value;date;time\nGlucose;5,1;{day};02:30\n", zone=BERLIN)
    assert doc.values[0].review_reasons == (AMBIGUOUS_LOCAL_TIME,)


@pytest.mark.parametrize(
    ("text", "code", "position"),
    [
        ("name;value\nGlucose;5,1\n", "unsupported_layout", "header"),  # no date column
        ("just some text\n", "unsupported_layout", "header"),
        ("name;value;date;wert\nGlucose;5,1;10.06.2025;5\n", "ambiguous_header", "'value'"),
        ("name;value;date\nGlucose;5,1;06/10/2025\n", "unsupported_date", "line 2"),  # slash date
        ("name;value;date\nGlucose;5,1;31.02.2025\n", "unsupported_date", "line 2"),
        ("name;value;date;time\nGlucose;5,1;10.06.2025;8.15\n", "unsupported_time", "line 2"),
        ("name;value;date\nGlucose;5,1;10.06.2025\nHbA1c;;10.06.2025\n", "missing_field", "line 3"),
        ("name;value;date\nGlucose;5,1\n", "malformed_table", "line 2"),  # short row
        ("name;value;date\n", "empty_document", "no values"),
        ("", "empty_document", "no header"),
        ('name;value;date\n"Glucose;5,1;10.06.2025\n', "malformed_table", "quoting"),
        (f"name;value;date\n{'G' * 201};5,1;10.06.2025\n", "field_too_long", "line 2"),
    ],
)
def test_structural_problems_refuse_the_whole_file(text: str, code: str, position: str) -> None:
    error = _error(text)
    assert error.code == code
    assert position in error.detail


@pytest.mark.parametrize(
    "text",
    [
        # An unquoted decimal comma in a comma-separated file: one cell too many. Read by
        # position this row would yield the value "3" — and publish.
        "Date,Analyte,Unit,Value\n2025-06-10,LDL,mmol/L,3,4\n",
        # The same slip in the reference bounds would yield 1–5 instead of 1,5–4,1.
        "Analyte,Value,Unit,Date,Reference_low,Reference_high\nLDL,3.4,mmol/L,2025-06-10,1,5,4,1\n",
        # A row that stops early would silently lose its trailing bound.
        "Analyte;Value;Date;Reference_low\nLDL;3,4;2025-06-10\n",
    ],
)
def test_a_row_that_does_not_line_up_with_the_header_is_never_read_by_position(text: str) -> None:
    error = _error(text)
    assert error.code == "malformed_table"
    assert "line 2" in error.detail and "cells" in error.detail


@pytest.mark.parametrize("lead", ["\r\r\n", "\x0c\n", "\u2028\n", "\x85\n", "\n\n"])
def test_odd_line_breaks_never_swallow_a_data_row(lead: str) -> None:
    # Two ways of counting lines used to disagree here, and the first data row vanished.
    newline = "\r\r\n" if lead == "\r\r\n" else "\n"
    text = lead + newline.join(
        ["Name;Wert;Datum", "LDL;3,4;10.06.2025", "Glucose;5,1;10.06.2025", ""]
    )
    assert [v.original_name for v in parse_csv(text, zone=BERLIN).values] == ["LDL", "Glucose"]


def test_quoting_is_judged_under_the_delimiter_that_fits() -> None:
    # Correct under ';' — and only looks broken when read with ',' or TAB.
    doc = parse_csv('Name;Wert;Datum\n"LDL";2,8;10.06.2025\n', zone=BERLIN)
    assert (doc.values[0].original_name, doc.values[0].original_value) == ("LDL", "2,8")


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Name;Wert;Datum\nLDL;3.4\x00;10.06.2025\n", "unsupported_character"),
        ("Name;Wert;Datum;Referenz_von\nLDL;3,4;10.06.2025;" + "9" * 61 + "\n", "field_too_long"),
        ("Name;Wert;Datum;Referenz_bis\nLDL;3,4;10.06.2025;" + "9" * 61 + "\n", "field_too_long"),
    ],
)
def test_a_field_that_cannot_be_stored_verbatim_refuses_the_file(text: str, code: str) -> None:
    assert _error(text).code == code


def test_errors_name_positions_never_content() -> None:
    error = _error("name;value;date\nZZ-secret-analyte;ZZ-secret-value;not-a-date\n")
    assert "ZZ-secret" not in error.detail
    assert "not-a-date" not in error.detail


def test_a_file_beyond_the_row_limit_is_refused() -> None:
    rows = "Glucose;5,1;10.06.2025\n" * (MAX_VALUES + 1)
    assert _error("name;value;date\n" + rows).code == "too_many_values"


def test_detection_reads_a_byte_order_mark_and_refuses_other_content() -> None:
    doc = parse_source_document("﻿name;value;date\nGlucose;5,1;10.06.2025\n".encode(), zone=BERLIN)
    assert doc.values[0].original_name == "Glucose"

    with pytest.raises(SourceParseError) as pdf:
        parse_source_document(b"%PDF-1.7\n...", zone=BERLIN)
    assert pdf.value.code == "unsupported_format"

    with pytest.raises(SourceParseError) as binary:
        parse_source_document(b"\xff\xfe\x00\x01 not text", zone=BERLIN)
    assert binary.value.code == "unsupported_format"
