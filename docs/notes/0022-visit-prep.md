# 0022 — Vorbereitung: the page before a visit

Status: implemented (synthetic Alpha). The seventh of the gaps in
`docs/product/COMPETITIVE_LANDSCAPE.md`: what has happened to a record since the latest
interpretation run, as facts a clinician reads in two minutes instead of six domain tables.
The feature that bears on the product's own metric (median preparation time per
appointment, CLAUDE.md) most directly.

## What it says

One card at the top of the patient page, and the same card on a page of its own
(`/patients/{id}/vorbereitung`) that fits a sheet of paper. Its eyebrow names the run the
facts are "since" (`Seit Lauf 2 · erfasst am 12.03.2026`), or says that no interpretation is
recorded yet. Then, each as a group with a count in its heading and one line per fact:

| Group                                        | What counts                                                                                        | The line                                                             |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Neue Werte seit Lauf n                       | published values received after the run was recorded; "davon n außerhalb" counts the ones outside  | marker · value and unit · source reference · measured on · Lage pill |
| Marker mit gewechselter Lage                 | the latest value, received after the run, lies on another side of the interval than the one before | marker · from → to · value · reference · the two days                |
| Kernmarker mit letztem Wert älter als n Tage | core markers whose latest value is older than `STALE_AFTER_DAYS` (180)                             | marker · last value's day · domain                                   |
| Kernmarker ohne veröffentlichten Wert        | core markers of the catalog with no published value                                                | marker (the catalog's name) · domain                                 |
| Werte in Prüfung                             | the review queue's count for the record                                                            | a sentence and the way to the queue                                  |
| Werte ohne Katalogmarker                     | values no catalog marker names                                                                     | a sentence pointing at the overview's own list                       |
| Domänen ohne Urteil in Lauf n                | domains the run recorded no verdict for                                                            | the domains, each a link                                             |
| Domänen auf korrigierten Werten              | verdicts that cite a value a laboratory correction has since replaced                              | the domains, each a link                                             |

Without a run there is no "since": the first two groups and "ohne Urteil" are left out, and
the eyebrow says why. When no group has anything, the card says that in one line.

Every marker's name is the way to its value: on the patient page it opens the marker's
history (the same dialog the domain lists open); on the page of its own it leads to the
marker's domain on the patient page. The page of its own has a print button; on paper the
shell is left out and every line is printed in full.

## What it is not

Nothing in the card is rated, ranked or summed. The order is the catalog's domain order and
within it the catalog's marker order, never "most important first". A position is the
laboratory interval's side (`lib/referencePosition`), the only verdicts named are the
clinician's own by their absence ("ohne Urteil"), and `STALE_AFTER_DAYS` is a stated number
on the page, not a judgement about any marker. The wording passed the forbidden-language scan.
This is a view over facts the patient page already shows, assembled differently; the
classification register carries its row.

## Where it is computed

`lib/presenters/visitPrep.ts`, a pure function over the domain overview
(`presentDomainOverview`), so every count agrees with the counts and filters of the "Vor dem
Termin" panel below it: a value this card calls new is a value that panel's `since_run`
filter shows. The page of its own reads what the patient page reads (patient, timeline,
interpretation, catalog) over the same governed loads; the API audits each read as it does
there. No new endpoint, no new table.

## Tests

`apps/web/e2e/visit-prep.spec.ts`: the presenter over synthetic timeline points (no run; a
new value and a crossed interval; an old core marker; a value awaiting review counted, not
listed; a value without a catalog marker; nothing at all), and one browser pass over the
seeded patient (the card, a marker's line opening the history, the page of its own with its
print button and the way back). The language test and the web smoke name the card in both
languages.

## Later

A clinic's own number of days instead of `STALE_AFTER_DAYS`; a narrative over these facts
only under CLAUDE.md's AI contract (every sentence with an observation id, a fake provider,
validation before persistence), and only after the clinic asks for one.
