"""The deterministic report statements, word for word (German, provider version narr-2).

A released statement is what the patient reads, so the wording is pinned. A statement gives
the value the way the source wrote it — name, value and unit verbatim — then the reference
interval the platform holds for it, the position relative to that interval only when the
value lies outside, and the deterministic change. What the platform adds is named: a unit
conversion appears beside the source value, never instead of it. A day-only sampling date
stays a day; a timed one is written as wall-clock time in the clinic's zone, with the zone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.evidence import _label
from hadp_api.modules.reports.narrative import DeterministicNarrativeProvider, EvidenceItem

BERLIN = ZoneInfo("Europe/Berlin")


def _item(
    source: str,
    low: str | None = None,
    high: str | None = None,
    *,
    source_unit: str | None = "mmol/L",
    value: str | None = "same",
    unit: str | None = "same",
    converted: bool = False,
    delta: str | None = None,
    name: str = "LDL Cholesterol",
    label: str = "10.06.2025",
) -> EvidenceItem:
    """`source`/`source_unit` are what the source wrote; `value`/`unit` the normalized form
    ("same" = the source's own, None = the value could not be normalized)."""
    return EvidenceItem(
        observation_id=uuid.uuid4(),
        metric_code="13457-7",
        name=name,
        original_value=source,
        original_unit=source_unit,
        value=Decimal(source.replace(",", ".")) if value == "same" else _dec(value),
        unit=source_unit if unit == "same" else unit,
        converted=converted,
        reference_low=_dec(low),
        reference_high=_dec(high),
        observed_at_label=label,
        delta_vs_previous=_dec(delta),
        previous_observation_id=uuid.uuid4() if delta is not None else None,
    )


def _dec(text: str | None) -> Decimal | None:
    return Decimal(text) if text is not None else None


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
            "LDL Cholesterol am 10.06.2025: 2.8 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L.",
            id="within the interval: no position sentence",
        ),
        pytest.param(
            _item("3.6", "0", "3.0"),
            "LDL Cholesterol am 10.06.2025: 3.6 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L. "
            "Der Wert liegt über dem Referenzintervall der Quelle.",
            id="above",
        ),
        pytest.param(
            _item("0.2", "0.5", "3.0"),
            "LDL Cholesterol am 10.06.2025: 0.2 mmol/L. "
            "Referenzintervall der Quelle: 0.5 bis 3 mmol/L. "
            "Der Wert liegt unter dem Referenzintervall der Quelle.",
            id="below",
        ),
        pytest.param(
            _item("3.0", "0", "3.0"),
            "LDL Cholesterol am 10.06.2025: 3.0 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L.",
            id="exactly on a bound is not outside",
        ),
        pytest.param(
            _item("2,80", "0", "3.0", source_unit="mmol/l", unit="mmol/L"),
            "LDL Cholesterol am 10.06.2025: 2,80 mmol/l. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L.",
            id="the source's own notation is kept: decimal comma, trailing zero, unit spelling",
        ),
        pytest.param(
            _item(
                "130",
                "0",
                "2.9997368",
                source_unit="mg/dL",
                value="3.361774",
                unit="mmol/L",
                converted=True,
            ),
            "LDL Cholesterol am 10.06.2025: 130 mg/dL (umgerechnet: 3.361774 mmol/L). "
            "Referenzintervall der Quelle (umgerechnet): 0 bis 2.9997368 mmol/L. "
            "Der Wert liegt über dem Referenzintervall der Quelle.",
            id="a converted unit: the source value first, the conversion named",
        ),
        pytest.param(
            _item("85", source_unit="ng/mL", value=None, unit=None, name="Ferritin"),
            "Ferritin am 10.06.2025: 85 ng/mL.",
            id="not normalized (unknown analyte): the source value, never 'no value'",
        ),
        pytest.param(
            _item("1.0", None, "3.0"),
            "LDL Cholesterol am 10.06.2025: 1.0 mmol/L. "
            "Referenzintervall der Quelle: obere Grenze 3 mmol/L.",
            id="only an upper bound is held: named, nothing claimed about a lower one",
        ),
        pytest.param(
            _item("4.0", None, "3.0"),
            "LDL Cholesterol am 10.06.2025: 4.0 mmol/L. "
            "Referenzintervall der Quelle: obere Grenze 3 mmol/L. "
            "Der Wert liegt über dem Referenzintervall der Quelle.",
            id="upper bound only, exceeded",
        ),
        pytest.param(
            _item("3.0", None, "3.0"),
            "LDL Cholesterol am 10.06.2025: 3.0 mmol/L. "
            "Referenzintervall der Quelle: obere Grenze 3 mmol/L.",
            id="upper bound only, exactly on it: not outside",
        ),
        pytest.param(
            _item("1.0", "3.9", None),
            "LDL Cholesterol am 10.06.2025: 1.0 mmol/L. "
            "Referenzintervall der Quelle: untere Grenze 3.9 mmol/L. "
            "Der Wert liegt unter dem Referenzintervall der Quelle.",
            id="lower bound only, undercut",
        ),
        pytest.param(
            _item("2.8"),
            "LDL Cholesterol am 10.06.2025: 2.8 mmol/L.",
            id="no interval: nothing is said about one",
        ),
        pytest.param(
            _item("2.8", "0", "3.0", delta="-0.8"),
            "LDL Cholesterol am 10.06.2025: 2.8 mmol/L. "
            "Referenzintervall der Quelle: 0 bis 3 mmol/L. "
            "Veränderung gegenüber der vorherigen vergleichbaren Messung: -0.8 mmol/L.",
            id="a decrease",
        ),
        pytest.param(
            _item("3.6", delta="0.8"),
            "LDL Cholesterol am 10.06.2025: 3.6 mmol/L. "
            "Veränderung gegenüber der vorherigen vergleichbaren Messung: +0.8 mmol/L.",
            id="an increase carries its sign",
        ),
        pytest.param(
            _item("3.6", delta="0.0"),
            "LDL Cholesterol am 10.06.2025: 3.6 mmol/L. "
            "Veränderung gegenüber der vorherigen vergleichbaren Messung: 0 mmol/L.",
            id="no change",
        ),
        pytest.param(
            _item("38", "35", "45", source_unit=None),
            "LDL Cholesterol am 10.06.2025: 38. Referenzintervall der Quelle: 35 bis 45.",
            id="no unit: no stray space",
        ),
        pytest.param(
            _item("250", source_unit="10*9/L", name="Thrombozyten"),
            "Thrombozyten am 10.06.2025: 250 10*9/L.",
            id="a plural analyte name reads correctly (no verb to agree with)",
        ),
        pytest.param(
            _item("2.8", label="10.06.2025 um 08:30 Uhr (CEST)"),
            "LDL Cholesterol am 10.06.2025 um 08:30 Uhr (CEST): 2.8 mmol/L.",
            id="timed sample",
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


NEW_YORK_SUMMER = timezone(timedelta(hours=-4))


@pytest.mark.parametrize(
    ("observed_at", "date_only", "expected"),
    [
        # A source that named only a day: the day, and no invented time.
        (datetime(2025, 6, 10, tzinfo=UTC), True, "10.06.2025"),
        # The same stored day read through a database session west of UTC is still that day.
        (datetime(2025, 6, 9, 20, tzinfo=NEW_YORK_SUMMER), True, "10.06.2025"),
        # Summer time (UTC+2) and winter time (UTC+1), each with its zone.
        (datetime(2025, 6, 10, 6, 30, tzinfo=UTC), False, "10.06.2025 um 08:30 Uhr (CEST)"),
        (datetime(2025, 1, 15, 7, 5, tzinfo=UTC), False, "15.01.2025 um 08:05 Uhr (CET)"),
        # Late evening in UTC is already the next day in the clinic's zone.
        (datetime(2025, 1, 15, 23, 30, tzinfo=UTC), False, "16.01.2025 um 00:30 Uhr (CET)"),
        # The hour the clocks go back happens twice: the zone tells the two apart.
        (datetime(2025, 10, 26, 0, 30, tzinfo=UTC), False, "26.10.2025 um 02:30 Uhr (CEST)"),
        (datetime(2025, 10, 26, 1, 30, tzinfo=UTC), False, "26.10.2025 um 02:30 Uhr (CET)"),
        # Seconds the source gave are kept.
        (datetime(2025, 6, 10, 6, 30, 59, tzinfo=UTC), False, "10.06.2025 um 08:30:59 Uhr (CEST)"),
    ],
)
def test_sampling_time_label(observed_at: datetime, date_only: bool, expected: str) -> None:
    assert _label(_observation(observed_at, date_only=date_only), BERLIN) == expected
