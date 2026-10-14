# 0023 — Vorbereitung je Akte: the practice view

Status: implemented (synthetic Alpha). Gap 5 of `docs/product/COMPETITIVE_LANDSCAPE.md`:
the page before a visit (docs/notes/0022) for every record of the clinic at once, so the
morning's question — which records have something new, old or missing — is answered on one
page instead of by opening each record.

## What it shows

One page, `/vorbereitung`, reached from the work list's header on the overview and from the
patient directory's header. One row per record of the clinic, with:

| Column                | What counts                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| Patient               | name and ID                                                                                             |
| Stand                 | where the record's latest report stands, as the patient page names it                                   |
| Letzte Interpretation | the latest interpretation run's number and day, or "Keine"                                              |
| Neu seit Lauf         | published values received after the run; "(n außerhalb)" says how many of them lie outside the interval |
| Außerhalb             | markers whose latest standing value lies outside the laboratory's interval                              |
| Älter als 180 T       | core markers whose latest value is older than `STALE_AFTER_DAYS` (180, printed on the page)             |
| Ohne Wert             | core markers of the catalog with no published value                                                     |
| In Prüfung            | values awaiting review                                                                                  |
| Ohne Urteil           | domains the latest run recorded no verdict for; "—" without a run                                       |

A value stands when it is published and no laboratory correction has replaced it; the
page says so under the table, with the catalog's number of core markers (43) as the
denominator. A record's name leads to its own Vorbereitung page.

The records are ordered as the work list orders them: by where the report stands (open
review first, then approved, then rejected, then no draft, then released), then by name. A
person may keep one filter pressed (new values, outside, old, missing, in review, without
verdict, without interpretation — each with its count) and sort by one column, largest
first, then smallest first, then the workflow order again. A search narrows by name or ID.

## What it is not

Nothing on the page is rated, ranked or summed. The order is workflow, never urgency; no
column is weighted into another; a position is the laboratory interval's side; the only
verdicts named are the clinician's own, by their absence. `STALE_AFTER_DAYS` is a stated
number, not a judgement about a marker. The wording passed the forbidden-language scan in
both languages, and the classification register carries the row.

## Where it is computed

The counts come from the API, in one pass: `GET /api/v1/worklist/preparation`
(`apps/api/src/hadp_api/api/worklist_routes.py`), open to every staff role that may read
observations, tenant-scoped under RLS, audited as `worklist.preparation.read` with the
number of rows only. `observations.service.preparation_facts_by_patient` walks the
tenant's observations ordered by patient and time, keeps the latest standing value per
marker, and counts; `interpretation.service` supplies the latest run per record and its
verdict count; the KPI catalog supplies the core markers. Positions use
`position_vs_source_interval`, the same function the patient page's TypeScript twin
follows, so a record's row here says what its own card says.

The web page (`apps/web/src/app/vorbereitung`) orders, filters and sorts what the API sent
in a pure presenter (`lib/presenters/practicePrep.ts`); nothing is computed in the browser
beyond that. No new table, no derived value stored.

## Tests

`apps/api/tests/test_preparation_api.py`: authentication, the counts of a record with an
import, a run, values after the run (one outside, one pending, one without a marker) and an
old core marker, an empty record, the audit event, every staff role, tenant isolation.
`apps/web/e2e/practice-prep.spec.ts`: the presenter's order, filters, counts, sort and
search over synthetic rows, and one browser pass over the demo clinic (the row of the
seeded record and its link, a filter pressed and released, a column sorted both ways, the
search, the two ways in). The layout test keeps the page from scrolling sideways on a phone;
the web smoke names the page in both languages.

## Later

Notifications over these facts (gap 3): a record that gained new values since a person
last opened it. A clinic's own number of days instead of `STALE_AFTER_DAYS` as a `rules`
feature with its own register row.
