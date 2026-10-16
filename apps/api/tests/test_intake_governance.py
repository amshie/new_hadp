"""Slice 5 governance: the error-rate report from the clinicians' decisions, auto-acceptance
that ships disabled and only confirms under a signed rule and a measured rate, shadow batches
that the screen never shows and nobody can decide."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import func, select

from hadp_api.config import get_settings
from hadp_api.modules.enums import IntakeDecisionKind, IntakeRejectionReason, Role
from hadp_api.modules.intake import auto_accept, error_rates
from hadp_api.modules.intake import service as intake_service
from hadp_api.modules.intake.models import IntakeAutoAcceptRule, IntakeBatch, IntakeDecision
from hadp_api.modules.intake.schemas import ProposedBatchIn
from hadp_api.modules.intake.tools import IntakeScope, IntakeTools
from hadp_api.modules.observations.models import Observation
from tests.helpers import login_as, switch_role
from tests.intake_support import CASES_DIR
from tests.test_intake_decisions import _batch, _propose, _sign_test_bounds

API = "/api/v1"
GREEN_CASE = CASES_DIR / "01_a_nord_all_green"
TODAY = datetime(2026, 10, 16).date()


def _patient(client) -> str:  # type: ignore[no-untyped-def]
    """A fresh synthetic patient each time (the API refuses a second identical identity)."""
    resp = client.post(
        f"{API}/patients",
        json={
            "display_name": f"Synthetic Governance {uuid.uuid4().hex[:8]}",
            "date_of_birth": "1970-03-12",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _upload(client, patient_id: str, case_dir) -> str:  # type: ignore[no-untyped-def]
    """The case's PDF, made unique per upload (a clinic stores one file once, by checksum)."""
    data = (
        case_dir / "input" / "report.pdf"
    ).read_bytes() + f"\n%run-{uuid.uuid4().hex}\n".encode()
    resp = client.post(
        f"{API}/patients/{patient_id}/documents",
        files={"file": ("report.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _staff(client, admin_session, slug: str, role: Role = Role.CLINICIAN):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"gov-{slug}@example.test",
        tenant_name=f"Governance {slug}",
        tenant_slug=f"gov-{slug}",
        role=role,
    )


def _green_batch(client, pid: str, did: str, *, confidence_last: str | None = None):  # type: ignore[no-untyped-def]
    """A batch through the agent's write with the golden proposal (green with signed bounds)."""
    me = client.get(f"{API}/auth/me").json()
    tools = IntakeTools(
        IntakeScope(
            tenant_id=uuid.UUID(me["active_tenant_id"]),
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            actor_user_id=uuid.UUID(me["user"]["id"]),
            extraction_provider="golden-fixture",
            model_id="fixture-proposal",
            prompt_version="fixture-1",
        ),
        today=TODAY,
    )
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    if confidence_last:
        raw["values"][-1]["confidence"] = confidence_last
    ProposedBatchIn.model_validate(raw)
    return tools.create_pending_batch(
        did,
        raw["values"],
        patient_date_of_birth=raw["patient_date_of_birth"],
        issue_date=raw["issue_date"],
        source_lab="Labor Nord Synthetik",
    )


def _decide(client, batch_id, value_id, decision, **extra):  # type: ignore[no-untyped-def]
    resp = client.post(
        f"{API}/intake/batches/{batch_id}/decisions",
        json={"pending_value_id": value_id, "decision": decision, **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- the error-rate report ---------------------------------------------------------------------


def test_the_report_counts_every_decision_per_laboratory_kpi_and_field(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _staff(client, admin_session, "rates")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    batch_id = _propose(client, pid, did)["batch_id"]  # text-layer: lab = letterhead line
    view = _batch(client, batch_id)
    assert view["source_lab"] == "Labor Nord Synthetik"
    by_name = {v["analyte_text"]: v for v in view["values"]}
    _decide(client, batch_id, by_name["HbA1c"]["pending_value_id"], "confirmed")
    _decide(
        client,
        batch_id,
        by_name["LDL"]["pending_value_id"],
        "corrected",
        correction={"value_text": "3,0"},
    )
    _decide(
        client,
        batch_id,
        by_name["Glucose"]["pending_value_id"],
        "rejected",
        rejection_reason="misread",
    )
    _decide(
        client,
        batch_id,
        by_name["Triglycerides"]["pending_value_id"],
        "corrected",
        correction={"unit_text": "mmol/l"},
    )

    strata = error_rates.error_rates(admin_session, tenant_id=tenant.id)
    rows = {s.kpi_code: s for s in strata}
    assert all(s.source_lab == "Labor Nord Synthetik" for s in strata)
    assert (
        rows["metabolic.hba1c"].confirmed == 1
        and rows["metabolic.hba1c"].field_errors["value_text"] == 0
    )
    ldl = rows["cardio.ldl_c"]
    assert (
        ldl.decided,
        ldl.corrected,
        ldl.field_errors["value_text"],
        ldl.field_errors["unit_text"],
    ) == (1, 1, 1, 0)
    glucose = rows["metabolic.fasting_plasma_glucose"]
    assert (
        glucose.rejected,
        glucose.field_errors["value_text"],
        glucose.field_errors["analyte_text"],
    ) == (1, 1, 1)
    tg = rows["metabolic.triglycerides"]
    assert (
        tg.field_errors["unit_text"] == 1 and tg.as_dict()["field_error_rates"]["unit_text"] == 1.0
    )
    # Text-layer values are yellow: no green stratum yet, so no green error rate — bound 1.0.
    assert all(s.green_decided == 0 and s.green_error_rate is None for s in strata)
    assert all(s.green_error_upper_95 == 1.0 for s in strata)

    # Owner reads the report over HTTP; a clinician may not.
    assert client.get(f"{API}/intake/error-rates").status_code == 403
    switch_role(
        client, admin_session, email="owner-rates@example.test", tenant=tenant, role=Role.OWNER
    )
    report = client.get(f"{API}/intake/error-rates")
    assert report.status_code == 200
    body = report.json()
    assert body["auto_accept_enabled_globally"] is False
    assert {s["kpi_code"] for s in body["strata"]} == set(rows)


def test_wilson_upper_bound_is_conservative_for_small_samples() -> None:
    assert error_rates.wilson_upper(0, 0) == 1.0
    assert 0.27 < error_rates.wilson_upper(0, 10) < 0.28
    assert error_rates.wilson_upper(0, 100) < 0.04
    assert error_rates.wilson_upper(5, 100) > 0.05
    assert error_rates.wilson_upper(100, 100) == 1.0


# --- auto-acceptance ships disabled ------------------------------------------------------------


def test_with_the_switch_off_nothing_is_confirmed_without_a_person_whatever_the_rule_says(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _staff(client, admin_session, "off", role=Role.OWNER)
    _sign_test_bounds(admin_session)
    assert get_settings().intake_auto_accept_enabled is False
    # The owner records the most permissive rule allowed.
    resp = client.post(
        f"{API}/intake/auto-accept/rules",
        json={
            "source_lab": "Labor Nord Synthetik",
            "kpi_code": "cardio.ldl_c",
            "enabled": True,
            "max_green_error_rate": "1",
            "min_sample": 1,
            "audit_sample_rate": "0.01",
        },
    )
    assert resp.status_code == 201, resp.text
    rule = resp.json()
    assert rule["eligibility"]["reason"] == "auto_accept_disabled_globally"
    assert rule["eligibility"]["eligible"] is False
    # A zero audit sample is refused by the schema (a rule never runs unwatched).
    bad = client.post(
        f"{API}/intake/auto-accept/rules",
        json={
            "source_lab": "x",
            "kpi_code": "cardio.ldl_c",
            "enabled": True,
            "max_green_error_rate": "0.01",
            "min_sample": 1,
            "audit_sample_rate": "0",
        },
    )
    assert bad.status_code == 422

    # Green values through the staff path: proposed, none confirmed.
    switch_role(
        client, admin_session, email="clin-off@example.test", tenant=tenant, role=Role.CLINICIAN
    )
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    outcome = _green_batch(client, pid, did)
    assert outcome.green == 6
    result = auto_accept.apply(
        admin_session, get_settings(), tenant_id=tenant.id, batch_id=outcome.batch_id
    )
    assert (result.considered, result.confirmed, result.routed_to_human) == (6, 0, 0)
    assert result.reasons == {"auto_accept_disabled_globally": 6}
    assert admin_session.execute(select(func.count()).select_from(IntakeDecision)).scalar_one() == 0
    assert admin_session.execute(select(func.count()).select_from(Observation)).scalar_one() == 0
    # Over HTTP the propose path reports the same: nothing auto-confirmed.
    proposed = client.post(f"{API}/patients/{pid}/documents/{did}/intake").json()
    assert proposed["auto_confirmed"] == 0
    assert (
        set(proposed["auto_accept_reasons"]) <= {"auto_accept_disabled_globally"}
        or proposed["auto_accept_reasons"] == {}
    )


def test_switch_on_a_rule_confirms_only_after_the_rate_qualifies_and_keeps_an_audit_sample(
    client, admin_session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _staff(client, admin_session, "on", role=Role.OWNER)
    _sign_test_bounds(admin_session)
    monkeypatch.setenv("INTAKE_AUTO_ACCEPT_ENABLED", "true")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.intake_auto_accept_enabled is True
        resp = client.post(
            f"{API}/intake/auto-accept/rules",
            json={
                "source_lab": "Labor Nord Synthetik",
                "kpi_code": "cardio.ldl_c",
                "enabled": True,
                "max_green_error_rate": "0.5",
                "min_sample": 2,
                "audit_sample_rate": "0.5",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["eligibility"]["reason"] == "sample_below_minimum"

        switch_role(
            client, admin_session, email="clin-on@example.test", tenant=tenant, role=Role.CLINICIAN
        )
        # No measured green decisions yet: the rule does nothing.
        pid = _patient(client)
        did = _upload(client, pid, GREEN_CASE)
        first = _green_batch(client, pid, did)
        out = auto_accept.apply(
            admin_session, settings, tenant_id=tenant.id, batch_id=first.batch_id
        )
        assert out.confirmed == 0 and out.reasons.get("sample_below_minimum") == 1
        assert out.reasons.get("no_enabled_rule_for_stratum") == 5  # the other KPIs have no rule
        # Two clinicians' confirmations of green LDL make the sample (upper bound 0 errors / 2).
        ldl_ids = []
        for _ in range(2):
            p2 = _patient(client)
            d2 = _upload(client, p2, GREEN_CASE)
            b2 = _green_batch(client, p2, d2)
            ldl = next(
                v for v in _batch(client, str(b2.batch_id))["values"] if v["analyte_text"] == "LDL"
            )
            _decide(client, str(b2.batch_id), ldl["pending_value_id"], "confirmed")
            ldl_ids.append(ldl["pending_value_id"])
        verdict = auto_accept.eligibility(
            admin_session,
            settings,
            tenant_id=tenant.id,
            source_lab="Labor Nord Synthetik",
            kpi_code="cardio.ldl_c",
        )
        assert verdict.green_decided == 2
        # Wilson upper bound of 0/2 is 0.66 > 0.5: still not eligible — the bound, not the point.
        assert verdict.reason == "error_bound_above_threshold"
        # A permissive threshold makes it eligible; a seeded chooser puts one in the audit sample.
        switch_role(
            client, admin_session, email="owner-on2@example.test", tenant=tenant, role=Role.OWNER
        )
        resp = client.post(
            f"{API}/intake/auto-accept/rules",
            json={
                "source_lab": "Labor Nord Synthetik",
                "kpi_code": "cardio.ldl_c",
                "enabled": True,
                "max_green_error_rate": "0.9",
                "min_sample": 2,
                "audit_sample_rate": "0.5",
            },
        )
        assert resp.status_code == 201 and resp.json()["eligibility"]["eligible"] is True
        # Two fresh green LDL values; a chooser that draws 0.1 then 0.9: one audited, one confirmed.
        p3 = _patient(client)
        switch_role(
            client, admin_session, email="clin-on3@example.test", tenant=tenant, role=Role.CLINICIAN
        )
        d3 = _upload(client, p3, GREEN_CASE)
        b3 = _green_batch(client, p3, d3)
        p4 = _patient(client)
        d4 = _upload(client, p4, GREEN_CASE)
        b4 = _green_batch(client, p4, d4)

        class Draws:
            def __init__(self, values):  # type: ignore[no-untyped-def]
                self.values = list(values)

            def random(self) -> float:
                return self.values.pop(0)

        out3 = auto_accept.apply(
            admin_session,
            settings,
            tenant_id=tenant.id,
            batch_id=b3.batch_id,
            rng=Draws([0.1]),  # type: ignore[arg-type]
        )
        assert (out3.confirmed, out3.routed_to_human) == (0, 1)
        out4 = auto_accept.apply(
            admin_session,
            settings,
            tenant_id=tenant.id,
            batch_id=b4.batch_id,
            rng=Draws([0.9]),  # type: ignore[arg-type]
        )
        assert (out4.confirmed, out4.routed_to_human) == (1, 0)
        admin_session.commit()
        auto = [
            d
            for d in admin_session.execute(select(IntakeDecision)).scalars()
            if d.auto_accept_rule_id is not None
        ]
        assert len(auto) == 1 and auto[0].decision is IntakeDecisionKind.CONFIRMED
        rule_row = admin_session.get(IntakeAutoAcceptRule, auto[0].auto_accept_rule_id)
        assert rule_row is not None and auto[0].decided_by_user_id == rule_row.signed_by_user_id
        # The rule's own confirmation does not feed the rate it is judged by.
        stratum = next(
            s
            for s in error_rates.error_rates(admin_session, tenant_id=tenant.id)
            if s.kpi_code == "cardio.ldl_c"
        )
        assert stratum.auto_confirmed == 1 and stratum.green_decided == 2
        # The observation exists like any confirmed one; the trail names the rule.
        assert admin_session.get(Observation, auto[0].observation_id) is not None
        from hadp_api.modules.audit.models import AuditEvent

        assert (
            admin_session.execute(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "intake.value_auto_accepted")
            ).scalar_one()
            == 1
        )
    finally:
        monkeypatch.delenv("INTAKE_AUTO_ACCEPT_ENABLED", raising=False)
        get_settings.cache_clear()


def test_a_rule_can_only_confirm(admin_session, client) -> None:  # type: ignore[no-untyped-def]
    from hadp_api.errors import Conflict
    from hadp_api.modules.intake import decisions

    _user, tenant = _staff(client, admin_session, "ruleonly")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    b = _green_batch(client, pid, did)
    value_id = uuid.UUID(b.values[0]["pending_value_id"])
    with pytest.raises(Conflict, match="rule_only_confirms"):
        decisions.decide(
            admin_session,
            tenant_id=tenant.id,
            pending_value_id=value_id,
            decision=IntakeDecisionKind.REJECTED,
            decided_by_user_id=uuid.uuid4(),
            rejection_reason=IntakeRejectionReason.MISREAD,
            auto_accept_rule_id=uuid.uuid4(),
        )
    admin_session.rollback()


# --- shadow batches ----------------------------------------------------------------------------


def test_a_shadow_batch_is_never_shown_and_never_decided(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, tenant = _staff(client, admin_session, "shadow")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    from hadp_api.db.engine import get_sessionmaker, set_tenant_context

    db = get_sessionmaker()()
    set_tenant_context(db, tenant.id, user.id)
    try:
        result = intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            proposal=ProposedBatchIn.model_validate(raw),
            created_by_user_id=user.id,
            today=TODAY,
            shadow=True,
        )
        db.commit()
    finally:
        db.close()
    assert client.get(f"{API}/patients/{pid}/intake-batches").json() == []
    assert client.get(f"{API}/intake/batches/{result.batch_id}").status_code == 404
    denied = client.post(
        f"{API}/intake/batches/{result.batch_id}/decisions",
        json={"pending_value_id": str(result.value_ids[0]), "decision": "confirmed"},
    )
    assert denied.status_code == 404
    assert (
        client.post(f"{API}/intake/batches/{result.batch_id}/confirm-green", json={}).status_code
        == 409
    )
    batch = admin_session.get(IntakeBatch, result.batch_id)
    assert batch is not None and batch.shadow is True
    assert (
        auto_accept.apply(
            admin_session, get_settings(), tenant_id=tenant.id, batch_id=result.batch_id
        ).considered
        == 0
    )
    assert admin_session.execute(select(func.count()).select_from(Observation)).scalar_one() == 0


def test_shadow_compare_sets_the_proposal_beside_what_a_person_keyed(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    from hadp_api.db.engine import get_sessionmaker, set_tenant_context
    from hadp_api.modules.intake import shadow

    user, tenant = _staff(client, admin_session, "compare")
    pid = _patient(client)
    did = _upload(client, pid, GREEN_CASE)
    raw = json.loads((GREEN_CASE / "input" / "proposal.json").read_text(encoding="utf-8"))
    raw["source_lab"] = "Labor Nord Synthetik"
    db = get_sessionmaker()()
    set_tenant_context(db, tenant.id, user.id)
    try:
        intake_service.create_pending_batch(
            db,
            tenant_id=tenant.id,
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            proposal=ProposedBatchIn.model_validate(raw),
            created_by_user_id=user.id,
            today=TODAY,
            shadow=True,
        )
        db.commit()
    finally:
        db.close()
    # Nothing to compare with yet: six proposals, no keyed value.
    before = shadow.compare(admin_session, tenant_id=tenant.id)
    assert [(r.source_lab, r.proposed, r.keyed, r.matched) for r in before] == [
        ("Labor Nord Synthetik", 6, 0, 0)
    ]
    assert before[0].as_dict()["field_divergence"]["value_text"] is None
    # The clinic keys two of the report's values the way it does today: LDL as printed, HbA1c
    # with a different number and the same unit written another way.
    keyed = client.post(
        f"{API}/patients/{pid}/imports",
        json={
            "source_document_id": did,
            "values": [
                {
                    "original_name": "LDL",
                    "original_value": "3.1",
                    "original_unit": "mmol/l",
                    "observed_at": "2026-09-05T00:00:00Z",
                    "observed_at_is_date_only": True,
                    "reference_high": "3.0",
                },
                {
                    "original_name": "HbA1c",
                    "original_value": "5.5",
                    "original_unit": "%",
                    "observed_at": "2026-09-05T00:00:00Z",
                    "observed_at_is_date_only": True,
                    "reference_low": "4.0",
                    "reference_high": "6.0",
                },
            ],
        },
    )
    assert keyed.status_code == 201, keyed.text
    assert keyed.json()["published_count"] == 2
    after = shadow.compare(admin_session, tenant_id=tenant.id)
    row = after[0].as_dict()
    assert (row["proposed"], row["keyed"], row["matched"]) == (6, 2, 2)
    assert (row["unmatched_proposed"], row["unmatched_keyed"]) == (4, 0)
    assert row["field_divergence"] == {
        "value_text": 0.5,
        "unit_text": 0.0,
        "reference_low": 0.0,
        "reference_high": 0.0,
    }
    assert row["keying_delay_samples"] == 1 and row["keying_delay_seconds_median"] >= 0
    # Comparing wrote nothing: the shadow batch has no decision and the record holds only the
    # two keyed values.
    assert admin_session.execute(select(func.count()).select_from(IntakeDecision)).scalar_one() == 0
    assert admin_session.execute(select(func.count()).select_from(Observation)).scalar_one() == 2
