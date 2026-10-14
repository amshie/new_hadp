# 0014 — Domain timelines on the patient page

Status: parts 1 and 2 implemented (synthetic Alpha). Register row: "Patient page domain
overview" (`docs/regulatory/CLASSIFICATION_REGISTER.md`), In review.

## Why

A clinician preparing a visit needs to see, per domain, what was measured, what changed, what lies
outside the laboratory's own interval, what is missing, and what they themselves concluded last
time. The patient page listed a domain's values only through the values an interpretation run
cited, showed one row per observation without history, and had no counts to start from. The
founder approved a mockup on 2026-10-13 with three decisions:

1. Lines in a history chart join only comparable values (part 2; see below).
2. Values awaiting review are shown, marked, and never counted as a marker's latest value.
3. The domain card quotes the clinician's CIS and Actionability, and says when values arrived
   after that interpretation.

## Part 1 (this change)

- **Grouping by catalog.** A value belongs to the domain of its KPI (`kpi_primary_domain`).
  Markers the catalog links to further domains are listed there too, under "Also relevant here",
  and counted only in their own domain. Values without a catalog marker keep their own list.
- **Four counts before a visit**, each a filter of every domain list: values received after the
  latest run was recorded; markers whose latest standing published value lies outside the source
  reference interval; values awaiting review; core markers without a published value. The counts
  and the filters are one definition (`apps/web/src/lib/presenters/domainOverview.ts`), tested
  together (`apps/web/e2e/domain-overview.spec.ts`).
- **Domain cards**: coverage of the core markers (one segment each), the counts, the date of the
  latest published value, and the latest run's verdicts quoted verbatim with run number and date.
  Neutral styling: CIS is never coloured like a grade.
- **One row per marker** with its latest standing published value, the change the API computed,
  its position against the source interval and its age; the marker's dialog lists every value.
- **API**: `GET /api/v1/kpi-catalog/core` (global reference data, not audited — no clinic data),
  `received_at` on the timeline, `recorded_at` on the interpretation.
- **Seed**: the synthetic run is now recorded after its values are committed. In one transaction
  the run's `created_at` (the database's `now()`, the transaction's start) preceded every value's
  `received_at`, which made every seeded value look newer than the run.

"Received after the run" compares the API's `received_at` (set by the application) with the run's
`created_at` (set by the database). Both clocks are the same host in the pilot setup; a skew
between application and database servers would blur the comparison by that skew.

## Part 2 (this change)

- **Sparklines.** Each marker row carries its history on the page's one calendar axis, from
  shortly before the oldest value to the moment the page was put together, so gaps and visit
  rhythm line up from row to row; a tick marks today. Each row has its own value scale.
- **History chart** in the marker dialog, above the table of every value. The geometry is one
  pure function (`apps/web/src/lib/presenters/history.ts`, tested in
  `apps/web/e2e/history.spec.ts`):
  - a line joins two values exactly where the API computed a change between them
    (`previous_observation_id` with `delta_vs_previous`); the chart decides no comparability of
    its own;
  - the source reference interval is drawn per value and steps where the laboratory changes; a
    one-sided interval stays open on its open side;
  - a value awaiting review is drawn hollow, a value a correction replaced is crossed out, a
    standing value outside its interval is ringed; none of the first two is joined;
  - a rejected value and a result that is no number are not drawn — the sentence above the chart
    says how many, and the table lists them;
  - no trend line, smoothing or forecast.
- **Reading it without the chart.** The chart is an image named by the marker and described by
  a summary sentence (how many published values, between which days, the latest, how many in
  review or replaced). Every drawn value is in the table beneath, so the hover readout is a
  convenience, not the way to a value; there is no keyboard stepping through the chart.

## Open points

- **Comparability of laboratory values by method.** The API's `method_aware` policy compares a
  laboratory value on KPI and unit only (ADR-0004 §9). No reader records `method` yet, so a stricter
  rule would change nothing today. Filling `comparison_policy` for the 43 core markers is the
  medical director's decision.
- **English names.** Missing core markers show the catalog's English display name (marked
  `lang="en"`) in both languages; German catalog names do not exist yet.
- **`display_unit`** is empty for every catalog row; the core-catalog endpoint does not return a
  unit for that reason.
- **Missing rows** take much room where a record has few values. Whether to collapse them is a
  question for the pilot clinicians.
