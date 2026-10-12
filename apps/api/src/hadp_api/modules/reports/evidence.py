"""Evidence payload builder + statement evidence validation.

The evidence payload is built ONLY from published observations that still stand. Statement
validation enforces the meaningful-approval rule: every statement must reference at least one
observation that is viewable (exists, published, belongs to this patient/tenant) and that no
published laboratory correction has replaced. A statement whose evidence is not viewable, or
rests on a replaced value, cannot be approved.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.modules.enums import KpiMeasurementClass
from hadp_api.modules.imports.normalize import is_plain_number, unit_was_converted
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.language import restricted_terms
from hadp_api.modules.reports.narrative import EvidenceItem

# What a statement may quote from a source. The value and unit columns hold whatever the
# source (a file, a person typing) put there — up to 120 / 60 characters. A statement becomes
# patient-facing, so only a result that is a number is repeated; a text result, a flagged
# value ("12,4 H") or free text is mentioned without its wording (see narrative.py).
_COMPARATOR = re.compile(r"(?:<=|>=|<|>|≤|≥)[ ]?")
# A unit: one token of at most 20 characters, no whitespace ("mmol/L", "10*9/L", "mm[Hg]",
# "Mio./µl"), with at least one letter or % ‰ ° (a unit of digits would change how the value
# reads: "5 000"). It may be a word — "Schritte" and "Punkte" are units — so the token is
# also refused when it carries a restricted intended-use term; that list knows English stems
# only. What remains is the same residual as the analyte name: a short token a clinician has
# published from the review queue.
_UNIT = re.compile(r"[A-Za-zÄÖÜäöüßµμ°%‰/*^.,·×\[\]()0-9²³-]{1,20}")
_UNIT_SIGN = re.compile(r"[A-Za-zÄÖÜäöüßµμ°%‰]")


def quotable_result(
    original_value: str, original_unit: str | None
) -> tuple[str | None, str | None]:
    """The source's value and unit as written if a statement may quote them, else (None, None)."""
    value = original_value.strip()
    unit = (original_unit or "").strip() or None
    comparator = _COMPARATOR.match(value)
    number = value[comparator.end() :] if comparator else value
    if not is_plain_number(number) or number != number.strip():
        return None, None
    if unit is not None and (
        not _UNIT.fullmatch(unit) or not _UNIT_SIGN.search(unit) or restricted_terms([unit])
    ):
        return None, None
    return value, unit


def decimal_comma(original_value: str, reference_text: str | None) -> bool:
    """Whether the source writes decimals with a comma: read from the value, and when the
    value has no decimal mark, from the reference text beside it. Undecided means a point."""
    for text in (original_value, reference_text or ""):
        if re.search(r"\d,\d", text):
            return True
        if re.search(r"\d\.\d", text):
            return False
    return False


def _utc_offset(moment: datetime) -> str:
    """The offset as text — "UTC+2", "UTC-7", "UTC+5:45", "UTC" — the same in every zone."""
    offset = moment.utcoffset()
    seconds = int(offset.total_seconds()) if offset is not None else 0
    hours, rest = divmod(abs(seconds) // 60, 60)  # whole minutes, toward zero on both sides
    if not hours and not rest:
        return "UTC"
    return f"UTC{'+' if seconds > 0 else '-'}{hours}" + (f":{rest:02d}" if rest else "")


def _label(observation: Observation, zone: ZoneInfo) -> str:
    """When the value was sampled, as a de-DE report states it after "am".

    A source that named only a day keeps the day — no time is invented; the day is read in
    UTC, where it is stored (whatever zone the database session reports). Otherwise the
    instant is written as wall-clock time in the clinic's zone, with its offset from UTC:
    the text then names one instant even in the hour a clock change repeats, and stays
    readable if the configured zone ever changes.
    """
    if observation.observed_at_is_date_only:
        return f"{observation.observed_at.astimezone(UTC).date():%d.%m.%Y}"
    local = observation.observed_at.astimezone(zone)
    clock = f"{local:%H:%M:%S}" if local.second else f"{local:%H:%M}"
    return f"{local:%d.%m.%Y} um {clock} Uhr ({_utc_offset(local)})"


def build_evidence_payload(db: Session, patient_id: uuid.UUID) -> list[EvidenceItem]:
    timeline = obs_service.build_timeline(db, patient_id)
    zone = ZoneInfo(get_settings().lab_local_timezone)
    items: list[EvidenceItem] = []
    by_id = {o.id: o for o in obs_service.list_observations(db, patient_id)}
    for point in timeline:
        obs = by_id[point.observation_id]
        if point.review_status.value != "published":
            continue
        # A value a published correction has replaced is history, not evidence for a new draft.
        if point.superseded_by_observation_id is not None:
            continue
        # Derived values are NOT auto-cited in the report draft (ADR-0004 Slice 4 / §0): they would
        # otherwise read as measured. Labelled inclusion is deferred to the derived-UI slice.
        if obs.source_category == KpiMeasurementClass.DERIVED:
            continue
        source_value, source_unit = quotable_result(obs.original_value, obs.original_unit)
        items.append(
            EvidenceItem(
                observation_id=point.observation_id,
                metric_code=point.metric_code,
                name=point.original_name,
                source_value=source_value,
                source_unit=source_unit,
                decimal_comma=decimal_comma(obs.original_value, obs.reference_text),
                value=point.value,
                unit=point.unit,
                converted=unit_was_converted(obs.original_unit, obs.normalized_unit),
                reference_low=point.reference_low,
                reference_high=point.reference_high,
                observed_at_label=_label(obs, zone),
                delta_vs_previous=point.delta_vs_previous,
                previous_observation_id=point.previous_observation_id,
            )
        )
    return items


def viewable_observation_ids(db: Session, patient_id: uuid.UUID) -> set[uuid.UUID]:
    """Observation IDs that may back a statement: published, for this patient (RLS-scoped)."""
    return {o.id for o in obs_service.list_published(db, patient_id)}


def validate_statements(db: Session, patient_id: uuid.UUID, statements: list[dict]) -> None:
    """Raise ValueError if any statement lacks viewable evidence.

    Callers translate this into the appropriate API error. Used on draft generation,
    editing, and (strictly) on approval.
    """
    viewable = viewable_observation_ids(db, patient_id)
    replaced = obs_service.not_standing(db, patient_id)
    for stmt in statements:
        ids = stmt.get("evidence_observation_ids") or []
        if not ids:
            raise ValueError(f"statement {stmt.get('id')!r} has no evidence")
        resolved = {uuid.UUID(str(i)) for i in ids}
        corrected = sorted(str(i) for i in resolved & replaced)
        if corrected:
            raise ValueError(
                f"statement {stmt.get('id')!r} references evidence a laboratory correction "
                f"has replaced: {corrected}"
            )
        missing = resolved - viewable
        if missing:
            missing_ids = sorted(str(m) for m in missing)
            raise ValueError(
                f"statement {stmt.get('id')!r} references non-viewable evidence: {missing_ids}"
            )
