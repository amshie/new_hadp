"""Narrative provider seam + deterministic local provider.

The narrative provider turns VERIFIED structured facts into a readable draft. It never
invents measurements, ranges, causes, diagnoses, or recommendations, and every statement
references the observation(s) it is built from. A deterministic fake is the default (and
is used in tests); a future AI provider must implement the same interface and obey the
same output contract (strict schema, evidence-linked, validated before persistence).

The text is written in German (de-DE, the product's initial locale): the released version
is what the patient reads. A statement gives the value the way the source wrote it — name,
value and unit verbatim. What the platform adds is named as such: a unit conversion appears
beside the source value, never instead of it.
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
    # The source representation, verbatim. This is what a statement states.
    original_value: str
    original_unit: str | None
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
    # only a day, "10.06.2025 um 08:30 Uhr (CEST)" otherwise (built in reports/evidence.py).
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


def _fmt(value: Decimal) -> str:
    return f"{value.normalize():f}"


def _with_unit(text: str, unit: str | None) -> str:
    return f"{text} {unit}" if unit else text


def _signed(value: Decimal) -> str:
    """A change says its direction: "+0.8", "-0.8", "0"."""
    text = _fmt(value)
    return f"+{text}" if value > 0 else text


def _bounds(low: Decimal | None, high: Decimal | None, unit: str | None) -> str | None:
    """The reference bounds the platform holds for a value, or None if it holds none.

    With one bound only, that bound is named and nothing is said about the other: the source
    may have given a one-sided interval, or a second bound that could not be read.
    """
    if low is not None and high is not None:
        return _with_unit(f"{_fmt(low)} bis {_fmt(high)}", unit)
    if high is not None:
        return _with_unit(f"obere Grenze {_fmt(high)}", unit)
    if low is not None:
        return _with_unit(f"untere Grenze {_fmt(low)}", unit)
    return None


class DeterministicNarrativeProvider:
    """Local, deterministic provider. Produces neutral, factual, evidence-linked text.

    Stays strictly inside the intended-use boundary: it states measured values, the
    lab-provided reference interval, and deterministic changes — no diagnosis, no advice,
    no inferred or "optimal" values.
    """

    name = "deterministic"
    # narr-2: German, and the value as the source wrote it (narr-1 was English and printed
    # the normalized value only). A stored version keeps its text and the version it was
    # generated with.
    version = "narr-2"

    def generate(self, payload: list[EvidenceItem]) -> list[DraftStatement]:
        statements: list[DraftStatement] = []
        for i, item in enumerate(payload, start=1):
            evidence = [item.observation_id]
            stated = _with_unit(item.original_value, item.original_unit)
            if item.converted and item.value is not None:
                stated += f" (umgerechnet: {_with_unit(_fmt(item.value), item.unit)})"
            parts = [f"{item.name} am {item.observed_at_label}: {stated}."]
            bounds = _bounds(item.reference_low, item.reference_high, item.unit)
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
                change = _with_unit(_signed(item.delta_vs_previous), item.unit)
                parts.append(
                    f"Veränderung gegenüber der vorherigen vergleichbaren Messung: {change}."
                )
                evidence.append(item.previous_observation_id)
            statements.append(
                DraftStatement(id=f"s{i}", text=" ".join(parts), evidence_observation_ids=evidence)
            )
        return statements
