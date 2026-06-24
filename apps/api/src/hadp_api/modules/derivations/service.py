"""Controlled derived-value computation (ADR-0004 §10, Slice 4).

`compute_derived` is the ONLY way a formula runs — an explicit, controlled call (seed / CLI /
clinician-authorized workflow), never automatic on import (§10). It resolves each required input to
the latest PUBLISHED, correct-unit, non-superseded Observation for the patient and FAILS CLOSED
(writes nothing, returns None) if any input is missing — never inferred, never partial (§9.8). On
success it writes a new `source_category='derived'` Observation with the frozen formula provenance
and append-only input lineage. Idempotent: the same inputs + version return the existing value.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.derivations.models import ObservationDerivation
from hadp_api.modules.derivations.registry import FORMULAS, Formula
from hadp_api.modules.enums import KpiMeasurementClass, ReviewStatus, ValueType
from hadp_api.modules.kpi.models import KpiCatalog
from hadp_api.modules.observations.models import Observation


def _latest_input(
    db: Session, patient_id: uuid.UUID, kpi_code: str, unit: str
) -> Observation | None:
    """The latest PUBLISHED, correct-unit, non-superseded observation for an input KPI, or None."""
    superseded = (
        select(Observation.supersedes_observation_id)
        .where(
            Observation.patient_id == patient_id,
            Observation.supersedes_observation_id.is_not(None),
        )
        .scalar_subquery()
    )
    return db.execute(
        select(Observation)
        .where(
            Observation.patient_id == patient_id,
            Observation.kpi_code == kpi_code,
            Observation.review_status == ReviewStatus.PUBLISHED,
            Observation.normalized_value.is_not(None),
            Observation.normalized_unit == unit,
            Observation.id.not_in(superseded),
        )
        .order_by(Observation.observed_at.desc())
    ).scalars().first()


def _resolve_inputs(
    db: Session, patient_id: uuid.UUID, formula: Formula
) -> dict[str, Observation] | None:
    """Resolve every required input observation, or None if ANY is missing (fail-closed, §9)."""
    resolved: dict[str, Observation] = {}
    for role, input_kpi_code in formula.inputs.items():
        obs = _latest_input(db, patient_id, input_kpi_code, formula.input_units[role])
        if obs is None:
            return None
        resolved[role] = obs
    return resolved


def compute_derived(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    formula_id: str,
    computed_by_user_id: uuid.UUID | None = None,
) -> Observation | None:
    """Compute one derived KPI for a patient under controlled invocation.

    Returns the derived Observation, or None if inputs are not all available (fail-closed). It is
    idempotent for the same (patient, kpi, formula_version, input set). `computed_by_user_id` is
    unused for now (recorded by the future audited workflow); kept so callers pass the actor.
    """
    formula = FORMULAS.get(formula_id)
    if formula is None:
        raise ValueError(f"unknown formula_id: {formula_id!r}")

    inputs = _resolve_inputs(db, patient_id, formula)
    if inputs is None:
        return None  # §9.8 fail-closed: a missing input yields NO derived value, never an inference

    values: dict[str, Decimal] = {}
    for role, obs in inputs.items():
        assert obs.normalized_value is not None  # guaranteed by _latest_input filter
        values[role] = obs.normalized_value
    value = formula.fn(values).quantize(formula.quantize, rounding=ROUND_HALF_UP)
    input_ids = {obs.id for obs in inputs.values()}

    # Idempotency: an identical (kpi, formula_version, input set) derived value already exists.
    existing = db.execute(
        select(Observation).where(
            Observation.patient_id == patient_id,
            Observation.kpi_code == formula.output_kpi_code,
            Observation.formula_version == formula.formula_version,
            Observation.source_category == KpiMeasurementClass.DERIVED,
        )
    ).scalars().all()
    prior_for_supersession: Observation | None = None
    for candidate in existing:
        candidate_inputs = set(
            db.execute(
                select(ObservationDerivation.input_observation_id).where(
                    ObservationDerivation.derived_observation_id == candidate.id
                )
            ).scalars()
        )
        if candidate_inputs == input_ids:
            return candidate  # exact recompute: no-op
        prior_for_supersession = candidate

    observed_at = max(obs.observed_at for obs in inputs.values())
    date_only = all(obs.observed_at_is_date_only for obs in inputs.values())
    display_name = db.execute(
        select(KpiCatalog.display_name).where(KpiCatalog.code == formula.output_kpi_code)
    ).scalar_one()

    derived = Observation(
        tenant_id=tenant_id,
        patient_id=patient_id,
        original_name=display_name,
        original_value=str(value),
        original_unit=formula.output_unit,
        metric_code=None,  # a derived value has no source/LOINC code
        code_system=None,
        kpi_code=formula.output_kpi_code,
        source_category=KpiMeasurementClass.DERIVED,
        formula_id=formula.formula_id,
        formula_version=formula.formula_version,
        algorithm_name=formula.algorithm_name,
        value_type=ValueType.NUMERIC,
        numeric_value=value,
        normalized_value=value,
        normalized_unit=formula.output_unit,
        normalization_version=formula.formula_id,
        observed_at=observed_at,
        observed_at_is_date_only=date_only,
        received_at=datetime.now(UTC),
        review_status=ReviewStatus.PUBLISHED,
        supersedes_observation_id=(
            prior_for_supersession.id if prior_for_supersession is not None else None
        ),
    )
    db.add(derived)
    db.flush()

    for role, obs in inputs.items():
        db.add(
            ObservationDerivation(
                tenant_id=tenant_id,
                derived_observation_id=derived.id,
                input_observation_id=obs.id,
                role=role,
            )
        )
    db.flush()
    return derived
