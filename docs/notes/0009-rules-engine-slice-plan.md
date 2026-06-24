# 0009 — Milestone-2 Rules-Engine slice plan

**Status: PLAN ONLY — not started.** This note records the agreed implementation plan for the
Milestone-2 rules engine so it survives across sessions. It is not an ADR (no decision is being
ratified here) and it does not authorize the build; each PR below still goes through the normal
branch + PR + green-CI + squash-merge cadence, and the founder/Regulatory-Lead gates in §7 are
hard gates that precede merge.

The plan was produced by a grounded multi-specialist read of the repo (doctrine-fit, data model,
architecture, API/UI, test matrix) and then **adversarially reviewed for doctrine leaks and false
integration claims**. The adversarial pass materially changed three things; they are called out
inline because they are the load-bearing corrections:

- **`build_timeline` cannot be the single delta path as-is.** `TimelinePoint` exposes no
  `prev_value` and no percentage change (`apps/api/src/hadp_api/modules/observations/service.py`),
  and `build_timeline` has **no supersession filter** — a change rule built directly on it would
  compute a "change" against an observation the lab has withdrawn. → A shared `comparable_pairs`
  helper is built **first** (PR 1a-0).
- **Wiring `report_evidence.rule_evaluation_id` in 1a is a path to a patient without a guard.** The
  meaningful-approval validator (`apps/api/src/hadp_api/modules/reports/evidence.py`) only checks
  *observation* viewability, not rule-evaluation viewability. → The FK is **deferred** to the slice
  that also extends `validate_statements`; when added it is `ON DELETE RESTRICT`, not `SET NULL`.
- **The `reason` field was the real language leak.** "above/below interval" is one careless enum
  value away from "high"/"low"/"abnormal". → A closed, strictly neutral `RuleResultReason` enum is
  part of this slice and its **values** (not just UI labels) must pass the language scanners.

---

## 0. Doctrine verdict (the gate before any code)

A deterministic rules engine **fits** under ADR-0003 — but **only as a recorder of verdict-free
facts** about already-*published* observations. It **records; it never derives**
(`docs/adr/0003-adopt-hadp-governance-doctrine.md:35-36`). A rule match must never *be, suggest,
weight, or be read as* a CIS or Actionability verdict or a tri-state cell
(`docs/regulatory/INTENDED_USE.md:128-134`). No unified score, no %, no per-domain index, and **no
aggregate counts** — the "domains + rule counts" model is exactly what ADR-0003 superseded
(`:19-20`).

Hard invariants — each becomes a structural guard **and** a test, not a sentence:

| #  | Invariant |
|----|-----------|
| I1 | A `RuleEvaluation` is structurally **incapable** of writing into the interpretation/verdict tables. |
| I2 | Reference comparisons use **only** the lab-provided `reference_low/high` on the Observation — never an introduced "optimal" bound. |
| I3 | Change rules fire only on a **comparable** delta (comparability gate, fail-closed) and only over **published, non-superseded** observations. |
| I4 | No aggregate / count / group-by read surface — facts stay atomic per observation. |
| I5 | Closed vocabulary in the **enum values themselves**, not just the UI label. |
| I6 | Append-only evidence, RLS tenant-scoped, synthetic-only — mirror `observation_derivation`. |

---

## 1. Scope & PR cut (small, reviewable slices)

Exactly **two** rule categories, because the second proves the valuable part (comparability):

1. **out-of-source-reference-interval** — deterministic restatement of the lab interval already on
   the Observation.
2. **change-since-previous-comparable** — the comparability-gate proof.

Rules are **code-defined** in a frozen registry (like `derivations`); thresholds are frozen by
`rule_version`. **No `RuleDefinition` config table in 1a.**

| PR | Content | Why separate |
|----|---------|--------------|
| **1a-0 (prerequisite)** | New **public** helper `comparable_pairs(db, patient_id)` in the observations module → `(prev_obs, cur_obs, abs_delta, pct_delta, comparability, reason)`, **excludes superseded + non-published points**, keyed on canonical KPI identity, resolves policy via `resolve_comparison_policies`. Refactor `build_timeline` onto it → **one** delta path. | Closes the false "single delta path" claim and the supersession leak. No new table; testable against existing fixtures. **Build first.** |
| **1a-1** | Migration **0008**: `rule_evaluations` + append-only M:N child `rule_evaluation_observations`; closed enums in `enums.py`. **No** `report_evidence` FK. | Schema only; mirrors `observation_derivation` (0007). |
| **1a-2** | `rules` module: `registry.py` (pure rules) + `service.py` (controlled apply). | Engine logic, unit-testable without a DB. |
| **1a-3** | Read endpoint `GET /api/v1/patients/{id}/rule-evaluations` + `gen:client` + `openapi.test.mjs` allowlist. | API surface + client regen (CI gate). |
| **1a-4** | Seed (synthetic, idempotent, fail-closed) + full test matrix. | Demo data + proof. |
| **1b** | Review UI: a `rule match` indicator in the Beobachtungsnachweis table, **structurally** separated from verdict cells; DE/EN copy mirroring `comparabilityCopy.ts`; language scan green. | UI separate, as Slice 3 → Marker-UI. |

**Explicitly deferred (own, gated slices):**

- **`report_evidence.rule_evaluation_id` FK** — *not* in 1a. Wiring it is the path by which a rule
  match reaches a report → approval → patient, and `evidence.py` validates only observation
  viewability today. → Only in the slice that **extends** `validate_statements` to gate
  rule-evaluation evidence; and then `ON DELETE RESTRICT`, **not** `SET NULL` (append-only).
- **clinic-configured threshold** → introduces the `RuleDefinition` config table (closest to an
  "optimal range" → its own classification-register review).
- **missing-expected-metric, stale-data** → need config (expected-metric set / staleness duration),
  follow with `RuleDefinition`.

---

## 2. Data model (migration 0008 — mirror `observation_derivation` verbatim)

**`rule_evaluations`** (append-only evidence):
`id`, `tenant_id` (NOT NULL, FK→tenants CASCADE, **direct**, indexed), `patient_id` (indexed),
`rule_id`, `rule_version` (snapshot string), `category` (enum), `result` (enum), `reason` (enum),
`thresholds_used` (Numeric/JSONB **snapshot**), `units_used`, `evaluated_at`. **No** column for
score / % / severity / CIS / Actionability / optimal (I1, I2).

**`rule_evaluation_observations`** (append-only M:N, like `observation_derivation`):
`rule_evaluation_id`, `observation_id`, `role`, `tenant_id`;
`UNIQUE(rule_evaluation_id, observation_id, role)`.

**Closed enums** (`native_enum=False`, CHECK-backed, like CIS/Actionability):

- `RuleCategory`: `out_of_source_interval`, `change_since_previous`
- `RuleResult`: `match` / `no_match` / `not_evaluable`
- **`RuleResultReason`** — *new; this was the leak* — directional/neutral only:
  `above_source_interval`, `below_source_interval`, `within_source_interval`, `delta_present`,
  `not_comparable`, `no_prior`, `not_evaluable`. **Forbidden as values:**
  `high`/`low`/`abnormal`/`normal`/`elevated`/`out_of_range`/`risk`. The enum *values* must pass the
  language scanners because they surface in the API payload and copy keys (I5).

**RLS + append-only (verbatim from 0007):** `GRANT` to `hadp_app` → `ENABLE` + `FORCE ROW LEVEL
SECURITY` → one `tenant_isolation` policy on `_TENANT_PREDICATE`
(`tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid`, USING + WITH CHECK) →
`REVOKE UPDATE, DELETE FROM hadp_app` → an **own** `BEFORE UPDATE OR DELETE` trigger function
`hadp_block_rule_evaluation_mutation` (do **not** reuse the derivation function, or the downgrade
`DROP FUNCTION` breaks). `down_revision='0007_derived_observations'`.

**Identity / idempotency:** `(tenant, patient, rule_id, rule_version, ordered input-observation-id
set)`. In 1a thresholds ⊂ `rule_version` (registry-frozen), so the key is complete: same inputs →
idempotent no-op; changed inputs → **new** row, old one stands. (The threshold-variation case
arises only with the clinic-threshold slice → there add `supersedes_rule_evaluation_id` or widen
the key.)

---

## 3. Engine (`rules` module, peer to `derivations`)

- **`registry.py`** — `@dataclass(frozen=True) Rule(rule_id, rule_version, category, evaluator)`;
  `evaluator` is **pure** (no DB/IO) over already-resolved inputs. Version is part of identity
  (changed threshold/operator/rounding = new version). Mirrors `derivations/registry.py`.
- **`service.py`** — `evaluate_rules(...)`: **explicit controlled** call (like `compute_derived`,
  never automatic on import), **fail-closed**, idempotent, append-only new-row.
  - Out-of-interval: reuse the **same pure predicate** that already exists inline in
    `apps/api/src/hadp_api/modules/reports/narrative.py:74-86` (extract it → one source, no drift).
    Missing/one-sided bound → `not_evaluable`, never guess "within". `thresholds_used` are **copied
    from** the Observation's `reference_low/high`; a test asserts equality and forbids any
    rule-supplied numeric range (I2).
  - Change rule: consume **only** `comparable_pairs` (PR 1a-0) → on `not_comparable` ⇒
    `result=not_evaluable`, **no number** (I3). It computes **no** delta of its own.
- **Module boundary:** call **only public services** (`comparable_pairs`,
  `resolve_comparison_policies`); do **not** import the `Observation` ORM for its own queries (the
  tempting violation — `derivations/service.py` does it; the rules module must not).
- **Audit:** `record_audit` (identifiers/codes only); raise `IntendedUseViolation` (HTTP 409) on a
  closed-vocabulary breach, like the interpretation service.
- **I4 guard:** the module exports **no** count/aggregate/group-by function; an architecture test
  asserts this.

---

## 4. API + UI

- **`GET /api/v1/patients/{patient_id}/rule-evaluations`** — tenant-scoped, deny-by-default,
  **404-no-leak**, snake_case; closed enums + provenance only, no score/verdict. → regenerate
  `gen:client`, commit the `openapi.json` diff, update the `openapi.test.mjs` allowlist (CI gate).
- **UI (1b):** indicator in the Beobachtungsnachweis table, **structurally** separated from verdict
  cells (CIS/Actionability live on the interpretation model, not on the evidence table) — a
  **different component, different service, no shared state**, not just CSS. DE/EN copy enum-keyed
  in a **single scanned file** like `comparabilityCopy.ts`. Labels: **`rule match` only** (see the
  founder gate on "attention item").

---

## 5. Test matrix (slice-done criteria)

- **Comparability negative test** (most important): the change rule emits **zero** evaluations over
  a non-comparable pair — reuse the body-composition fixture from `test_comparability.py`.
- **Supersession negative test**: no match against superseded points.
- Per category positive + no-match; out-of-interval: above / below / within / one-sided-high /
  one-sided-low / both-NULL=no-match; thresholds == observation bounds.
- **Append-only**: `UPDATE`/`DELETE` on `rule_evaluations` → `DBAPIError` (under `hadp_app`).
- **RLS cross-tenant**: under the `hadp_app` session — own rows visible, foreign 0/404, no context 0
  (three layers, like `test_tenant_isolation.py`).
- **Idempotency/determinism**: re-running yields identical evaluations, no duplicate rows.
- **Frozen provenance**: `rule_version` + inputs + thresholds frozen at write time.
- **High-risk** (CLAUDE.md): exact `Decimal` arithmetic; confusable units (no compare across
  differing `normalized_unit`); impossible/very large values; date-only without inventing a time;
  published/non-superseded inputs only.
- **Language scan**: `apps/api/tests/test_web_copy_language.py` + `test_forbidden_language.py` green
  (including the new enum values / copy keys).

---

## 6. Gates (this repo's actual gates — not the sibling repo's)

`make lint` (ruff + pnpm lint) · `make typecheck` (mypy `src` — new module fully annotated like
derivations) · `make test-db` (pytest incl. RLS/append-only; the language scanners run as pytest) ·
**`gen:client`** when the API changes (commit it) · `make smoke` for 1b.

**Not applicable here:** `pnpm quality/test:db/web:build/smoke:routes`, the `.mjs` language scanner,
the `WorkflowError` structural assertion, the page-file textual scan, and the UUID-query guard —
those artifacts do not exist in this repo (verified by the architecture review). The language gates
exist here as **pytest scanners** under `apps/api/tests/`.

---

## 7. Founder / Regulatory-Lead gates (hard gates before merge — not engineering defaults)

1. **Register sign-off:** the "Clinic-configured rule matches" row
   (`docs/regulatory/CLASSIFICATION_REGISTER.md:34`) is *Touches clinical meaning = Yes* → a
   Regulatory-Lead sign-off is required **before merge**. The role is UNASSIGNED. As with the
   ADR-0004 rows 37–39: **Founder (acting)**, dated — or hold the slice until a named lead exists?
2. **"attention item" label:** not on the HADP sanctioned bank (`INTENDED_USE.md:144-148`).
   **Recommendation: drop it, use `rule match` only** (pure provenance) until decided otherwise.
3. **No aggregate read surface, now or later:** touches the anti-"rule counts" decision in ADR-0003.
   Recommendation: confirm, and note in the register that any future rollup view is a **separate
   gated** row.
4. **UI co-display policy:** may rule matches ever appear in the same view as verdicts (structurally
   separated), or must they be a physically separate view? Recommendation: same view allowed, but
   structurally separated (own component/service).

*(Unchanged and not moved by this slice: the MDR/SaMD determination; the Regulatory-Lead
assignment.)*

---

## 8. Top risks → mitigation

| Risk | Mitigation |
|------|------------|
| **Verdict leakage** (a rule match becomes/feeds a verdict) | Schema cannot write into interpretation tables (I1); no FK to interpretation in 1a. |
| **Score by accumulation** (counts → implicit severity index) | No aggregate read surface + architecture test (I4). |
| **Comparability/supersession bypass** (fabricated change) | One delta path via `comparable_pairs` (excl. superseded/unpublished) + negative tests (I3). |
| **"optimal range" via the `thresholds` column** | Out-of-interval thresholds == observation bounds, enforced by test (I2). |
| **Language regression in the `reason` enum** | `RuleResultReason` neutral/directional; scanner covers enum values (I5). |
| **Half-wired report FK** → path to a patient without a guard | FK **deferred** until `validate_statements` is extended; then `RESTRICT`. |

---

## 9. Recommended build order

1a-0 (helper — defuses most risks at once) → 1a-1 (migration) → 1a-2 (engine) → 1a-3 (endpoint) →
1a-4 (seed + tests) → 1b (UI). Each a separate branch + PR, CI green, squash-merge.
