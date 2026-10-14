"""Observations read service: timeline + deterministic change calculations.

Changes are computed only between comparable observations (same metric code AND same
normalized unit) — never across incompatible units/methods (CLAUDE.md). Deltas are exact
decimal subtraction. A value that could not be normalized is shown as the source wrote it,
in the source's unit, and takes no part in a change calculation. Review-required
observations are surfaced with their status but are not treated as published evidence. An
observation a published correction has replaced — and a value derived from one — stays on
the timeline as a preserved record, marked, and takes no part in a change calculation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.modules.derivations.models import ObservationDerivation
from hadp_api.modules.enums import (
    ComparabilityState,
    KpiComparisonPolicy,
    KpiMeasurementClass,
    ReviewStatus,
)
from hadp_api.modules.imports.normalize import unit_was_converted
from hadp_api.modules.kpi.service import domain_membership, resolve_comparison_policies
from hadp_api.modules.observations.comparability import is_comparable
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.reference_position import position_vs_source_interval
from hadp_api.modules.observations.sampling import same_sampling_time


@dataclass
class TimelinePoint:
    observation_id: uuid.UUID
    metric_code: str | None
    original_name: str
    # The source representation, verbatim.
    original_value: str
    original_unit: str | None
    # The number the platform holds and its unit (see `held_value`); the bounds are in that unit.
    value: Decimal | None
    unit: str | None
    # normalized: value/unit are the catalog's canonical representation. converted: getting
    # there changed the unit, so value and bounds are the platform's conversion of the source's.
    normalized: bool
    converted: bool
    reference_low: Decimal | None
    reference_high: Decimal | None
    observed_at: datetime
    observed_at_is_date_only: bool
    # When the platform received the value — what a clinician could have seen by a given date.
    received_at: datetime
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
    # Correction lineage. `supersedes` is set on a value a source sent as a correction of an
    # earlier one (a proposal until this value is published); `superseded_by` is set on a value
    # a PUBLISHED correction has replaced.
    supersedes_observation_id: uuid.UUID | None
    superseded_by_observation_id: uuid.UUID | None
    # A derived value one of whose inputs a published correction has replaced: it was computed
    # from a value that no longer stands.
    input_replaced: bool


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
    # Observations linked to a catalog KPI (a mapping, not a judgement of the value).
    with_kpi: int = 0


@dataclass
class PatientValueCounts:
    """What lies under one patient's record, counted for the worklist. Workflow counts only:
    how many values are published, how many await a human decision, how many arrived after
    the patient's latest interpretation run — never a statement about any value."""

    published: int = 0
    pending: int = 0
    # Received after the cutoff the caller gives (the latest run); rejected values excluded.
    received_after_cutoff: int = 0
    latest_received_at: datetime | None = None
    # When the oldest value still awaiting a decision was received.
    pending_since: datetime | None = None


def value_counts_by_patient(
    db: Session,
    tenant_id: uuid.UUID,
    cutoffs: dict[uuid.UUID, datetime],
) -> dict[uuid.UUID, PatientValueCounts]:
    """Per-patient value counts for one tenant (explicit tenant filter; RLS beneath it).

    `cutoffs` maps a patient to the moment after which a value counts as "received after"
    (the patient's latest interpretation run). A patient without a cutoff counts none. The
    definition matches the patient page's (rejected values never count).
    """
    rows = db.execute(
        select(Observation.patient_id, Observation.review_status, Observation.received_at).where(
            Observation.tenant_id == tenant_id
        )
    ).all()
    out: dict[uuid.UUID, PatientValueCounts] = {}
    for patient_id, status, received_at in rows:
        counts = out.setdefault(patient_id, PatientValueCounts())
        if status == ReviewStatus.PUBLISHED:
            counts.published += 1
        elif status == ReviewStatus.PENDING:
            counts.pending += 1
            if counts.pending_since is None or received_at < counts.pending_since:
                counts.pending_since = received_at
        if counts.latest_received_at is None or received_at > counts.latest_received_at:
            counts.latest_received_at = received_at
        cutoff = cutoffs.get(patient_id)
        if cutoff is not None and status != ReviewStatus.REJECTED and received_at > cutoff:
            counts.received_after_cutoff += 1
    return out


# After this many days a core marker's latest value counts as old on the practice view and
# the page before a visit. A stated constant, printed beside the count (the web's
# STALE_AFTER_DAYS is its twin); a clinic's own setting is a later step.
STALE_AFTER_DAYS = 180


@dataclass
class PatientPreparationFacts:
    """What the practice view says about one record (docs/notes/0023): counts of what stands
    in it, against the catalog and the latest interpretation run. Workflow and provenance
    facts only — a position is the laboratory interval's side, nothing is rated or summed."""

    # Published, standing values received after the patient's latest run (0 without a run).
    new_since_run: int = 0
    # Of those, how many lie outside their laboratory's interval.
    new_outside: int = 0
    # Markers whose latest standing value lies outside their laboratory's interval.
    outside: int = 0
    # Core markers whose latest standing value is older than STALE_AFTER_DAYS.
    stale_core: int = 0
    # Core markers of the catalog with no standing value.
    missing_core: int = 0
    pending: int = 0
    # Standing values no catalog marker names.
    unassigned: int = 0


def superseded_by_tenant(db: Session, tenant_id: uuid.UUID) -> set[uuid.UUID]:
    """Every observation of a tenant a PUBLISHED source value has replaced — the tenant-wide
    twin of `superseded_by`, the same definition, for the practice view's one pass."""
    rows = db.execute(
        select(Observation.supersedes_observation_id).where(
            Observation.tenant_id == tenant_id,
            Observation.supersedes_observation_id.is_not(None),
            Observation.review_status == ReviewStatus.PUBLISHED,
            Observation.source_category.is_distinct_from(KpiMeasurementClass.DERIVED),
        )
    ).scalars()
    return {replaced for replaced in rows if replaced is not None}


def preparation_facts_by_patient(
    db: Session,
    tenant_id: uuid.UUID,
    cutoffs: dict[uuid.UUID, datetime],
    core_codes: set[str],
    now: datetime,
    stale_after_days: int = STALE_AFTER_DAYS,
) -> dict[uuid.UUID, PatientPreparationFacts]:
    """The practice view's facts for every record of a tenant in one pass (explicit tenant
    filter; RLS beneath it). A value stands when it is published, no laboratory correction
    has replaced it, and it was not derived from a replaced input — the timeline's
    definition. A marker's latest value is its newest standing one by sample time; the
    position against the interval is `position_vs_source_interval`, the timeline's as well.
    Every record of the tenant gets an entry, even one without a value."""
    replaced = superseded_by_tenant(db, tenant_id)
    stale_derived = derived_from(db, replaced)
    rows = (
        db.execute(
            select(Observation)
            .where(Observation.tenant_id == tenant_id)
            .order_by(Observation.patient_id, Observation.observed_at, Observation.received_at)
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, PatientPreparationFacts] = {}
    # The latest standing value per (patient, marker), in sample order.
    latest: dict[tuple[uuid.UUID, str], Observation] = {}
    for obs in rows:
        facts = out.setdefault(obs.patient_id, PatientPreparationFacts())
        if obs.review_status == ReviewStatus.PENDING:
            facts.pending += 1
            continue
        standing = (
            obs.review_status == ReviewStatus.PUBLISHED
            and obs.id not in replaced
            and obs.id not in stale_derived
        )
        if not standing:
            continue
        value, _unit = held_value(obs)
        position = position_vs_source_interval(value, obs.reference_low, obs.reference_high)
        cutoff = cutoffs.get(obs.patient_id)
        if cutoff is not None and obs.received_at > cutoff:
            facts.new_since_run += 1
            if position in ("above", "below"):
                facts.new_outside += 1
        if obs.kpi_code is None:
            facts.unassigned += 1
            continue
        latest[(obs.patient_id, obs.kpi_code)] = obs
    stale_before = now - timedelta(days=stale_after_days)
    seen: dict[uuid.UUID, set[str]] = {}
    for (patient_id, code), obs in latest.items():
        facts = out[patient_id]
        seen.setdefault(patient_id, set()).add(code)
        value, _unit = held_value(obs)
        if position_vs_source_interval(value, obs.reference_low, obs.reference_high) in (
            "above",
            "below",
        ):
            facts.outside += 1
        if code in core_codes and obs.observed_at < stale_before:
            facts.stale_core += 1
    for patient_id, facts in out.items():
        facts.missing_core = len(core_codes - seen.get(patient_id, set()))
    return out


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
            func.count().filter(Observation.kpi_code.is_not(None)).label("with_kpi"),
        ).where(Observation.tenant_id == tenant_id)
    ).one()
    return CoverageSummary(
        total=row.total or 0,
        published=row.published or 0,
        with_reference=row.with_reference or 0,
        latest_observed_at=row.latest_observed_at,
        with_kpi=row.with_kpi or 0,
    )


def list_observations(db: Session, patient_id: uuid.UUID) -> list[Observation]:
    return list(
        db.execute(
            select(Observation)
            .where(Observation.patient_id == patient_id)
            .order_by(Observation.observed_at, Observation.received_at, Observation.id)
        )
        .scalars()
        .all()
    )


def list_published(db: Session, patient_id: uuid.UUID) -> list[Observation]:
    return [
        o for o in list_observations(db, patient_id) if o.review_status == ReviewStatus.PUBLISHED
    ]


def superseded_by(db: Session, patient_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    """Replaced observation id -> the PUBLISHED source value that replaced it.

    The single definition of "superseded". A supersession takes effect only once the replacing
    observation is published: a correction still in review, or one a human rejected, replaces
    nothing. The replaced observation itself is never changed. A recomputed derived value is
    lineage, not a correction, and is not counted here.
    """
    rows = db.execute(
        select(Observation.supersedes_observation_id, Observation.id)
        .where(
            Observation.patient_id == patient_id,
            Observation.supersedes_observation_id.is_not(None),
            Observation.review_status == ReviewStatus.PUBLISHED,
            Observation.source_category.is_distinct_from(KpiMeasurementClass.DERIVED),
        )
        .order_by(Observation.received_at, Observation.id)
    ).tuples()
    return {replaced: replacement for replaced, replacement in rows if replaced is not None}


def derived_from(db: Session, input_ids: set[uuid.UUID]) -> set[uuid.UUID]:
    """Derived observations computed from any of the given inputs (append-only lineage)."""
    if not input_ids:
        return set()
    return set(
        db.execute(
            select(ObservationDerivation.derived_observation_id).where(
                ObservationDerivation.input_observation_id.in_(input_ids)
            )
        ).scalars()
    )


def derivation_inputs(
    db: Session, derived_ids: set[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[str, uuid.UUID]]]:
    """Derived observation id -> its (role, input observation id) pairs (append-only lineage)."""
    out: dict[uuid.UUID, list[tuple[str, uuid.UUID]]] = {}
    if not derived_ids:
        return out
    rows = db.execute(
        select(
            ObservationDerivation.derived_observation_id,
            ObservationDerivation.role,
            ObservationDerivation.input_observation_id,
        )
        .where(ObservationDerivation.derived_observation_id.in_(derived_ids))
        .order_by(ObservationDerivation.role)
    ).tuples()
    for derived_id, role, input_id in rows:
        out.setdefault(derived_id, []).append((role, input_id))
    return out


def not_standing(db: Session, patient_id: uuid.UUID) -> set[uuid.UUID]:
    """Observations that must not back anything new: replaced by a published correction, or
    derived from a value that was."""
    replaced = set(superseded_by(db, patient_id))
    return replaced | derived_from(db, replaced)


def plain(value: Decimal | None) -> str | None:
    """An exact decimal as a plain string. `str()` switches to exponent notation for small
    magnitudes — a reference bound of 0 converted by a seven-digit factor reads "0E-7"."""
    return None if value is None else format(value, "f")


def held_value(observation: Observation) -> tuple[Decimal | None, str | None]:
    """The number the platform holds for an observation, and its unit.

    The normalized value in its KPI's canonical unit when the import normalized it; otherwise
    the source's own number in the source's own unit — a value the import does not act on by
    itself, or in a unit without an approved conversion, is not normalized, and it is not
    lost either. `reference_low`/`reference_high` are in the same unit. None when the
    source's writing is not one number.
    """
    if observation.normalized_value is not None:
        return observation.normalized_value, observation.normalized_unit
    return observation.numeric_value, (observation.original_unit or "").strip() or None


def build_timeline(db: Session, patient_id: uuid.UUID) -> list[TimelinePoint]:
    observations = list_observations(db, patient_id)
    kpi_codes = {o.kpi_code for o in observations if o.kpi_code is not None}
    # Resolve each observation's catalog domains (Slice 2b) and comparison policies (Slice 3) once.
    membership = domain_membership(db, kpi_codes)
    policies = resolve_comparison_policies(db, kpi_codes)
    replaced = superseded_by(db, patient_id)
    stale_derived = derived_from(db, set(replaced))
    zone = ZoneInfo(get_settings().lab_local_timezone)
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
        # A value that no longer stands is neither compared nor compared against: a change is
        # only ever computed between values that currently stand.
        if (
            obs.review_status == ReviewStatus.PUBLISHED
            and obs.normalized_value is not None
            and obs.id not in replaced
            and obs.id not in stale_derived
        ):
            prev = last_published.get(key)
            same_sample = prev is not None and same_sampling_time(prev, obs, zone)
            # Two values standing for one sampling time — or for one day, when only one of
            # them names a time — are not a change over time.
            if prev is not None and prev.normalized_value is not None and not same_sample:
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
        value, unit = held_value(obs)
        points.append(
            TimelinePoint(
                observation_id=obs.id,
                metric_code=obs.metric_code,
                original_name=obs.original_name,
                original_value=obs.original_value,
                original_unit=obs.original_unit,
                value=value,
                unit=unit,
                normalized=obs.normalized_value is not None,
                converted=unit_was_converted(obs.original_unit, obs.normalized_unit),
                reference_low=obs.reference_low,
                reference_high=obs.reference_high,
                observed_at=obs.observed_at,
                observed_at_is_date_only=obs.observed_at_is_date_only,
                received_at=obs.received_at,
                review_status=obs.review_status,
                delta_vs_previous=delta,
                previous_observation_id=prev_id,
                kpi_code=obs.kpi_code,
                kpi_primary_domain=primary.value if primary is not None else None,
                kpi_secondary_domains=[axis.value for axis in secondary],
                comparability=comparability,
                comparability_reason=comparability_reason,
                supersedes_observation_id=obs.supersedes_observation_id,
                superseded_by_observation_id=replaced.get(obs.id),
                input_replaced=obs.id in stale_derived,
            )
        )
    return points
