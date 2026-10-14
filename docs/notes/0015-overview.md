# 0015 — The overview

Status: implemented (synthetic Alpha). Register row: "Overview: "Heute" tiers, work list next
step, clinic weeks, data and sources, activity" (`docs/regulatory/CLASSIFICATION_REGISTER.md`),
In review.

## Why

The overview answered no question: four large counters, a status snapshot, and two empty
tiles in developer language. The founder approved a mockup on 2026-10-14 with all of its
options. The page now answers "what needs me today?" for the reader's role, and then shows
the clinic's work, weeks, data and activity.

## What is on the page

- **A band of five counts**: open reviews, reports to release, values in the review queue,
  releases in the last 30 days (with one point per day), and patients (with and without a
  report).
- **Heute**, in three tiers. All rules are in one pure function
  (`apps/web/src/lib/presenters/today.ts`), tested in `apps/web/e2e/today.spec.ts`:

  - **Jetzt** — what waits on the reader's role. Clinician: drafts to review, rejected
    versions to rework, values to decide. Medical director: approved reports to release,
    erasures to decide or carry out. Assistant: records without any value. Owner: erasures to
    carry out, open team invitations, and a missing baseline or no preparation-time statement
    for 30 days.
  - **Demnächst** — the same for every role: records with values received after their latest
    interpretation run, and records with published values but no report.
  - **Zur Kenntnis** — reports released in the last 7 days; for the clinician, approved
    reports waiting for release; for the owner, erasure requests waiting for the medical
    director.

  Within a tier the order is the kind of work, then how long it has waited. Nothing reads a
  value, a range or a domain, and the card says that the order is workflow, not a judgement.

- **The work list** with each record's next step (clinical review, release, rework, nothing
  open, create a draft, read in values), its counts of published and pending values, and six
  tabs: the five places a report can stand in, and all.
- **The clinic's weeks**: drafts created and reviews signed, per ISO calendar week, with a table
  of the same numbers. For the owner, beneath: the measured median from first draft to approval
  (last 30 days) and the clinic's own baseline. They are two different measures and are not
  set against each other (see the preparation-time page).
- **Data and sources**: three counts of the whole (published; with a source reference interval;
  linked to a catalog marker) and the newest observation; then each laboratory file reader and
  when it was last used, values entered by hand or through the API, and wearables (not
  connected in pilot phase 1).
- **Activity**: the latest five audit events, in the audit page's wording. The owner sees the
  clinic's; everyone else their own. Reads, listings and sign-ins are left out.

## What the API gained

- Worklist rows: `status_at` (when the latest version reached its status), `values_published`,
  `values_pending`, `pending_since`, `latest_received_at`, `latest_run_number`,
  `latest_run_at`, `values_since_run` (rejected values not counted — the patient page's
  definition).
- Throughput: `released` per day and `total_released`.
- Coverage: `with_kpi`.
- `GET /api/v1/worklist/sources` (`OBSERVATION_READ`, audited as `worklist.sources.read`): import
  jobs and rows per reader, and one line for everything else.
- `GET /api/v1/audit-events/mine` (new action `AUDIT_READ_OWN`, every staff role; audited as
  `audit.own.read`): the reader's own latest events, reads and listings left out, at most 20.

Each role loads only what it may read. A request the role may not make would be refused and
recorded as a denied access in the clinic's trail.

## Open points

- **The work list carries only each patient's latest report.** An activity event about an older
  report is named by its kind, not by the patient.
- **The preparation-time reminder after 30 days** is a choice for the pilot, not a rule of the
  metric. The owner may want a different rhythm.
- **The "Patient hinzufügen" button** shows for the medical director, who may not create
  patients (the API refuses). That was so before this change.
