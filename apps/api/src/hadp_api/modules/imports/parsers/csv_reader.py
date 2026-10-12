"""Reader for the delimited laboratory table (CSV) — `hadp-csv`.

A plain table with a header line. The header decides the layout; the recognized column names
are a closed list (German and English), and anything else in the header is ignored. Layout
rules are strict because a table read "roughly right" is how a value ends up in the wrong
field:

- one of `;`, `,` or TAB as delimiter — the one under which the header carries every required
  column; a header that does not fit exactly one of them is refused;
- every row must have exactly as many cells as the header. A row with one cell too many is
  what an unquoted decimal comma in a comma-separated file looks like — it is refused, never
  read by position;
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
    MAX_BOUND,
    MAX_NAME,
    MAX_REFERENCE_TEXT,
    MAX_UNIT,
    MAX_VALUE,
    MAX_VALUES,
    ParsedDocument,
    ParsedValue,
    SourceParseError,
    check_text,
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
_LIMITS = {
    "name": MAX_NAME,
    "value": MAX_VALUE,
    "unit": MAX_UNIT,
    "reference_low": MAX_BOUND,
    "reference_high": MAX_BOUND,
    "reference_text": MAX_REFERENCE_TEXT,
}

_ISO_DATE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")
_GERMAN_DATE = re.compile(r"^([0-9]{2})\.([0-9]{2})\.([0-9]{4})$")
_CLOCK = re.compile(r"^([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?$")


def _rows(text: str, delimiter: str) -> list[tuple[int, list[str]]]:
    """All non-empty rows as (line number, cells). The csv module does the line counting, so
    a locator always names the line the row really ends on."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    rows = []
    try:
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append((reader.line_num, row))
    except csv.Error as exc:
        raise SourceParseError(
            "malformed_table", f"line {reader.line_num}: unbalanced quoting"
        ) from exc
    return rows


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
    layouts = []
    quoting_error: SourceParseError | None = None
    for delimiter in _DELIMITERS:
        try:
            rows = _rows(text, delimiter)
        except SourceParseError as exc:
            # Under the wrong delimiter a correctly quoted file looks broken; only when no
            # delimiter fits is this the file's own problem.
            quoting_error = quoting_error or exc
            continue
        if not rows:
            raise SourceParseError("empty_document", "the file has no header line")
        fields = _header_fields(rows[0][1])
        if fields is not None:
            layouts.append((rows, fields))
    if not layouts and quoting_error is not None:
        raise quoting_error
    if len(layouts) != 1:
        raise SourceParseError(
            "unsupported_layout",
            "the header must name the analyte, the value and the date columns, "
            "separated by ';', ',' or TAB",
        )
    rows, fields = layouts[0]
    width = len(rows[0][1])

    values: list[ParsedValue] = []
    for line_no, row in rows[1:]:
        locator = f"line {line_no}"
        if len(row) != width:
            # Never read a ragged row by position: the cells no longer line up with the header.
            raise SourceParseError(
                "malformed_table",
                f"{locator}: the row has {len(row)} cells, the header has {width}",
            )
        cells = {field: row[index].strip() for field, index in fields.items()}
        for field in _REQUIRED:
            if not cells[field]:
                raise SourceParseError("missing_field", f"{locator}: {field} is empty")
        for field, limit in _LIMITS.items():
            check_text(cells.get(field), limit, field, locator)

        day = _parse_date(cells["date"], locator)
        clock_raw = cells.get("time", "")
        reasons: tuple[str, ...] = ()
        if clock_raw:
            observed_at, ambiguous = local_instant(day, _parse_clock(clock_raw, locator), zone)
            if ambiguous:
                reasons = (AMBIGUOUS_LOCAL_TIME,)
        else:
            observed_at = date_only(day)

        values.append(
            ParsedValue(
                original_name=cells["name"],
                original_value=cells["value"],
                original_unit=cells.get("unit") or None,
                observed_at=observed_at,
                observed_at_is_date_only=not clock_raw,
                source_record_locator=locator,
                reference_low=cells.get("reference_low") or None,
                reference_high=cells.get("reference_high") or None,
                reference_text=cells.get("reference_text") or None,
                review_reasons=reasons,
            )
        )
        if len(values) > MAX_VALUES:
            raise SourceParseError("too_many_values", f"more than {MAX_VALUES} values")

    if not values:
        raise SourceParseError("empty_document", "the file has a header but no values")
    return ParsedDocument(parser_name=PARSER_NAME, parser_version=PARSER_VERSION, values=values)
