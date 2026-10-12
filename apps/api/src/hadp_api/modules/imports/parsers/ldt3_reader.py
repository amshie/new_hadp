"""Reader for LDT 3 laboratory reports (KBV "LDT 3 Satzbeschreibung", record type 8205).

Written against the KBV record description v3.2.20 and checked against the KBV's published test
files. LDT 3 is a tree: an attribute line (e.g. `8160 UE_Klinische_Chemie`) is always followed
by its object, `8002 Obj_0060` … `8003 Obj_0060`. What is read:

- the file is 8220 (header), one or more 8205 (report), 8221 (trailer). The trailer's checksum
  (9300, SHA-1 over everything before that line) must match — a damaged file is refused;
- the version (0001 in the header) must be LDT3.2.x; the character set is ISO 8859-15;
- per report: the patient's date of birth (Obj_0045 → Obj_0047 → 3103), every material
  (Obj_0037) with its sampling timestamp (8219), and the clinical-chemistry results
  (Obj_0035 → Obj_0060);
- a result names its sample by 7364; the sampling time is the one of the material with that
  identifier. The measurement time (8225) and the report time are never used in its place;
- a result's values hang under 7306 (how the value is written) → 8420 (the value) with its unit
  system 8419, unit 8421 and reference ranges (Obj_0042). When the same measurement is given in
  several unit systems, the SI one (8419 = 1) is taken.

Everything else under a report — microbiology, cytology, blood group, tumour and "other"
results, body measurements, attachments — is not carried; result objects of those kinds are
recorded as not imported.

The patient's name is compared in memory to make sure the file is about ONE person and is never
returned; only the date of birth leaves the reader, for the patient guard.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    AMBIGUOUS_REFERENCE,
    CORRECTED_RESULT,
    MAX_NAME,
    MAX_REFERENCE_TEXT,
    MAX_UNIT,
    MAX_VALUE,
    MAX_VALUES,
    MULTIPLE_RESULT_VALUES,
    NO_RESULT,
    NO_SAMPLING_DATE,
    PRELIMINARY_REPORT,
    PREVIOUSLY_REPORTED,
    RESULT_PENDING,
    SOURCE_COMMENT,
    TEXT_RESULT,
    UNSUPPORTED_RESULT_TYPE,
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

PARSER_NAME = "ldt3-8205"
PARSER_VERSION = "1"

_ENCODING = "iso-8859-15"
_VERSION_PREFIX = "LDT3.2."
_MAX_DEPTH = 40  # far beyond any real file; stops a hostile one

_RECORD_END = "8001"
_OBJECT_START = "8002"
_OBJECT_END = "8003"
_HEADER, _REPORT, _TRAILER = "8220", "8205", "8221"

_PATIENT, _PERSON = "Obj_0045", "Obj_0047"
_REPORT_INFO = "Obj_0017"
_MATERIAL = "Obj_0037"
_RESULTS = "Obj_0035"
_CHEMISTRY = "Obj_0060"
_REFERENCE = "Obj_0042"
_TIMESTAMP = "Obj_0054"
# Result objects of other kinds, allowed under the Laborergebnisbericht.
_OTHER_RESULTS = {"Obj_0061", "Obj_0062", "Obj_0063", "Obj_0055", "Obj_0073", "Obj_0056"}
# Objects that carry a note or an attention message from the laboratory.
_NOTES = {"Obj_0068", "Obj_0026"}

_SAMPLING_TIME = "8219"  # Timestamp_Materialabnahme_entnahme
# 8418 Ergebnisstatus.
_STATUS_FINAL = {"05", "06"}
_STATUS_REVIEW = {
    "03": PRELIMINARY_REPORT,  # technically validated only
    "10": PRELIMINARY_REPORT,  # extended analysis required
    "04": CORRECTED_RESULT,
    "08": CORRECTED_RESULT,
    "07": PREVIOUSLY_REPORTED,
}
_STATUS_NOT_IMPORTED = {
    "02": RESULT_PENDING,
    "01": NO_RESULT,
    "09": NO_RESULT,
    "11": NO_RESULT,
    "12": NO_RESULT,
}
# 7306 Darstellung Ergebniswerte: 01 a number, 02/03 a number with a measuring limit (< / >).
_NUMERIC = {"01", "02", "03"}
_SI = "1"  # 8419 Einheitensystem

_ZONE = re.compile(r"UTC(?:([+-])(\d{1,2})(?::(\d{2}))?)?")


@dataclass
class _Node:
    """An object (or a record): its lines and nested objects in file order."""

    name: str
    line: int
    attribute: str = ""  # the field id of the attribute line that introduced the object
    items: list[tuple[str, str, int] | _Node] = field(default_factory=list)

    def values(self, field_id: str) -> list[str]:
        return [i[1] for i in self.items if not isinstance(i, _Node) and i[0] == field_id]

    def one(self, field_id: str) -> str | None:
        found = self.values(field_id)
        if len(found) > 1:
            raise SourceParseError(
                "duplicate_field", f"line {self.line}: field {field_id} repeats in {self.name}"
            )
        return found[0] if found else None

    def children(self, name: str) -> list[_Node]:
        return [i for i in self.items if isinstance(i, _Node) and i.name == name]

    def has_note(self) -> bool:
        return any(isinstance(i, _Node) and (i.name in _NOTES or i.has_note()) for i in self.items)


@dataclass
class _Value:
    line: int
    shape: str  # 7306
    value: str
    unit_system: str | None = None
    unit: str | None = None
    references: list[_Node] = field(default_factory=list)


def is_ldt3(lines: list[Line]) -> bool:
    """LDT 3 names its version in field 0001 at the top of the header record."""
    return any(line.field_id == "0001" and line.raw.startswith(b"LDT3") for line in lines[:10])


def _verify_checksum(data: bytes) -> None:
    marker = data.rfind(b"9300")
    start = data.rfind(b"\r\n", 0, marker) + 2 if marker != -1 else -1
    if start < 2 or data[start + 3 : start + 7] != b"9300":
        raise SourceParseError("malformed_record", "the trailer carries no checksum (9300)")
    declared = data[start + 7 : data.index(b"\r\n", start)].decode("ascii", "replace")
    if hashlib.sha1(data[:start], usedforsecurity=False).hexdigest() != declared.strip().lower():
        raise SourceParseError("checksum_mismatch", "the file's checksum (9300) does not match")


def _records(lines: list[Line]) -> list[_Node]:
    """Build one tree per record, checking that every object and record is closed properly."""
    records: list[_Node] = []
    stack: list[_Node] = []
    for line in lines:
        try:
            content = line.raw.decode(_ENCODING).strip()
        except UnicodeDecodeError as exc:  # pragma: no cover - ISO 8859-15 decodes every byte
            raise SourceParseError("unsupported_charset", f"line {line.number}") from exc
        where = f"line {line.number}"
        if line.field_id == RECORD_START:
            if stack:
                raise SourceParseError("malformed_record", f"{where}: the previous record is open")
            stack = [_Node(name=content, line=line.number)]
            records.append(stack[0])
        elif not stack:
            raise SourceParseError("malformed_record", f"{where}: a line outside any record")
        elif line.field_id == _RECORD_END:
            if len(stack) != 1 or stack[0].name != content:
                raise SourceParseError("malformed_record", f"{where}: the record end does not fit")
            stack = []
        elif line.field_id == _OBJECT_START:
            parent = stack[-1]
            # "Auf das Objektattribut folgt immer das Objekt": the line before names it.
            attribute = parent.items.pop() if parent.items else None
            if attribute is None or isinstance(attribute, _Node) or len(stack) >= _MAX_DEPTH:
                raise SourceParseError("malformed_object", f"{where}: an object without attribute")
            node = _Node(name=content, line=line.number, attribute=attribute[0])
            parent.items.append(node)
            stack.append(node)
        elif line.field_id == _OBJECT_END:
            if len(stack) < 2 or stack[-1].name != content:
                raise SourceParseError("malformed_object", f"{where}: the object end does not fit")
            stack.pop()
        else:
            stack[-1].items.append((line.field_id, content, line.number))
    if stack:
        raise SourceParseError("malformed_record", "the last record is not closed")
    return records


def _day(raw: str, locator: str) -> date | None:
    """Parse JJJJMMTT. A date with unknown parts (zeros) yields None."""
    if not re.fullmatch(r"\d{8}", raw):
        raise SourceParseError("unsupported_date", f"{locator}: the date must have 8 digits")
    year, month, day = int(raw[0:4]), int(raw[4:6]), int(raw[6:8])
    if 0 in (day, month, year):
        return None
    return plausible_day(year, month, day, locator)


def _instant(stamp: _Node, zone: ZoneInfo) -> tuple[datetime, bool, bool] | None:
    """Resolve a timestamp object to (instant, is_date_only, ambiguous); None without a date."""
    locator = f"line {stamp.line}"
    day_raw = stamp.one("7278")
    day = _day(day_raw, locator) if day_raw else None
    if day is None:
        return None
    clock_raw = stamp.one("7279")
    if not clock_raw:
        return date_only(day), True, False
    if not re.fullmatch(r"\d{6}(\d{3})?", clock_raw):
        raise SourceParseError("unsupported_time", f"{locator}: the time must be hhmmss")
    try:
        clock = time(int(clock_raw[0:2]), int(clock_raw[2:4]), int(clock_raw[4:6]))
    except ValueError as exc:
        raise SourceParseError("unsupported_time", f"{locator}: not a time of day") from exc
    zone_raw = stamp.one("7273")
    if not zone_raw:
        # The description requires a zone with a time; without one the laboratory's is assumed.
        observed_at, ambiguous = local_instant(day, clock, zone)
        return observed_at, False, ambiguous
    match = _ZONE.fullmatch(zone_raw)
    if match is None or int(match[2] or 0) > 14 or int(match[3] or 0) > 59:
        raise SourceParseError("unsupported_time", f"{locator}: the time zone must be like UTC+2")
    offset = timedelta(hours=int(match[2] or 0), minutes=int(match[3] or 0))
    if match[1] == "-":
        offset = -offset
    exact = datetime.combine(day, clock, tzinfo=timezone(offset)).astimezone(UTC)
    return exact, False, False


def _value_groups(result: _Node) -> tuple[list[_Value], bool]:
    """Split a result into its values. Returns (values, has_non_numeric_value)."""
    groups: list[_Value] = []
    shape: str | None = None
    current: _Value | None = None
    for item in result.items:
        if isinstance(item, _Node):
            if current is not None and item.attribute == "8142" and item.name == _REFERENCE:
                current.references.append(item)
            elif item.attribute not in ("8225", "8237"):
                current = None  # the value's own block is over
            continue
        field_id, content, line = item
        if field_id == "7306":
            shape, current = content, None
        elif field_id == "8420":
            current = _Value(line=line, shape=shape or "", value=content)
            groups.append(current)
        elif field_id == "8419" and current is not None and current.unit_system is None:
            current.unit_system = content
        elif field_id == "8421" and current is not None and current.unit is None:
            current.unit = content
        else:
            current = None
    numeric = [g for g in groups if g.shape in _NUMERIC and g.value]
    return numeric, len(numeric) != len(groups)


def _reference(value: _Value, locator: str) -> tuple[str | None, str | None, str | None, bool]:
    """Return (low, high, text, ambiguous) for a value's reference ranges."""
    if not value.references:
        return None, None, None, False
    if len(value.references) > 1:
        return None, None, None, True
    ref = value.references[0]
    low, high = ref.one("8461"), ref.one("8462")
    text = " ".join(t for t in ref.values("8460") if t) or None
    check_length(text or "", MAX_REFERENCE_TEXT, "reference_text", locator)
    # Each bound may name its own unit; a bound in another unit than the value is not usable.
    bound_units = {u for u in ref.values("8421") if u}
    if (low or high) and bound_units and bound_units != {value.unit or ""}:
        return None, None, text, True
    return low or None, high or None, text, False


def parse_ldt3(data: bytes, lines: list[Line], *, zone: ZoneInfo) -> ParsedDocument:
    _verify_checksum(data)
    records = _records(lines)
    kinds = [r.name for r in records]
    if kinds[0] == "8230":
        # A practice-to-laboratory package (orders), not a laboratory report package.
        raise SourceParseError(
            "unsupported_record_type", "line 1: order packages (8230) carry no results"
        )
    if len(kinds) < 2 or kinds[0] != _HEADER or kinds[-1] != _TRAILER:
        raise SourceParseError("malformed_record", "expected a header (8220) and a trailer (8221)")
    versions = [v for node in records[0].children("Obj_0032") for v in node.values("0001")]
    if len(versions) != 1 or not versions[0].startswith(_VERSION_PREFIX):
        raise SourceParseError("unsupported_ldt_version", "the LDT version (0001) must be LDT3.2.x")

    values: list[ParsedValue] = []
    not_imported: list[NotImported] = []
    patients: set[tuple[str, ...]] = set()
    birth_dates: set[date] = set()

    for record in records[1:-1]:
        if record.name != _REPORT:
            raise SourceParseError(
                "unsupported_record_type",
                f"line {record.line}: only report records (8205) can be read",
            )
        for patient in record.children(_PATIENT):
            for person in patient.children(_PERSON):
                born_raw = person.one("3103") or ""
                patients.add(
                    (
                        (person.one("3101") or "").casefold(),
                        " ".join(person.values("3102")).casefold(),
                        born_raw,
                    )
                )
                born = _day(born_raw, f"line {person.line}") if born_raw else None
                if born is not None:
                    birth_dates.add(born)

        for info in record.children(_REPORT_INFO):
            if (info.one("8401") or "2") not in ("1", "2"):
                raise SourceParseError(
                    "unsupported_report_kind", f"line {info.line}: unknown status (8401)"
                )

        # Sample identifier -> sampling timestamp (None when the material names none).
        sampling: dict[str, tuple[datetime, bool, bool] | None] = {}
        for material in record.children(_MATERIAL):
            sample = material.one("7364")
            stamps = [c for c in material.children(_TIMESTAMP) if c.attribute == _SAMPLING_TIME]
            if sample:
                sampling[sample] = _instant(stamps[0], zone) if len(stamps) == 1 else None

        for report in record.children(_RESULTS):
            for item in report.items:
                if not isinstance(item, _Node):
                    continue
                where = f"line {item.line}"
                if item.name in _OTHER_RESULTS:
                    not_imported.append(NotImported(where, UNSUPPORTED_RESULT_TYPE))
                    continue
                if item.name != _CHEMISTRY:
                    continue  # the report's own timestamp, notes and attachments

                status = item.one("8418") or ""
                if status in _STATUS_NOT_IMPORTED:
                    not_imported.append(NotImported(where, _STATUS_NOT_IMPORTED[status]))
                    continue
                if status not in _STATUS_FINAL and status not in _STATUS_REVIEW:
                    raise SourceParseError(
                        "unsupported_test_status", f"{where}: unknown Ergebnisstatus (8418)"
                    )
                numeric, has_text_value = _value_groups(item)
                if not numeric:
                    not_imported.append(NotImported(where, TEXT_RESULT))
                    continue
                name = item.one("8411") or item.one("8410")
                if not name:
                    raise SourceParseError("missing_field", f"{where}: the result has no name")
                check_length(name, MAX_NAME, "name", where)

                # The sampling time is the material's. Several samples must agree on it.
                moments = {sampling.get(sample) for sample in item.values("7364")}
                moment = next(iter(moments)) if len(moments) == 1 else None
                if moment is None:
                    not_imported.append(NotImported(where, NO_SAMPLING_DATE))
                    continue
                observed_at, is_date_only, ambiguous_time = moment

                shared: list[str] = []
                if ambiguous_time:
                    shared.append(AMBIGUOUS_LOCAL_TIME)
                if status in _STATUS_REVIEW:
                    shared.append(_STATUS_REVIEW[status])
                if has_text_value or item.has_note():
                    # A text result or a note may qualify the value; it is not carried.
                    shared.append(SOURCE_COMMENT)

                # One measurement written in several unit systems: the SI one is taken.
                chosen = numeric
                if len(numeric) > 1:
                    si = [g for g in numeric if g.unit_system == _SI]
                    if len(si) == 1:
                        chosen = si
                    else:
                        shared.append(MULTIPLE_RESULT_VALUES)

                for group in chosen:
                    locator = f"line {group.line}"
                    low, high, text, ambiguous_reference = _reference(group, locator)
                    check_length(group.value, MAX_VALUE, "value", locator)
                    check_length(group.unit or "", MAX_UNIT, "unit", locator)
                    reasons = [*shared, *([AMBIGUOUS_REFERENCE] if ambiguous_reference else [])]
                    values.append(
                        ParsedValue(
                            original_name=name,
                            original_value=group.value,
                            original_unit=group.unit or None,
                            observed_at=observed_at,
                            observed_at_is_date_only=is_date_only,
                            source_record_locator=locator,
                            reference_low=low,
                            reference_high=high,
                            reference_text=text,
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
