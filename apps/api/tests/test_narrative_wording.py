"""The deterministic report statements, word for word (German, provider version narr-2).

A released statement is what the patient reads, so the wording is pinned. A statement gives
a numeric result the way the source wrote it — value and unit verbatim — then the reference
interval the platform holds for it, the position relative to that interval only when the
value lies outside, and the deterministic change. What the platform adds is named: a unit
conversion appears beside the source value, never instead of it. Numbers the platform writes
follow the source value's decimal mark. A result that is not a number is mentioned, never
quoted. A day-only sampling date stays a day; a timed one is written as wall-clock time in
the clinic's zone, with its offset from UTC.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.evidence import _label, quotable_result
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
        source_value=source,
        source_unit=source_unit,
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
            _item("2,80", "0.5", "3.0", source_unit="mmol/l", unit="mmol/L"),
            "LDL Cholesterol am 10.06.2025: 2,80 mmol/l. "
            "Referenzintervall der Quelle: 0,5 bis 3 mmol/l.",
            id="the source's own notation is kept: decimal comma, trailing zero, unit spelling",
        ),
        pytest.param(
            _item("5,55", "3.885", "5.55", source_unit="mmol/l", unit="mmol/L", delta="0.3"),
            "LDL Cholesterol am 10.06.2025: 5,55 mmol/l. "
            "Referenzintervall der Quelle: 3,885 bis 5,55 mmol/l. "
            "Veränderung gegenüber der vorherigen vergleichbaren Messung: +0,3 mmol/l.",
            id="one statement never mixes decimal marks: the platform's numbers follow the source",
        ),
        pytest.param(
            _item("<0.5", source_unit="mU/L", value=None, unit=None, name="TSH"),
            "TSH am 10.06.2025: <0.5 mU/L.",
            id="a comparator result is a numeric result",
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
            EvidenceItem(
                observation_id=uuid.uuid4(),
                metric_code=None,
                name="HIV-1/2 Screening",
                source_value=None,
                source_unit=None,
                value=None,
                unit=None,
                converted=False,
                reference_low=None,
                reference_high=None,
                observed_at_label="10.06.2025",
            ),
            "Für HIV-1/2 Screening liegt am 10.06.2025 ein Ergebnis der Quelle vor, "
            "das hier nicht im Wortlaut wiedergegeben wird.",
            id="a result that may not be quoted is mentioned, never repeated",
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
            _item("2.8", label="10.06.2025 um 08:30 Uhr (UTC+2)"),
            "LDL Cholesterol am 10.06.2025 um 08:30 Uhr (UTC+2): 2.8 mmol/L.",
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
        # Summer time and winter time, each with its offset.
        (datetime(2025, 6, 10, 6, 30, tzinfo=UTC), False, "10.06.2025 um 08:30 Uhr (UTC+2)"),
        (datetime(2025, 1, 15, 7, 5, tzinfo=UTC), False, "15.01.2025 um 08:05 Uhr (UTC+1)"),
        # Late evening in UTC is already the next day in the clinic's zone.
        (datetime(2025, 1, 15, 23, 30, tzinfo=UTC), False, "16.01.2025 um 00:30 Uhr (UTC+1)"),
        # The hour the clocks go back happens twice: the offset tells the two apart.
        (datetime(2025, 10, 26, 0, 30, tzinfo=UTC), False, "26.10.2025 um 02:30 Uhr (UTC+2)"),
        (datetime(2025, 10, 26, 1, 30, tzinfo=UTC), False, "26.10.2025 um 02:30 Uhr (UTC+1)"),
        # Seconds the source gave are kept.
        (datetime(2025, 6, 10, 6, 30, 59, tzinfo=UTC), False, "10.06.2025 um 08:30:59 Uhr (UTC+2)"),
    ],
)
def test_sampling_time_label(observed_at: datetime, date_only: bool, expected: str) -> None:
    assert _label(_observation(observed_at, date_only=date_only), BERLIN) == expected


@pytest.mark.parametrize(
    ("zone", "expected"),
    [
        ("UTC", "10.06.2025 um 06:30 Uhr (UTC)"),
        ("America/Los_Angeles", "09.06.2025 um 23:30 Uhr (UTC-7)"),
        ("Asia/Kathmandu", "10.06.2025 um 12:15 Uhr (UTC+5:45)"),
        ("America/St_Johns", "10.06.2025 um 04:00 Uhr (UTC-2:30)"),
    ],
)
def test_the_offset_is_written_the_same_way_in_every_zone(zone: str, expected: str) -> None:
    sample = _observation(datetime(2025, 6, 10, 6, 30, tzinfo=UTC), date_only=False)
    assert _label(sample, ZoneInfo(zone)) == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("85", "ng/mL", ("85", "ng/mL")),
        (" 2,80 ", " mmol/l ", ("2,80", "mmol/l")),
        ("<0.5", "mU/L", ("<0.5", "mU/L")),
        ("≥ 100", None, ("≥ 100", None)),
        ("1e3", "10*9/L", ("1e3", "10*9/L")),
        ("122", "mm[Hg]", ("122", "mm[Hg]")),
        ("5.4", "%", ("5.4", "%")),
        ("34", "ml/kg/min", ("34", "ml/kg/min")),
        ("90", "", ("90", None)),
        # Not a number: a text result, a flagged value, free text, a second line, markup.
        ("reaktiv", None, (None, None)),
        ("12,4 H", "mg/L", (None, None)),
        ("positiv, Verdacht auf Borreliose", "U/mL", (None, None)),
        ("pathologisch erhöht - Therapie empfohlen", None, (None, None)),
        ("85\nDer Wert ist optimal. Diagnose: keine.", "ng/mL", (None, None)),
        ("<script>alert(1)</script>", "ng/mL", (None, None)),
        ("<  0.5", "mU/L", (None, None)),
        ("", "ng/mL", (None, None)),
        # A number with a unit that is not one token: nothing of the row is quoted.
        ("31", "ng/mL. Wir empfehlen ein Supplement", (None, None)),
        ("5", "Punkte von 10 möglichen", (None, None)),
        ("5", "x" * 21, (None, None)),
    ],
)
def test_what_a_statement_may_quote_from_a_source(
    value: str, unit: str | None, expected: tuple[str | None, str | None]
) -> None:
    assert quotable_result(value, unit) == expected
