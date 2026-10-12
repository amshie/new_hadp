"""Narrative provider seam + deterministic local provider.

The narrative provider turns VERIFIED structured facts into a readable draft. It never
invents measurements, ranges, causes, diagnoses, or recommendations, and every statement
references the observation(s) it is built from. A deterministic fake is the default (and
is used in tests); a future AI provider must implement the same interface and obey the
same output contract (strict schema, evidence-linked, validated before persistence).

The text is written in German (de-DE, the product's initial locale): the released version
is what the patient reads. A statement gives a numeric result the way the source wrote it —
value and unit verbatim. What the platform adds is named as such: a unit conversion appears
beside the source value, never instead of it. A result that is not a number is never quoted:
source free text does not enter a statement (reports/evidence.py decides what may be quoted).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from hadp_api.modules.observations.reference_position import position_vs_source_interval


@dataclass
class EvidenceItem:
    observation_id: uuid.UUID
    metric_code: str | None
    name: str
    # The result as the source wrote it, when it may be quoted: a number (optionally with a
    # comparator) and a unit-shaped unit. None for anything else — a text result, a flagged
    # value, free text — which a statement mentions but never quotes.
    source_value: str | None
    source_unit: str | None
    # The normalized representation (None when the value could not be normalized, e.g. an
    # analyte the terminology does not know). Reference bounds are in the normalized unit.
    value: Decimal | None
    unit: str | None
    # True when normalization converted the unit, so `value`, `unit` and the bounds are the
    # platform's conversion of what the source wrote.
    converted: bool
    reference_low: Decimal | None
    reference_high: Decimal | None
    # When the value was sampled, ready to follow "am": "10.06.2025" for a source that named
    # only a day, "10.06.2025 um 08:30 Uhr (UTC+2)" otherwise (built in reports/evidence.py).
    observed_at_label: str
    delta_vs_previous: Decimal | None = None
    previous_observation_id: uuid.UUID | None = None


@dataclass
class DraftStatement:
    id: str
    text: str
    evidence_observation_ids: list[uuid.UUID] = field(default_factory=list)


class NarrativeProvider(Protocol):
    name: str
    version: str

    def generate(self, payload: list[EvidenceItem]) -> list[DraftStatement]: ...


def _fmt(value: Decimal, comma: bool) -> str:
    """A number the platform writes. It follows the decimal mark of the source value it stands
    beside, so one statement never mixes "5,55" with "3.885"."""
    text = f"{value.normalize():f}"
    return text.replace(".", ",") if comma else text


def _with_unit(text: str, unit: str | None) -> str:
    return f"{text} {unit}" if unit else text


def _signed(value: Decimal, comma: bool) -> str:
    """A change says its direction: "+0.8", "-0.8", "0"."""
    text = _fmt(value, comma)
    return f"+{text}" if value > 0 else text


def _bounds(low: Decimal | None, high: Decimal | None, unit: str | None, comma: bool) -> str | None:
    """The reference bounds the platform holds for a value, or None if it holds none.

    With one bound only, that bound is named and nothing is said about the other: the source
    may have given a one-sided interval, or a second bound that could not be read.
    """
    if low is not None and high is not None:
        return _with_unit(f"{_fmt(low, comma)} bis {_fmt(high, comma)}", unit)
    if high is not None:
        return _with_unit(f"obere Grenze {_fmt(high, comma)}", unit)
    if low is not None:
        return _with_unit(f"untere Grenze {_fmt(low, comma)}", unit)
    return None


class DeterministicNarrativeProvider:
    """Local, deterministic provider. Produces neutral, factual, evidence-linked text.

    Stays strictly inside the intended-use boundary: it states measured values, the
    lab-provided reference interval, and deterministic changes — no diagnosis, no advice,
    no inferred or "optimal" values.
    """

    name = "deterministic"
    # narr-2: German, and the numeric result as the source wrote it (narr-1 was English and
    # printed the normalized value only). A stored version keeps its text and the version it
    # was generated with.
    version = "narr-2"

    def generate(self, payload: list[EvidenceItem]) -> list[DraftStatement]:
        statements: list[DraftStatement] = []
        for i, item in enumerate(payload, start=1):
            evidence = [item.observation_id]
            if item.source_value is None:
                # Not a numeric result (or not one that can be quoted safely): the statement
                # says a result exists and does not repeat source text. Nothing else is said
                # about a value the reader is not shown.
                text = (
                    f"Für {item.name} liegt am {item.observed_at_label} ein Ergebnis der Quelle "
                    "vor, das hier nicht im Wortlaut wiedergegeben wird."
                )
                statements.append(
                    DraftStatement(id=f"s{i}", text=text, evidence_observation_ids=evidence)
                )
                continue

            comma = "," in item.source_value
            # Unconverted, the platform's numbers are in the source's unit: its spelling is kept.
            unit = item.unit if item.converted else item.source_unit
            stated = _with_unit(item.source_value, item.source_unit)
            if item.converted and item.value is not None:
                stated += f" (umgerechnet: {_with_unit(_fmt(item.value, comma), unit)})"
            parts = [f"{item.name} am {item.observed_at_label}: {stated}."]
            bounds = _bounds(item.reference_low, item.reference_high, unit, comma)
            if bounds is not None:
                # Converted bounds are the source's interval in the platform's unit — said so.
                label = "Referenzintervall der Quelle"
                parts.append(f"{label}{' (umgerechnet)' if item.converted else ''}: {bounds}.")
                # Factual comparison to the lab-provided interval (a rule match, not a diagnosis).
                # Uses the shared predicate so the narrative, the web "Lage" column, and the
                # planned out_of_source_interval rule cannot drift. Only above/below are stated;
                # within / not-evaluable add no sentence (unchanged behaviour).
                position = position_vs_source_interval(
                    item.value, item.reference_low, item.reference_high
                )
                if position == "above":
                    parts.append("Der Wert liegt über dem Referenzintervall der Quelle.")
                elif position == "below":
                    parts.append("Der Wert liegt unter dem Referenzintervall der Quelle.")
            if item.delta_vs_previous is not None and item.previous_observation_id is not None:
                change = _with_unit(_signed(item.delta_vs_previous, comma), unit)
                parts.append(
                    f"Veränderung gegenüber der vorherigen vergleichbaren Messung: {change}."
                )
                evidence.append(item.previous_observation_id)
            statements.append(
                DraftStatement(id=f"s{i}", text=" ".join(parts), evidence_observation_ids=evidence)
            )
        return statements
