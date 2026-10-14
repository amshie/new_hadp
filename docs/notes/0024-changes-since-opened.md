# 0024 — Seit zuletzt: what moved in a record since the person opened it

Status: implemented (synthetic Alpha). Gap 3 of `docs/product/COMPETITIVE_LANDSCAPE.md`
("notifications"), in-app first: when a person signs in, the overview names the records in
which something arrived or moved since they last opened them. The e-mail channel the gap
names waits for a production mail provider inside the EU residency constraint (see "Later").

## What it shows

A card on the overview, "Seit zuletzt", between "Heute" and the work list. One entry per
record the person has opened at least once and in which something happened after that
opening, the latest change first:

| Fact                   | What counts                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| n neue Werte           | values published and received after the opening (a rejected value never counts)                |
| n Werte in Prüfung     | values received after the opening that await a human decision                                  |
| Interpretation: Lauf n | an interpretation run a colleague recorded after the opening                                   |
| Bericht vN: _status_   | the step a colleague took on the latest report after the opening, as the patient page names it |
| zuletzt geöffnet vor … | when the person opened the record                                                              |

The entry's time is the latest of those moments. "Akte öffnen" leads to the record, and
opening it is what clears the entry — nothing is marked read by hand. Records the person has
never opened are counted under the card ("n Akten haben Sie noch nie geöffnet"), not
listed: without an opening there is no "since".

A step the person took themselves is not news to them: a run they recorded, a draft they
generated or edited, a report they approved or rejected stays out. A release carries no
account on the version, so a release is shown to everyone, the releasing director included.

## What it is not

Nothing is rated, weighted, summed or ranked. The order is time. No value, no position
against an interval and no verdict is named on the card — only that values arrived, a run
was recorded, a report moved. A clinic-wide alert rule (a threshold, a deviation) would be a
`rules` feature with its own register row.

## Where it is computed

`GET /api/v1/worklist/changes` (`apps/api/src/hadp_api/api/worklist_routes.py`), open to
every staff role that may read observations, tenant-scoped under RLS, audited as
`worklist.changes.read` with the number of entries only. The person's last opening of each
record is their own `patient.read` event in the clinic's trail
(`audit.service.last_reads_by_actor`): the trail already holds every opening, so nothing new
is stored and no table was added. `observations.service.arrivals_by_patient` counts the
values received after each opening; the latest run and the latest report's current version
come from the interpretation and reports services, with `reports.service.version_stepped_by`
saying whether the person took the step themselves.

The web (`apps/web/src/app/overview`) loads it beside the rest of the overview; a failed
load leaves the card saying so and the page stands. The presenter
(`lib/presenters/changes.ts`) only orders.

## Tests

`apps/api/tests/test_changes_api.py`: authentication; a record opened, then a colleague's
import, run and draft and a value awaiting review, against a record never opened; the entry
cleared by opening the record again; the person's own run left out; the audit count per
read; every staff role; tenant isolation. `apps/web/e2e/changes.spec.ts`: the presenter's
order, and one browser story — a clinician creates and opens a record, a colleague imports a
file into it, the overview names it with its counts, and opening the record clears it. The
web smoke names the card in both languages.

## Later

E-mail (then push) over the same facts, once a mail provider inside the EU residency
constraint is contracted: identifiers and counts only in the message, never a value, with
the send recorded in the trail. A per-person "mark all as seen" is deliberately not built:
opening the record is the only mark, so the card never says "seen" of a record nobody looked
at.
