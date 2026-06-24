# ADR-0002: Wiring the frontend to the backend — contract direction, sequencing, gates

- Status: **Proposed** (planning only — not yet implemented; awaiting go-ahead + two human gates)
- Date: 2026-06-21
- Deciders: Engineering; gates owned by Regulatory Lead + clinical/founder (see §6)
- Supersedes/relates: ADR-0001 (stack). Reviewed pre-implementation by the CTO-architect
  and senior-fullstack agents; this ADR records their converged findings as decisions.

## 1. Context

Login is wired to the real API. The **worklist** and the **patient assessment review** still
render a hardcoded fixture (`apps/web/src/lib/synthetic.ts`). A proposal asked to treat the
synthetic types as the API response contract and do a "mechanical swap". A two-reviewer
pre-implementation review rejected that framing. This ADR captures the corrected plan.

Two decisions in this ADR are **deferred behind human gates** (§6) and, per the current
go-ahead, **only the ungated work in §5 will be built** when implementation starts.

## 2. Findings that drive the decision (both reviewers concurred)

1. **`synthetic.ts` is a view-model, not a contract.** ~70% of its string fields are
   pre-formatted `de-DE` display strings or un-provenanced derived labels:
   `updated: "vor 2 h"`, `current: "5,4 %"` (unit+comma fused), `change: "↓ 0,4 %"`,
   `trend.detail: "62 → 78 %"`, derived labels `"Verbessert"/"Hoch"/"Stabil"`, and
   `WORKLIST_STATUS` even carries **CSS class names** + German button labels. Returning that
   shape from the API would violate CLAUDE.md: raw/derived/narrative separation, `de-DE`
   localization-readiness, and per-value provenance (a label "Verbessert" with no rule ID /
   input observation IDs / version is the prohibited "inferred-as-measured" failure).
2. **Half of "Phase A" is new domain modeling, not wiring (grep-confirmed):** there is **no**
   `Assessment` entity, **no** six-domain taxonomy, **no** `RuleDefinition`/`RuleEvaluation`
   (only a dangling, unbacked `rule_evaluation_id` column on `ReportEvidence`), and **no**
   data-quality/coverage concept in `apps/api/src`. The worklist attention-summary and
   data-quality, and the review's six domains + rule status, require new models/migrations/
   services — additive (safe) migrations, but **the clinical meaning they encode is gated**.
3. **The ready, correct primitives** already exist and are tested: report lifecycle
   (`draft → approved → released`, evidence-gated approval, release-after-approval,
   edit-invalidates-approval, released-only patient view) in
   `apps/api/src/hadp_api/modules/reports/service.py`; RLS tenant isolation
   (`alembic/versions/0002_security_rls.py`); structured observation timeline
   (`modules/observations/service.py`, `api/observations_routes.py` already returns
   separate `value`/`unit`/`reference_low`/`reference_high`/`delta_vs_previous`).

## 3. Decisions

1. **Contract direction (reversed from the proposal).** API endpoints return **structured
   data with machine codes + per-item provenance** (the observation/report contracts already
   do). The **frontend owns a presenter/formatter layer** that turns structured DTOs into the
   existing view types (`WorklistItem`, `ReviewDomain`, …) — this is what preserves the pixel
   match while keeping `de-DE` formatting and badge/status mapping in the frontend.
   - New: `apps/web/src/lib/presenters/{worklist,review}.ts`.
   - `synthetic.ts` is split: **view types + `WORKLIST_STATUS` badge/label map + formatter
     helpers are kept** (view config, moved into the presenter layer); **fixture _data_ is
     deleted** once its endpoint exists. "Still needs the fixture data" ⇒ missing endpoint.
2. **No un-provenanced derived field on the wire.** Any derived label/percentage an endpoint
   returns must carry `rule_id`/algorithm id + input observation ids + version. Reviewer
   blocks a Pydantic field like `trend_label: str = "Verbessert"`.
3. **Real UUID id-threading** worklist → review → approve. Worklist rows carry real
   `patient_id` + `report_id` (UUIDs). The review route is keyed by `report_id`; the synthetic
   `assessments/2`/`P-2026-0017` literals are removed. Route params are **UUID-validated**
   before any rendered shell (CLAUDE.md), `notFound()` on a bad id.
4. **New read endpoints declare `response_model`** (the existing report endpoints return
   `dict[str, Any]` and are therefore untyped in the generated client — do not repeat that).
5. **Every new read uses the existing authz pattern** `Depends(require(Action.X))` →
   tenant-scoped query (never bare `get_db`, which is reserved for the unauthenticated patient
   view). Every new write emits an audit event.
6. **Two decisions are deferred behind human gates (§6)** and excluded from the first build.

## 4. Open contract sketches (ungated reads — structured, NOT synthetic display strings)

```
GET /api/v1/worklist?status=&q=        (Action.PATIENT_READ; tenant-scoped)
WorklistRowOut {
  patient_id: UUID            # → review route
  report_id: UUID | null      # → getReport/approve; null if no draft yet
  display_name: str           # raw; frontend builds initials
  external_ref: str | null
  sex: str | null; date_of_birth: date | null   # frontend formats "M · 52 J."
  report_status: ReportStatus | null            # enum; frontend maps to badge/label
  updated_at: datetime (UTC)                      # frontend formats "vor 2 h"
  # attention summary + data_quality: OMITTED until the rules/coverage gate (§6) clears
}
```

- Review reads use **existing** endpoints: `GET /reports/{report_id}` (source-grounded draft +
  inline evidence) and `GET /patients/{patient_id}/observations` (structured markers:
  current/previous/delta/reference + per-observation `source` provenance). The **six-domain
  grouping + derived trend/rule-status/function/coverage is gated** (§6) — until then the
  review shows the real draft + raw markers without the domain rollup, with the domain/quality
  cells in an explicit "noch nicht verfügbar" empty state.
- Dashboard aggregate feeds (stat counts, "Letzte Aktivität", "Datenqualität heute") are
  **deferred** to a later slice; the recent-activity feed, when built, reads the append-only
  `audit_events` and composes names at read time via a tenant-scoped lookup (audit `detail`
  stays PII-free — do not write names into audit).

## 5. Execution plan — what gets built first (ungated)

Build in this order; each slice ends only when wired AND verified (Playwright at 1440/390 +
negative tests). Verify against `next build && next start` (not `next dev` — `.next`
corruption), expecting worklist/review to flip static → dynamic once they fetch per request.

- **Slice 0 — Foundation (no new endpoints).** Presenter-layer scaffold; **fix the login
  swallow** (`app/login/actions.ts` currently proceeds on failure → a silently-failed login
  becomes a logged-in shell that 401s on real data) and map `ApiError` 401/403 → redirect to
  `/login`; UUID-guard the review route params.
- **Slice 1 — Worklist table on real data.** Add `GET /worklist` (§4). Presenter →
  `WorklistItem`. Wire `app/worklist/`. Attention/data-quality columns render the empty state
  (gated). Negative test: tenant B sees none of tenant A's rows.
- **Slice 2 — Review reads.** Point `app/patients/[id]/assessments/[assessmentId]/` at
  `getReport(report_id)` + `timeline(patient_id)`; render real draft narrative + raw markers
  (provenance preserved). Domain rollup stays empty (gated). UUID-validate params.
- **Slice 3 — Patient view fix.** `release_report` builds `patient_view_url` against the API
  host (`:8000`) instead of the web `patient-view` page — correct it so released content is
  viewed through the web route (released-only behavior already enforced server-side).
- **Slice 4 — Negative-test hardening (proof, not eye).** Server-side + web assertions:
  cross-tenant read empty/404; approval without complete evidence refused; release before
  approval refused; bad-UUID param → `notFound()`; unauthenticated worklist → redirect.
- Pin the demo seed to the prototype dataset for the pixel-match showcase shot; add
  data-tolerant DOM smokes (long names, empty list, one-sided reference, no-previous marker).

## 6. Deferred — blocked on human gates (NOT built in the first pass)

Per the current decision, both are **parked**; the work below waits for sign-off.

- **Gate G1 — Regulatory/classification (Regulatory Lead + classification register).** The
  six domains + "function" axis + derived rule-status + data-quality/coverage% are adjacent to
  the **excluded** "biological-age / disease-risk score" and "autonomous risk prediction"
  classes. A determination + classification-register entry is required **before** the
  domain/rules/coverage model is designed. Blocks: worklist attention-summary & data-quality,
  the review six-domain rollup, the rules engine, coverage.
- **Gate G2 — Signature state semantics (clinical/founder).** The UI "Review signieren" is a
  _clinical review sign-off that does not release_; the backend lifecycle has no intermediate
  `clinically_reviewed` state (only `DRAFT → APPROVED → RELEASED`, clinician-only). Decide:
  add an intermediate state, or relabel the action. **Until decided, the review signature stays
  UI-only (unwired to the lifecycle).** The report _draft read_ (Slice 2) is unaffected.

## 7. Consequences

- The "mechanical swap" is replaced by a small presenter layer + a few structured read
  endpoints; the screens barely change, so the pixel match is preserved.
- The richest parts of the previews (domain rollups, attention, data-quality, dashboard
  aggregates, the live signature) are **explicitly not delivered** in the first pass and remain
  on placeholder/empty states until the gates clear — this is visible and honest, not faked.
- No destructive migration is implied; all new tables/columns are additive. The migrations are
  safe; the _meaning_ of the gated ones is what needs human sign-off.

## 8. Status / next step

Awaiting: (a) go-ahead to build §5 (ungated), and (b) G1 + G2 decisions before §6. No code is
written under this ADR yet.
