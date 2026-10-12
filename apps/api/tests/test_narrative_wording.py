"""The deterministic report statements, word for word (German, provider version narr-2).

A released statement is what the patient reads, so the wording is pinned: the measured value
with its unit and sampling time, the source's reference interval, the position relative to it
only when the value lies outside, and the deterministic change — nothing else. A day-only
sampling date stays a day; a timed one is written as wall-clock time in the clinic's zone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.evidence import _label
from hadp_api.modules.reports.narrative import DeterministicNarrativeProvider, EvidenceItem

BERLIN = ZoneInfo("Europe/Berlin")


def _item(
    value: str | None,
    low: str | None = None,
    high: str | None = None,
    *,
    delta: str | None = None,
    unit: str | None = "mmol/L",
    label: str = "10.06.2025",
) -> EvidenceItem:
    return EvidenceItem(
        observation_id=uuid.uuid4(),
        metric_code="13457-7",
        name="LDL Cholesterol",
        value=Decimal(value) if value is not None else None,
        unit=unit,
        reference_low=Decimal(low) if low is not None else None,
        reference_high=Decimal(high) if high is not None else None,
        observed_at_label=label,
        delta_vs_previous=Decimal(delta) if delta is not None else None,
        previous_observation_id=uuid.uuid4() if delta is not None else None,
    )


def _text(item: EvidenceItem) -> str:
    (statement,) = DeterministicNarrativeProvider().generate([item])
    return statement.text


def test_provider_version_marks_the_german_wording() -> None:
    provider = DeterministicNarrativeProvider()
    assert (provider.name, provider.version) == ("deterministic", "narr-2")


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        pytest.param(
            _item("2.8", "0", "3.0"),
            "LDL Cholesterol lag am 10.06.2025 bei 2.8 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L.",
            id="within the interval: no position sentence",
        ),
        pytest.param(
            _item("3.6", "0", "3.0"),
            "LDL Cholesterol lag am 10.06.2025 bei 3.6 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L. "
            "Der Wert liegt über dem Referenzintervall der Quelle.",
            id="above",
        ),
        pytest.param(
            _item("0.2", "0.5", "3.0"),
            "LDL Cholesterol lag am 10.06.2025 bei 0.2 mmol/L. "
            "Referenzintervall der Quelle: 0.5 bis 3 mmol/L. "
            "Der Wert liegt unter dem Referenzintervall der Quelle.",
            id="below",
        ),
        pytest.param(
            _item("1.0", None, "3.0"),
            "LDL Cholesterol lag am 10.06.2025 bei 1 mmol/L. "
            "Referenzintervall der Quelle: bis 3 mmol/L.",
            id="upper bound only, not exceeded: no position sentence",
        ),
        pytest.param(
            _item("4.0", None, "3.0"),
            "LDL Cholesterol lag am 10.06.2025 bei 4 mmol/L. "
            "Referenzintervall der Quelle: bis 3 mmol/L. "
            "Der Wert liegt über dem Referenzintervall der Quelle.",
            id="upper bound only, exceeded",
        ),
        pytest.param(
            _item("1.0", "3.9", None),
            "LDL Cholesterol lag am 10.06.2025 bei 1 mmol/L. "
            "Referenzintervall der Quelle: ab 3.9 mmol/L. "
            "Der Wert liegt unter dem Referenzintervall der Quelle.",
            id="lower bound only, undercut",
        ),
        pytest.param(
            _item("2.8"),
            "LDL Cholesterol lag am 10.06.2025 bei 2.8 mmol/L.",
            id="no interval: nothing is said about one",
        ),
        pytest.param(
            _item("2.8", "0", "3.0", delta="-0.8"),
            "LDL Cholesterol lag am 10.06.2025 bei 2.8 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L. "
            "Veränderung gegenüber der vorherigen vergleichbaren Messung: -0.8 mmol/L.",
            id="with a change",
        ),
        pytest.param(
            _item("38", "35", "45", unit=None),
            "LDL Cholesterol lag am 10.06.2025 bei 38. Referenzintervall der Quelle: 35 bis 45.",
            id="no unit: no stray space",
        ),
        pytest.param(
            _item("2.8", label="10.06.2025 um 08:30 Uhr"),
            "LDL Cholesterol lag am 10.06.2025 um 08:30 Uhr bei 2.8 mmol/L.",
            id="timed sample",
        ),
        pytest.param(
            _item(None, "0", "3.0"),
            "Für LDL Cholesterol ist am 10.06.2025 kein Zahlenwert erfasst. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L.",
            id="no numeric value: said, not invented",
        ),
    ],
)
def test_statement_wording(item: EvidenceItem, expected: str) -> None:
    assert _text(item) == expected


def test_a_change_cites_both_observations() -> None:
    item = _item("2.8", "0", "3.0", delta="-0.8")
    (statement,) = DeterministicNarrativeProvider().generate([item])
    assert statement.evidence_observation_ids == [
        item.observation_id,
        item.previous_observation_id,
    ]


def _observation(observed_at: datetime, *, date_only: bool) -> Observation:
    return Observation(observed_at=observed_at, observed_at_is_date_only=date_only)


@pytest.mark.parametrize(
    ("observed_at", "date_only", "expected"),
    [
        # A source that named only a day: the day, and no invented time.
        (datetime(2025, 6, 10, tzinfo=UTC), True, "10.06.2025"),
        # Summer time (UTC+2) and winter time (UTC+1).
        (datetime(2025, 6, 10, 6, 30, tzinfo=UTC), False, "10.06.2025 um 08:30 Uhr"),
        (datetime(2025, 1, 15, 7, 5, tzinfo=UTC), False, "15.01.2025 um 08:05 Uhr"),
        # Late evening in UTC is already the next day in the clinic's zone.
        (datetime(2025, 1, 15, 23, 30, tzinfo=UTC), False, "16.01.2025 um 00:30 Uhr"),
    ],
)
def test_sampling_time_label(observed_at: datetime, date_only: bool, expected: str) -> None:
    assert _label(_observation(observed_at, date_only=date_only), BERLIN) == expected
