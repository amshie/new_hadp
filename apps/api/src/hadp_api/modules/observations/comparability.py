"""Longitudinal comparability (ADR-0004 §9 non-merge).

Decides whether two observations of the same KPI may form a longitudinal delta, given the KPI's
comparison policy and the source-supplied measurement context. This is a verdict-free
validation/grouping decision — it produces no number, score, or clinical conclusion; it only
withholds a delta that would be a fabricated change. Fail-closed: if a policy-required context
field is missing on either side, or differs, the two are NOT comparable.
"""

from __future__ import annotations

from hadp_api.modules.enums import ComparabilityReason, KpiComparisonPolicy
from hadp_api.modules.observations.models import Observation

# For each policy, the Observation context columns that must be present (non-NULL) AND equal on both
# observations for a longitudinal delta to be legitimate. METHOD_AWARE requires no extra context
# (compare on KPI + normalized unit alone); NOT_LONGITUDINAL never merges.
POLICY_REQUIRED_COLUMNS: dict[KpiComparisonPolicy, tuple[str, ...]] = {
    KpiComparisonPolicy.METHOD_AWARE: (),
    KpiComparisonPolicy.SAME_METHOD_REQUIRED: ("method",),
    KpiComparisonPolicy.SAME_PROTOCOL_REQUIRED: ("protocol",),
    KpiComparisonPolicy.SAME_DEVICE_PROTOCOL_REQUIRED: ("device_model", "protocol"),
    KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED: (
        "device_model",
        "firmware_or_algorithm_version",
    ),
    KpiComparisonPolicy.SAME_INSTRUMENT_VERSION_REQUIRED: ("instrument_version",),
    KpiComparisonPolicy.SAME_IMAGING_PROTOCOL_REQUIRED: (
        "protocol",
        "firmware_or_algorithm_version",
    ),
    KpiComparisonPolicy.SAME_FORMULA_VERSION_REQUIRED: ("formula_version",),
    KpiComparisonPolicy.SAME_OMICS_PLATFORM_REQUIRED: ("source_system", "method"),
    KpiComparisonPolicy.NOT_LONGITUDINAL: (),
}


def is_comparable(
    prev: Observation, cur: Observation, policy: KpiComparisonPolicy
) -> tuple[bool, ComparabilityReason | None]:
    """Whether `cur` may form a longitudinal delta against `prev` under `policy`.

    Returns (comparable, reason). reason is None when comparable, else why not (fail-closed).
    """
    if policy is KpiComparisonPolicy.NOT_LONGITUDINAL:
        return False, ComparabilityReason.NOT_LONGITUDINAL
    for column in POLICY_REQUIRED_COLUMNS[policy]:
        prev_value = getattr(prev, column)
        cur_value = getattr(cur, column)
        if prev_value is None or cur_value is None:
            return False, ComparabilityReason.CONTEXT_MISSING
        if prev_value != cur_value:
            return False, ComparabilityReason.CONTEXT_DIFFERS
    return True, None
