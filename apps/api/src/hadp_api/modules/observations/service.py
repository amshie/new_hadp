"""Observations read service: timeline + deterministic change calculations.

Changes are computed only between comparable observations (same metric code AND same
normalized unit) — never across incompatible units/methods (CLAUDE.md). Deltas are exact
decimal subtraction. Review-required observations are surfaced with their status but are
not treated as published evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import ComparabilityState, KpiComparisonPolicy, ReviewStatus
from hadp_api.modules.kpi.service import domain_membership, resolve_comparison_policies
from hadp_api.modules.kpi_config.service import ClinicReference
from hadp_api.modules.observations.comparability import is_comparable
from hadp_api.modules.observations.models import Observation


@dataclass
class TimelinePoint:
    observation_id: uuid.UUID
    metric_code: str | None
    original_name: str
    value: Decimal | None
    unit: str | None
    reference_low: Decimal | None
    reference_high: Decimal | None
    observed_at: datetime
    observed_at_is_date_only: bool
    review_status: ReviewStatus
    delta_vs_previous: Decimal | None
    previous_observation_id: uuid.UUID | None
    # Catalog linkage (ADR-0004 Slice 2b). The canonical KPI and its navigational domains; the
    # secondary domains let a domain view surface this single Observation where it is also relevant
    # — visibility only, never a second verdict (ADR-0003).
    kpi_code: str | None
    kpi_primary_domain: str | None
    kpi_secondary_domains: list[str]
    # Comparability marker (ADR-0004 Slice 3, §9). Set only when a prior comparable-by-identity
    # observation exists: "comparable" (delta computed) or "not_comparable" (delta withheld; reason
    # set). None for the first point of a series (nothing to compare). Verdict-free.
    comparability: str | None
    comparability_reason: str | None
    # Which reference the within/above/below marker is based on: "laboratory" (the source-provided
    # interval on reference_low/high — always takes precedence), "clinic" (a clinic-defined fallback
    # used only when the lab gave none AND the unit matches), or None (no reference at all). The
    # clinic fallback bounds are surfaced separately and NEVER overwrite the source reference above;
    # they are opt-in per caller (the clinician timeline passes them; the report evidence does not).
    reference_source: str | None
    clinic_reference_low: Decimal | None
    clinic_reference_high: Decimal | None


@dataclass
class CoverageSummary:
    """Tenant-wide observation COVERAGE — deterministic counts + freshness over real observations.

    Explicitly NOT a clinical data-quality score: there is no tenant-wide quality/rules model
    (Gate G1, see worklist_routes + ADR-0006). These are plain counts (how many observations are
    published / carry a source reference interval) and the newest observation timestamp. The UI
    renders them as coverage, never as a merged quality %.
    """

    total: int
    published: int
    with_reference: int
    latest_observed_at: datetime | None


def coverage_summary(db: Session, tenant_id: uuid.UUID) -> CoverageSummary:
    """Aggregate observation coverage for one tenant in a single query (tenant-scoped; RLS is
    defense-in-depth on top of the explicit tenant filter, matching the worklist aggregate)."""
    row = db.execute(
        select(
            func.count().label("total"),
            func.count()
            .filter(Observation.review_status == ReviewStatus.PUBLISHED)
            .label("published"),
            func.count()
            .filter(
                or_(Observation.reference_low.is_not(None), Observation.reference_high.is_not(None))
            )
            .label("with_reference"),
            func.max(Observation.observed_at).label("latest_observed_at"),
        ).where(Observation.tenant_id == tenant_id)
    ).one()
    return CoverageSummary(
        total=row.total or 0,
        published=row.published or 0,
        with_reference=row.with_reference or 0,
        latest_observed_at=row.latest_observed_at,
    )


def list_observations(db: Session, patient_id: uuid.UUID) -> list[Observation]:
    return list(
        db.execute(
            select(Observation)
            .where(Observation.patient_id == patient_id)
            .order_by(Observation.observed_at)
        )
        .scalars()
        .all()
    )


def list_published(db: Session, patient_id: uuid.UUID) -> list[Observation]:
    return [
        o for o in list_observations(db, patient_id) if o.review_status == ReviewStatus.PUBLISHED
    ]


def _resolve_reference_source(
    obs: Observation, clinic_references: dict[str, ClinicReference] | None
) -> tuple[str | None, Decimal | None, Decimal | None]:
    """Decide which reference backs the position marker for one observation (fallback-only).

    The lab-provided reference always wins: if the observation carries any source bound, the source
    is used ("laboratory") and no clinic fallback is applied. Only when the source has NO bound at
    all is the tenant's clinic reference considered, and then ONLY if its unit matches the
    observation's normalized unit (never classify across units). Returns
    (reference_source, clinic_low, clinic_high); clinic bounds are non-None only for "clinic".
    """
    if obs.reference_low is not None or obs.reference_high is not None:
        return "laboratory", None, None
    if clinic_references is not None and obs.kpi_code is not None:
        cref = clinic_references.get(obs.kpi_code)
        if (
            cref is not None
            and obs.normalized_unit is not None
            and obs.normalized_unit == cref.unit
        ):
            return "clinic", cref.low, cref.high
    return None, None, None


def build_timeline(
    db: Session,
    patient_id: uuid.UUID,
    clinic_references: dict[str, ClinicReference] | None = None,
) -> list[TimelinePoint]:
    """Timeline points for a patient.

    `clinic_references` is opt-in: the clinician timeline passes the tenant's clinic-defined
    reference intervals so a value with no lab reference can still show a within/above/below marker
    (fallback-only, unit-checked). The report/evidence path passes nothing, so patient-facing
    content stays strictly on lab-provided references.
    """
    observations = list_observations(db, patient_id)
    kpi_codes = {o.kpi_code for o in observations if o.kpi_code is not None}
    # Resolve each observation's catalog domains (Slice 2b) and comparison policies (Slice 3) once.
    membership = domain_membership(db, kpi_codes)
    policies = resolve_comparison_policies(db, kpi_codes)
    # Track the previous PUBLISHED observation per (canonical KPI identity, normalized_unit). The
    # identity is kpi_code when resolved (the canonical comparison unit), else the source code.
    last_published: dict[tuple[str | None, str | None], Observation] = {}
    points: list[TimelinePoint] = []

    for obs in observations:
        key = (obs.kpi_code or obs.metric_code, obs.normalized_unit)
        delta: Decimal | None = None
        prev_id: uuid.UUID | None = None
        comparability: str | None = None
        comparability_reason: str | None = None
        if obs.review_status == ReviewStatus.PUBLISHED and obs.normalized_value is not None:
            prev = last_published.get(key)
            if prev is not None and prev.normalized_value is not None:
                policy = policies.get(obs.kpi_code or "", KpiComparisonPolicy.METHOD_AWARE)
                ok, reason = is_comparable(prev, obs, policy)
                if ok:
                    # Comparable: a deterministic delta against the prior is legitimate.
                    delta = obs.normalized_value - prev.normalized_value
                    prev_id = prev.id
                    comparability = ComparabilityState.COMPARABLE.value
                else:
                    # §9 fail-closed: withhold the delta (it would be a fabricated change).
                    comparability = ComparabilityState.NOT_COMPARABLE.value
                    comparability_reason = reason.value if reason is not None else None
            last_published[key] = obs

        primary, secondary = membership.get(obs.kpi_code or "", (None, []))
        reference_source, clinic_low, clinic_high = _resolve_reference_source(
            obs, clinic_references
        )
        points.append(
            TimelinePoint(
                observation_id=obs.id,
                metric_code=obs.metric_code,
                original_name=obs.original_name,
                value=obs.normalized_value,
                unit=obs.normalized_unit,
                reference_low=obs.reference_low,
                reference_high=obs.reference_high,
                observed_at=obs.observed_at,
                observed_at_is_date_only=obs.observed_at_is_date_only,
                review_status=obs.review_status,
                delta_vs_previous=delta,
                previous_observation_id=prev_id,
                kpi_code=obs.kpi_code,
                kpi_primary_domain=primary.value if primary is not None else None,
                kpi_secondary_domains=[axis.value for axis in secondary],
                comparability=comparability,
                comparability_reason=comparability_reason,
                reference_source=reference_source,
                clinic_reference_low=clinic_low,
                clinic_reference_high=clinic_high,
            )
        )
    return points
