"""Shared types for the structured-source readers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Column limits of the observation's immutable source representation: a value that does not fit
# is refused, never truncated.
MAX_NAME = 200
MAX_VALUE = 120
MAX_UNIT = 60
MAX_REFERENCE_TEXT = 200
MAX_BOUND = 60
# A single laboratory report beyond this size is a different kind of file.
MAX_VALUES = 2000

# Reader-supplied review reasons (closed set; the review queue labels them). They describe the
# SOURCE's own status of a result — a human decides, the reader never does.
AMBIGUOUS_LOCAL_TIME = "ambiguous_local_time"
PRELIMINARY_REPORT = "preliminary_report"
PREVIOUSLY_REPORTED = "previously_reported"
CORRECTED_RESULT = "corrected_result"
# The laboratory attached a note to this result that the pipeline cannot carry.
SOURCE_COMMENT = "source_comment"
# The source gives several reference ranges, or one in another unit than the value.
AMBIGUOUS_REFERENCE = "ambiguous_reference"
# The source gives several values for one test and does not single one out.
MULTIPLE_RESULT_VALUES = "multiple_result_values"

# Why a result in the file was NOT imported (closed set). Recorded and counted, never dropped
# silently: the pipeline carries numeric observations only.
TEXT_RESULT = "text_result"
# The same measurement written a second time in another unit; the carried one names the unit.
ALTERNATE_VALUE = "alternate_unit_value"
RESULT_PENDING = "result_pending"
NO_RESULT = "no_result"
# The source names no sampling date; the report or measurement date is never used instead.
NO_SAMPLING_DATE = "no_sampling_date"
# A result kind this reader does not carry (microbiology, cytology, …).
UNSUPPORTED_RESULT_TYPE = "unsupported_result_type"


class SourceParseError(Exception):
    """A source file that cannot be read structurally. Nothing is imported from it.

    `detail` names positions and field names only — never file content.
    """

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class ParsedValue:
    original_name: str
    original_value: str
    original_unit: str | None
    observed_at: datetime
    observed_at_is_date_only: bool
    source_record_locator: str
    reference_low: str | None = None
    reference_high: str | None = None
    reference_text: str | None = None
    review_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class NotImported:
    source_record_locator: str
    reason: str


@dataclass(frozen=True)
class ParsedDocument:
    parser_name: str
    parser_version: str
    values: list[ParsedValue] = field(default_factory=list)
    not_imported: list[NotImported] = field(default_factory=list)
    # Only what the patient guard needs — no name or identifier leaves the reader.
    patient_date_of_birth: date | None = None


def plausible_day(year: int, month: int, day: int, locator: str) -> date:
    """Build a calendar date, refusing one that cannot be a real sampling or birth date.

    A date before 1900 or after tomorrow is almost always a misread layout (day and year
    swapped), so it is refused instead of being stored.
    """
    try:
        value = date(year, month, day)
    except ValueError as exc:
        raise SourceParseError("unsupported_date", f"{locator}: not a calendar date") from exc
    if value.year < 1900 or value > datetime.now(UTC).date() + timedelta(days=1):
        raise SourceParseError("implausible_date", f"{locator}: the date is not plausible")
    return value


def date_only(day: date) -> datetime:
    """A date-only source value stays date-only: midnight UTC as the storage convention."""
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def local_instant(day: date, clock: time, zone: ZoneInfo) -> tuple[datetime, bool]:
    """Resolve a laboratory-local wall-clock time to a UTC instant.

    Returns (instant, ambiguous). `ambiguous` is true when the wall-clock time does not name
    exactly one instant in `zone` — it falls into a daylight-saving gap or repeats at the
    change back — so the row is sent to review instead of being published as if certain.
    """
    naive = datetime.combine(day, clock)
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    ambiguous = first.utcoffset() != second.utcoffset()
    return first.astimezone(UTC), ambiguous


_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def check_text(value: str | None, limit: int, field_name: str, locator: str) -> None:
    """Refuse a field that cannot be stored verbatim: too long, or with control characters."""
    if value is None:
        return
    if len(value) > limit:
        raise SourceParseError(
            "field_too_long", f"{locator}: {field_name} exceeds {limit} characters"
        )
    if _CONTROL.search(value):
        raise SourceParseError(
            "unsupported_character", f"{locator}: {field_name} contains a control character"
        )
