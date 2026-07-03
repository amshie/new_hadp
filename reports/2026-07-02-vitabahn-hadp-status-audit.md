# VitaBahn / HADP — Engineering Status & Documentation-Drift Audit

- **Date:** 2026-07-02
- **Repo:** `/Users/amershieban/Desktop/NEW_HADP`
- **Branch / HEAD audited:** `feat/web-dashboard-vitabahn` @ `50f4769`
- **Scope:** Read-only audit. Nothing was edited, moved, or deleted. This file is the only artifact created (in a new `reports/` folder — none existed).
- **Grounding rule applied:** every "current state" claim below cites a file (and line/section where useful) that was actually opened. Claims that were not opened at the artifact level are marked **not verified** and kept separate from **verified**.

### Method & coverage caveats (read this first)

- The audit combined a 10-agent parallel workflow (7 area-survey agents + 3 adversarial verifiers) with the auditor's own firsthand reads of every doctrine-critical file (interpretation model/service, reports/consent gate, patient-view route, enums, `INTENDED_USE.md`, `CLASSIFICATION_REGISTER.md`, ADR-0003/0005/0006, and the web copy).
- **One survey agent failed** (`backend-services`, StructuredOutput retry cap). That gap is fully covered by the auditor's own reads of the backend modules — those files are cited directly below, so no backend claim rests on the failed agent.
- **Test PRESENCE is verified; test PASSAGE is not.** No suite was executed in this read-only session. Where the report says "23 API test files exist," it means they exist, not that they are green today.
- A second git worktree exists at `.claude/worktrees/tender-elbakyan-954d32` (branch `claude/tender-elbakyan-954d32` @ `b4940eb`); it is a separate checkout and was excluded from the audit of the working tree.
- Two contract files named CLAUDE.md exist: the **in-repo** `CLAUDE.md` (the superseded lab-analytics contract) and a **parent-directory** `/Users/amershieban/Desktop/CLAUDE.md` (the governance-doctrine project-instructions layer). Where they diverge, this is called out.

---

## 1. Executive summary

**What is built.** HADP is a synthetic-data-only Alpha of a physician-governed clinical-decision-**support** platform, and the governance core is real, not scaffolded. The backend (FastAPI modular monolith) implements the ADR-0003 doctrine faithfully in code: a per-patient interpretation run of six domain axes, each carrying **one CIS + one Actionability verdict as two disjoint closed enums in separate DB columns**, plus **three verdict-free tri-state cells** — created only from a whole clinician-authored draft that the service **validates and records but never derives** (`apps/api/src/hadp_api/modules/interpretation/{models.py,service.py}`, `modules/enums.py`). Tenant isolation is enforced at the database with `ENABLE + FORCE ROW LEVEL SECURITY` and a deny-on-missing-GUC predicate, exercised by tests running under the real non-superuser app role (`alembic/versions/0002_security_rls.py`, `tests/test_tenant_isolation.py`). A KPI terminology catalog (120 definitions across the six domains, 43 Core-enabled, LOINC/UCUM mappings, definitions-only) ships (`modules/kpi/catalog_data.py`). Report release is fail-closed behind approval + an active consent event, and the patient view returns released content only (`modules/reports/service.py`, `api/patient_view_routes.py`). The Next.js web app presents six real, tenant-scoped, deny-by-default surfaces (`apps/web/src/app/**`).

**How far along.** By the repo's own milestone map (`CLAUDE.md`), the product is solidly through **Milestone 0–3 on synthetic data**: foundation, the lab vertical slice, timeline/observations, the interpretation model, KPI catalog, derived-value registry, the report lifecycle, and the VitaBahn dashboard. It is **pre-pilot and pre-real-data**: production OIDC/MFA, rate limiting, malware scanning, backup/restore, the async worker's clinical jobs, and — decisively — the legal/regulatory gates (named Regulatory Lead, MDR/MDSW determination, DPA/TOMs/§203, DPIA/ROPA) are all explicitly **pending/absent**, and the docs say so honestly. Doctrine holds where it counts: **no unified score, no %-health-index, no biological-age, no autonomous derivation** anywhere in the shipping product (independently re-verified across `apps/api` and `apps/web`).

> **Scope correction (CTO, 2026-07-02).** An earlier draft of this report led with the observation that no €3.0M Pre-Seed investor pitch page exists in this repo. That is **intentional and out of scope**: the investor pitch page lives in a **separate repository** the CTO built for it; NEW_HADP is the governance / clinician-review synthetic-data Alpha and is **correctly not** the pitch. Its absence here is **not drift and not a gap** — this correction supersedes the pitch-page framing wherever it still appears below.

**The single most important thing the docs get wrong about the current state.** The compliance-facing `docs/regulatory/CLASSIFICATION_REGISTER.md` rows 42–44 still mark the ADR-0005 diverging labels — data-quality **%**, patient **Risiko Hoch/Mittel/Niedrig**, and observation **Normal/Grenzwertig/Auffällig** — as **"Shipped (synthetic Alpha)"**, but the **current** UI has already **gated or replaced all three** on the real-data path per ADR-0006 (Risiko/Datenqualität → "n. v."; Normal/Auffällig → verdict-free positional Lage). A reader who stops at rows 42–44 — exactly the rows a regulator or diligence reviewer would read — is told a diverging, MDSW-exposing surface is live when it is not. The register is internally reconciled only if the reader reaches rows 46–48. This is the highest-consequence documentation drift because it sits in the register that exists specifically to state, truthfully, what is shipped. `CLASSIFICATION_REGISTER.md:42-48` vs `apps/web/src/app/patients/PatientsContent.tsx:15-17,105-107`.

Runner-up drift (same family): `apps/web/DESIGN-VERIFICATION.md` still describes a retired `/worklist` UI generation, ADR-0002 is still marked "Proposed / no code written," and the in-repo `CLAUDE.md`/`AGENTS.md` still carry the *superseded* lab-analytics contract as body text. Otherwise the documentation is **mostly current and unusually honest about its own divergences**.

---

## 2. Component status

Maturity legend: **Shipped** (implemented + within boundary) · **Partial** · **Scaffold/Skeleton** · **Absent/Pending** · **Superseded**.

### 2.1 Interpretation governance core — **Shipped** (doctrine-faithful)
- Six-axis run = 6 verdicts + 18 verdict-free cells; CIS + Actionability are two disjoint closed enums in **separate columns**, tri-state cell carries **no** verdict column. Verified: `apps/api/src/hadp_api/modules/interpretation/models.py:65-138`, `modules/enums.py:108-160`.
- Service is **validate-and-record, never derive**: `create_run` shape-validates a whole clinician-authored draft and records it; corrections are a new append-only run; `latest_matrix` returns CIS and Actionability as two separate fields. Verified: `modules/interpretation/service.py:31-172`.
- Migration `0003_interpretation_axes.py` backs this with CHECK-constrained enums and free-text `rationale VARCHAR(2000)` columns (flagged elsewhere as a redaction concern).

### 2.2 Reports, consent gate, patient view — **Shipped** (fail-closed)
- Lifecycle `DRAFT_GENERATED → DRAFT_EDITED → APPROVED → RELEASED` with meaningful approval (every statement's evidence must be viewable or approval fails) and edit-after-approval invalidation. Verified: `modules/reports/service.py:302-344`.
- **Consent gate fail-closed:** `release_report` requires `APPROVED` **and** an active `report_release` consent, checked after the approval invariant; withdrawal is a new event that revokes live access links. Verified: `modules/reports/service.py:324-344`, `modules/consents/*`, register row at `CLASSIFICATION_REGISTER.md:41`.
- **Patient view returns RELEASED only, else 404 (no info leak):** `api/patient_view_routes.py:1-52`, `modules/reports/service.py:407-423`.
- **Disclosed divergence:** release is permitted to `Role.CLINICIAN`; there is **no `medical_director` role member** (`enums.py:23-28` = OWNER/CLINICIAN/ASSISTANT), although `INTENDED_USE.md:47-52` assigns lock/release to a medical director. Honestly recorded at `CLASSIFICATION_REGISTER.md:41` as a "named (not fixed) divergence." → see §3.

### 2.3 KPI / biomarker catalog — **Shipped** (definitions-only terminology layer)
- **120 KPI definitions across the six DomainAxis, 43 Core `default_enabled`** (confirmed by importing the module and counting). Single source of truth `modules/kpi/catalog_data.py:3,44-437`; idempotent versioned seed `modules/kpi/service.py`.
- **Definitions only** — no reference/optimal ranges, no scores, no CIS/Actionability; enforced by CHECK constraints + `tests/test_kpi_catalog.py`. UCUM canonical units per row; **7 verified LOINC** external codes + explicit source-name aliases (`catalog_data.py:445-472`).
- Secondary-domain layer (migration `0005`, Slice 2): **34 KPIs, 44 navigational-only links**, global non-tenant SELECT-only tables. Verified: `alembic/versions/0005_kpi_secondary_domain.py`, `tests/test_kpi_secondary_domain.py`.
- Blocked-concept KPIs (biological-age, healthspan-score, telomere-age, NAD+) are **absent** by design. The only grep hits for "score" are external **instrument names** in the input catalog (e.g. `cognitive_composite_score`, `SPPB total score`) — input terminology, not computed output.

### 2.4 Derived-value registry — **Shipped** (arithmetic tranche only)
- Deterministic, versioned formula registry writing `source_category='derived'` observations with frozen `formula_id/version` + append-only lineage (`observation_derivation`, migration `0007`), fail-closed on missing/wrong-unit input. First tranche = trivially-safe arithmetic (`non_hdl_c`, `pulse_pressure`, `map`, `nlr`). Verified via `CLASSIFICATION_REGISTER.md:39`, `modules/derivations/*`, `tests/test_derivations.py`.
- **Clinical-estimator tranche (eGFR CKD-EPI, FIB-4, HOMA-IR, ALMI) is BLOCKED** pending clinical + Regulatory-Lead sign-off. Correctly not implemented.

### 2.5 Data layer / infra / security — **Shipped (DB isolation)**, **Pending (production controls)**
- **Genuine DB-level tenant isolation:** every tenant-scoped table has `ENABLE + FORCE ROW LEVEL SECURITY` with a deny-on-missing-GUC predicate `NULLIF(current_setting('app.current_tenant', true), '')::uuid`; app connects as non-superuser `hadp_app`; production boot is fail-fast-guarded against a BYPASSRLS DSN. Verified: `alembic/versions/0002_security_rls.py`, `db/engine.py`, `config.py`, and the app-role tests `tests/test_tenant_isolation.py`, `tests/test_consent_append_only.py`.
- **Append-only** enforced defense-in-depth (BEFORE UPDATE/DELETE triggers + REVOKE) on consent/derivation ledgers.
- **Log-redaction test PRESENT** (emails/tokens/values scrubbed): `tests/test_logging_redaction.py`.
- **Absent / Pending (all self-documented):** production OIDC + MFA/passkeys (dev provider refuses to run in prod — `auth/provider.py`), rate limiting, upload malware scanning (integration point only), backup/restore + RTO/RPO (Milestone 5), CSRF (only `SameSite=lax`, no dedicated token). References: `docs/security/THREAT_MODEL.md:127-131`, `CLASSIFICATION_REGISTER.md:53-60`.

### 2.6 Async worker — **Skeleton**
- `apps/worker` has a real Redis/async seam but processes **no clinical jobs** and has **no idempotency/retry logic or tests**; import normalization currently runs inline in the API. Verified: `apps/worker/src/hadp_worker/main.py:35-45`. (Legitimately un-built, not doc drift — but the `CLAUDE.md` "background-job idempotency/retry tests" layer cannot exist yet.)

### 2.7 Web app (Next.js clinician + patient portal) — **Shipped** (six real surfaces)
- Six surfaces route-load over the real tenant-scoped API via `lib/api.ts`, all server components, deny-by-default (`ApiError 401/403 → /login`), UUID-guarded params: `/overview`, `/patients`, `/patients/[id]`, `/patients/[id]/assessments/[assessmentId]`, `/patient-view`, and `/worklist` (now a **redirect stub** to `/overview`, `app/worklist/page.tsx:1-7`).
- ADR-0006 real-data path confirmed: `/overview` shows a real coverage donut labeled "keine Qualitätsbewertung" (published-share ratio, not a quality score — `OverviewContent.tsx:180-295`), a real throughput chart from persisted `ReportVersion` timestamps, and honestly-gated Risiko/Datenqualität columns rendering "n. v." with "Kein Datenqualitätsmodell (Gate G1)" (`PatientsContent.tsx:15-17,105-107`).
- **Known, planned-for-a-later-phase item (CTO-acknowledged — not a defect or drift):** the presenter computes `cisLabel`, `actionabilityLabel`, and the tri-state `cells` (`lib/presenters/review.ts:114-232`), but the **review card currently renders only `d.actionabilityLabel`** (`ReviewContent.tsx:373`; header copy `:296` = "Actionability-Verdict je Achse. Kein Score.") — CIS and the three tri-state cells are computed but not yet surfaced, and `PatientDetailContent` shows neither. Nothing is merged (the "never merged" invariant holds); rendering CIS + the verdict-free supporting cells is a **deliberately staged product decision scheduled for a future phase**, confirmed by the CTO on 2026-07-02. Tracked, not a surprise. → see §3 and §5.
- **Demo hardcodes:** clinic name is a hardcoded `"Meridian Longevity"` string in the shell topbar and patients header (not threaded from the session tenant); login redirects `/ → /worklist → /overview` (indirect via the legacy redirect, `login/actions.ts:27`). Verified by the drift verifier.
- **No web tests / no web CI:** no route-smoke or DOM tests exist for `apps/web`, and `.github/workflows/ci.yml` runs only lint + types + pytest — the web build, route smoke, and Playwright e2e are **not gated in CI**. → see §4 (contradiction) and §5.

### 2.8 Static HTML mockups & design system — **Superseded** (historical prototypes)
- `HADP-UI-Optimiert-v2/` is a git-tracked, backend-less static prototype (auth → worklist → patient-review) driven by hardcoded synthetic arrays in `assets/hadp.js`. It uses the **pre-ADR-0003 lab-analytics vocabulary** (Regelhinweise/rule-matches, trend/"Funktion" percentages like "62 → 78 %", "Datenqualität/Datenabdeckung 86 %") and contains **none** of the CIS/Actionability/tri-state doctrine. It honors the physician gate (draft-not-released banner, 5-step audit, "signature does not yet publish to patient") but its scoring/percentage content **violates the current product doctrine** — because it is a **superseded artifact**, not the live product. Evidence: `HADP-UI-Optimiert-v2/assets/hadp.js:426-921`, `patient-review.html:121-227`.
- The design zip (`docs/Marker professionell und gemütlich-handoff-2.zip`) is a **Claude Design component export** of a single "Lage zur Referenz" marker (linear + arc variants) plus the "VitaBahn Design System" tokens/manifest — the lineage now driving `apps/web` per ADR-0005/0006. **Not a pitch, not a full app.**
- **Investor pitch page — intentionally absent (out of scope).** The €3.0M Pre-Seed pitch page lives in a **separate repository** the CTO built for it (confirmed 2026-07-02). NEW_HADP is the governance / clinician-review Alpha and is correctly not the pitch; there is no pitch page, commercial framing, or live-site/deployment config here **by design**. This is scope, not drift.

### 2.9 Regulatory / doctrine document set — **Shipped & current** (see §4 for the exceptions)
- `INTENDED_USE.md`, `CLASSIFICATION_REGISTER.md`, `OWNERSHIP.md`, ADR-0003/0005/0006, `README.md`, `THREAT_MODEL.md`, `DATA_FLOW.md`, `WORKFLOW.md` form an internally-coherent, doctrine-holding corpus that matches `enums.py` and the shipped code. MDR positioning is correct throughout (open/pending determination on an MDR pathway; **no "MDR-compliant" overclaim**). All regulatory gates are correctly marked pending; Regulatory Lead is **UNASSIGNED** (all sign-offs are "Founder (acting)"), `OWNERSHIP.md:17-27`.

---

## 3. Doctrine conformance

Independently re-verified against the code by an adversarial verifier (agent type `cto-principal-architect`) **and** by the auditor's own reads.

| Doctrine point | Verdict | Evidence |
|---|---|---|
| Tri-State separation (Biological/Risk/Functional distinct, verdict-free) | **Holds** (structurally) | `interpretation/models.py:105-138` (cell has no verdict column; `UNIQUE(interpretation_id, tri_state_axis)`); `enums.py` TriStateAxis. **UI caveat below.** |
| CIS (0–5) & Actionability (A–E) never merged; no derivation between them | **Holds** | Distinct Enum classes, separate DB columns with independent CHECK, independent validation; `latest_matrix` returns two separate fields. `models.py:85-89`, `service.py:145-172`, `enums.py:118-160` |
| No unified/composite score, no %-health-index, no biological-age | **Holds (product)** | Re-verified across `apps/api` + `apps/web`; only "score" strings are external instrument **names** in the read-only KPI input catalog. Blocked rows intact: `CLASSIFICATION_REGISTER.md:49-51` |
| Physician Gate present wherever an interpretation reaches a user | **Holds, with a modeled-tier gap** | Fail-closed release + released-only patient view are enforced server-side (`reports/service.py:324-344`, `patient_view_routes.py`). **But** the clinician-authors-vs-medical-director-locks *two-tier* separation is **not modeled in code** — no `medical_director` role; release is allowed to `CLINICIAN`. Disclosed at `CLASSIFICATION_REGISTER.md:41`. |
| MDR positioning = pathway / open determination (never "MDR-compliant") | **Holds** | No "MDR-compliant"/"CE-marked"/"certified" claim anywhere; the one "compliant medical-device feature" hit in `ADR-0005:117` is a **negation** ("must not be presented as one"). `INTENDED_USE.md:182-205` |
| Synthetic-data-only | **Holds** | `is_synthetic` marker; `POST /api/v1/patients` forces `is_synthetic=True` (`apps/web/src/app/patients/actions.ts:13`); UI disclaimers ("Synthetische Beispieldaten · keine reale Patientenversorgung", `VitaShell.tsx:365`) |
| €3.0M Pre-Seed commercial framing | **Absent by design — out of scope** | Pitch page lives in a **separate repository** (CTO, 2026-07-02); NEW_HADP is the governance Alpha, not the pitch. Not a gap, not drift. |

**Risks / nuances to log (not hard violations):**

1. **UI does not yet render CIS + tri-state cells — known and planned (CTO-acknowledged; not a defect).** CIS and the three tri-state cells are computed by the presenter but **not yet shown** on the review or detail cards; only Actionability is rendered (`ReviewContent.tsx:296,373`; `presenters/review.ts:114-232`). Nothing is *merged*, so the "never merged" invariant holds. Surfacing CIS + the verdict-free supporting cells is a **deliberately staged product decision scheduled for a future phase** (CTO, 2026-07-02) — recorded here as a tracked item, not a drift or a finding.

2. **Founder-directed doctrine divergences are real but disciplined.** ADR-0005 knowingly shipped, on synthetic data, three surfaces that diverge from "no %/no verdict-label" doctrine (data-quality %, Risiko Hoch/Mittel/Niedrig, Normal/Grenzwertig/Auffällig). Crucially, ADR-0006 + the **current code** already **gated or replaced** all three on the real-data path (Risiko/Datenqualität → "n. v."; Normal/Auffällig → verdict-free positional Lage). So the *live* product holds doctrine; the divergence survives mainly in `CLASSIFICATION_REGISTER.md` rows 42–44 status text (see §4).

3. **Coverage `%` appears in the UI** (`OverviewContent.tsx:295` `publishedPct%`). This is a documented carve-out: a published-share/completeness ratio is explicitly "keine Qualitätsbewertung," not the forbidden unified clinical %. Defensible and cross-referenced (ADR-0006 addendum), but worth the CTO knowing a literal `%` renders.

4. **Anchor phrasing is English-only.** The doctrinal anchor **"validates and records; it never derives"** appears only in English (`INTENDED_USE.md:27`, `README.md`, `enums.py` comments). The German UI carries a *different*, shorter anchor ("**Kein Score**" / "Actionability-Verdict je Achse", `ReviewContent.tsx:296`). There is **no German rendering of the regulatory anchor** despite de-DE being the default locale — so the instruction to "preserve the anchor verbatim in both German and English" currently has no German counterpart to preserve. → see §5.

---

## 4. Report & doc freshness

Per-document verdicts. **CURRENT** = matches current artifacts; **STALE** = describes an earlier state; **CONTRADICTORY** = conflicts with another doc/the doctrine/reality. Every non-CURRENT verdict is evidence-backed and, where two agents disagreed, adjudicated by the auditor.

### 4.1 CURRENT (spot-checked against code)
| Doc | Why current |
|---|---|
| `README.md` | Governance model, no-score, MDR-pending all match `enums.py`/code |
| `docs/regulatory/INTENDED_USE.md` | Matches interpretation model + enums; MDR wording correct (`:27,:182-205`) |
| `docs/regulatory/OWNERSHIP.md` | Regulatory Lead UNASSIGNED / Founder-acting matches sign-offs |
| `docs/adr/0003-adopt-hadp-governance-doctrine.md` | Doctrine matches shipped enums/model |
| `docs/adr/0004-kpi-catalog.md` | 120/43, secondary-domain, SELECT-only all match `catalog_data.py` + migrations |
| `docs/adr/0005-…` / `0006-…` (as ADRs of record) | Accurately describe the decisions; ADR-0006 matches the gated/real code |
| `docs/adr/0001-stack.md` | Stack matches |
| `docs/security/THREAT_MODEL.md`, `DATA_FLOW.md` | Match RLS/consent-gate code; pending controls correctly listed |
| `docs/product/WORKFLOW.md` | Matches report lifecycle |
| `docs/data-governance/THIRD_PARTY_DATA.md` | Consistent |
| `docs/notes/0002,0003,0005 (RLS), 0006, 0007, 0008` | Match current db/auth/CI behavior |
| `HADP-UI-Optimiert-v2/README.md`, marker-zip `README.md` | Accurate for the artifacts they describe |

### 4.2 STALE
| Doc | Verdict evidence |
|---|---|
| `apps/web/DESIGN-VERIFICATION.md` | **STALE (largest live drift).** Documents `/worklist` as the wired home ("## Worklist (FE-4) — MATCHES", "login → /worklist", "307") and `lib/synthetic.ts` wiring. But ADR-0005/0006 retired `/worklist` to a redirect stub, made `/overview` home, and `synthetic.ts` is gone. **No section exists for the VitaBahn Übersicht/Patienten/Detail surfaces that now ship.** The working-tree edit added only two blank lines — no content refresh. `DESIGN-VERIFICATION.md:38-95` vs `app/worklist/page.tsx:1-7`, ADR-0005:124-129 |
| `docs/adr/0002-frontend-backend-wiring.md` | **STALE.** Status still "Proposed … No code is written under this ADR yet," yet its §5 slices shipped (login fix, worklist endpoint, review reads, presenters) and were then superseded by ADR-0005/0006. Status + closing line never updated. `0002:3,146-149` |
| `HADP-UI-Optimiert-v2/DESIGN-REVIEW.md` | **STALE as a product description** (CURRENT as a review of the prototype it critiques). Describes a pre-ADR-0003 lab-analytics MVP (rule matches, Confidence-as-Datenqualität, trend/function). Two agents split CURRENT/STALE; the verifier upheld the nuanced STALE. `DESIGN-REVIEW.md:17-26` |
| `HADP-UI-Optimiert-v2/CLAUDE-CODE-HANDOFF.md` | **STALE.** A vertical-slice handoff that was implemented and then diverged; it never mentions CIS/Actionability/tri-state and recommends the now-retired `/worklist` as a core route. Accurate as history, not as guidance. `:22-42` |

### 4.3 CONTRADICTORY
| Doc | Verdict evidence |
|---|---|
| in-repo `CLAUDE.md` **and** `AGENTS.md` | **CONTRADICTORY / self-superseded by design.** The ADR-0003 banner (`:3-13`) declares the body's lab-analytics intended-use / prohibited-list / forbidden-language **superseded for the product model**, yet the full superseded contract remains the body text (`:67-96`). A reader taking the body at face value gets the wrong product model. `AGENTS.md` is a near-verbatim Codex-branded copy (5 rebrand lines only) → two-source-of-truth maintenance hazard. |
| `CLASSIFICATION_REGISTER.md` rows 42–44 | **Status reads stale-in-isolation.** Rows for data-quality %, Risiko Hoch/Mittel/Niedrig, and Normal/Grenzwertig/Auffällig are marked **"Shipped (synthetic Alpha)"**, but ADR-0006 (rows 46–48) and the current code **gated/replaced** all three ("n. v.", verdict-free Lage). The register is self-consistent only if the reader reaches row 46; rows 42–44 in isolation misstate the live UI. (Register **framing** is otherwise CURRENT.) `CLASSIFICATION_REGISTER.md:42-48` vs `PatientsContent.tsx:15-17,105-107` |
| `CLAUDE.md` gate "`pnpm smoke:routes`" / "`pnpm web:build`" | **CONTRADICTORY / not runnable as written.** Neither script exists in any `package.json`; the repo is Makefile-based (`make web-build` @ `Makefile:136`, `make smoke` = API smoke). The named pnpm gates cannot be run. (This is the parent-`Desktop/CLAUDE.md` gate vocabulary; the in-repo `CLAUDE.md`/Makefile is the accurate source.) |
| `docs/notes/0010-patient-invitation-plan.md` | **CONTRADICTORY (working-tree vs HEAD).** Exists at HEAD (added in `5fa354d`) but is **deleted in the working tree** (`git status: D`, currently **unstaged**). `MEMORY.md` says it "lives in git, not here" — true for HEAD, but the working copy is removed and a commit would drop it. The plan also references a future migration `0009` (repo max is `0008`). |

### 4.4 NOT VERIFIED (named honestly)
- `docs/notes/0001` (git-root note) and `0004` (Next spike) were not opened at artifact level by the freshness sweep — **not verified**.
- External references in ADR-0003 (`~/Desktop/test2/docs/DOCTRINE.md`, `~/Desktop/new_files/hadp-alpha/docs/SCHEMA.md`, `:7-8`) point **outside** this repo/worktree and were not openable — **not verified** (and see cross-ref #3 below).

### 4.5 Cross-reference conflicts (docs that disagree, or reference things that don't exist as stated)
1. **`docs/DOCTRINE.md` does not exist in this repo.** It is named "authoritative" by the **parent** `/Users/amershieban/Desktop/CLAUDE.md:10` and referenced by in-repo `ADR-0003:7` as an **external absolute path** (`~/Desktop/test2/...`). Within `NEW_HADP` the authoritative doctrine is actually ADR-0003 + `INTENDED_USE.md` + `enums.py`, not a file named DOCTRINE.md. The parent contract also tells the reader to read `docs/SCHEMA.md`, `docs/EVENTS.md`, `docs/ACCEPTANCE_TESTS.md` — **none of those exist here** either. Net: the parent-directory contract describes a differently-organized sibling repo; the in-repo contract is the accurate one.
2. **`CLAIMS_REVIEW.md` referenced but absent** (`INTENDED_USE.md:174-176`, `OWNERSHIP.md`). Correctly marked *pending*, so this is a planned-not-yet-created pointer, not a broken link — but it is a claimed control with no artifact.
3. **ADR-0005 §Consequences vs later commits.** ADR-0005:128 says "the worklist API/presenter helpers **remain** as unused library surface." Commit `d66fcec` then **removed** them, and ADR-0006 **re-added** `worklist()` as an active real-data helper (now present: `api.ts:182-193`). So the ADR-0005 line is stale, and neither ADR-0005 (Status still "Accepted," not "superseded") nor ADR-0006 marks ADR-0005 as superseded even though ADR-0006 changes 3 of its 4 surfaces.
4. **`CLASSIFICATION_REGISTER.md` marked NOT_VERIFIED by one sweep, CURRENT by another** — adjudicated in §4.3: framing current, rows 42–44 stale-in-isolation.
5. **The forbidden-language mechanism named in the parent CLAUDE.md** (`scripts/check-forbidden-language.mjs`, `packages/core/src/index.ts`) does not match this repo — enforcement is a **pytest** scanner (`tests/test_forbidden_language.py`, `tests/test_web_copy_language.py`) in CI, and there is no `packages/core`. Policy is enforced, but via a different file/mechanism than that contract documents.

---

## 5. Recommended updates (proposals only — nothing applied)

Prioritized. These are reconciliation proposals for the CTO to accept/reject; none were performed.

### P0 — resolved (no action in this repo)
1. **Investor pitch page — resolved.** The €3.0M Pre-Seed pitch page intentionally lives in a **separate repository** the CTO built for it (confirmed 2026-07-02). NEW_HADP is the governance / clinician-review Alpha and correctly contains no pitch. **No action here.** *(Optional: add one line to `README.md` noting the pitch/marketing site lives in its own repo, so future contributors and audits don't re-flag its absence.)*

### P1 — fix drift that would mislead a reader about the current product
2. **Refresh or retire `apps/web/DESIGN-VERIFICATION.md`.** It documents a retired `/worklist` UI generation and deleted `synthetic.ts`; it has no section for the shipped VitaBahn surfaces. Either rewrite against `/overview`+`/patients`+`/patients/[id]` or mark it superseded.
3. **Update `CLASSIFICATION_REGISTER.md` rows 42–44 status** to point at the ADR-0006 resolution (rows 46–48) — e.g. "Superseded on the real-data path; see rows 46–48" — so the "Shipped" diverging-label rows aren't read in isolation.
4. **Update `ADR-0002` Status** from "Proposed / no code written" to Accepted-then-superseded (by ADR-0005/0006), and mark **ADR-0005 as partially superseded by ADR-0006**.
5. **Resolve the in-repo `CLAUDE.md`/`AGENTS.md` self-supersession.** Either trim the superseded lab-analytics body to a pointer to `INTENDED_USE.md`, or add an unmissable per-section "SUPERSEDED — see ADR-0003" marker. Consider generating `AGENTS.md` from `CLAUDE.md` to kill the two-source-of-truth drift risk.
6. **Decide `docs/notes/0010`'s fate.** It's deleted in the working tree but live at HEAD and referenced by `MEMORY.md`. Either restore it or commit the deletion and update `MEMORY.md`; note its stale `0009` migration reference.

### P2 — product-fidelity and doc-hygiene
7. **Surface CIS + the tri-state cells in the web UI — already a planned phase item (CTO-acknowledged).** The presenter computes them; rendering them on the review/detail cards is scheduled for a future phase, not a newly-found gap. Recommended supporting action: **record the deliberate deferral in an ADR or a `CLASSIFICATION_REGISTER.md` note** so the "Actionability-only for this iteration" choice is on the record until the phase lands (keeps the doc set honest about why CIS/cells aren't yet visible).
8. **Reconcile the gate vocabulary.** The parent `CLAUDE.md` names `pnpm smoke:routes`/`pnpm web:build` and `scripts/check-forbidden-language.mjs`/`packages/core` that don't exist here; the repo is Makefile+pytest based. Align the contract to the real `make` targets and pytest scanners (or add the pnpm scripts).
9. **Fix the ADR-0003 external doctrine paths** (`~/Desktop/test2/...`) — replace hardcoded machine-absolute paths with in-repo references (ADR-0003 / INTENDED_USE.md) so the "authoritative doctrine" pointer resolves inside the repo.
10. **Add web CI coverage.** `ci.yml` runs no web build, route smoke, or e2e. Add at least a web build + route-smoke gate (the `smoke:routes` the contract already assumes).
11. **Provide a German rendering of the regulatory anchor** ("validates and records; it never derives") if the de-DE default locale is to carry the doctrinal anchor bilingually; today only the shorter "Kein Score" German anchor exists.
12. **De-hardcode the demo tenant name** ("Meridian Longevity") in the shell/patients header — thread the selected tenant through, so the dashboard doesn't misrepresent multi-tenancy in a demo.

### Housekeeping (non-doctrinal)
13. Create `CLAIMS_REVIEW.md` (referenced-but-absent) or downgrade the references to "planned."
14. Note the second worktree (`.claude/worktrees/tender-elbakyan-954d32`) — confirm it's intentional and not a stale checkout drifting from `feat/web-dashboard-vitabahn`.

---

### Appendix — what "verified" vs "inferred" means here
- **Verified (opened firsthand):** `enums.py`, `interpretation/models.py`, `interpretation/service.py`, `reports/service.py` (grep-level), `patient_view_routes.py`, `INTENDED_USE.md`, `CLASSIFICATION_REGISTER.md`, `ADR-0003/0005/0006`, `worklist/page.tsx`, `api.ts`, `ReviewContent.tsx`/`PatientsContent.tsx`/`OverviewContent.tsx` (grep-level), `catalog_data.py` (grep-level), git HEAD/working-tree state, `docs/adr` listing, CLAUDE.md/AGENTS.md diff, the extracted marker zip.
- **Inferred / agent-reported (cited but not re-opened line-by-line by the auditor):** exact worker skeleton internals, the full migration-by-migration RLS enumeration, the CSRF `SameSite=lax` detail, and the "no web tests" enumeration — these come from the survey/verify agents and are cited to their evidence files; they are consistent with the auditor's own reads but were not independently re-opened at every line.
