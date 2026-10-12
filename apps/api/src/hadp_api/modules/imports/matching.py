"""Repeated and corrected values: match an incoming value against what the patient holds.

A laboratory sends the same measurement more than once — a final report repeats the values of
a partial one, a file is sent again, a result is corrected. Without matching, each of these is
imported as one more observation. This module decides, per incoming value, one of three things
(CLAUDE.md "Corrected reports"; the rule is documented in docs/product/LAB_IMPORT_FORMATS.md):

- **Not imported twice.** Nothing distinguishes it from a value that stands, and whatever is
  decided about that value is what would be decided about this one.
- **Proposed correction.** The source marks it corrected and exactly one held value, sampled
  at exactly that time, can be the one it corrects. The link is only a proposal: it takes
  effect when a human publishes it.
- **Held for review.** Any other value for an analyte and sampling time that is already
  occupied. A human decides; nothing is superseded automatically.

"The same measurement" is deliberately narrow: same patient, same analyte, same sampling time.
The matcher never looks at magnitudes and never reaches across patients.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import KpiMeasurementClass, ReviewStatus
from hadp_api.modules.imports.models import ReviewItem
from hadp_api.modules.imports.parsers.base import (
    AMBIGUOUS_LOCAL_TIME,
    AMBIGUOUS_REFERENCE,
    CORRECTED_RESULT,
    MULTIPLE_RESULT_VALUES,
    PRELIMINARY_REPORT,
    PREVIOUSLY_REPORTED,
    SOURCE_COMMENT,
)
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.sampling import same_instant, same_sampling_time

# Why a value in the input was not imported: the patient already holds exactly this value.
DUPLICATE_VALUE = "duplicate_value"
# Review reasons (closed set; the review queue labels them).
# Another value for this analyte and sampling time is already held.
POSSIBLE_DUPLICATE = "possible_duplicate"
# The source marks the value corrected, but several held values could be the one it corrects.
AMBIGUOUS_CORRECTION = "ambiguous_correction"

# Reader-supplied reasons that describe the SOURCE's own status of a result. A value that
# carries one is never dropped as a repeat. "Previously reported" is left out on purpose: it
# is the laboratory saying the value is a repeat.
_SOURCE_STATUS = frozenset(
    {
        AMBIGUOUS_LOCAL_TIME,
        PRELIMINARY_REPORT,
        CORRECTED_RESULT,
        SOURCE_COMMENT,
        AMBIGUOUS_REFERENCE,
        MULTIPLE_RESULT_VALUES,
    }
)


@dataclass(frozen=True)
class Match:
    # The held observation this value repeats — the value is then not imported.
    duplicate_of: Observation | None = None
    # The held observation this value would replace once a human publishes it.
    supersedes: Observation | None = None
    review_reasons: tuple[str, ...] = ()


def lock_patient_record(db: Session, patient_id: uuid.UUID) -> None:
    """Serialize matching per patient for the rest of the transaction.

    Two imports for one patient that ran side by side would each miss the other's rows.
    """
    key = func.hashtextextended(f"patient-observations:{patient_id}", 0)
    db.execute(select(func.pg_advisory_xact_lock(key)))


def _name_key(observation: Observation) -> str:
    return " ".join(observation.original_name.split()).casefold()


def _same_analyte(a: Observation, b: Observation) -> bool:
    if _name_key(a) == _name_key(b):
        return True
    if a.metric_code is not None and a.metric_code == b.metric_code:
        return True
    return a.kpi_code is not None and a.kpi_code == b.kpi_code


def same_measurement(a: Observation, b: Observation, zone: ZoneInfo) -> bool:
    """Same analyte and same sampling time (the patient is the caller's concern).

    If only one side names a time of day, the two may still be the same sample, so a human
    gets to look. Such a pair is never treated as certain — nothing is dropped or linked on it.
    """
    return _same_analyte(a, b) and same_sampling_time(a, b, zone)


def _text(value: str | None) -> str:
    return (value or "").strip()


def _same_representation(a: Observation, b: Observation) -> bool:
    """Everything the system stores about the two values is equal."""
    return (
        _name_key(a) == _name_key(b)
        and same_instant(a, b)
        and _text(a.original_value) == _text(b.original_value)
        and _text(a.original_unit) == _text(b.original_unit)
        and _text(a.reference_text) == _text(b.reference_text)
        and a.reference_low == b.reference_low
        and a.reference_high == b.reference_high
    )


class PatientRecord:
    """The values a patient already holds, loaded once per import.

    Rows accepted during the import are added as they go, so a value that meets another one
    of the same file is held for review like any other.
    """

    def __init__(self, db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID, zone: ZoneInfo):
        self._zone = zone
        # Derived values are computed, not reported by a source: never a match.
        self._held: list[Observation] = [
            o
            for o in db.execute(
                select(Observation).where(
                    Observation.tenant_id == tenant_id,
                    Observation.patient_id == patient_id,
                )
            ).scalars()
            if o.source_category != KpiMeasurementClass.DERIVED
        ]
        self._replaced = set(obs_service.superseded_by(db, patient_id))
        self._this_import: set[uuid.UUID] = set()
        # Every review reason a held value was ever given (resolved or not).
        self._reasons: dict[uuid.UUID, set[str]] = {}
        for observation_id, reason in db.execute(
            select(ReviewItem.observation_id, ReviewItem.reason)
            .join(Observation, ReviewItem.observation_id == Observation.id)
            .where(Observation.tenant_id == tenant_id, Observation.patient_id == patient_id)
        ).tuples():
            if observation_id is not None:
                self._reasons.setdefault(observation_id, set()).add(reason)

    def _repeats(self, incoming: Observation, held: Observation, source_reasons: set[str]) -> bool:
        """Nothing distinguishes `incoming` from `held`, and it would share `held`'s fate.

        `held` stands (the caller's filter). The remaining conditions make sure that not
        importing the copy loses nothing a human would have wanted to see.
        """
        if not _same_representation(held, incoming):
            return False
        # Twice in one file is more likely a second measurement than a file sent again.
        if held.id in self._this_import:
            return False
        reasons = self._reasons.get(held.id, set())
        # A value that came with a laboratory status or note is never a plain repeat.
        if reasons & _SOURCE_STATUS:
            return False
        # A copy still waiting as "already reported" may be rejected as a mere repeat: only
        # another such copy may hide behind it, never the publishable original.
        return not (
            held.review_status == ReviewStatus.PENDING
            and PREVIOUSLY_REPORTED in reasons
            and PREVIOUSLY_REPORTED not in source_reasons
        )

    def _has_open_proposal(self, target: Observation) -> bool:
        return any(
            held.supersedes_observation_id == target.id
            and held.review_status == ReviewStatus.PENDING
            for held in self._held
        )

    def match(self, incoming: Observation, source_reasons: tuple[str, ...]) -> Match:
        series = [held for held in self._held if same_measurement(held, incoming, self._zone)]
        if not series:
            return Match()
        # A value a reviewer rejected, or a published correction replaced, does not stand:
        # the same number arriving again is a human's call, never a silent drop.
        standing = [
            o
            for o in series
            if o.review_status != ReviewStatus.REJECTED and o.id not in self._replaced
        ]
        given = set(source_reasons)

        if not (given & _SOURCE_STATUS):
            for held in standing:
                if self._repeats(incoming, held, given):
                    return Match(duplicate_of=held)

        if CORRECTED_RESULT in given:
            # Only a value sampled at exactly this time can be THE corrected one; a value
            # that merely shares the day cannot. And a value is proposed for replacement at
            # most once: a second correction waits for a human without a link.
            if (
                len(standing) == 1
                and same_instant(standing[0], incoming)
                and not self._has_open_proposal(standing[0])
            ):
                return Match(supersedes=standing[0])
            if standing:
                return Match(review_reasons=(AMBIGUOUS_CORRECTION,))
            return Match()
        return Match(review_reasons=(POSSIBLE_DUPLICATE,))

    def add(self, observation: Observation, review_reasons: list[str]) -> None:
        self._held.append(observation)
        self._this_import.add(observation.id)
        self._reasons[observation.id] = set(review_reasons)
