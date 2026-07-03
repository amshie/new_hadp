# VitaBahn / HADP — Execution Plan: Synthetic Alpha → Live, Purchasable SaaS

- **Date:** 2026-07-03
- **Repo:** `/Users/amershieban/Desktop/NEW_HADP`, branch `feat/web-dashboard-vitabahn` @ `50f4769` + uncommitted WIP (analyzed as-is)
- **Author:** CTO-directed planning run (Claude Code). Analysis-only session: this file is the only artifact created; nothing else was edited.
- **Method:** firsthand reads of every doctrine-, regulatory-, and gate-critical file, plus a five-agent parallel evidence sweep (backend/data, frontend/product, security/data-protection, regulatory/clinical, legal/commercial/ops), each instructed to cite `file:line` and to report NOT FOUND rather than infer. The 2026-07-02 status audit (`reports/2026-07-02-vitabahn-hadp-status-audit.md`) was used as input and re-verified against the tree; where this run found it stale or wrong, that is called out (§2.8, Appendix A).
- **Grounding rule:** every "done / not done" call below cites an artifact that was actually opened in this run. If no artifact could be pointed to, the item is treated as **not built** and appears in the plan as work.

> **Not legal or regulatory advice.** This is an engineering/program plan. The binding determinations belong to qualified counsel (Fachanwalt IT-/Medizinrecht), a DPO, the named Regulatory Lead, and — for device qualification — a notified body or competent authority.

---

## 0. Fixed constraints the plan must not break

These are held as invariants through every phase. Any phase item that would touch one goes through the documented boundary-change process (`docs/regulatory/CLASSIFICATION_REGISTER.md` "How to use this register") — it is never a silent engineering decision.

1. **Tri-State separation.** Biological / Risk / Functional tri-state cells stay distinct, verdict-free supporting evidence (`modules/enums.py:110-115,154-186`; `docs/adr/0003-adopt-hadp-governance-doctrine.md`).
2. **CIS and Actionability never merged.** CIS 0–5 (`CIS_0_INSUFFICIENT_EVIDENCE` … `CIS_5_STABLE_NO_MATERIAL_CHANGE`) and Actionability A–E (`A_DISCOVERY` … `E_DO_NOT_ACT`) are two disjoint closed enums in separate columns; no function maps one to the other (`modules/enums.py:118-136`, `modules/interpretation/run_shape.py`). **No unified/composite score, no %-health-index, no biological age — anywhere, ever** (BLOCKED rows, `CLASSIFICATION_REGISTER.md:49-51`).
3. **Physician Gate wherever an interpretation reaches a user.** Clinician authors; a medical director locks/releases; patients see released content only (`INTENDED_USE.md:47-52`; enforced release gate `modules/reports/service.py:329-340`, `api/patient_view_routes.py`). The plan closes the two known gaps in this gate (missing `medical_director` role; seed-only authoring path) — it never widens them.
4. **Doctrinal anchor phrasing — preserved verbatim wherever it appears:**
   - **EN (regulatory anchor):** "**validates and records; it never derives**" — `docs/regulatory/INTENDED_USE.md:27`, `README.md:10`, `modules/enums.py:96`, `modules/interpretation/__init__.py:2`.
   - **DE (UI anchors):** "**Sechs Domänen-Achsen · Actionability-Verdict je Achse. Kein Score.**" — `ReviewContent.tsx:296`; "**Pilotumgebung — Synthetische Beispieldaten · keine reale Patientenversorgung.**" — `AppShell.tsx:126`, `VitaShell.tsx:365`.
   - **Sanctioned disclaimers (the only two negations the language scanner permits, `apps/api/tests/test_web_copy_language.py:42-45`):** DE "**keine automatische Diagnose oder Therapieempfehlung.**" · EN "**not a diagnosis or treatment advice**".
   - Note: no German rendering of the *regulatory* anchor exists yet (de-DE is the default locale). Phase 1 adds one alongside — never instead of — the English anchor, routed through the language scan.
5. **Regulatory positioning wording.** The product is **on an MDR pathway**; its MDR/MDSW qualification is an "**open, pending determination**" (`INTENDED_USE.md:5-8,182-205`, `README.md:13-14`). The phrase "MDR-compliant" (or "CE-marked", "certified") is never used, in any language, in any material. "Non-device" is **not assumed by default**.
6. **Synthetic data only** until the human gates clear — mechanically enforced today (`is_synthetic` forced server-side, `modules/patients/service.py:30`; seed refuses `APP_ENV=production`) and kept enforced until the Phase 3 gate ceremony flips it deliberately, per clinic, under contract.
7. **Commercial framing:** €3.0M Pre-Seed. The investor pitch page lives in a **separate repository by design** — its absence here is scope, not a gap. Phases below note where they are raise-gated.

---

## 1. Executive summary

**Where the project stands.** NEW_HADP is a ~2-week-old, single-contributor (`@amshie`), unusually well-governed synthetic-data Alpha. The hard, differentiating core is real and demo-proven: the six-axis interpretation model with disjoint CIS/Actionability closed enums, validate-never-derive enforced in code and tests; FORCE row-level security on all 16 tenant tables with fail-closed GUC binding, tested under the production-like non-superuser role; five append-only ledgers (audit, consent, interpretation runs, cells, derivation lineage); a 120-KPI six-domain catalog; a fail-closed consent gate on patient release; and six real-data web surfaces holding the doctrine in mature German copy. The regulatory record (intended use, classification register, ownership gates) is current, honest, and diligence-grade.

**What does not exist yet** — and is therefore the plan: production identity (no OIDC/MFA; production is deliberately un-runnable today), the approve→release workflow in the UI (server-side only; the sign dialog is an honest Gate-G2 demo stub), interpretation *authoring* through the API (seed-only today), any lab-file parser (register row 29 overclaims this — corrected in Phase 0), review-queue resolution, GDPR data-subject-rights machinery (export/erasure/retention), backups, deployment of any kind (`infra/docker/` is empty; no Dockerfile, no host, no domain), the entire legal/corporate layer (no operating entity — IP currently vests in the GbR individuals — no AVV/DPA, TOMs, ToS, Impressum), the entire commercial layer (no pricing, billing, contracts, provisioning), and the regulatory launch gates themselves (Regulatory Lead UNASSIGNED; MDR/MDSW determination PENDING; DPIA/ROPA not started; UAE workstream at zero and facially in tension with the EU/EEA-only residency doctrine).

**Shortest credible path to purchasable.** One stabilization sprint (Phase 0), then three parallel tracks through Q3 2026 — (a) incorporate and retain counsel/DPO, (b) assign the Regulatory Lead and commission the formal MDR/MDSW qualification determination, (c) close the engineering gap so the governed workflow runs end-to-end in the UI — converging on an EU production platform hardened and pen-tested in Q4 2026 (Phase 2), a real-data design-partner pilot in DACH opening **Dec 2026 – Feb 2027** (Phase 3, "live"), and the contract/pricing/billing layer that converts the design partner into the first paying customer **Feb – Apr 2027** (Phase 4, "purchasable"). The UAE design partner proceeds on a synthetic-demo track now; UAE real-data entry is a separately gated decision with local counsel.

**A defensible target range:** **live (first real patient data, lawfully, in production): Dec 2026 – Feb 2027. Purchasable (first signed order + paid invoice + provisioned tenant): Feb – Apr 2027** — assuming the qualification determination lands on the documentation/decision-support side (Branch A) and the Pre-Seed closes in H2 2026. If the determination goes the MDSW way (Branch B), the full-claims product shifts behind a QMS/notified-body track (~18–30 months) and interim revenue is restricted to counsel-confirmed scope; the €3.0M raise must be sized to survive that branch.

**The three gates most likely to block launch:**
1. **The MDR/MDSW qualification determination** — and its prerequisite, a named Regulatory Lead (`OWNERSHIP.md:17-27` blocks *any* pilot, paid or unpaid, and any clinical-claim marketing until assigned). Everything real-data hangs off this.
2. **The data-protection/contract chain** — incorporation → AVV/DPA + TOMs + §203 safeguards + DPIA + consent taxonomy. No real patient record may exist before it; none of it exists today, and the AVV cannot be signed by a GbR that hasn't assigned the IP it is licensing.
3. **The production-identity + verification chain** — OIDC vendor selection (an explicitly unmade, EU-residency-gated decision) → production environment → independent pen-test → remediation. Longest engineering lead time; starts earliest.

---

## 2. Current-state baseline (evidence-grounded)

Verdicts: **DONE** (implemented + tested, Alpha scope) · **PARTIAL** · **SCAFFOLD** · **NOT FOUND** (treated as not built). Every row cites the artifact behind the call.

### 2.1 Governance core (the product's differentiator) — DONE (Alpha scope), with two authoring gaps
| Item | Verdict | Evidence |
|---|---|---|
| Six-axis interpretation model; CIS/Actionability disjoint; tri-state cells verdict-free; append-only runs | DONE | `modules/interpretation/{models,service,run_shape}.py`; `modules/enums.py:99-186`; migration `0003` (RLS FORCE + append-only); 13 tests |
| Validate-never-derive (no code path computes a verdict or score) | DONE | `interpretation/service.py:31-98`; grep-verified across `apps/api` + `apps/web`; only "score" hits are measured-instrument KPI names (`kpi/catalog_data.py:183`) |
| **Interpretation authoring via API/UI** | **NOT FOUND** | `create_run` called only from `scripts/seed.py:395` + tests; API exposes GET only (`api/interpretation_routes.py:58`); `created_by_user_id` nullable — "clinician authors" is a provenance claim, not an exercisable workflow |
| Report lifecycle server-side (draft→edit→approve→release, evidence-gated approval, consent-gated release, edit-invalidates-approval, released-only patient view) | DONE (API) | `modules/reports/service.py:268-340,407-432`; `test_report_invariants.py`; `REJECTED` enum state unreachable (no setter) |
| **Approve/release in the UI (Gate G2)** | **SCAFFOLD** | `approveReport`/`releaseReport` in `lib/api.ts:201-214` have zero call sites; sign dialog is an honest demo toast (`ReviewContent.tsx:678-684`) |
| **Medical-director role (two-tier Physician Gate)** | **NOT FOUND** | `Role` = owner/clinician/assistant only (`enums.py:25-30`); release granted to CLINICIAN (`auth/authz.py:40-41`); named divergence, register row 41 |
| KPI catalog: 120 definitions (43 core/61 extended/6 specialist/10 research), six domains, read-only, doctrine CHECKs | DONE | `kpi/catalog_data.py`; migrations `0004/0005`; 17 tests |
| Derived values: 4 arithmetic formulas, fail-closed, append-only lineage; clinical estimators BLOCKED | DONE (tranche 1) | `derivations/registry.py:46-91`; migration `0007`; register row 39; no invocation route (seed/tests only) |
| Comparability gating (withhold, never fabricate) | DONE | `observations/comparability.py`; `comparabilityCopy.ts`; 9 tests |
| Consent gate: append-only events, fail-closed release, withdrawal revokes links | DONE (API core) | `modules/consents/`, migration `0008`, `reports/service.py:334-340`, 7 tests. **But:** no consent HTTP endpoint exists (`Action.CONSENT_RECORD` wired to no route); purposes are synthetic placeholders (`enums.py:77-88`); consent changes not audited |

### 2.2 Data layer & tenant isolation — DONE (the strongest area)
FORCE RLS + fail-closed `NULLIF(current_setting('app.current_tenant', true),'')::uuid` predicate on all 16 tenant tables (migrations `0002/0003/0007/0008`); app runs as non-superuser `hadp_app`; production boot refuses superuser/BYPASSRLS DSN (`db/engine.py:22-47`) and weak secrets (`config.py:72-94`); all three documented RLS gotchas (notes `0002/0003/0005`) have verified fixes in shipped code. 118 API test functions run under the RLS-subject role, including cross-tenant negatives and append-only enforcement tested against an admin role. CI provisions the same role (`.github/workflows/ci.yml:65-72`). Known soft spots: the BYPASSRLS guard is production-only (dev/staging can silently fall back to a superuser DSN); `observations.original_*` and approved `report_versions` are immutable by convention, not by trigger; `tri_state_cells.evidence_refs` are not resolved against the patient's own data (cross-patient refs would go undetected).

### 2.3 Web product — DONE for read surfaces; workflow and admin surfaces missing
Eight routes; `/overview`, `/patients`, `/patients/[id]`, assessment review, `/patient-view` all load real tenant-scoped API data server-side, deny-by-default, UUID-guarded (ADR-0006 path; `lib/api.ts`). Doctrine holds in UI: no score/%, no merged verdict, A–E chip deliberately dropped, verdict-free positional Lage, honest gated panels ("n. v.", "keine Qualitätsbewertung"). German clinician copy is mature; synthetic-data banner on every authed screen; copy locked by pytest scanners in CI (`test_web_copy_language.py`, `test_forbidden_language.py`). CIS + tri-state cells are computed by the presenter but **deliberately not yet rendered** (CTO-acknowledged staged decision, 2026-07-02 — a planned phase item, not a defect). **Missing:** login is dev-theater (password/2FA not verified; prod path 404s); logout not wired; hardcoded persona ("Dr. Sarah Johnson"/"Meridian Longevity"); no import/upload UI; no review-queue UI; no consent/invitation UI; no user/tenant admin; no audit viewer; no PDF export; no error boundaries; `patient-view` copy is English; zero web tests; `make test-e2e` calls a script that doesn't exist.

### 2.4 Ingestion — SCAFFOLD (register row 29 overclaims)
What exists: raw-blob upload with checksum idempotency, content-type allowlist, 20MB cap (`documents/service.py:16-52`); manual JSON value entry (`ImportValueIn`, `api/imports_routes.py:28`); deterministic versioned normalization with exact Decimals — but a **6-term terminology map and 4 unit conversions** (`imports/normalize.py:19-35`); review items are created but **can never be resolved** (no endpoint; `ReviewItem.resolved` only ever written False). **NOT FOUND: any CSV/PDF/LDT/HL7/FHIR parser, OCR, supersession matching** (verified firsthand: the only "csv" hits are upload content-type checks). Pipeline states STORED→…→READY are enum values with no setters. Worker is a self-labeled skeleton that logs and discards (`apps/worker/src/hadp_worker/main.py`).

### 2.5 Security & data protection — strong skeleton; production controls NOT FOUND
Present: server-side hashed sessions (httpOnly, 8h TTL, revocable); deny-by-default authz matrix on all 15 tenant route handlers; DB-enforced append-only audit with 20 audited actions; tested log-redaction layer; gitleaks + blocking pip-audit/pnpm-audit in CI; honest STRIDE threat model that matches the code (`docs/security/THREAT_MODEL.md`). NOT FOUND (all self-documented as pending): production OIDC + MFA (dev-login 404s in prod; OIDC stub raises `NotImplementedError`), rate limiting, CSRF tokens (SameSite=lax only), malware scanning, magic-byte upload checks, backups/restore, TLS/encryption-at-rest/production infra of any kind, Sentry/OTEL. Known debts: 7 runtime starlette CVEs consciously allow-listed (`docs/notes/0008`); patient bearer token travels in a URL query param; failed logins and consent events unaudited; `record_security_event` failures are swallowed.

### 2.6 GDPR / data-subject rights — NOT FOUND (documented as pending gates)
No `privacy_requests` module, no export/deletion endpoints, no `DataExportRequest`/`DeletionRequest` tables, no retention controls. Erasure is structurally blocked by design (`ON DELETE RESTRICT` on the consent ledger) pending a DPO-designed retain-then-erase strategy (migration `0008:58-63`, register pending-gate list). DPIA, ROPA, lawful-basis map, consent taxonomy/texts: NOT FOUND — named DPO/counsel deliverables. EU/EEA residency is doctrine but there is no deployment to apply it to.

### 2.7 Regulatory / clinical governance — record excellent; gates all open
`INTENDED_USE.md` (current model, correct MDR-pathway wording), `CLASSIFICATION_REGISTER.md` (~23 feature rows, actively maintained, BLOCKED rows intact, named divergences recorded; working tree already fixes the rows-42–44 staleness the 2026-07-02 audit flagged), `OWNERSHIP.md` (Regulatory Lead **UNASSIGNED** — blocking founder gate). NOT FOUND: formal qualification memo, `CLAIMS_REVIEW.md`, clinical SOPs (clinician review, medical-director responsibilities), adverse-event/complaint intake, named-clinician sign-off of the KPI catalog (ADR-0004's "four-specialist review" includes no named clinician), QMS/ISO 13485/clinical evaluation/PMS (Branch B artifacts), **any UAE/Gulf artifact** (zero mentions of UAE/DHA/DoH/MOHAP anywhere; the EU/EEA-only residency doctrine is facially contradictory with UAE health-data localization — licensed UAE counsel required). Language scanners cover `apps/web/src` + the narrative provider only; docs/README/marketing copy are unscanned claims surfaces.

### 2.8 Legal / corporate / commercial / ops — NOT FOUND (greenfield)
No incorporation artifacts (GbR→entity), founder/shareholder agreement, IP assignment (IP currently vests in the individuals), trademark filing, LICENSE, Impressum/Datenschutz/ToS (login-footer links are dead `href="#"`), AVV/DPA template, TOMs, design-partner agreement, sub-processor list. The **signed UAE design-partner LOI exists outside this repo** (CTO input; not repo-verified). Commercial: zero — no pricing, billing, subscription, payment, sign-up, sales collateral, onboarding runbook; tenants exist only via the synthetic seed. Ops: no runbooks, incident response, on-call, monitoring config, SLAs, backups, support process. Deployment: **no evidence of any environment beyond localhost** (no Dockerfile/hosting config; `infra/docker/` empty; no domain references; CI has no deploy job and no web build). The product live site does not exist yet; the pitch page is a separate repo by design.
**Corrections this run adds to the 2026-07-02 audit:** register row 29 ("CSV laboratory import — Shipped", incl. "parser name/version recorded") overclaims — no parser exists; and the audit's §2/§3 treatment of "clinician authors" missed that authoring has **no API write path at all** (seed-only). Both are Phase 0 record fixes and Phase 1 build items. (The audit's other P1 doc fixes — register rows 42–44, ADR-0002 status, AGENTS.md mirror — are already applied in the working tree.)

### 2.9 Team & repo reality
Single contributor (`@amshie`, 14 commits, 2026-06-24→27 + WIP to 07-03); CODEOWNERS routes everything to `@amshie`. Named humans: the CTO (Amer, `@amshie`); "Dr. Motaz" appears as the clinical stakeholder in the repo's agent definitions (`.claude/agents/clinical-regulatory-liaison.md:3,11`) but no doc formally names a medical director. Regulatory Lead UNASSIGNED. Brand naming is inconsistent across surfaces (package "longevity-health-analytics-platform" / README "HADP" / UI "VitaBahn" / GitHub `new_hadp`) — align before anything public.

---

## 3. Phased plan

Phases overlap deliberately; the gate at the end of each phase is what must be true before the *next* phase's gated work starts, not before any of it starts. Owners are from the founding team: **CTO (Amer)**, **Medical Director (Dr. Motaz — to be formally recorded)**, **Founder/CEO** (corporate & commercial), plus retained externals (counsel, DPO, regulatory consultant, pen-test firm). **Funding key:** 🔓 = can proceed pre-raise on founder budget; 💰 = sized for post-Pre-Seed-close.

### Phase 0 — Close the Alpha, true up the record 🔓
**Objective:** land the in-flight work, make every governance artifact match reality, and add the cheap guardrails the later phases depend on.
**Duration:** 1–2 weeks (Jul 2026). **Owner:** CTO. **Dependencies:** none.
**Work:**
- Merge `feat/web-dashboard-vitabahn` through the established cadence (adversarial self-review, CI green, squash-merge); decide the untracked items (`AGENTS.md`, `.codex/`, design zip, `reports/`) and the stale second worktree (`.claude/worktrees/tender-elbakyan-954d32`).
- **Register truth fixes:** reword row 29 (source-document upload + manual structured entry shipped; CSV *parser* NOT built); add a register note for the seed-only interpretation-authoring divergence and the deliberate CIS/tri-state-cells UI deferral; one-line clarification that `KpiValueKind.SCORE` is a measured-instrument value kind, not a computed composite.
- **CI hardening:** add `next build` + a minimal route-smoke job for `apps/web` (none exists); fix or remove the broken `make test-e2e` target; keep the language scans blocking.
- Small honest-UX fixes: wire `logout()`; remove the login screen's untrue trust claims (2FA/SSO theater) or label them "geplant"; fix the `/worklist` double-hop; add `error.tsx`/`not-found.tsx` boundaries.
**Exit gate:** branch merged; CI builds and smoke-tests the web app; the classification register contains no claim this run's evidence contradicts.

### Phase 1 — Foundations: entity, regulatory determination, workflow completion (3 parallel tracks)
**Duration:** 6–10 weeks (Jul – mid-Sep 2026). **Dependencies:** Phase 0 for 1C merge hygiene; none for 1A/1B.

**Track 1A — Corporate & legal foundation.** **Owner: Founder/CEO** with external counsel. 🔓 start, 💰 to complete.
- Incorporate the operating entity (GbR → GmbH, or UG→GmbH per counsel; the €3.0M raise and §203-exposed health-data processing both effectively require it); founder/shareholder agreements; **IP assignment of the repo, docs, and brand from the individuals to the entity** (currently unassigned — a diligence blocker); trademark search/filing (VitaBahn/HADP) and a deliberate brand alignment decision.
- Retain: Fachanwalt IT-/Medizinrecht, external DPO, regulatory consultant.
- First drafts: AVV/DPA template + TOMs skeleton, design-partner agreement, ToS, Impressum/Datenschutz pages, sub-processor register (empty until vendors chosen), professional-liability + cyber insurance quotes.
**Exit gate (hard, legal):** entity registered; IP assigned; counsel + DPO retained. *The AVV/DPA cannot be signed, and the raise cannot close cleanly, before this gate.*

**Track 1B — Regulatory determination & clinical governance.** **Owner: Founder/CEO (gate) → named Regulatory Lead (execution), Medical Director (clinical artifacts).** 🔓
- **Assign the Regulatory Lead** and record the holder in `OWNERSHIP.md` — the single highest-leverage unblock; until then no pilot (paid or unpaid), no real data, no clinical-claim marketing (`OWNERSHIP.md:21-27`).
- **Commission the formal MDR/MDSW qualification & classification determination** from qualified regulatory counsel, on the exact open question `INTENDED_USE.md:188-199` frames (physician-authored validate-never-derive governance verdicts with a medical-director gate: documentation/decision-support vs MDSW under Annex VIII Rule 11). Input package: intended use, classification register, architecture description, workflow SOPs (below). Target: determination memo on record with rationale.
- Institute **`CLAIMS_REVIEW.md`** and run the first claims review over README, login copy, and any external material (pitch repo included — the claims boundary spans repos); extend the language-scan scope or add a review step for docs/marketing surfaces.
- Clinical governance artifacts: clinician-review SOP, medical-director responsibilities SOP, adverse-event/complaint intake process, **named-clinician (Medical Director) sign-off of the 120-KPI catalog content**, formally record the Medical Director role holder.
- Add the **German rendering of the regulatory anchor** ("validates and records; it never derives") to `INTENDED_USE.md` and user-facing surfaces where the English appears, through the language scan; the English anchor is preserved verbatim everywhere it exists.
- **Open the UAE workstream:** brief licensed UAE counsel (health-data residency under the UAE ICT-in-health framework, DoH/DHA/MOHAP touchpoints, whether the UAE deployment needs its own qualification); define what the signed LOI's design-partner phase may lawfully include **now** (synthetic-demo/workflow validation: yes; real patient data: blocked until this workstream reports).
**Exit gate (hard, regulatory):** Regulatory Lead named in `OWNERSHIP.md`; determination formally commissioned with agreed scope/timeline; claims review live. *(The determination itself lands during Phase 2; see critical path.)*

**Track 1C — Engineering: make the governed workflow real end-to-end (synthetic).** **Owner: CTO.** 🔓
- **Interpretation authoring:** `POST` run endpoint + `INTERPRETATION_AUTHOR` action (clinician-gated), evidence-ref resolution against the patient's own data (closes the cross-patient-ref hole), non-null authorship; authoring UI on the review surface.
- **Two-tier Physician Gate:** add `Role.MEDICAL_DIRECTOR`; keep `REPORT_APPROVE` with the clinician, move `REPORT_RELEASE` (lock) to the medical director; update the register row-41 divergence to resolved; migration + authz-matrix tests.
- **Gate G2:** wire approve/release/reject into the UI (real Freigabe replacing the demo toast); make `REJECTED` reachable; report-version history UI.
- **Consent API** (record/withdraw endpoints, audited) + audit failed logins + stop swallowing `record_security_event` failures.
- **Review-queue resolution** (endpoint + minimal UI) — without it no low-confidence value can ever be published.
- **P-pre security slices** per `docs/notes/0010`: Redis rate limiting (fail-closed), CSRF double-submit + `__Host-` cookies + HSTS, token-out-of-URL + `uvicorn.access` redaction. Then **patient-invitation P1–P3** (invite entity/endpoint → redeem/consent capture → staff link UI + `/einladung` page + reusable four-part disclaimer component), synthetic identities only.
- Clear the 8 allow-listed dependency advisories (upgrade slice); de-hardcode persona/tenant display; real identity/role in the shell; basic member/tenant admin UI; Germanize `/patient-view`.
**Exit gate (engineering):** on synthetic data, a clinician can author an interpretation, a medical director can lock/release, and a patient link can be minted, consented, and viewed — entirely through the product UI, with rate limiting and CSRF in force. This is the demo that sales, the UAE partner, and the determination package all reuse.

**Track 1D — Commercial groundwork (thin, parallel).** **Owner: Founder/CEO.** 🔓
Pricing/packaging hypothesis (site- or seat-based, pilot pricing); design-partner agreement term sheet (counsel); pilot success criteria — anchored on the in-product preparation-time metric (`WORKFLOW.md` §6: per-clinic baseline + workflow timestamps; instrumentation itself is Phase 3 build); UAE partner kept warm on the synthetic-demo track.

### Phase 2 — Production platform & data-protection readiness 💰
**Objective:** an EU production environment that could lawfully and safely hold real special-category data — verified, not asserted.
**Duration:** 8–10 weeks (Sep – Nov 2026), overlapping late Phase 1. **Owner: CTO** (platform), **DPO + counsel** (artifacts), **Regulatory Lead** (gate). **Dependencies:** 1A (entity for contracts/vendors), 1B (determination in progress), 1C (surfaces to harden).
**Work:**
- **EU production platform:** EU-region cloud + managed Postgres (RLS role separation preserved: app role ≠ superuser, BYPASSRLS boot guard extended to *all* environments), EU object storage, TLS, encryption at rest, WAF/rate-limit at the edge, IaC, staging + production, Dockerfiles + CI deploy job, secrets management. Vendor choices go through the sub-processor/EU-residency review before integration (they are the first entries in the sub-processor list).
- **Production identity:** select the OIDC provider (explicitly unmade, EU-residency-gated decision — longest lead item, start week 1 of the phase), integrate + MFA, real logout/session UI, remove dev-login from anything reachable.
- **Observability & ops:** error reporting + metrics + alerting with the redaction layer extended to traces; backup/restore implemented and **restore-tested** with documented RTO/RPO (pilot targets: RPO ≤ 24h, RTO ≤ 1 business day); incident-response runbook; status page; support inbox.
- **GDPR build-out (DPO-led, engineering-supported):** DPIA; ROPA; consent-purpose taxonomy + counsel-authored versioned consent texts replacing `synthetic-v1`; data-subject export; **retain-then-erase** deletion design + implementation (resolving the append-only/RESTRICT tension deliberately); retention policy + controls; TOMs written from the actual controls; finalized AVV/DPA pack; Impressum/Datenschutz/ToS shipped in the web app.
- **Independent penetration test** (scope: tenant isolation/RLS, authn/session, patient-view + invitation token surfaces, upload pipeline) → remediation → re-test. Broaden the cross-tenant test matrix to per-endpoint/per-table ahead of it.
**Exit gate (hard — "Real-Data Readiness Review", the security gate):** pen-test passed with criticals/highs closed; DPIA complete; restore test passed; OIDC+MFA live in production; DSR export + erasure working; TOMs/AVV pack final; every register "pending external gate" except the determination and per-clinic contracts is closed. **No real tenant or patient record exists before this review passes — verified, not assumed.**

### Phase 3 — Design-partner pilot on real data (DACH first) → **"Live"** 💰
**Objective:** first clinic using the product on real patient data, lawfully, in production.
**Duration:** 8–12 weeks (Nov 2026 – Feb 2027). **Owner: Medical Director** (clinical workflow + gate), **CTO** (delivery), **Founder/CEO** (partner relationship). **Dependencies:** Phase 2 exit gate + determination on record + signed contracts.
**Pre-flight gate ceremony (all must be green, recorded in the register):** MDR/MDSW determination memo on record (Branch A assumed; see §4 for Branch B); Regulatory-Lead go-live sign-off; entity + insurance in force; AVV/DPA + TOMs + §203 safeguards signed with the pilot clinic; DPIA covering the pilot; counsel-approved consent texts live; pen-test report accepted. Only then is the synthetic-only enforcement deliberately lifted **for that tenant**, per contract.
**Work:**
- **Pilot-lab ingestion (the fragile path — budget 2–3× naive):** procure a **structured feed** from the pilot clinic's lab (LDT/HL7/FHIR/CSV — a procurement lever before a parsing project); build that one parser with golden-fixture tests; expand the terminology map + unit conversions from 6 terms/4 conversions to the pilot's actual panel (LOINC/UCUM verification per ADR-0004 discipline); supersession/corrected-report matching (conservative, review-queue on ambiguity); import/upload UI + review-queue UI in production use.
- **Preparation-time instrumentation** (the 50% metric): per-clinic baseline capture at onboarding + workflow timestamps (report-prep start → approval), identifiers/timings only — the pilot's conversion evidence; no metrics module exists today, so this is a build item, not a toggle.
- Supervised onboarding: tenant provisioning runbook, staff training, medical-director gate exercised in production, support + incident response live, weekly pilot review against the register (any new clinical-meaning surface gets a row first).
- **UAE track:** design-partner workflow validation on the synthetic demo; UAE counsel report lands → decide the UAE real-data architecture (likely a separate UAE-resident deployment or hosting partner) as its own gated project; convert the LOI into a design-partner agreement scoped to what counsel allows now.
**Exit gate ("live"):** ≥1 DACH clinic on real patient data in production for ≥4 continuous weeks; every release passed the two-tier Physician Gate; prep-time metric flowing; zero unresolved critical security/privacy incidents; Regulatory Lead + DPO sign the pilot-operation review.

### Phase 4 — Purchasable: contracts, pricing, billing, provisioning 💰
**Objective:** a clinic can sign, pay, be provisioned, and onboard — through a documented flow, not founder heroics.
**Duration:** 6–10 weeks (Jan – Apr 2027), overlapping late Phase 3. **Owner: Founder/CEO** (commercial), **CTO** (provisioning/billing plumbing). **Dependencies:** Phase 3 evidence (pricing + case study), Phase 1A contract pack.
**Work:**
- **Contract pack v1 (counsel):** order form + MSA/ToS + AVV/DPA + TOMs annex + sub-processor list + SLA schedule + support terms. Sales-assisted signing flow (e-signature); self-serve checkout is explicitly *not* v1 for special-category B2B health data.
- **Pricing & packaging finalized** from pilot economics (site/seat-based; pilot→production tiers); collateral written inside the claims ceiling and through claims review (no outcome/diagnosis/risk-detection claims; the anchor phrases verbatim; "on an MDR pathway" wording only).
- **Billing:** invoice-first B2B (SEPA/bank transfer; a billing provider only after sub-processor review — it sees no health data by design); subscription/entitlement records; dunning later.
- **Tenant provisioning productized:** create-tenant + owner-invite + OIDC onboarding flow replacing seed-only provisioning; onboarding checklist; provisioning runbook target ≤ 5 business days signature→first login.
- **Trust surface:** security/compliance page (TOMs summary, sub-processors, residency, register-honest regulatory positioning), status page, support tiers.
- **Convert the design partner into the first paying customer** (LOI → paid agreement) and open a small DACH pipeline (2–3 clinics) under the same pack.
**Exit gate ("purchasable", the commercial gate):** first signed order + first paid invoice + tenant provisioned and onboarded through the documented flow; a second, unaffiliated clinic could repeat it without engineering intervention beyond the runbook.

### Phase 5 — Scale & the certification branch (post-launch, 2027+) 💰
**Branch A (determination: documentation/decision-support, non-device):** keep the register/claims discipline as the permanent operating system (per-feature rows, periodic re-assessment, annual counsel review); ISO 27001 (+ BSI C5 attestation for the German health market) as sales enablers; second lab parser + wearable provider per the phase-2 product list; rules-engine slice (`docs/rules-engine-slice-plan` branch exists); CIS + tri-state-cells UI phase (the planned deferral); the founder's "A–E grade later" note is handled **only** through the documented boundary-change process — a merged grade is a rolled-up score and collides with doctrine (`ADR-0006:64-66`); UAE real-data deployment per counsel outcome; hire to break the bus factor (≥2 senior engineers, a clinical-ops hire).
**Branch B (determination: MDSW):** immediate claims/scope freeze to counsel-confirmed non-device functionality (sell the documentation/audit workflow only, if counsel confirms severability); stand up ISO 13485 QMS, technical documentation (Annex II/III), clinical evaluation, PRRC, notified-body engagement (Class IIa assumed under Rule 11), UDI/EUDAMED, PMS; realistic CE timeline 18–30 months and high-six-figure cost — the €3.0M raise must carry this branch; revenue plan shifts to design-partner co-development + restricted-scope subscriptions in the interim.

---

## 4. Critical path & gating

**The chain that sets the go-live (first-real-data) date:**

```
Regulatory Lead assigned (1B, founder decision — days, not weeks)
  → determination commissioned (1B) ──────────────┐
Incorporation + IP assignment (1A) → AVV/DPA capability ─┤
OIDC vendor selected (2) → production platform (2) ──────┼→ pen-test + remediation (2)
DPIA + consent taxonomy + erasure design (2, DPO) ───────┘        │
                                                                   ▼
                        Real-Data Readiness Review (Phase 2 exit gate)
                                   + determination memo on record
                                   + pilot clinic AVV/§203 signed
                                                                   ▼
                                          first real patient data (Phase 3) = LIVE
```

**The purchasable date adds:** pilot evidence (≥4 weeks stable + prep-time metric) → pricing finalized → contract pack executed → billing + provisioning flow → first paid invoice.

**Slip table — what each gate does to the dates:**

| Gate | Owner | If it slips… |
|---|---|---|
| Regulatory Lead assignment | Founder | Blocks *everything* real-data and all clinical-claim marketing (`OWNERSHIP.md:21-27`). Zero-cost to clear; clear it first. |
| MDR/MDSW determination | Regulatory Lead + counsel | Day-for-day slip of Phase 3. If **adverse (Branch B)**: full-product go-live shifts ~18–30 months behind QMS/notified body; pilot continues synthetic-only or counsel-confirmed restricted scope; raise narrative changes — this is the plan's dominant risk. |
| Incorporation + IP assignment | Founder + counsel | Blocks AVV signature (the processor must be the entity), insurance, and the raise close. 4–8 weeks typical for a GmbH incl. notary/registry — start immediately. |
| OIDC vendor + production platform | CTO | Longest engineering lead; a late vendor decision serially delays pen-test → readiness review → pilot. Mitigate by deciding the vendor in week 1 of Phase 2. |
| Pen-test + remediation | CTO + external firm | Booking lead times are 3–6 weeks; findings typically cost 2–6 weeks. Book the slot at Phase 2 start, not end. |
| DPIA / consent taxonomy / erasure design | DPO + counsel | Hard legal prerequisite for real data (Art. 35 will apply to special-category processing at this scale); serially blocks Phase 3 regardless of engineering readiness. |
| Pilot clinic contract (AVV + §203) | Founder + counsel | Clinic-side legal review commonly takes 4–8 weeks — send the pack the day the entity exists; a warm design partner is the mitigation. |
| Pre-Seed close | Founder | Phases 2–4 are 💰 (infra, pen-test, DPO/counsel depth, hires). If the raise slips, Phase 1 (mostly 🔓) still completes; Phase 2 compresses to a minimal EU single-region footprint; dates shift roughly week-for-week thereafter. |

**Funding alignment:** Phase 0–1 are executable pre-close on founder budget (🔓) and are exactly the de-risking evidence the €3.0M Pre-Seed story needs (entity, determination commissioned, workflow complete end-to-end). Phase 2 onward assumes the raise; the plan's dates assume a close in H2 2026.

---

## 5. Definition of done

**Definition of LIVE** — all true simultaneously:
1. EU production deployment (TLS, encryption at rest, EU residency incl. backups) serving the governed workflow; OIDC + MFA; rate limiting + CSRF in force.
2. ≥1 real clinic tenant processing **real patient data lawfully**: entity + insurance in force; signed AVV/DPA + TOMs + §203 safeguards; DPIA on record; counsel-approved consent texts + working DSR (export + retain-then-erase).
3. MDR/MDSW **determination memo on record**; Regulatory Lead go-live sign-off; classification register current with zero overclaims; all public copy claims-reviewed; positioning wording = "on an MDR pathway / open, pending determination", never "MDR-compliant".
4. The **two-tier Physician Gate exercised in production**: clinician authors (API-enforced authorship), medical director locks/releases (dedicated role), patients see released content only; append-only audit + provenance intact end-to-end.
5. Independent pen-test passed (criticals/highs closed); restore test passed with documented RTO/RPO; monitoring + alerting + incident runbook + support channel operational.
6. Doctrine invariants verified in the shipped build: Tri-State separate; CIS 0–5 and Actionability A–E never merged; no unified score/%/biological age anywhere; anchor phrases verbatim (EN + the new DE rendering); synthetic-data labeling now **data-driven and truthful** (no hardcoded `synthetic: True`).

**Definition of PURCHASABLE** — all true simultaneously:
1. A clinic can execute the full contract pack (order form + MSA/ToS + AVV/DPA + TOMs + sub-processor list + SLA) with the operating entity, and **pay** (invoice/SEPA), with the payment recorded against a subscription/entitlement.
2. Provisioning is productized: signature → tenant created → owner invited → OIDC onboarding → first governed release achievable in ≤ 30 days, following the runbook, with **no engineering intervention**.
3. Pricing/packaging is quotable and published to prospects; all sales/onboarding collateral passed claims review and the language ceiling (no diagnosis/risk-detection/outcome/score claims; approved regulatory wording only).
4. Support + SLA are contractual and staffed; status page live; incident and DSR processes tested at least once.
5. At least one paying customer (the converted design partner) is operating on real data — and the flow has been shown repeatable for a second, unaffiliated clinic.
6. The €3.0M Pre-Seed framing is intact: nothing sold or promised exceeds the determination's scope, the register, or the doctrine.

---

## 6. Risks & assumptions

**Assumptions the plan rests on:**
1. Pre-Seed closes H2 2026 (Phases 2–4 are raise-gated; Phase 0–1 proceed regardless).
2. The qualification determination is *obtainable* in 6–10 weeks once commissioned, and Branch A is plausible because the architecture was deliberately built for it (validate-never-derive, no autonomous outputs, medical-director gate) — but the plan does **not** assume the answer (`INTENDED_USE.md:193`).
3. Dr. Motaz accepts the formally recorded Medical Director role; a Regulatory Lead can be named from/around the founding team with external regulatory counsel behind them.
4. A DACH pilot clinic is identified by Phase 3 start (none is named in the repo; the UAE partner is a design partner, not the first real-data tenant, until UAE counsel reports).
5. The pilot lab can provide a structured feed (CSV/LDT/HL7/FHIR) — the ingestion estimate assumes procurement succeeds; PDF parsing would add 2–3× effort (per the repo's own budgeting rule).
6. The signed UAE LOI (outside this repo) does not commit to real-patient-data processing before the UAE regulatory workstream reports.

**Top risks (with phase and mitigation):**
| # | Risk | Phase | Mitigation |
|---|---|---|---|
| R1 | **MDSW determination (Branch B)** — Rule 11 casts a wide net over decision-support software | 1B/2 | Architecture + claims engineered for the documentation-support position; counsel-led framing; severability analysis (which scope remains sellable) prepared *with* the determination; raise sized to survive Branch B; never market ahead of the determination |
| R2 | **Single-contributor bus factor** — all 14 commits are one person; every phase-1C item serializes through the CTO | all | Post-close: 2 senior hires (platform/security + full-stack); the repo's unusually complete docs/tests lower onboarding cost; freeze scope during hiring |
| R3 | **Clinic-side AVV/§203 negotiation drag** | 2/3 | Standard pack early (1A), warm design partner, pilot-friendly terms, counsel with health-sector track record |
| R4 | **UAE residency conflict** — EU/EEA-only doctrine vs UAE health-data localization; possible UAE device/licensing exposure | 1B/3/5 | Treat UAE as a separate gated deployment decision; synthetic-demo track keeps LOI momentum; licensed UAE counsel before any commitment; do not let Gulf enthusiasm pull real data ahead of the gates |
| R5 | **Ingestion underestimation** — today: no parser, 6 mapped terms, 4 conversions; wrong value/unit is the top patient-safety failure mode | 3 | Structured-feed procurement before parser work; golden fixtures; review-queue + supersession discipline; 2–3× budget rule already in the contract (`CLAUDE.md` ingestion section) |
| R6 | **Erasure vs append-only ledger** (Art. 17 vs `ON DELETE RESTRICT` defensibility design) | 2 | DPO-designed retain-then-erase with counsel sign-off *before* real data; already an explicit register gate — keep it one |
| R7 | **Claims drift as marketing ramps** — precedents exist (register row 29 overclaim; login-screen MFA theater; pitch repo outside the language scan) | 1B+ | CLAIMS_REVIEW.md as a standing gate; extend scans/review to docs + marketing + the pitch repo; Regulatory Lead owns a quarterly claims audit |
| R8 | **Prep-time metric missing** — the 50% reduction is the pilot conversion criterion and is not instrumented | 3 | Build baseline capture + workflow-timestamp metrics (identifiers/timings only) as a Phase 3 entry item, not an afterthought |
| R9 | **Founder-direction vs doctrine collisions** (the recorded "A–E grade later" note; ADR-0005 episode) | 5 | Boundary-change process only: documented decision + clinical/privacy/regulatory review before implementation or marketing; the register's BLOCKED rows are the line |
| R10 | **Security regressions during the build-out** — 7 allow-listed CVEs, token-in-URL, no web tests today | 1C/2 | Phase 0 CI gates; P-pre slices before any new token surface (per `docs/notes/0010` sequencing); advisory-clearing slice; pen-test as the independent check |

---

## Appendix A — Corrections this run establishes (vs the 2026-07-02 audit and the register)

1. **Register row 29 ("CSV laboratory import — Shipped (Milestone 1)") overclaims.** No CSV (or any) parser exists; the only "csv" references are upload content-type checks (`documents/service.py:17,51`); ingestion is manual structured JSON (`api/imports_routes.py:28`, `imports/service.py:44`). Fix in Phase 0.
2. **Interpretation authoring has no API write path.** `create_run` is invoked only by `scripts/seed.py:395` and tests; the API exposes GET only (`api/interpretation_routes.py:58`). "Clinician authors" is not yet an exercisable, role-gated workflow — build in Phase 1C, note in the register in Phase 0. (The 2026-07-02 audit did not surface this.)
3. **Already fixed in the working tree since the audit** (verify at merge): register rows 42–44 now marked "Superseded on the real-data path — see rows 46–48"; ADR-0002 status updated; `AGENTS.md` mirror + sync note created. Remaining audit P1s (refresh `DESIGN-VERIFICATION.md` — currently marked SUPERSEDED — decide `docs/notes/0010`'s committed status) fold into Phase 0.
4. **Also new in this run:** consent record/withdraw has no HTTP endpoint and is unaudited; failed logins are unaudited; `record_security_event` failures are swallowed; `ReportStatus.REJECTED` is unreachable; review items can never be resolved; the BYPASSRLS boot guard is production-only; `tri_state_cells.evidence_refs` are unvalidated against patient scope; `/patient-view` copy is English; logout is not wired. All are scheduled (Phases 0–1C).

## Appendix B — Where each baseline claim was verified

Firsthand reads this run: `docs/regulatory/{INTENDED_USE,CLASSIFICATION_REGISTER,OWNERSHIP}.md`, `docs/adr/{0003,0006}`, `docs/notes/{0006,0010}`, `docs/product/WORKFLOW.md` (part), `modules/enums.py`, imports/documents source (grep), web copy anchors (grep), working-tree diffs vs HEAD, `reports/2026-07-02-vitabahn-hadp-status-audit.md`. Area evidence sweeps (five parallel agents, all citations spot-checkable): backend/data (migrations 0001–0008, RLS/append-only, interpretation/consents/reports/kpi/derivations services, 118 tests, CI), frontend/product (all 8 routes, api layer, presenters, copy scanners, deployment census), security/data-protection (authn/authz, RLS guards vs notes 0002/0003/0005, audit coverage, GDPR-artifact census, threat model), regulatory/clinical (positioning wording, anchor census DE/EN, physician-gate code chain, artifact gap table incl. UAE), legal/commercial/ops (corporate/contract/commercial/ops censuses — all NOT FOUND — plus repo meta and git history).
