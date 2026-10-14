"""When two observations were sampled at the same time.

One definition for the matcher (repeated and corrected values) and the timeline (no change is
computed between two values of one sample). An observation carries either an instant or, when
the source named only a date, that calendar day (`observed_at_is_date_only`).
"""

from __future__ import annotations

from datetime import UTC, date
from zoneinfo import ZoneInfo

from hadp_api.modules.observations.models import Observation


def same_instant(a: Observation, b: Observation) -> bool:
    """Both name the same instant, or both name the same day and nothing more."""
    return (
        a.observed_at_is_date_only == b.observed_at_is_date_only and a.observed_at == b.observed_at
    )


def sampling_day(observation: Observation, zone: ZoneInfo) -> date:
    """The day the value was sampled, as the laboratory's zone reads it. A source that named
    only a day keeps that day (stored at UTC midnight, it is read in UTC)."""
    if observation.observed_at_is_date_only:
        return observation.observed_at.astimezone(UTC).date()
    return observation.observed_at.astimezone(zone).date()


def same_sampling_time(a: Observation, b: Observation, zone: ZoneInfo) -> bool:
    """The same instant — or, if only one side names a time of day, the same day in the
    laboratory's zone. The second case is a "may be the same sample", never a certainty."""
    if a.observed_at_is_date_only == b.observed_at_is_date_only:
        return a.observed_at == b.observed_at
    return sampling_day(a, zone) == sampling_day(b, zone)
