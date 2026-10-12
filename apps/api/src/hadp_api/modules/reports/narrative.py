"""Narrative provider seam + deterministic local provider.

The narrative provider turns VERIFIED structured facts into a readable draft. It never
invents measurements, ranges, causes, diagnoses, or recommendations, and every statement
references the observation(s) it is built from. A deterministic fake is the default (and
is used in tests); a future AI provider must implement the same interface and obey the
same output contract (strict schema, evidence-linked, validated before persistence).

The text is written in German (de-DE, the product's initial locale): the released version
is what the patient reads. Analyte names, values and units stay as the source wrote them.
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
    value: Decimal | None
    unit: str | None
    reference_low: Decimal | None
    reference_high: Decimal | None
    # When the value was sampled, ready to follow "am": "10.06.2025" for a source that named
    # only a day, "10.06.2025 um 08:30 Uhr" otherwise (built in reports/evidence.py).
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


def _interval(low: Decimal | None, high: Decimal | None, unit: str | None) -> str | None:
    """The source's reference interval; a one-sided interval names its one bound; None if the
    source gave no bound at all."""
    if low is not None and high is not None:
        return _with_unit(f"{_fmt(low)} bis {_fmt(high)}", unit)
    if high is not None:
        return _with_unit(f"bis {_fmt(high)}", unit)
    if low is not None:
        return _with_unit(f"ab {_fmt(low)}", unit)
    return None


class DeterministicNarrativeProvider:
    """Local, deterministic provider. Produces neutral, factual, evidence-linked text.

    Stays strictly inside the intended-use boundary: it states measured values, the
    lab-provided reference interval, and deterministic changes — no diagnosis, no advice,
    no inferred or "optimal" values.
    """

    name = "deterministic"
    # narr-2: the same facts as narr-1, worded in German. A stored version keeps the text and
    # the version it was generated with.
    version = "narr-2"

    def generate(self, payload: list[EvidenceItem]) -> list[DraftStatement]:
        statements: list[DraftStatement] = []
        for i, item in enumerate(payload, start=1):
            evidence = [item.observation_id]
            if item.value is None:
                parts = [
                    f"Für {item.name} ist am {item.observed_at_label} kein Zahlenwert erfasst."
                ]
            else:
                measured = _with_unit(_fmt(item.value), item.unit)
                parts = [f"{item.name} lag am {item.observed_at_label} bei {measured}."]
            interval = _interval(item.reference_low, item.reference_high, item.unit)
            if interval is not None:
                parts.append(f"Referenzintervall der Quelle: {interval}.")
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
                change = _with_unit(_fmt(item.delta_vs_previous), item.unit)
                parts.append(
                    f"Veränderung gegenüber der vorherigen vergleichbaren Messung: {change}."
                )
                evidence.append(item.previous_observation_id)
            statements.append(
                DraftStatement(id=f"s{i}", text=" ".join(parts), evidence_observation_ids=evidence)
            )
        return statements
