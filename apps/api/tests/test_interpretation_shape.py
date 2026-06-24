"""Pure (no-DB) tests for the interpretation doctrine: closed vocabularies + run-shape validation.

These exercise the validate-never-derive port (ADR-0003): CIS and Actionability are disjoint and
validated independently; a run is exactly 6 verdicts x 3 verdict-free cells; risk states are
disjoint from biological/functional; determinate cells must cite evidence.
"""

from __future__ import annotations

from hadp_api.modules.enums import (
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    TriStateAxis,
)
from hadp_api.modules.interpretation.run_shape import (
    CellInput,
    DomainInput,
    EvidenceRef,
    RunInput,
    validate_run_input,
)

_REF = EvidenceRef(kind="measurement", id="11111111-1111-1111-1111-111111111111")


def _valid_domain(axis: DomainAxis) -> DomainInput:
    return DomainInput(
        domain_axis=axis,
        cis_status=CisStatus.CIS_4_CREDIBLE_IMPROVEMENT,
        actionability_class=ActionabilityClass.C_CLINICALLY_INTERPRETABLE,
        followup_adequacy=AdequacyStatus.ADEQUATE,
        rationale="clinician note",
        cells=[
            CellInput(TriStateAxis.BIOLOGICAL, "STABLE", AdequacyStatus.ADEQUATE, [_REF]),
            CellInput(TriStateAxis.RISK, "REDUCED", AdequacyStatus.ADEQUATE, [_REF]),
            CellInput(TriStateAxis.FUNCTIONAL, "IMPROVED", AdequacyStatus.ADEQUATE, [_REF]),
        ],
    )


def _valid_run() -> RunInput:
    return RunInput(domains=[_valid_domain(a) for a in DomainAxis])


def test_cis_and_actionability_are_disjoint() -> None:
    cis = {c.value for c in CisStatus}
    overlap = [a.value for a in ActionabilityClass if a.value in cis]
    assert overlap == []


def test_six_axes_three_cells_cardinality() -> None:
    assert len(tuple(DomainAxis)) == 6
    assert len(tuple(CisStatus)) == 6
    assert len(tuple(ActionabilityClass)) == 5
    assert len(tuple(TriStateAxis)) == 3


def test_the_six_founder_approved_axes() -> None:
    assert [a.value for a in DomainAxis] == [
        "metabolic",
        "immune_inflammation",
        "cardiovascular",
        "neurocognitive",
        "musculoskeletal",
        "regenerative_capacity",
    ]


def test_accepts_a_complete_run() -> None:
    assert validate_run_input(_valid_run()) is None


def test_rejects_wrong_domain_count() -> None:
    run = _valid_run()
    run.domains.pop()
    err = validate_run_input(run)
    assert err is not None and err.code == "wrong_domain_count"


def test_rejects_a_cis_value_in_the_actionability_field() -> None:
    run = _valid_run()
    run.domains[0].actionability_class = CisStatus.CIS_4_CREDIBLE_IMPROVEMENT  # type: ignore[assignment]
    err = validate_run_input(run)
    assert err is not None and err.code == "invalid_actionability_class"


def test_rejects_an_actionability_value_in_the_cis_field() -> None:
    run = _valid_run()
    run.domains[0].cis_status = ActionabilityClass.A_DISCOVERY  # type: ignore[assignment]
    err = validate_run_input(run)
    assert err is not None and err.code == "invalid_cis_status"


def test_rejects_a_risk_only_state_on_a_biological_cell() -> None:
    run = _valid_run()
    run.domains[0].cells[0].state = "DOMINANT"  # risk-only
    err = validate_run_input(run)
    assert err is not None and err.code == "invalid_cell_state_for_axis"


def test_requires_evidence_on_a_determinate_cell() -> None:
    run = _valid_run()
    run.domains[0].cells[0].evidence_refs = []
    err = validate_run_input(run)
    assert err is not None and err.code == "missing_evidence_on_determinate_cell"


def test_allows_an_indeterminate_cell_without_evidence() -> None:
    run = _valid_run()
    run.domains[0].cells[0].state = "INDETERMINATE"
    run.domains[0].cells[0].evidence_refs = []
    assert validate_run_input(run) is None
