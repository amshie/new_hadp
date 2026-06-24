"""Interpretation-run shape validation — dependency-free doctrine, no DB (ADR-0003).

A run is a fully-formed DRAFT that arrives whole: exactly 6 domain verdicts x 3 verdict-free cells.
This module VALIDATES and never DERIVES: CIS and Actionability are each checked against their OWN
disjoint closed set independently, so "never derived from each other" is structural (a CIS value in
the actionability field is not an ActionabilityClass and is rejected). Evidence RESOLUTION (refs
must point at the case's own data) is enforced at the DB/service layer, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hadp_api.modules.enums import (
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    TriStateAxis,
    cell_states_for_axis,
)


@dataclass(frozen=True)
class EvidenceRef:
    kind: str  # "source" | "measurement" | "observation"
    id: str


@dataclass
class CellInput:
    tri_state_axis: TriStateAxis
    state: str
    endpoint_adequacy: AdequacyStatus
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    rationale: str | None = None


@dataclass
class DomainInput:
    domain_axis: DomainAxis
    cis_status: CisStatus
    actionability_class: ActionabilityClass
    followup_adequacy: AdequacyStatus
    cells: list[CellInput]
    rationale: str | None = None


@dataclass
class RunInput:
    domains: list[DomainInput]


@dataclass(frozen=True)
class RunShapeError:
    code: str
    detail: str


_ALL_AXES = tuple(DomainAxis)
_TRI_AXES = tuple(TriStateAxis)


def validate_run_input(run: RunInput) -> RunShapeError | None:
    """Validate a draft run's shape + vocabulary. Returns the first violation, or None if valid."""
    domains = run.domains
    if len(domains) != len(_ALL_AXES):
        return RunShapeError(
            "wrong_domain_count", f"expected {len(_ALL_AXES)} domains, got {len(domains)}"
        )

    seen: set[DomainAxis] = set()
    for d in domains:
        if not isinstance(d.domain_axis, DomainAxis):
            return RunShapeError("invalid_domain_axis", str(d.domain_axis))
        if d.domain_axis in seen:
            return RunShapeError(
                "duplicate_or_missing_domain_axis", f"duplicate {d.domain_axis.value}"
            )
        seen.add(d.domain_axis)

        # CIS and Actionability validated INDEPENDENTLY against their own disjoint sets: a value
        # from one set placed in the other field is not an instance of that enum -> rejected.
        if not isinstance(d.cis_status, CisStatus):
            return RunShapeError("invalid_cis_status", f"{d.domain_axis.value}: {d.cis_status!r}")
        if not isinstance(d.actionability_class, ActionabilityClass):
            return RunShapeError(
                "invalid_actionability_class",
                f"{d.domain_axis.value}: {d.actionability_class!r}",
            )
        if not isinstance(d.followup_adequacy, AdequacyStatus):
            return RunShapeError(
                "invalid_followup_adequacy", f"{d.domain_axis.value}: {d.followup_adequacy!r}"
            )

        cell_error = _validate_cells(d)
        if cell_error is not None:
            return cell_error

    if len(seen) != len(_ALL_AXES):
        return RunShapeError("duplicate_or_missing_domain_axis", "not all domain axes present")
    return None


def _validate_cells(d: DomainInput) -> RunShapeError | None:
    cells = d.cells
    if len(cells) != len(_TRI_AXES):
        return RunShapeError(
            "wrong_cell_count",
            f"{d.domain_axis.value}: expected {len(_TRI_AXES)} cells, got {len(cells)}",
        )

    seen: set[TriStateAxis] = set()
    for c in cells:
        if not isinstance(c.tri_state_axis, TriStateAxis) or c.tri_state_axis in seen:
            return RunShapeError(
                "duplicate_or_missing_tri_state_axis",
                f"{d.domain_axis.value}: {c.tri_state_axis!r}",
            )
        seen.add(c.tri_state_axis)

        if c.state not in cell_states_for_axis(c.tri_state_axis):
            return RunShapeError(
                "invalid_cell_state_for_axis",
                f"{d.domain_axis.value}/{c.tri_state_axis.value}: {c.state!r}",
            )
        if not isinstance(c.endpoint_adequacy, AdequacyStatus):
            return RunShapeError(
                "invalid_endpoint_adequacy",
                f"{d.domain_axis.value}/{c.tri_state_axis.value}: {c.endpoint_adequacy!r}",
            )
        # A determinate (non-INDETERMINATE) cell must cite at least one evidence ref.
        if c.state != "INDETERMINATE" and len(c.evidence_refs) == 0:
            return RunShapeError(
                "missing_evidence_on_determinate_cell",
                f"{d.domain_axis.value}/{c.tri_state_axis.value}",
            )

    if len(seen) != len(_TRI_AXES):
        return RunShapeError(
            "duplicate_or_missing_tri_state_axis",
            f"{d.domain_axis.value}: not all tri-state axes present",
        )
    return None
