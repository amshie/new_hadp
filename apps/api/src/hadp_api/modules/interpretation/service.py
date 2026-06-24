"""Interpretation service: create a run (validate-and-record) and read the latest matrix.

A run arrives WHOLE as a clinician-authored draft (6 verdicts + 18 verdict-free cells). The service
VALIDATES the shape (run_shape) and RECORDS it; it never derives CIS/Actionability. Corrections are
a NEW run (runs are append-only). Reads return the latest run as a structured matrix — CIS and
Actionability as two separate fields, the three tri-state cells as supporting evidence.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.errors import IntendedUseViolation
from hadp_api.modules.enums import DomainAxis, ReviewStatus
from hadp_api.modules.interpretation.models import (
    DomainAxisInterpretation,
    InterpretationRun,
    TriStateCell,
)
from hadp_api.modules.interpretation.run_shape import RunInput, validate_run_input
from hadp_api.modules.observations.models import Observation

# Canonical axis order for stable rendering (matches DOMAIN_AXES / the closed enum).
_AXIS_ORDER = {axis: i for i, axis in enumerate(DomainAxis)}


def create_run(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
    run: RunInput,
    reason: str,
) -> InterpretationRun:
    """Validate a whole draft run and record it (run + 6 verdicts + 18 cells). Append-only."""
    shape_error = validate_run_input(run)
    if shape_error is not None:
        raise IntendedUseViolation(f"invalid run shape: {shape_error.code}: {shape_error.detail}")

    last_number = db.execute(
        select(func.max(InterpretationRun.run_number)).where(
            InterpretationRun.tenant_id == tenant_id,
            InterpretationRun.patient_id == patient_id,
        )
    ).scalar()
    previous = db.execute(
        select(InterpretationRun.id)
        .where(
            InterpretationRun.tenant_id == tenant_id,
            InterpretationRun.patient_id == patient_id,
        )
        .order_by(InterpretationRun.run_number.desc())
        .limit(1)
    ).scalar()

    run_row = InterpretationRun(
        tenant_id=tenant_id,
        patient_id=patient_id,
        run_number=(last_number or 0) + 1,
        supersedes_run_id=previous,
        reason=reason,
        created_by_user_id=created_by_user_id,
    )
    db.add(run_row)
    db.flush()

    for d in run.domains:
        verdict = DomainAxisInterpretation(
            tenant_id=tenant_id,
            interpretation_run_id=run_row.id,
            domain_axis=d.domain_axis,
            cis_status=d.cis_status,
            actionability_class=d.actionability_class,
            followup_adequacy=d.followup_adequacy,
            rationale=d.rationale,
            created_by_user_id=created_by_user_id,
        )
        db.add(verdict)
        db.flush()
        for c in d.cells:
            db.add(
                TriStateCell(
                    tenant_id=tenant_id,
                    domain_axis_interpretation_id=verdict.id,
                    tri_state_axis=c.tri_state_axis,
                    state=c.state,
                    endpoint_adequacy=c.endpoint_adequacy,
                    evidence_refs=[{"kind": r.kind, "id": r.id} for r in c.evidence_refs],
                    rationale=c.rationale,
                )
            )
    db.flush()
    return run_row


def latest_matrix(
    db: Session, tenant_id: uuid.UUID, patient_id: uuid.UUID
) -> dict[str, Any] | None:
    """Latest run for a patient as a structured matrix, or None if no run exists."""
    run = db.execute(
        select(InterpretationRun)
        .where(
            InterpretationRun.tenant_id == tenant_id,
            InterpretationRun.patient_id == patient_id,
        )
        .order_by(InterpretationRun.run_number.desc())
    ).scalar()
    if run is None:
        return None

    verdicts = list(
        db.execute(
            select(DomainAxisInterpretation).where(
                DomainAxisInterpretation.interpretation_run_id == run.id
            )
        )
        .scalars()
        .all()
    )
    verdicts.sort(key=lambda v: _AXIS_ORDER.get(v.domain_axis, 99))

    cells_by_verdict: dict[uuid.UUID, list[TriStateCell]] = {}
    all_cells: list[TriStateCell] = []
    if verdicts:
        rows = (
            db.execute(
                select(TriStateCell).where(
                    TriStateCell.domain_axis_interpretation_id.in_([v.id for v in verdicts])
                )
            )
            .scalars()
            .all()
        )
        for cell in rows:
            cells_by_verdict.setdefault(cell.domain_axis_interpretation_id, []).append(cell)
            all_cells.append(cell)

    obs_map = _resolve_evidence_observations(db, all_cells)

    return {
        "run_id": str(run.id),
        "run_number": run.run_number,
        "domains": [
            {
                "domain_axis": v.domain_axis.value,
                "cis_status": v.cis_status.value,
                "actionability_class": v.actionability_class.value,
                "followup_adequacy": v.followup_adequacy.value,
                "review_status": v.review_status.value,
                "rationale": v.rationale,
                "cells": [
                    {
                        "tri_state_axis": c.tri_state_axis.value,
                        "state": c.state,
                        "endpoint_adequacy": c.endpoint_adequacy.value,
                        "evidence_count": len(c.evidence_refs or []),
                        "evidence": _cell_evidence(c, obs_map),
                        "rationale": c.rationale,
                    }
                    for c in sorted(
                        cells_by_verdict.get(v.id, []), key=lambda c: c.tri_state_axis.value
                    )
                ],
            }
            for v in verdicts
        ],
    }


def _evidence_obs_ids(cells: list[TriStateCell]) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for cell in cells:
        for ref in cell.evidence_refs or []:
            if isinstance(ref, dict) and ref.get("kind") == "observation":
                try:
                    ids.add(uuid.UUID(str(ref.get("id"))))
                except (ValueError, TypeError):
                    continue
    return ids


def _resolve_evidence_observations(
    db: Session, cells: list[TriStateCell]
) -> dict[uuid.UUID, Observation]:
    ids = _evidence_obs_ids(cells)
    if not ids:
        return {}
    rows = db.execute(select(Observation).where(Observation.id.in_(ids))).scalars().all()
    return {o.id: o for o in rows}


def _cell_evidence(
    cell: TriStateCell, obs_map: dict[uuid.UUID, Observation]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[uuid.UUID] = set()
    for ref in cell.evidence_refs or []:
        if not (isinstance(ref, dict) and ref.get("kind") == "observation"):
            continue
        try:
            oid = uuid.UUID(str(ref.get("id")))
        except (ValueError, TypeError):
            continue
        obs = obs_map.get(oid)
        if obs is None or oid in seen:
            continue
        seen.add(oid)
        has_ref = obs.reference_low is not None or obs.reference_high is not None
        reference = None
        if has_ref:
            lo = obs.reference_low if obs.reference_low is not None else "—"
            hi = obs.reference_high if obs.reference_high is not None else "—"
            reference = f"{lo}–{hi} {obs.normalized_unit or ''}".strip()
        observed = (
            obs.observed_at.date().isoformat()
            if obs.observed_at_is_date_only
            else obs.observed_at.isoformat()
        )
        out.append(
            {
                "original_name": obs.original_name,
                "value": str(obs.normalized_value) if obs.normalized_value is not None else None,
                "unit": obs.normalized_unit,
                "reference": reference,
                "observed_at": observed,
                "review_status": obs.review_status.value,
                "metric_code": obs.metric_code,
            }
        )
    return out


def list_published_observation_ids(db: Session, patient_id: uuid.UUID) -> list[uuid.UUID]:
    """Published observation ids for a patient — used by the seed to cite evidence on cells."""
    return list(
        db.execute(
            select(Observation.id).where(
                Observation.patient_id == patient_id,
                Observation.review_status == ReviewStatus.PUBLISHED,
            )
        )
        .scalars()
        .all()
    )
