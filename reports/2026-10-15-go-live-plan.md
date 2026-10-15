# HADP — Go-live Plan (state as of 2026-10-15)

- **Date:** 2026-10-15
- **Repo:** `new_hadp`, `main` @ `a812ee4`. 39 pull requests have been merged since §9 of the previous plan was recorded (2026-10-13, `4e2afe7` = #74): #75–#113.
- **Author:** CTO-directed planning run (Claude Code).
- **Method:**
  - Every open item of `reports/2026-10-12-go-live-plan.md`, its §9 included, was checked against the current tree: the file, function, CI job or test that would prove it.
  - The repository on GitHub was also checked for open pull requests.
  - The register's status column was counted row by row.
- **Relation to earlier records:**
  - `reports/2026-07-03-execution-plan-to-launch.md` remains the basis (phases, Branch A / Branch B).
  - This plan re-bases the 2026-10-12 plan and keeps its numbering: A1–A12, B–G, and decisions 1–14.
- **Blind spot:** as before, nothing outside the repository is visible (incorporation, counsel, DPO, Regulatory Lead, the pilot laboratory's answer). Those items are treated as **not done** until corrected.

> **Not legal or regulatory advice.** This is an engineering/program plan. The binding determinations belong to qualified counsel, a DPO, the named Regulatory Lead, and — for device qualification — a notified body or competent authority.

**"Go-live" means here** (unchanged): at least one DACH clinic works **lawfully with real patient data in an EU production environment**. Every release passes the two-tier physician gate, and the preparation-time metric is flowing. Everything before that is a demo.

---

## 0. In one paragraph

The engineering backlog of §9.5 is done except the parts that wait on a decision. Then came 29 pull requests of clinic-facing product work that no plan listed: interface language, design consistency, settings, domain timelines, Vorbereitung, Seit zuletzt, and the patient page's tabs.

None of the ten hard gates of §2 has moved since 2026-10-12. The register's "In review" backlog grew from 10 to 18 sign-offs, and nobody is appointed to sign them.

The critical path is unchanged, for the third plan in a row: the Regulatory Lead, the determination, and the OIDC and cloud vendors. **Every further week without them moves the earliest first real patient by a week. No engineering work shortens that wait.**

---

## 1. What changed since 2026-10-13

### 1.1 §9.5 of the previous plan

| §9.5 step                                                  | Pull requests | State                                                                                                                                                                                                                                    |
| ---------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 — Rate limits on the real client                         | #75           | **Done.** The address-keyed limits count the client behind a trusted hop. A clinic's trail takes a bounded number of refusals.                                                                                                     |
| 2 — Role guard: refuse a table owner; no admin fallback    | #86           | **Done.** The application refuses a role that owns the tables and never falls back to the admin DSN.                                                                                                                                    |
| 3 — Local object storage (decision 14)                     | #82           | **Done for development.** The S3 test double (moto) that CI and the demo already used now runs locally as well; MinIO is gone. Decision 14 is taken for local development; the store a deployment uses is still a vendor decision (§6.4). |
| 4 — The browser test's blind spots                         | —             | **Open.** The Playwright suite grew to 98 tests (some of them presenter tests without a browser), nearly all for the new pages. The rejection and rework path, a second clinic and LDT files still have no browser test (`docs/notes/0006`).                                                     |
| 5 — CI gaps                                                | #87           | **Part done.** ESLint for the web app (TypeScript, hooks, accessibility) in `make lint` and CI. Still open: property-based tests for the conversions (no `hypothesis`) and `apps/worker` tests in CI (CI only builds and scans its image).                         |
| 6 — A recorded start of preparation                        | —             | **Open.** Waits for decision 12. The figure now appears on the overview and under Einstellungen (#109). It is still the draft-to-approval interval, which cannot be compared with the clinic's baseline.                                         |

### 1.2 Operations (not in §9.5)

- **Demo server** (#76, #103): HADP on one server behind a gate, on synthetic data only. It follows `main`.
- **Encrypted database backups with a tested restore** (#104, `docs/security/BACKUP_RESTORE.md`):
  - RPO 24 h, RTO one business day;
  - a CI job backs up, restores and compares the database every Monday and on every change to the scripts.
  - **Not covered:** the object store (the demo's store is in memory); a restore drill on the server (the table in the file is empty).
- **Technical due diligence, one page** (`docs/TECHNICAL_DUE_DILIGENCE.md`). Its "missing before a real clinic" table agrees with this plan.

### 1.3 Product work that no plan listed (#77–#113)

- **Interface language:** German or English for every page of the clinic team; the closed vocabularies stay German (#77–#90).
- **One look and accessibility:**
  - the clinic's words, not the platform's (#99);
  - form controls, phone layout without sideways scrolling, contrast, no type under 11 px (#100–#102);
  - the report page in the dashboard shell (#83);
  - the dashboard on a phone, and a stored dark theme (#81).
- **Overview "Heute" per role** (#94). **Einstellungen:** its sections, Team & Rollen, and the six sections that did not exist yet (#95–#98).
- **Domain timelines:**
  - every value in its domain through the KPI catalog (#92);
  - sparklines and a history chart per marker (#93).
- **Vorbereitung:**
  - the page before a visit (#106) and the practice view across all records (#107);
  - "Seit zuletzt" (#108); the patient page in three tabs (#109);
  - "Lage heute": counts, values outside the source interval, and the six verdicts (#110).
- **Truthful presentation** (#111, #112):
  - the laboratory's sampling day; only the bounds the source gave;
  - derived values say they are computed and name their inputs;
  - the medical-director gate described as it is built (see 1.4).
- **Browser suite** (#113): an intermittent failure of the production build worked around in the tests (see 1.4).
- **Documents for the founder and the medical director:** a clinical and biological review of the interpretation model (#91); a competitive landscape of ten platforms (#105).

### 1.4 New findings, now part of this plan

- **There is no medical-director sign-off on an interpretation run.**
  - The release gate as built: a clinician approves the report (`report.approve`), and only the medical director releases it (`report.release`).
  - The interpretation run itself is never locked: its review status stays `draft`, and nothing writes `clinician_reviewed`.
  - #112 corrected `README.md`, `INTENDED_USE.md`, ADR-0003 and register rows 32, 39 and 49 to say so.
  - Whether a lock is required before go-live is a decision (§6.15).
- **Next.js drops about one link click in a hundred on a production build** (`docs/notes/0027`).
  - The payload arrives, nothing navigates, and there is no error. Once, the router aborted its own request.
  - Measured with the same frequency on `main` and on the branch; the development server does not show it.
  - The tests click a second time (`followLink`). **The product does not:** a clinician will meet it in a pilot.
  - Cause unknown. Next to try: a newer 15.5 patch release, and `prefetch={false}`.
- **A5 is half done and the register does not say so.**
  - The patient page has shown CIS beside Actionability since #92, and "Lage heute" has since #110.
  - The report review page still shows one badge (Actionability).
  - The three tri-state cells still appear on no reading page.
  - Register row 50 still reads "Actionability-only (CIS + tri-state cells deferred)".
- **The register backlog grows with every product pull request.** 18 sign-offs are pending: 17 rows with status "In review" (lines 35, 61–76) and the `norm-2` part of row 31; the 2026-10-12 plan counted 10 the same way. Rows added since: the metric (#67), the interface language (#77–#90), the domain timelines (#92, #93), the overview (#94), Vorbereitung (#106, #107), Seit zuletzt (#108).
- **Unchanged and unowned:**
  - the same 19 Dependabot pull requests (#2–#48, the oldest from June);
  - PR #12 (superseded model);
  - PR #41 (`feat/tenant-kpi-config`, conflicting with `main`).
- **Proposal, not built — Kumulativbefund:**
  - a cumulative laboratory table with markers as rows and draw dates as columns, the newest on the left;
  - it reuses the app's chips for "above/below the source interval", marks values in review, and tags computed values.
  - A mockup was compared with today's pages on 2026-10-14. It is not in the repository.
  - It needs no API change. Seven design choices are open (§6.16).

---

## 2. Hard gates (no go-live without all of them)

| Gate                                                            | Owner                                | State          | Evidence today                                                                                                                         |
| --------------------------------------------------------------- | ------------------------------------ | -------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Regulatory Lead named                                           | Founder                              | **open**       | `OWNERSHIP.md`: UNASSIGNED                                                                                                             |
| MDR/MDSW qualification determination on record (Branch A or B)  | Regulatory Lead + regulatory counsel | **open**       | no memo in `docs/regulatory/`                                                                                                          |
| Operating entity + IP assignment                                | Founder + counsel                    | unknown        | not visible from the repo                                                                                                              |
| AVV/DPA + TOMs + §203 safeguards, signed with the pilot clinic  | Counsel + DPO                        | **open**       | `docs/data-governance/` holds only `THIRD_PARTY_DATA.md`                                                                               |
| DPIA + ROPA + lawful-basis map                                  | DPO                                  | **open**       | same                                                                                                                                   |
| Production identity (OIDC + MFA) live, dev-login unreachable    | CTO                                  | **open**       | provider stub (`auth/provider.py:54`); no MFA                                                                                          |
| Independent penetration test, criticals/highs closed            | External tester                      | **open**       | —                                                                                                                                      |
| Restore test passed (RPO ≤ 24 h, RTO ≤ 1 business day)          | CTO                                  | **part done**  | database: weekly in CI (#104). Open: a drill on a real server recorded in `BACKUP_RESTORE.md`, and the object store                    |
| Clinical SOPs + medical director formally recorded              | Medical Director                     | **open**       | —                                                                                                                                      |
| Register rows "In review" signed off                            | Regulatory Lead                      | **open**       | **18 sign-offs** (was 10)                                                                                                               |

---

## 3. Workstreams, re-based

### A — Complete the product workflow

Only rows whose state changed, plus the new items. All other rows are as the 2026-10-12 plan states.

| #   | Item                                  | State                     | Evidence / what remains                                                                                                                                                                                       |
| --- | ------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1  | Pilot-lab data feed                   | **partly done**           | Unchanged: waits for the laboratory's format.                                                                                                                                                                 |
| A5  | Show CIS + tri-state cells            | **half done**             | CIS + Actionability on the patient page (#92, #110). Open: the report review page, the tri-state cells on any reading page, and register row 50 brought up to date. Decision 2 now covers only the tri-state cells. |
| A6  | Preparation-time metric               | **part 1 + surface**      | #67, #109. Open: a recorded start of preparation (decision 12).                                                                                                                                               |
| A11 | Worker                                | **later — now due**       | Still a 59-line skeleton: imports and drafts run inside the request. The due-diligence note estimates one week before a real clinic.                                                                         |
| A12 | `feat/tenant-kpi-config` (PR #41)     | **open, degraded**        | Unchanged; decision 3.                                                                                                                                                                                         |
| A13 | Kumulativbefund (new)                 | **proposal**              | Mockup on 2026-10-14; UI only, no API change. Waits for decision 16. Adds one register row.                                                                                                                   |
| A14 | Medical-director sign-off on an interpretation run (new) | **not built** | Only if decision 15 requires it before go-live. Needs a state change on the run, an audit event, and a register row.                                                                                          |

**Exit (unchanged):** a pilot laboratory result travels, on synthetic data, from file through the review queue, interpretation, draft, approval and release to the patient view, through the UI alone, with the metric recorded. Everything but a comparable metric does.

### B — Production identity and security

Closed since 2026-10-13:

- rate limits keyed on the real client (#75);
- the role guard refuses a table owner and never falls back to the admin DSN (#86).

Still open:

- OIDC provider and MFA. **Longest lead time; the vendor is not chosen.**
- Removing dev-login from the UI.
- A nonce-based CSP (`apps/web/next.config.mjs` still has `'unsafe-inline'`).
- A malware-scan step on upload; short-lived signed URLs.
- Report edits are not rate-limited: only draft and release are (`api/reports_routes.py`).
- `report.edit` is still granted to all care staff (`auth/authz.py:120`); this is decision 6.
- Throttling events carry neither user nor clinic.
- An alert for a failed security-event write: it needs monitoring (C).

### C — Platform and operations

Done:

- images and a production-shaped stack (#65, #69);
- the demo server following `main` (#76, #103);
- encrypted database backups with a weekly restore test in CI (#104).

Open:

- **Without a vendor:**
  - monitoring and alerting with redaction (logs exist; there are no metrics and no alerts);
  - base images pinned by digest and pulled from a registry instead of being built on the server;
  - a path to replace a catalog release;
  - the worker's real jobs (A11).
- **With a vendor:**
  - staging and production in an EU region;
  - a real object store with versioning and replication;
  - a restore drill on that server.

### D — Data protection

Unchanged and all open: DPIA, ROPA, lawful-basis map, sub-processor list, counsel-authored consent texts (placeholder `synthetic-v1`), TOMs, AVV pack, retention policy, and the DPO questions on the audit trail and the metric (decisions 9, 13). The web app still has no Impressum, Datenschutz or terms page.

One item is added: **the backups.** Deleted records survive in a backup for up to 30 days (`BACKUP_RESTORE.md`). The erasure process has to tell the person who asked.

### E — Regulatory and clinical governance

Unchanged and all open:

- the Regulatory Lead;
- the determination;
- `CLAIMS_REVIEW.md`;
- SOPs;
- the German language bank;
- narrowing `report.edit`;
- the clinician's signature on the names the import publishes without a human (decision 7);
- the rejection vocabulary (A8);
- **18 pending register sign-offs** (17 rows "In review" + row 31's `norm-2`).

Added:

- bring register row 50 up to date (A5);
- record the medical director's position on decision 15.

The clinical review of the interpretation model (#91) is ready for the medical director to read and answer.

### F — Quality and CI

Done since 2026-10-13:

- ESLint for the web app (#87);
- a Playwright suite of 98 tests;
- `followLink` for the dropped navigation (#113).

Open:

- property-based tests for the unit conversions (required by `CLAUDE.md`; no `hypothesis` yet);
- `apps/worker` tests in CI;
- browser tests for rejection and rework, a second clinic, and LDT;
- unit tests on the web presenters;
- a load test;
- **the dropped-navigation bug itself** (`docs/notes/0027`).

### G — Legal and commercial (founder)

Not visible from the repository; treated as open.

---

## 4. Changes to the 2026-10-12 plan

1. **§9.5 steps 1–3 are done,** and step 5 is half done. Steps 4 and 6 remain (§1.1).
2. **Decision 14 is taken** for local development (#82). The production store stays with §6.4.
3. **A5 has half moved.** Decision 2 now concerns only the tri-state cells and the report review page.
4. **New items:**
   - A13 Kumulativbefund;
   - A14 medical-director sign-off on an interpretation run;
   - the Next.js dropped-navigation bug (F);
   - the object-store backup and a server restore drill (C);
   - the backup retention note for erasure (D).
5. **A11 changes from "later" to "due before real data".** The other open items of C and B now outweigh new product surfaces.
6. **The restore gate is part done,** not open.
7. **Timing:** Block 1 (Oct–Nov) is nearly spent on engineering. The founder items of "Now (mid-Oct)" in §5 have not visibly started.

---

## 5. Sequence and critical path

| When                       | What                                                                                                                                                                                       | Critical                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| **Now (second half Oct)**  | Name the Regulatory Lead; commission the determination; engage counsel and a DPO; choose the OIDC provider and the cloud region; send the laboratory-feed request; take decisions 15 and 16 | yes — everything else hangs off it |
| **Rest of Block 1 (Oct–Nov)** | Engineering steps of §7 that need no vendor: the navigation bug, Kumulativbefund, worker jobs, monitoring, quality gaps; A1 fixtures the day the laboratory answers                        | engineering                        |
| **Block 2 (Nov–Dec)**      | OIDC + MFA live; staging and production in the EU; object store with versioning; restore drill; the D artifacts in parallel (DPO)                                                          | vendor lead time                   |
| **Dec–Jan**                | Penetration test, remediation and re-test; go-live readiness review; pilot contract signed                                                                                                  | external                           |
| **Earliest Jan–Feb 2027**  | First real patient data, one tenant                                                                                                                                                         | only if the determination is A, and only if "Now" starts this month |

If the determination lands on Branch B (MDSW), the full product moves behind a QMS / notified-body track. Only the documentation scope that counsel confirms stays sellable in the meantime. All of this still rests on one engineer.

---

## 6. Decisions needed from the founder

Carried over. None is recorded in the repository, except 14:

1. **Regulatory Lead** — who, and by when.
2. **The three tri-state cells and the report review page** (A5, now narrower): show them as the doctrine says, or record the deferral in register row 50.
3. **PR #41:** rebuild it on today's `main` after sign-off, park it, or close it.
4. **OIDC provider** (EU) and **cloud region/provider**. This includes the production object store.
5. **The pilot clinic and its laboratory.** Was the feed request sent?
6. **German language bank; narrowing `report.edit` to the clinician** — yes/no.
7. **Which names may publish without a human,** signed per name by a named clinician.
8. **"Referenzintervall der Quelle"** for typed or device-supplied intervals.
9. **The audit trail, with the DPO:** whether reads are shown by default, who may read it, and how long it is kept.
10. **Dependabot cadence:**
    - close #2 and #47, which `main` already satisfies;
    - merge the minor and patch bumps in one batch;
    - treat each major bump as its own decision.
11. **Close PR #12** — yes/no.
12. **What starts and what ends the preparation interval.**
13. **With the DPO:** the metric describes individual clinicians.
14. ~~Local S3 store~~ — **taken** (#82: the moto test double, for development only).

New:

15. **Must the medical director sign off an interpretation run before go-live,** or is the release gate on the report enough for the pilot? Whatever is decided goes into ADR-0003 and the register; if a sign-off is required, A14 is built.
16. **Kumulativbefund: the seven design choices from 2026-10-14:**
    - which way the date columns run;
    - a toggle beside the domain lists, or a replacement for them;
    - how many draws are shown;
    - two samples on the same day;
    - a reference interval that changes between draws;
    - scrolling on a phone;
    - the wording of the "Vor dem Termin" card.
17. **New clinic-facing surfaces while 18 register sign-offs wait:**
    - either keep adding (each one adds a row nobody can sign);
    - or limit product work to what the pilot workflow needs until a Regulatory Lead clears the backlog.
    - Recommendation: the second, with A13 as the one exception, because it serves preparation time directly.

---

## 7. Recommendation: the next engineering steps

This order needs none of the decisions in §6 except where marked. Each step is one branch and one pull request, reviewed and merged on its own.

1. **The dropped navigation (`docs/notes/0027`) — small; affects every page in production.**
   - Measure with the existing harness against a newer 15.5 patch release and against `prefetch={false}` on the links that change pages.
   - Fix it in the product. If no fix holds, record what was tried.
   - A pilot clinician must not have to click twice.
2. **Kumulativbefund (A13) — after decision 16.**
   - The cumulative table of draws per marker, which is how a DACH clinician reads a laboratory history and therefore the most direct lever on preparation time.
   - UI only, on today's API, synthetic data; a browser test and its register row.
3. **The worker (A11).** Imports and draft generation move out of the request, with explicit retries and idempotency (`CLAUDE.md`), and `apps/worker` tests run in CI.
4. **Monitoring and alerting with redaction (C).**
   - Metrics and alerts that carry no health data, including the alert that a failed security-event write lacks today (B).
   - Base images pinned by digest.
5. **Quality gaps (F, B).**
   - Property-based tests for the approved conversions.
   - Browser tests for rejection and rework, and for a second clinic.
   - A rate limit on report edits.
6. **Once a decision is taken:**
   - a recorded start of preparation (decision 12);
   - the tri-state cells (decision 2);
   - A14 (decision 15);
   - the OIDC adapter and MFA the week the vendor is chosen (decision 4).

In parallel, and not engineering: §6.1, §6.4 and §6.5 start the two long clocks. Steps 1–6 are not wasted whichever way the determination falls. A Branch B outcome would stop new clinical-meaning surfaces, not these.

---

## 8. Go-live readiness review (unchanged)

Only then is the tenant provisioned and synthetic-only lifted for that tenant. The conditions:

- all gates in §2 green and recorded in the register;
- exit criteria A–F met;
- AVV, TOMs and §203 safeguards signed with **this** clinic;
- counsel's consent texts live;
- the penetration-test report accepted;
- the restore protocol on file, the server drill included;
- runbooks written and support reachable;
- no claim in the register that the evidence contradicts.
