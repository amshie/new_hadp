"""Narrative provider seam + deterministic local provider.

The narrative provider turns VERIFIED structured facts into a readable draft. It never
invents measurements, ranges, causes, diagnoses, or recommendations, and every statement
references the observation(s) it is built from. A deterministic fake is the default (and
is used in tests); a future AI provider must implement the same interface and obey the
same output contract (strict schema, evidence-linked, validated before persistence).
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


def _fmt(value: Decimal | None) -> str:
    return "unknown" if value is None else f"{value.normalize():f}"


class DeterministicNarrativeProvider:
    """Local, deterministic provider. Produces neutral, factual, evidence-linked text.

    Stays strictly inside the intended-use boundary: it states measured values, the
    lab-provided reference interval, and deterministic changes — no diagnosis, no advice,
    no inferred or "optimal" values.
    """

    name = "deterministic"
    version = "narr-1"

    def generate(self, payload: list[EvidenceItem]) -> list[DraftStatement]:
        statements: list[DraftStatement] = []
        for i, item in enumerate(payload, start=1):
            evidence = [item.observation_id]
            parts = [
                f"{item.name} was {_fmt(item.value)} {item.unit or ''}".rstrip()
                + f" on {item.observed_at_label}."
            ]
            if item.reference_low is not None or item.reference_high is not None:
                interval = (
                    f"{_fmt(item.reference_low)}-{_fmt(item.reference_high)} {item.unit or ''}"
                )
                parts.append(f"Source reference interval: {interval.rstrip()}.")
                # Factual comparison to the lab-provided interval (a rule match, not a diagnosis).
                # Uses the shared predicate so the narrative, the web "Lage" column, and the
                # planned out_of_source_interval rule cannot drift. Only above/below are stated;
                # within / not-evaluable add no sentence (unchanged behaviour).
                position = position_vs_source_interval(
                    item.value, item.reference_low, item.reference_high
                )
                if position == "above":
                    parts.append("The value is above the source reference interval.")
                elif position == "below":
                    parts.append("The value is below the source reference interval.")
            if item.delta_vs_previous is not None and item.previous_observation_id is not None:
                parts.append(
                    f"Change of {_fmt(item.delta_vs_previous)} {item.unit or ''}".rstrip()
                    + " since the previous comparable measurement."
                )
                evidence.append(item.previous_observation_id)
            statements.append(
                DraftStatement(id=f"s{i}", text=" ".join(parts), evidence_observation_ids=evidence)
            )
        return statements
