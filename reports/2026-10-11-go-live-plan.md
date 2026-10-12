# HADP — Go-live Plan (state as of 2026-10-11)

- **Date:** 2026-10-11
- **Repo:** `new_hadp`, `main` @ `c6834f3`, plus two uncommitted slices on branch `feat/web-report-review-entry` (review-page entry + draft generation; rework after rejection + edit-time language guard).
- **Author:** CTO-directed planning run (Claude Code).
- **Method:** a full read of the code (API, worker, web, tests, CI) through three parallel read-only sweeps, plus firsthand reads of the launch plan, notes 0006/0008/0012, and `docs/regulatory/OWNERSHIP.md`. The classification register, ADR-0004, and the 2026-07-02 status audit were read in excerpts only.
- **Relation to earlier records:** `reports/2026-07-03-execution-plan-to-launch.md` remains the basis. This plan re-bases it on today's state; it does not replace its phase definitions or its Branch A / Branch B analysis.
- **Blind spot:** nothing outside the repository is visible to this run (incorporation, counsel, DPO, Regulatory Lead). Those items are treated as **not done** until corrected.

> **Not legal or regulatory advice.** This is an engineering/program plan. The binding determinations belong to qualified counsel, a DPO, the named Regulatory Lead, and — for device qualification — a notified body or competent authority.

**"Go-live" means here** (definition from the 2026-07-03 plan, Phase 3): at least one DACH clinic works **lawfully with real patient data in an EU production environment**, every release passes the two-tier physician gate, and the preparation-time metric is flowing. Everything before that is a demo.

---

## 1. Starting point

**Done since July (evidenced in the repo):** Phase 0 complete. From Track 1C: interpretation authoring, the medical-director role, approve/reject/release in the UI, the consent API, the review queue, rate limiting and CSRF, patient and staff invitations, the onboarding wizard, erasure (two-person gate + tombstone), member administration, DB CHECK constraints for every enum column. On 2026-10-11 (uncommitted): the entry to the review page, draft generation from the UI, and rework after rejection with a server-side language check.

**Still open:** no lab-file parser; no production login (OIDC is a stub, `apps/api/src/hadp_api/auth/provider.py:54`); no Dockerfile or infrastructure; no backups; no preparation-time metric; no data export; no browser tests; Regulatory Lead **UNASSIGNED** (`docs/regulatory/OWNERSHIP.md:17`); MDR determination, claims review, AVV/TOMs, and DPIA all "Pending"; `docs/data-governance/` contains only `THIRD_PARTY_DATA.md`.

---

## 2. Hard gates (no go-live without all of them)

| Gate                                                              | Owner                                | State   | Evidence                        |
| ----------------------------------------------------------------- | ------------------------------------ | ------- | ------------------------------- |
| Regulatory Lead named                                             | Founder                              | open    | `OWNERSHIP.md` updated          |
| MDR/MDSW qualification determination on record (Branch A or B)    | Regulatory Lead + regulatory counsel | open    | memo in `docs/regulatory/`      |
| Operating entity + IP assignment                                  | Founder + counsel                    | unknown | commercial register, assignment |
| AVV/DPA + TOMs + §203 safeguards, signed with the pilot clinic    | Counsel + DPO                        | open    | `docs/data-governance/`         |
| DPIA + ROPA + lawful-basis map                                    | DPO                                  | open    | `docs/data-governance/`         |
| Production identity (OIDC + MFA) live, dev-login unreachable      | CTO                                  | open    | production smoke                |
| Independent penetration test, criticals/highs closed              | External tester                      | open    | report + re-test                |
| Restore test passed (RPO ≤ 24 h, RTO ≤ 1 business day)            | CTO                                  | open    | runbook + protocol              |
| Clinical SOPs + medical director formally recorded                | Medical Director                     | open    | `docs/regulatory/`              |

The register rows marked "In review" (today: rework + language guard; after a merge: `feat/tenant-kpi-config`) need Regulatory-Lead sign-off. Until that role is assigned, all of it sits on "Founder (acting)".

---

## 3. Workstreams

### A — Complete the product workflow (engineering, from now)

1. **Pilot-lab data feed.** Procurement first: ask the pilot clinic's laboratory for a structured feed (LDT/HL7/FHIR/CSV) — a contractual lever, not a parsing project. Then **exactly one** parser with golden fixtures (synthetic), content-based file-type inspection, a page limit, and the idempotency key (`ImportJob.idempotency_key` exists, unused). Budget 2–3× the naive estimate.
2. **Terminology and units** for the pilot panel: today 6 terms / 4 conversions (`modules/imports/normalize.py`); LOINC/UCUM only when verified, otherwise the review queue.
3. **Corrected lab reports:** conservative matching, ambiguity → review queue (`supersedes_observation_id` exists, the logic does not).
4. **Import/upload UI** (API exists, no UI) and **consent UI** to grant/withdraw after creation (API exists, no UI).
5. **Show CIS + tri-state cells** — doctrine says "two badges", the UI shows one. Founder decision (see §6), then implementation in `ReviewContent.tsx` / `PatientDetailContent.tsx`.
6. **Preparation-time metric** (the pilot's primary metric): per-clinic baseline at onboarding + workflow timestamps (draft → approval); identifiers and timings only.
7. **Data export (GDPR Art. 15/20):** endpoint + UI. Erasure is done.
8. **Rejection reason** as a closed enum (migration) — whoever reworks a report must know why it was rejected.
9. **Audit-log view** (a navigation placeholder today) — the clinic is the controller and needs to see it.
10. **Remove prototype remnants:** the password/2FA mock on the login page, the "Prototyp-Zustände" switcher, dead navigation entries (Importe/Berichte/Regeln/Audit), inert tabs, toast stubs; `/patient-view` in German; the wrong "nicht freigegeben" labels on released reports.
11. **Worker:** wire real jobs (import/parser) or remove it — no skeleton in production.
12. **Decide the branch `feat/tenant-kpi-config`** (migrations 0017/0018, clinic-defined reference intervals). Its register row argues "fallback-only, position-only, never patient-facing" — doctrine-adjacent to the BLOCKED "Optimal ranges" row; it needs Regulatory-Lead sign-off before merge, not only green CI.

**Exit:** a pilot lab result travels, on synthetic data, from file → review queue → interpretation → draft → approval → release → patient view through the UI alone, with the metric recorded.

### B — Production identity and security

- Choose the OIDC provider (EU residency; **longest lead time, start first**), integrate it, MFA, a real logout (today it clears `hadp_session` but not `hadp_csrf`), remove dev-login from the UI.
- Cookies with `secure` + the `__Host-` prefix, HSTS, a CSP without `unsafe-inline` (nonce — noted as a follow-up in `apps/web/next.config.mjs`).
- Rate limit on report generation as well; the BYPASSRLS boot guard in **all** environments (production-only today).
- A malware-scan integration point on upload; short-lived signed URLs for documents (no download path exists today).
- Reduce the dependency-advisory allow-list (`docs/notes/0008`).
- Stop swallowing `record_security_event` failures.

**Exit:** the penetration-test scope (tenant isolation, authn/session, patient link and invitation tokens, upload) shows no critical or high finding.

### C — Platform and operations

- Dockerfiles (api, web, worker), IaC, an EU region, managed Postgres (app role ≠ superuser stays), EU object storage, TLS, encryption at rest, a secret manager, staging + production, a CI deploy job running `alembic upgrade head` (forward-safe).
- Encrypted backups in the EU and a **restore test** with a protocol; monitoring, alerting, and error reporting **with** the redaction layer; runbooks for deploy, rollback, restore, incident, and tenant provisioning; a support inbox and a status page.

**Exit:** staging equals production except for data; the restore test passed; an alert on an RLS error / 5xx is demonstrated.

### D — Data protection (DPO-led, engineering-supported)

- DPIA, ROPA, lawful-basis map, sub-processor list (cloud, OIDC, e-mail if used).
- Consent taxonomy + versioned, counsel-authored texts — replacing the placeholders `synthetic-v1` and `modules/enums.py:119`.
- TOMs written **from the actual controls**; the AVV/DPA pack; a retention policy and its technical implementation.
- Impressum / Datenschutz / terms in the web app (dead `href="#"` links today).
- Extend the redaction tests to real request and trace paths.

### E — Regulatory and clinical governance

- Name the Regulatory Lead; commission the determination (input: `INTENDED_USE.md`, the register, the architecture, the SOPs).
- Create `CLAIMS_REVIEW.md` and run the first claims review over the README, the login copy, and the pitch material.
- SOPs: clinician review, medical-director responsibilities, incident/complaint intake; a named-clinician sign-off of the KPI catalog.
- Language bank: add the German terms (Therapie, Behandlung, Empfehlung, …) to `modules/reports/language.py` through the boundary-change process; narrow `report.edit` to the clinician (WORKFLOW §2.2 vs `auth/authz.py`).
- Lift the synthetic-only enforcement **per tenant, by contract** — a deliberate, recorded step.

### F — Quality and CI

- Playwright end-to-end for the primary workflow (login → import → review → interpretation → draft → approval → release → patient view).
- Property-based tests (`hypothesis`) for conversions; parser golden tests; a per-endpoint cross-tenant matrix; worker tests.
- CI gaps: `format-check`, JS lint (no ESLint script exists), `apps/worker` unchecked, container scan, make `make test-e2e` real.
- A load test at the expected pilot volume.

### G — Legal and commercial (founder)

Entity, IP assignment, insurance, a design-partner agreement with pilot success criteria (the metric from A6), a pricing hypothesis. The UAE partner stays on the synthetic-demo track until local counsel reports.

---

## 4. Sequence and critical path

| When                               | What                                                                                                                                              | Critical                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **Now (Oct)**                      | Name the Regulatory Lead; commission the determination; counsel/DPO; choose the OIDC provider; request the lab feed from the pilot clinic; §6      | yes — everything else hangs off it |
| **Block 1 (Oct–Nov, ~6 weeks)**    | A1–A4, A8–A12; B without the vendor-dependent parts; C: Docker/IaC/staging; F: Playwright + CI gaps                                                | engineering                        |
| **Block 2 (Nov–Dec, ~6 weeks)**    | OIDC + MFA live; production; backups + restore test; monitoring; A5–A7; the D artifacts in parallel (DPO)                                          | vendor lead time                   |
| **Dec–Jan**                        | Penetration test + remediation + re-test; go-live readiness review; pilot contract signed                                                          | external                           |
| **Earliest Jan–Feb 2027**          | First real patient data, one tenant                                                                                                               | only if the determination is A     |

The longest paths are the **determination** (counsel's turnaround is unknown) and **OIDC vendor → production → penetration test**. If the determination lands on Branch B (MDSW), the full product moves behind a QMS / notified-body track (18–30 months), and only the counsel-confirmed documentation scope remains sellable in the interim. All of it rests on one engineer — the bus factor is the largest delivery risk.

---

## 5. Go-live readiness review (ceremony checklist)

All gates in §2 green and recorded in the register; exit criteria A–F met; AVV/TOMs/§203 signed with **this** clinic; counsel's consent texts live; penetration-test report accepted; restore protocol on file; runbooks and support reachable; the register contains no claim the evidence contradicts. Only then: provision the tenant and lift synthetic-only for that tenant.

---

## 6. Decisions needed from the founder now

1. **Regulatory Lead** — who, and by when.
2. **Show CIS + tri-state cells in the UI** (doctrine), or record the deferral in the register as a pilot divergence.
3. **`feat/tenant-kpi-config`:** merge (after regulatory sign-off), park, or drop.
4. **OIDC provider** (EU) and **cloud region/provider** — both vendor decisions block Block 2.
5. **The pilot clinic and its laboratory** — without the feed format there is no parser.
6. **Extend the language bank to German** and narrow `report.edit` to the clinician — yes/no.

**Proposed next engineering slice:** Dockerfiles + a staging environment + Playwright end-to-end (streams C/F). They need none of the decisions above and protect every later slice. In parallel: the feed request to the pilot clinic.
