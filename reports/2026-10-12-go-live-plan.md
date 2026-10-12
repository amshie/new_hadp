# HADP — Go-live Plan (state as of 2026-10-12)

- **Date:** 2026-10-12
- **Repo:** `new_hadp`, `main` @ `fb84c0c` (15 pull requests merged since the state the previous plan described, `c6834f3`: #49–#63).
- **Author:** CTO-directed planning run (Claude Code).
- **Method:** every item of the 2026-10-11 plan was checked against the current tree — the file, the function or the CI job that would prove it — and against the repository on GitHub (open pull requests, branches, branch protection). Register rows and ADR-0004 §18 were read in full; the 2026-07-03 plan was read only where this plan refers to it.
- **Relation to earlier records:** `reports/2026-07-03-execution-plan-to-launch.md` remains the basis (phase definitions, Branch A / Branch B). `reports/2026-10-11-go-live-plan.md` is the plan this one re-bases; its numbering (A1–A12, B–G, §6) is kept so that commits and notes that cite it stay readable.
- **Blind spot:** nothing outside the repository is visible to this run (incorporation, counsel, DPO, Regulatory Lead, the pilot clinic's answer). Those items are treated as **not done** until corrected.

> **Not legal or regulatory advice.** This is an engineering/program plan. The binding determinations belong to qualified counsel, a DPO, the named Regulatory Lead, and — for device qualification — a notified body or competent authority.

**"Go-live" means here** (2026-07-03 plan, Phase 3): at least one DACH clinic works **lawfully with real patient data in an EU production environment**, every release passes the two-tier physician gate, and the preparation-time metric is flowing. Everything before that is a demo.

---

## 1. What changed since 2026-10-11

**Merged (workstream A):** the structured laboratory readers CSV, LDT 2 and LDT 3 (#54); duplicate detection and supersession of corrected values (#55); upload and import from the patient page (#56); consent state and recording on the patient page (#57); the patient data export, GDPR Art. 15/20 (#58); the rejection reason as a closed vocabulary (#59); the prototype remnants removed (#60); German report statements that give the result as the source wrote it (#61); the import looks names up in the KPI catalog and a value keeps its number and bounds in the source's unit (#62, normalization `norm-2`); the clinic reads its own audit trail (#63). 831 API tests pass on `main`; both live smokes pass against the running app.

**Not changed:** workstreams B–G. The OIDC provider is still a stub that fails visibly (`apps/api/src/hadp_api/auth/provider.py:54`); there is no Dockerfile, no `infra/`, no deploy, no backup; `docs/data-governance/` still holds one file; the Regulatory Lead is still **UNASSIGNED** (`docs/regulatory/OWNERSHIP.md`); none of the six founder decisions of the previous plan is recorded in the repository.

**New findings recorded by the slices** (ADR-0004 §18, `docs/notes/0006-review-followups.md`), now part of this plan:

- Nothing seeds the KPI catalog in production; without it the import holds every value for review and says so only in an error log (→ C).
- A laboratory that writes three decimals (`4.000`) loses the number of every value of 1 or more until a reader states the decimal mark of its format; CSV and manual entry have none (→ A1).
- Which names the import may publish without a human is a clinical decision, name by name; today it is the six names of `norm-1`, which nobody signed either (→ E, §6).
- Audit events carry no patient identifier; report reads and administrative lists are not audited; the trail has no index, export or retention rule (→ A9 follow-up, D).
- The web build downloads four Google font families at build time and failed CI once on that alone (→ C/F).

---

## 2. Hard gates (no go-live without all of them)

| Gate                                                            | Owner                                | State       | Evidence today                                                         |
| --------------------------------------------------------------- | ------------------------------------ | ----------- | ---------------------------------------------------------------------- |
| Regulatory Lead named                                           | Founder                              | **open**    | `OWNERSHIP.md`: UNASSIGNED                                             |
| MDR/MDSW qualification determination on record (Branch A or B)  | Regulatory Lead + regulatory counsel | **open**    | no memo in `docs/regulatory/`                                          |
| Operating entity + IP assignment                                | Founder + counsel                    | unknown     | not visible from the repo                                              |
| AVV/DPA + TOMs + §203 safeguards, signed with the pilot clinic  | Counsel + DPO                        | **open**    | `docs/data-governance/` holds only `THIRD_PARTY_DATA.md`               |
| DPIA + ROPA + lawful-basis map                                  | DPO                                  | **open**    | same                                                                   |
| Production identity (OIDC + MFA) live, dev-login unreachable    | CTO                                  | **open**    | provider stub; `dev-login` returns 404 in production (the only change) |
| Independent penetration test, criticals/highs closed            | External tester                      | **open**    | —                                                                      |
| Restore test passed (RPO ≤ 24 h, RTO ≤ 1 business day)          | CTO                                  | **open**    | no backup exists to restore                                            |
| Clinical SOPs + medical director formally recorded              | Medical Director                     | **open**    | —                                                                      |
| Register rows "In review" signed off                            | Regulatory Lead                      | **open**    | 10 rows (`CLASSIFICATION_REGISTER.md` lines 31, 35, 61–68)             |

The last row is new. Each slice since October added a register row with status **In review** and "Founder (acting)" as reviewer; the count grows with every merge and nobody is appointed to clear it.

---

## 3. Workstreams, re-based

### A — Complete the product workflow

| #   | Item                                 | State              | Evidence / what remains                                                                                                                                                                                                                                                                                      |
| --- | ------------------------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A1  | Pilot-lab data feed                  | **partly done**    | Readers for CSV, LDT 2, LDT 3 with synthetic golden fixtures (#54); content-based file-type check, 20 MB limit, document-scoped idempotency key in use (`modules/imports/document_import.py`). **Remaining:** the pilot laboratory's actual format and fixtures made from it; the decimal mark of that format; the feed request drafted on 2026-10-12 (`reports/2026-10-12-lab-feed-request.de.pdf`, not under version control) — whether it was sent is not visible here. |
| A2  | Terminology and units                | **part 1 done**    | `norm-2` (#62): a value keeps its number and bounds in the source's unit; the import acts on the same six names as before, held against the catalog. **Part 2 is not engineering** — see E and §6: which further names publish without a human, per name, signed by a clinician, for a known test list.         |
| A3  | Corrected lab reports                | done               | #55; limits in `docs/product/LAB_IMPORT_FORMATS.md`                                                                                                                                                                                                                                                          |
| A4  | Import/upload UI, consent UI         | done               | #56, #57                                                                                                                                                                                                                                                                                                     |
| A5  | Show CIS + tri-state cells           | **open**           | The review page renders one badge (`ReviewContent.tsx:636`, Actionability); `cisLabel` is built in `lib/presenters/review.ts` and rendered nowhere; the tri-state cells are entered on the authoring page and shown on no reading page. Waits for §6.2.                                                   |
| A6  | Preparation-time metric              | **not started**    | No `metrics` module, no baseline capture, no workflow timing. This is the pilot's success criterion.                                                                                                                                                                                                          |
| A7  | Data export (Art. 15/20)             | done               | #58, `docs/product/DATA_EXPORT.md` (format version 2 since #62)                                                                                                                                                                                                                                             |
| A8  | Rejection reason                     | done               | #59; values PROPOSED, awaiting the medical director's confirmation (`modules/enums.py`)                                                                                                                                                                                                                      |
| A9  | Audit-log view                       | done               | #63. Follow-ups: events carry no patient id; report reads not audited; no index/export/retention                                                                                                                                                                                                              |
| A10 | Remove prototype remnants            | done               | #60, #61                                                                                                                                                                                                                                                                                                     |
| A11 | Worker                               | **decided: later** | 59-line skeleton kept by founder decision; real jobs (import, parser) to be wired before production, not removed                                                                                                                                                                                             |
| A12 | Branch `feat/tenant-kpi-config`      | **open, degraded** | PR #41 (July). Its migrations `0017_tenant_kpi_settings` / `0018_tenant_kpi_reference` collide with `main`'s `0017_report_rejection_reason` / `0018_observation_source_number`, and eight of its files were changed on `main` since (`authz.py`, `main.py`, `observations/service.py`, `observations_routes.py`, `einstellungen/page.tsx`, `lib/api.ts`, the register, `openapi.json`). It cannot be merged as it is. Decision §6.3; if wanted, rebuild on today's `main` after the register row is signed. |

**Exit (unchanged):** a pilot lab result travels, on synthetic data, from file → review queue → interpretation → draft → approval → release → patient view through the UI alone, with the metric recorded. Today everything but the metric does.

### B — Production identity and security

Changed since 10-11: production config requires the `__Host-` prefix on both cookies (`config.py:100–103`); `dev-login` is hidden in production.

Still open:

- OIDC provider (EU residency; **longest lead time, start first**), MFA, remove dev-login from the UI.
- Logout deletes the session cookie only, not `hadp_csrf` (`api/auth_routes.py:142`).
- CSP still carries `'unsafe-inline'`; the nonce middleware is the noted follow-up (`apps/web/next.config.mjs:7–8`).
- Rate limits exist for ten actions (`audit.read`, uploads, imports, invitations, `report.release`, …) but not for draft generation.
- The BYPASSRLS boot guard runs in production only (`db/engine.py`); it should run everywhere.
- No malware-scan integration point on upload; no short-lived signed URLs (no document download path exists).
- `record_security_event` writes an ERROR log and continues when its own write fails (`modules/audit/service.py`, a documented boundary so that a 403 cannot become a 500) — without alerting (C) that log line is the whole control; decide whether that is enough once monitoring exists.
- Dependency advisories: the allow-list is empty (`ci.yml:217`). 19 Dependabot pull requests are open, the oldest from June: two are already satisfied on `main` (pytest 9, Next 15.5.24 — `main` is at `^15.5.27`), eight are major bumps (Next 16, mypy 2, cryptography 50 for api and worker, four GitHub Actions), nine are minor or patch. None is in any plan.

### C — Platform and operations

Nothing exists: no Dockerfile (api, web, worker), no `infra/`, no IaC, no staging, no deploy job, no backup, no monitoring, no runbooks. Added to the list:

- **Catalog seeding as a deploy step.** `alembic upgrade head` is not enough: the import needs the KPI catalog or it holds every value. Today only the synthetic seed script loads it (`scripts/seed.py` → `seed_kpi_catalog`), and that script must never run against a production database.
- **Self-hosted web fonts.** The build must not depend on a Google download.

### D — Data protection

Unchanged: DPIA, ROPA, lawful-basis map, sub-processor list, consent taxonomy and counsel-authored texts (placeholder `synthetic-v1`, `modules/consents/service.py:24`), TOMs from the actual controls, AVV/DPA pack, retention policy; no Impressum / Datenschutz / terms page in the web app. Added:

- **Audit trail questions for the DPO:** the trail documents each colleague's activity (purpose, retention, works-council position); a staff member's name and e-mail stay attached to their events, and a `users` row with events cannot be deleted; OWNER-only reading means a sole owner reads their own actions; reads shown by default is a product decision.
- Redaction tests exist (`tests/test_logging_redaction.py`) and the suite asserts that no audit event carries a patient or staff name — extending them to real request and trace paths is still open.

### E — Regulatory and clinical governance

Unchanged and all open: name the Regulatory Lead; commission the determination; `CLAIMS_REVIEW.md` and the first claims review; SOPs; the German language bank; narrow `report.edit` to the clinician (`auth/authz.py:101` still grants it to all care staff); lift synthetic-only per tenant by contract. Added:

- **A named clinician signs which names the import publishes without a human** (ADR-0004 §18) — today's six included (`glucose` is published as fasting plasma glucose whatever the specimen; no plausibility check; four mass-concentration LOINC codes are stamped on values held in mmol/L).
- **Confirm the rejection-reason vocabulary** (A8, PROPOSED).
- **Clear the ten "In review" register rows.**

### F — Quality and CI

Unchanged and all open: Playwright end-to-end (`make test-e2e` still runs the browserless smoke); property-based tests for conversions (no `hypothesis` in `pyproject.toml`); JS lint (no ESLint script in `apps/web/package.json`); `apps/worker` outside CI; container scan; load test. CI today: `lint-types-test`, `web-build-smoke`, `secret-scan` (gitleaks), `dependency-scan` (pip-audit, pnpm audit).

### G — Legal and commercial (founder)

Not visible from the repository; treated as open.

---

## 4. Changes to the 2026-10-11 plan

1. **A1 is redefined.** The readers are done; the item is now the pilot laboratory's format, fixtures from it, and its decimal mark.
2. **A2 part 2 moves to E.** Publication without a human is decided per name by a clinician; engineering implements the signed list.
3. **New engineering items:** catalog seeding at deploy (C), self-hosted fonts (C/F), audit events findable by patient and report reads audited (A9 follow-up), the small security items under B that need no vendor.
4. **New governance items:** the DPO questions on the audit trail (D), the clinician's signature on automatic names (E), the rejection vocabulary (E), the register backlog (E, §2).
5. **A12 changed state:** the branch now conflicts with `main`; "merge after sign-off" is no longer an option without a rebuild.
6. **Housekeeping not in any plan:** PR #12 (June, a rules-engine slice plan) belongs to the lab-analytics model that ADR-0003 superseded; 19 Dependabot pull requests have no owner or cadence.
7. **Timing:** of Block 1 (Oct–Nov) the A items are done except A1 (lab-dependent), A5/A12 (decisions), A6, A11 (deferred). B, C-staging and F-Playwright have not started. The critical path has not moved: the vendor clock (OIDC, cloud) has not started, and nothing on the regulatory path has been commissioned.

---

## 5. Sequence and critical path

| When                            | What                                                                                                                                                                                           | Critical                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **Now (mid-Oct)**               | Name the Regulatory Lead; commission the determination; counsel/DPO; choose the OIDC provider and cloud region; send the lab-feed request; §6 decisions                                         | yes — everything else hangs off it |
| **Block 1 rest (Oct–Nov)**      | F: Playwright + CI gaps; C: Dockerfiles + production-shaped compose + catalog seeding + fonts; A6 metric; B items that need no vendor; A1 fixtures as soon as the laboratory answers; A5 after §6.2 | engineering                        |
| **Block 2 (Nov–Dec)**           | OIDC + MFA live; staging and production in the EU; backups + restore test; monitoring with redaction; A11 worker jobs; the D artifacts in parallel (DPO)                                       | vendor lead time                   |
| **Dec–Jan**                     | Penetration test + remediation + re-test; go-live readiness review; pilot contract signed                                                                                                        | external                           |
| **Earliest Jan–Feb 2027**       | First real patient data, one tenant                                                                                                                                                             | only if the determination is A     |

The longest paths are unchanged: the **determination** (counsel's turnaround is unknown) and **OIDC vendor → production → penetration test**. If the determination lands on Branch B (MDSW), the full product moves behind a QMS / notified-body track and only the counsel-confirmed documentation scope remains sellable in the interim. All of it rests on one engineer.

---

## 6. Decisions needed from the founder now

Carried over, none recorded yet:

1. **Regulatory Lead** — who, and by when.
2. **Show CIS + tri-state cells in the UI** (doctrine says two badges and three verdict-free cells; the UI shows one badge), or record the deferral in the register as a pilot divergence.
3. **`feat/tenant-kpi-config`:** rebuild on today's `main` after regulatory sign-off, park, or close PR #41.
4. **OIDC provider** (EU) and **cloud region/provider**.
5. **The pilot clinic and its laboratory** — confirm the feed request was sent; without the format there are no fixtures.
6. **Extend the language bank to German** and narrow `report.edit` to the clinician — yes/no.

New:

7. **Which names may publish without a human** — per name, signed by a named clinician, for a laboratory whose test list is known (A2 part 2); and whether the six names stay automatic as they are (specimen, plausibility, the four LOINC codes).
8. **Whether a typed or device-supplied interval may be called "Referenzintervall der Quelle"** (register row "Source reference-interval display").
9. **Audit trail:** reads shown by default or hidden; OWNER-only or also the medical director; retention — with the DPO.
10. **Dependabot cadence:** close the two already-satisfied pull requests; merge the nine minor/patch bumps in one batch after CI; treat each of the eight major bumps as its own decision (an unrequested major upgrade is out of bounds by CLAUDE.md; the four GitHub Actions bumps carry the least risk).
11. **Close PR #12** (superseded model) — yes/no.

---

## 7. Recommendation: the next engineering steps

The order below needs **none** of the decisions in §6 and protects every later slice. Each is one branch, one pull request, reviewed and merged on its own.

1. **Playwright end-to-end for the primary workflow (F).** Login → upload → review queue → interpretation → draft → approval → release → patient view, on the seeded synthetic data, run in CI next to `web-build-smoke`. Today the only browser-level proof is a hand check per slice; the web has no tests of its own. This slice makes every following change — and the OIDC switch in Block 2 — safe to make.
2. **Dockerfiles and a production-shaped compose (C).** Images for api, web and worker; the app role is not a superuser; a migrate step that runs `alembic upgrade head` **and** seeds the KPI catalog; the web fonts in the repository; a container scan in CI. No vendor is needed for this, and staging in Block 2 is a configuration of it, not a new project.
3. **Preparation-time metric (A6).** Per-clinic baseline captured at onboarding by structured input; workflow timestamps from report-prep start to approval; identifiers and timings only, tenant-scoped, audited; a readable surface for the owner. Without it the pilot cannot be evaluated against its own success criterion.
4. **Security items that need no vendor (B).** Logout clears both cookies; a rate limit on draft generation; the BYPASSRLS guard in every environment; a decision-backed treatment of a failed security event. Small, one pull request.
5. **A1 fixtures the day the laboratory answers**, with the decimal mark of its format stated in the reader.

In parallel and not engineering: §6.1 (the Regulatory Lead), §6.4 (vendors) and §6.5 (the feed request) start the two long clocks. Nothing in steps 1–4 is wasted whichever way the determination falls; a Branch B outcome would stop step 5's successors, not these.

---

## 8. Go-live readiness review (unchanged)

All gates in §2 green and recorded in the register; exit criteria A–F met; AVV/TOMs/§203 signed with **this** clinic; counsel's consent texts live; penetration-test report accepted; restore protocol on file; runbooks and support reachable; the register contains no claim the evidence contradicts. Only then: provision the tenant and lift synthetic-only for that tenant.
