# 0026 — Lage heute: the preparation tab leads with today's position

Status: implemented (synthetic Alpha). Follows a clinician's reading of the patient page:
the Vorbereitung tab (docs/notes/0022, 0025) answered "what is missing" first and "how does
the record stand" only on the Werte tab. The mockup that settled the order, and the
comparison with Function Health, Superpower, Heads Up Health, Healthie and Epic's Results
Review behind it, are in the founder's design canvas "Patientenakte: Vorbereitung neu".

## What the tab shows, in order

1. **Header** (the whole page): the date of birth beside the age, the newest sample day,
   the latest interpretation run.
2. **Lage heute**: a row of counts — markers with a value, outside the laboratory's
   interval, within it, without an interval of the source, values in review — so the
   record's position is read in seconds. Then two tables, side by side where both fit,
   one under the other otherwise:
   - the markers whose latest standing value lies **outside** the interval: value,
     interval, side, sample day, and the **course** — one point per standing value placed
     above, in or below the interval band; a line joins two points only where the API
     marked the later value comparable to the earlier one. One value is one point;
   - the **latest interpretation**: per domain, its core markers with a value, its markers
     outside the interval, and the clinician's CIS, Actionability and follow-up adequacy as
     recorded — quoted, never computed. Under it, how many domains have inadequate or
     unassessed follow-up, counted.
3. **Seit Lauf n**: the new and moved values as before; when nothing came, one line with
   the values in review and those no catalog marker names.
4. **Alt und fehlend**: the old core markers grouped by sample day ("16 vom 10.06.2025 · 1
   vom 12.06.2025") and by domain, the missing ones by domain; each list on request. The
   printable page lists everything.

## What it is not

No score, grade, colour per organ system, "optimal" zone or biological age — the forms the
consumer products use and ADR-0003 excludes. The counts are of positions the laboratory's
interval gives; the verdicts are the clinician's words; the course draws nothing between
values the API did not compare. The forbidden-language scan passed in both languages.

## Where it is computed

`lib/presenters/visitPrep.ts` (`today`, `domains`, `staleByDay`, `staleByAxis`,
`missingByAxis`) from the domain overview the page already builds; `lib/presenters/review.ts`
gives the date of birth as the clinic reads it. No API change.

## Tests

`apps/web/e2e/visit-prep.spec.ts`: the counts by side of the interval, the course and its
links (comparable and not), the domain lines with and without a verdict, the groupings by
day and domain; on the seeded record, the counts, the six verdict rows, the header's run
line, and a folded list opened. `apps/web/e2e/language.spec.ts`: the English heading.
