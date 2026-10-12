"""Reader for the delimited laboratory table (CSV) — `hadp-csv`.

A plain table with a header line. The header decides the layout; the recognized column names
are a closed list (German and English), and anything else in the header is ignored. Layout
rules are strict because a table read "roughly right" is how a value ends up in the wrong
field:

- one of `;`, `,` or TAB as delimiter — the one under which the header carries every required
  column; a header that does not fit exactly one of them is refused;
- required columns: analyte name, value, date; optional: unit, reference low/high, reference
  text, time;
- dates as `YYYY-MM-DD` or `DD.MM.YYYY` only (a slash date is ambiguous and refused);
- values, units and reference bounds are passed on verbatim.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, time
from zoneinfo import ZoneInfo

from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    MAX_NAME,
    MAX_REFERENCE_TEXT,
    MAX_UNIT,
    MAX_VALUE,
    MAX_VALUES,
    ParsedDocument,
    ParsedValue,
    SourceParseError,
    check_length,
    date_only,
    local_instant,
    plausible_day,
)

PARSER_NAME = "hadp-csv"
PARSER_VERSION = "1"

_DELIMITERS = (";", ",", "\t")
_REQUIRED = ("name", "value", "date")
# Recognized header names (lowercased, trimmed) -> field. A closed list, not a similarity match.
_COLUMNS: dict[str, str] = {
    "analyt": "name",
    "analyse": "name",
    "parameter": "name",
    "bezeichnung": "name",
    "analyte": "name",
    "test": "name",
    "name": "name",
    "wert": "value",
    "ergebnis": "value",
    "value": "value",
    "result": "value",
    "einheit": "unit",
    "unit": "unit",
    "referenz_von": "reference_low",
    "referenz_unten": "reference_low",
    "reference_low": "reference_low",
    "referenz_bis": "reference_high",
    "referenz_oben": "reference_high",
    "reference_high": "reference_high",
    "referenzbereich": "reference_text",
    "reference_text": "reference_text",
    "datum": "date",
    "abnahmedatum": "date",
    "date": "date",
    "collected_on": "date",
    "uhrzeit": "time",
    "abnahmezeit": "time",
    "time": "time",
}

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_GERMAN_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_CLOCK = re.compile(r"^(\d{2}):(\d{2})(?::(\d{2}))?$")


def _header_fields(cells: list[str]) -> dict[str, int] | None:
    """Map field -> column index, or None when the header is not this layout."""
    fields: dict[str, int] = {}
    for index, cell in enumerate(cells):
        field = _COLUMNS.get(cell.strip().lower())
        if field is None:
            continue
        if field in fields:
            raise SourceParseError(
                "ambiguous_header", f"the header has more than one column for {field!r}"
            )
        fields[field] = index
    if not all(required in fields for required in _REQUIRED):
        return None
    return fields


def _layout(header_line: str) -> tuple[str, dict[str, int]]:
    matches = []
    for delimiter in _DELIMITERS:
        cells = next(csv.reader([header_line], delimiter=delimiter))
        fields = _header_fields(cells)
        if fields is not None:
            matches.append((delimiter, fields))
    if len(matches) != 1:
        raise SourceParseError(
            "unsupported_layout",
            "the header must name the analyte, the value and the date columns, "
            "separated by ';', ',' or TAB",
        )
    return matches[0]


def _parse_date(raw: str, locator: str) -> date:
    iso = _ISO_DATE.match(raw)
    german = _GERMAN_DATE.match(raw)
    if iso:
        return plausible_day(int(iso[1]), int(iso[2]), int(iso[3]), locator)
    if german:
        return plausible_day(int(german[3]), int(german[2]), int(german[1]), locator)
    raise SourceParseError(
        "unsupported_date", f"{locator}: the date must be YYYY-MM-DD or DD.MM.YYYY"
    )


def _parse_clock(raw: str, locator: str) -> time:
    clock = _CLOCK.match(raw)
    try:
        if clock:
            return time(int(clock[1]), int(clock[2]), int(clock[3] or 0))
    except ValueError:
        pass
    raise SourceParseError("unsupported_time", f"{locator}: the time must be HH:MM or HH:MM:SS")


def parse_csv(text: str, *, zone: ZoneInfo) -> ParsedDocument:
    lines = text.splitlines()
    header_at = next((i for i, line in enumerate(lines) if line.strip()), None)
    if header_at is None:
        raise SourceParseError("empty_document", "the file has no header line")
    delimiter, fields = _layout(lines[header_at])

    def cell(row: list[str], field: str) -> str:
        index = fields.get(field)
        return row[index].strip() if index is not None and index < len(row) else ""

    values: list[ParsedValue] = []
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
    try:
        for row in reader:
            line_no = reader.line_num
            if line_no <= header_at + 1 or not any(c.strip() for c in row):
                continue
            locator = f"line {line_no}"
            name, value, day_raw = cell(row, "name"), cell(row, "value"), cell(row, "date")
            for field, content in (("name", name), ("value", value), ("date", day_raw)):
                if not content:
                    raise SourceParseError("missing_field", f"{locator}: {field} is empty")
            unit = cell(row, "unit") or None
            reference_text = cell(row, "reference_text") or None
            check_length(name, MAX_NAME, "name", locator)
            check_length(value, MAX_VALUE, "value", locator)
            check_length(unit or "", MAX_UNIT, "unit", locator)
            check_length(reference_text or "", MAX_REFERENCE_TEXT, "reference_text", locator)

            day = _parse_date(day_raw, locator)
            clock_raw = cell(row, "time")
            reasons: tuple[str, ...] = ()
            if clock_raw:
                observed_at, ambiguous = local_instant(day, _parse_clock(clock_raw, locator), zone)
                if ambiguous:
                    reasons = (AMBIGUOUS_LOCAL_TIME,)
            else:
                observed_at = date_only(day)

            values.append(
                ParsedValue(
                    original_name=name,
                    original_value=value,
                    original_unit=unit,
                    observed_at=observed_at,
                    observed_at_is_date_only=not clock_raw,
                    source_record_locator=locator,
                    reference_low=cell(row, "reference_low") or None,
                    reference_high=cell(row, "reference_high") or None,
                    reference_text=reference_text,
                    review_reasons=reasons,
                )
            )
            if len(values) > MAX_VALUES:
                raise SourceParseError("too_many_values", f"more than {MAX_VALUES} values")
    except csv.Error as exc:
        raise SourceParseError(
            "malformed_table", f"line {reader.line_num}: unbalanced quoting"
        ) from exc

    if not values:
        raise SourceParseError("empty_document", "the file has a header but no values")
    return ParsedDocument(parser_name=PARSER_NAME, parser_version=PARSER_VERSION, values=values)
