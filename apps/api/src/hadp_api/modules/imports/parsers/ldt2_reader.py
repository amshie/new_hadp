"""Reader for LDT 2 laboratory reports (KBV "Labordatentransfer", record type 8201).

Written against the KBV "Datensatzbeschreibung LDT" (LDT1014.01; LDT1001.02 for its date
order). Only what that description fixes is read; anything outside it refuses the file:

- the line format and its length check are the shared xDT ones (`xdt.py`);
- a record starts with field 8000 (record type); the package header 8220 carries the LDT
  version (9212) and the character set (9106: 2 = CP437, 3 = ISO 8859-1, 4 = ISO 8859-15);
- results are read from 8201 "Labor-Bericht" records only. A file that also carries another
  report type (8202, 8203, 8204 …) is refused rather than read in part;
- inside a report every test starts with 8410; the fields up to the next 8410 belong to it.
  A value that comes with a result text (8480) or a test-related note (8470) is held for
  review, because that text is not carried. The laboratory's own limit indicator (8422), the
  specimen fields (8428-8431) and report-level notes (8490) are not read;
- dates are JJJJMMTT (LDT1014.01) or TTMMJJJJ (LDT1001.02); any other version is refused,
  because the date order depends on it. (LDT 3 is a different, object-based format with its
  own reader.)

The file's patient name is compared in memory to make sure the file is about ONE person and is
never returned; only the date of birth leaves the reader, for the patient guard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time
from zoneinfo import ZoneInfo

from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    CORRECTED_RESULT,
    MAX_NAME,
    MAX_REFERENCE_TEXT,
    MAX_UNIT,
    MAX_VALUE,
    MAX_VALUES,
    NO_SAMPLING_DATE,
    PRELIMINARY_REPORT,
    PREVIOUSLY_REPORTED,
    RESULT_PENDING,
    SOURCE_COMMENT,
    TEXT_RESULT,
    NotImported,
    ParsedDocument,
    ParsedValue,
    SourceParseError,
    check_length,
    date_only,
    local_instant,
    plausible_day,
)
from hadp_api.modules.imports.parsers.xdt import RECORD_START, Line

PARSER_NAME = "ldt2-8201"
PARSER_VERSION = "1"

_CHARSETS = {"2": "cp437", "3": "iso-8859-1", "4": "iso-8859-15"}
# LDT version (9212) -> True when dates are day-first (TTMMJJJJ).
_DAY_FIRST = {"LDT1014.01": False, "LDT1001.02": True}

_PACKAGE_HEADER = "8220"
_REPORT = "8201"
# Framing records that carry no results.
_FRAMING = {"0020", "0021", "8220", "8221"}

_TEST_START = "8410"
_AFTER_TESTS = "8490"  # report-level notes that follow the tests
# Fields that may appear at most once per test.
_SINGLE = {"8411", "8418", "8420", "8421", "8432", "8433", "8461", "8462"}
# Befundart (8401): only the preliminary report changes how its values are treated.
_REPORT_KINDS = {"E", "T", "V", "A", "N"}
# Teststatus (8418).
_STATUS_REASON = {"B": PREVIOUSLY_REPORTED, "K": CORRECTED_RESULT}
_STATUS_PENDING = "F"


@dataclass
class _Test:
    line: int
    ident: str
    single: dict[str, str] = field(default_factory=dict)
    reference_text: list[str] = field(default_factory=list)
    # A result text (8480) or test-related note (8470) accompanies the value.
    commented: bool = False


def _records(lines: list[Line]) -> list[list[Line]]:
    records: list[list[Line]] = []
    for line in lines:
        if line.field_id == RECORD_START:
            records.append([])
        records[-1].append(line)
    return records


def _header(records: list[list[Line]]) -> tuple[str, bool]:
    """Return (encoding, day_first) from the package header."""
    header = next((r for r in records if r[0].raw == _PACKAGE_HEADER.encode()), None)
    if header is None:
        raise SourceParseError("malformed_record", "no package header record (8220)")

    def only(field_id: str) -> str | None:
        found = [
            line.raw.decode("ascii", "replace").strip()
            for line in header
            if line.field_id == field_id
        ]
        if len(found) > 1:
            raise SourceParseError("duplicate_field", f"package header: field {field_id} repeats")
        return found[0] if found else None

    version = only("9212")
    if version not in _DAY_FIRST:
        raise SourceParseError(
            "unsupported_ldt_version", "the LDT version (9212) must be LDT1014.01 or LDT1001.02"
        )
    charset = only("9106")
    if charset is None:
        # Without a declared character set only plain ASCII is unambiguous.
        encoding = "ascii"
    elif charset in _CHARSETS:
        encoding = _CHARSETS[charset]
    else:
        raise SourceParseError("unsupported_charset", "the character set (9106) is not supported")
    return encoding, _DAY_FIRST[version]


def _day(raw: str, day_first: bool, locator: str) -> date | None:
    """Parse an 8-digit LDT date. A date with unknown parts (zeros) yields None."""
    if not re.fullmatch(r"\d{8}", raw):
        raise SourceParseError("unsupported_date", f"{locator}: the date must have 8 digits")
    if day_first:
        day, month, year = int(raw[0:2]), int(raw[2:4]), int(raw[4:8])
    else:
        year, month, day = int(raw[0:4]), int(raw[4:6]), int(raw[6:8])
    if 0 in (day, month, year):
        return None
    return plausible_day(year, month, day, locator)


def _clock(raw: str, locator: str) -> time:
    if re.fullmatch(r"\d{4}", raw) and int(raw[:2]) < 24 and int(raw[2:]) < 60:
        return time(int(raw[:2]), int(raw[2:]))
    raise SourceParseError("unsupported_time", f"{locator}: the time must be HHMM")


def _tests(record: list[Line], encoding: str) -> tuple[dict[str, list[str]], list[_Test]]:
    """Split a report into its report-level fields and its tests."""
    report: dict[str, list[str]] = {}
    tests: list[_Test] = []
    current: _Test | None = None
    for line in record[1:]:
        try:
            content = line.raw.decode(encoding).strip()
        except UnicodeDecodeError as exc:
            raise SourceParseError(
                "unsupported_charset",
                f"line {line.number}: not valid in the declared character set",
            ) from exc
        if line.field_id == _TEST_START:
            current = _Test(line=line.number, ident=content)
            tests.append(current)
        elif line.field_id == _AFTER_TESTS:
            current = None
        elif current is None:
            report.setdefault(line.field_id, []).append(content)
        elif line.field_id in _SINGLE:
            if line.field_id in current.single:
                raise SourceParseError(
                    "duplicate_field",
                    f"line {line.number}: field {line.field_id} repeats in a test",
                )
            current.single[line.field_id] = content
        elif line.field_id in ("8470", "8480"):
            current.commented = current.commented or bool(content)
        elif line.field_id == "8460":
            current.reference_text.append(content)
    return report, tests


def parse_ldt2(lines: list[Line], *, zone: ZoneInfo) -> ParsedDocument:
    records = _records(lines)
    encoding, day_first = _header(records)

    values: list[ParsedValue] = []
    not_imported: list[NotImported] = []
    patients: set[tuple[str, ...]] = set()
    birth_dates: set[date] = set()

    for record in records:
        kind = record[0].raw.decode("ascii", "replace")
        if kind in _FRAMING:
            continue
        if kind != _REPORT:
            raise SourceParseError(
                "unsupported_record_type",
                f"line {record[0].number}: only Labor-Bericht records (8201) can be read",
            )
        report, tests = _tests(record, encoding)
        where = f"line {record[0].number}"

        patients.add(
            tuple(" ".join(report.get(f, [])).casefold() for f in ("3101", "3102", "3103"))
        )
        for raw in report.get("3103", []):
            born = _day(raw, day_first, where)
            if born is not None:
                birth_dates.add(born)

        report_kind = "".join(report.get("8401", []))
        if report_kind and report_kind not in _REPORT_KINDS:
            raise SourceParseError("unsupported_report_kind", f"{where}: unknown Befundart (8401)")

        for test in tests:
            locator = f"line {test.line}"
            status = test.single.get("8418", "")
            if status and status not in (*_STATUS_REASON, _STATUS_PENDING):
                raise SourceParseError(
                    "unsupported_test_status", f"{locator}: unknown Teststatus (8418)"
                )

            value = test.single.get("8420", "")
            if not value:
                # No numeric result value: a text result, or a result that is still to come.
                reason = RESULT_PENDING if status == _STATUS_PENDING else TEXT_RESULT
                not_imported.append(NotImported(source_record_locator=locator, reason=reason))
                continue

            name = test.single.get("8411") or test.ident
            if not name:
                raise SourceParseError(
                    "missing_field", f"{locator}: the test has no name (8411/8410)"
                )
            unit = test.single.get("8421") or None
            reference_text = " ".join(t for t in test.reference_text if t) or None
            check_length(name, MAX_NAME, "name", locator)
            check_length(value, MAX_VALUE, "value", locator)
            check_length(unit or "", MAX_UNIT, "unit", locator)
            check_length(reference_text or "", MAX_REFERENCE_TEXT, "reference_text", locator)

            day_raw = test.single.get("8432")
            day = _day(day_raw, day_first, locator) if day_raw else None
            if day is None:
                # The report and receipt dates are not the sampling date; none is invented.
                not_imported.append(
                    NotImported(source_record_locator=locator, reason=NO_SAMPLING_DATE)
                )
                continue

            reasons: list[str] = []
            clock_raw = test.single.get("8433")
            if clock_raw:
                observed_at, ambiguous = local_instant(day, _clock(clock_raw, locator), zone)
                if ambiguous:
                    reasons.append(AMBIGUOUS_LOCAL_TIME)
            else:
                observed_at = date_only(day)
            if report_kind == "V":
                reasons.append(PRELIMINARY_REPORT)
            if status in _STATUS_REASON:
                reasons.append(_STATUS_REASON[status])
            if test.commented:
                # The note may qualify the value; it is not carried, so a human reads the source.
                reasons.append(SOURCE_COMMENT)

            values.append(
                ParsedValue(
                    original_name=name,
                    original_value=value,
                    original_unit=unit,
                    observed_at=observed_at,
                    observed_at_is_date_only=not clock_raw,
                    source_record_locator=locator,
                    reference_low=test.single.get("8461") or None,
                    reference_high=test.single.get("8462") or None,
                    reference_text=reference_text,
                    review_reasons=tuple(reasons),
                )
            )
            if len(values) > MAX_VALUES:
                raise SourceParseError("too_many_values", f"more than {MAX_VALUES} values")

    if len(patients) > 1 or len(birth_dates) > 1:
        raise SourceParseError(
            "multiple_patients", "the file contains reports for more than one patient"
        )
    if not values and not not_imported:
        raise SourceParseError("empty_document", "the file contains no laboratory results")
    return ParsedDocument(
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        values=values,
        not_imported=not_imported,
        patient_date_of_birth=next(iter(birth_dates), None),
    )
