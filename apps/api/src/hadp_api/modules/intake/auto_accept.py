"""Auto-acceptance of green values — configuration that ships DISABLED.

A rule names one laboratory and one KPI and says: green values of this stratum may be confirmed
without a person, provided the measured green error rate (`error_rates.py`, the upper bound of
its 95 % interval) is under `max_green_error_rate` over at least `min_sample` decided green
values — and even then a random `audit_sample_rate` of them is still routed to a human.

Three gates stand in front of every automatic confirmation, and all three must be open:

1. the deployment's global switch `INTAKE_AUTO_ACCEPT_ENABLED` — **off** in every environment
   until go-live decision 7 (which names may publish without a human, signed by a named
   clinician) and the Regulatory Lead's sign-off; nothing in this module can turn it on;
2. a rule for the stratum, enabled, signed by a named person (`signed_by_user_id`), the newest
   row per stratum counting;
3. the measurement: enough decided green values, and an error bound under the threshold.

What passes all three is confirmed through the same `decide()` as a person's confirmation —
the same re-check against the record, the same observation, the same audit event (named
`intake.value_auto_accepted`) — with the rule's signer as the accountable person and the rule
on the decision. A rule only confirms; it never corrects or rejects, and it never touches a
yellow or red value. Decisions a rule made do not feed the error rate a rule is judged by.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import Settings
from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import IntakeDecisionKind, PendingValueStatus
from hadp_api.modules.intake import decisions as decisions_service
from hadp_api.modules.intake import error_rates as rates_mod
from hadp_api.modules.intake.models import (
    IntakeAutoAcceptRule,
    IntakeBatch,
    IntakeDecision,
    PendingValue,
)
from hadp_api.modules.kpi.models import KpiCatalog

NOT_ELIGIBLE_GLOBAL_OFF = "auto_accept_disabled_globally"
NOT_ELIGIBLE_NO_RULE = "no_enabled_rule_for_stratum"
NOT_ELIGIBLE_SAMPLE = "sample_below_minimum"
NOT_ELIGIBLE_RATE = "error_bound_above_threshold"
ELIGIBLE = "eligible"
ROUTED_TO_AUDIT = "routed_to_human_audit_sample"


@dataclass(frozen=True)
class Eligibility:
    source_lab: str
    kpi_code: str
    reason: str
    rule_id: uuid.UUID | None = None
    green_decided: int = 0
    green_error_upper_95: float | None = None

    @property
    def eligible(self) -> bool:
        return self.reason == ELIGIBLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_lab": self.source_lab,
            "kpi_code": self.kpi_code,
            "eligible": self.eligible,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "green_decided": self.green_decided,
            "green_error_upper_95": self.green_error_upper_95,
        }


def current_rules(
    db: Session, *, tenant_id: uuid.UUID
) -> dict[tuple[str, str], IntakeAutoAcceptRule]:
    """The newest rule per (laboratory, KPI) of this clinic — the one that counts."""
    rules: dict[tuple[str, str], IntakeAutoAcceptRule] = {}
    for rule in db.execute(
        select(IntakeAutoAcceptRule)
        .where(IntakeAutoAcceptRule.tenant_id == tenant_id)
        .order_by(IntakeAutoAcceptRule.created_at, IntakeAutoAcceptRule.id)
    ).scalars():
        rules[(rule.source_lab, rule.kpi_code)] = rule
    return rules


def record_rule(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source_lab: str,
    kpi_code: str,
    enabled: bool,
    max_green_error_rate: Decimal,
    min_sample: int,
    audit_sample_rate: Decimal,
    signed_by_user_id: uuid.UUID,
    correlation_id: str | None = None,
) -> IntakeAutoAcceptRule:
    """Append a rule (a change is a new row). The signer is the accountable person."""
    if db.get(KpiCatalog, kpi_code) is None:
        raise NotFound("kpi not found")
    if not (Decimal("0") < audit_sample_rate <= Decimal("1")):
        raise Conflict("audit_sample_rate must be above 0 and at most 1")
    if not (Decimal("0") <= max_green_error_rate <= Decimal("1")) or min_sample < 1:
        raise Conflict("rule bounds out of range")
    rule = IntakeAutoAcceptRule(
        tenant_id=tenant_id,
        source_lab=" ".join(source_lab.split())[:200],
        kpi_code=kpi_code,
        enabled=enabled,
        max_green_error_rate=max_green_error_rate,
        min_sample=min_sample,
        audit_sample_rate=audit_sample_rate,
        signed_by_user_id=signed_by_user_id,
    )
    db.add(rule)
    db.flush()
    record_audit(
        db,
        action="intake.auto_accept_rule_recorded",
        actor_user_id=signed_by_user_id,
        tenant_id=tenant_id,
        target_type="intake_auto_accept_rule",
        target_id=rule.id,
        correlation_id=correlation_id,
        detail={
            "kpi_code": kpi_code,
            "enabled": enabled,
            "max_green_error_rate": format(max_green_error_rate, "f"),
            "min_sample": min_sample,
            "audit_sample_rate": format(audit_sample_rate, "f"),
        },
    )
    return rule


def eligibility(
    db: Session, settings: Settings, *, tenant_id: uuid.UUID, source_lab: str, kpi_code: str
) -> Eligibility:
    """Whether green values of a stratum may be confirmed without a person right now."""

    def verdict(
        reason: str,
        rule_id: uuid.UUID | None = None,
        decided: int = 0,
        upper: float | None = None,
    ) -> Eligibility:
        return Eligibility(
            source_lab=source_lab,
            kpi_code=kpi_code,
            reason=reason,
            rule_id=rule_id,
            green_decided=decided,
            green_error_upper_95=upper,
        )

    if not settings.intake_auto_accept_enabled:
        return verdict(NOT_ELIGIBLE_GLOBAL_OFF)
    rule = current_rules(db, tenant_id=tenant_id).get((source_lab, kpi_code))
    if rule is None or not rule.enabled:
        return verdict(NOT_ELIGIBLE_NO_RULE)
    stratum = next(
        (
            s
            for s in rates_mod.error_rates(db, tenant_id=tenant_id, source_lab=source_lab)
            if s.kpi_code == kpi_code
        ),
        None,
    )
    decided = stratum.green_decided if stratum else 0
    upper = stratum.green_error_upper_95 if stratum else 1.0
    if decided < rule.min_sample:
        return verdict(NOT_ELIGIBLE_SAMPLE, rule.id, decided, upper)
    if Decimal(str(upper)) > rule.max_green_error_rate:
        return verdict(NOT_ELIGIBLE_RATE, rule.id, decided, upper)
    return verdict(ELIGIBLE, rule.id, decided, upper)


@dataclass(frozen=True)
class AutoAcceptOutcome:
    considered: int
    confirmed: int
    routed_to_human: int
    reasons: dict[str, int]


def apply(
    db: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    batch_id: uuid.UUID,
    correlation_id: str | None = None,
    today: date | None = None,
    rng: random.Random | None = None,
) -> AutoAcceptOutcome:
    """Confirm the GREEN, undecided values of a batch that a rule is entitled to confirm; leave
    every other value — and the audit sample — to a person. Called from the staff-triggered
    propose path only, never from the agent's tool."""
    batch = db.execute(
        select(IntakeBatch).where(IntakeBatch.id == batch_id, IntakeBatch.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if batch is None:
        raise NotFound("batch not found")
    reasons: dict[str, int] = {}
    considered = confirmed = routed = 0
    if batch.shadow:
        return AutoAcceptOutcome(0, 0, 0, {"shadow_batch": 0})
    chooser = rng or random.SystemRandom()
    lab = batch.source_lab or rates_mod.UNKNOWN_LAB
    rules = current_rules(db, tenant_id=tenant_id)
    for value in db.execute(
        select(PendingValue)
        .where(PendingValue.batch_id == batch.id, PendingValue.status == PendingValueStatus.GREEN)
        .order_by(PendingValue.row_index)
    ).scalars():
        if (
            db.execute(
                select(IntakeDecision.id).where(IntakeDecision.pending_value_id == value.id)
            ).first()
            is not None
        ):
            continue
        considered += 1
        kpi = value.kpi_code or rates_mod.UNMAPPED
        verdict = eligibility(db, settings, tenant_id=tenant_id, source_lab=lab, kpi_code=kpi)
        if not verdict.eligible:
            reasons[verdict.reason] = reasons.get(verdict.reason, 0) + 1
            continue
        rule = rules[(lab, kpi)]
        if Decimal(str(chooser.random())) < rule.audit_sample_rate:
            routed += 1
            reasons[ROUTED_TO_AUDIT] = reasons.get(ROUTED_TO_AUDIT, 0) + 1
            continue
        try:
            with db.begin_nested():
                decisions_service.decide(
                    db,
                    tenant_id=tenant_id,
                    pending_value_id=value.id,
                    decision=IntakeDecisionKind.CONFIRMED,
                    decided_by_user_id=rule.signed_by_user_id,
                    correlation_id=correlation_id,
                    today=today,
                    auto_accept_rule_id=rule.id,
                )
        except Conflict as exc:
            code = str(exc).split(":", 1)[0]
            reasons[code] = reasons.get(code, 0) + 1
            continue
        confirmed += 1
    return AutoAcceptOutcome(considered, confirmed, routed, reasons)
