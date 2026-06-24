"""Evidence payload builder + statement evidence validation.

The evidence payload is built ONLY from published observations. Statement validation
enforces the meaningful-approval rule: every statement must reference at least one
observation that is viewable (exists, published, belongs to this patient/tenant). A
statement whose evidence is not viewable cannot be approved.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from hadp_api.modules.enums import KpiMeasurementClass
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.narrative import EvidenceItem


def _label(observation: Observation) -> str:
    if observation.observed_at_is_date_only:
        return observation.observed_at.date().isoformat()
    return observation.observed_at.isoformat()


def build_evidence_payload(db: Session, patient_id: uuid.UUID) -> list[EvidenceItem]:
    timeline = obs_service.build_timeline(db, patient_id)
    items: list[EvidenceItem] = []
    by_id = {o.id: o for o in obs_service.list_observations(db, patient_id)}
    for point in timeline:
        obs = by_id[point.observation_id]
        if point.review_status.value != "published":
            continue
        # Derived values are NOT auto-cited in the report draft (ADR-0004 Slice 4 / §0): they would
        # otherwise read as measured. Labelled inclusion is deferred to the derived-UI slice.
        if obs.source_category == KpiMeasurementClass.DERIVED:
            continue
        items.append(
            EvidenceItem(
                observation_id=point.observation_id,
                metric_code=point.metric_code,
                name=point.original_name,
                value=point.value,
                unit=point.unit,
                reference_low=point.reference_low,
                reference_high=point.reference_high,
                observed_at_label=_label(obs),
                delta_vs_previous=point.delta_vs_previous,
                previous_observation_id=point.previous_observation_id,
            )
        )
    return items


def viewable_observation_ids(db: Session, patient_id: uuid.UUID) -> set[uuid.UUID]:
    """Observation IDs that may back a statement: published, for this patient (RLS-scoped)."""
    return {o.id for o in obs_service.list_published(db, patient_id)}


def validate_statements(db: Session, patient_id: uuid.UUID, statements: list[dict]) -> None:
    """Raise ValueError if any statement lacks viewable evidence.

    Callers translate this into the appropriate API error. Used on draft generation,
    editing, and (strictly) on approval.
    """
    viewable = viewable_observation_ids(db, patient_id)
    for stmt in statements:
        ids = stmt.get("evidence_observation_ids") or []
        if not ids:
            raise ValueError(f"statement {stmt.get('id')!r} has no evidence")
        resolved = {uuid.UUID(str(i)) for i in ids}
        missing = resolved - viewable
        if missing:
            missing_ids = sorted(str(m) for m in missing)
            raise ValueError(
                f"statement {stmt.get('id')!r} references non-viewable evidence: {missing_ids}"
            )
