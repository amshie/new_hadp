# 0025 — The patient page in three tabs, and the pilot's figure

Status: implemented (synthetic Alpha). Item 3 of the design review (long, repetitive pages)
and item 6 of the CTO assessment (the primary metric on screen), as the founder decided:
tabs, with the preparation first.

## The page

`/patients/{id}` keeps its header (name, reference, where the report stands, the actions)
and puts the rest in three tabs, in this order:

| Tab          | Holds                                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| Vorbereitung | the page before a visit (docs/notes/0022) and the data coverage                                                   |
| Werte        | "Vor dem Termin" with its filters, the six domain cards, the six domain lists, the values no catalog marker names |
| Akte         | consents, laboratory files, the data export (owner), the audit steps                                              |

The page opens on Vorbereitung: one screen instead of seven. The Werte tab carries the
number of published values; nothing else is counted on a tab.

A domain list folds the core markers no source has named for the record into one line —
"n Kernmarker ohne Wert anzeigen" — and unfolds them on request. With a filter pressed on
"Vor dem Termin" nothing is folded: the "ohne Wert" filter lists exactly those markers, as
before. The domain cards' bars and counts still count every core marker.

Every panel is in the page, hidden rather than left out: the server's HTML holds the whole
record, a page without scripts shows every part one under the other, and a link into a
domain list still lands. The address's fragment names the target — `#vb-domain-<axis>` or
`#vb-unassigned` from the preparation card, the practice view and the printable page;
`#vorbereitung`, `#werte`, `#akte` for a tab — and the fragment opens the tab that holds it,
on load and when it changes. The tabs follow the ARIA tabs pattern: arrow keys, Home and
End move between them; the selected tab is the one in the tab order.

## The pilot's figure

CLAUDE.md names one primary metric: the median preparation time per appointment, reduced
by at least half against a captured baseline. The platform already held the two statements
(docs/notes on the preparation time; `GET /api/v1/metrics/preparation-time`): the baseline
the clinic stated before the platform, and its latest follow-up. What was missing was the
one number.

`lib/presenters/preparationTime.ts` sets the two statements against each other —
`statedChange`: minutes and a rounded percentage, negative when the follow-up lies below
the baseline, null without both statements or against a baseline of zero — and says whether
the pilot criterion (`PILOT_TARGET_PERCENT`, 50) is met. The figure is shown twice: on the
owner's overview, as the first line of the practice card ("Vorbereitungszeit je Termin:
−55 %", with the two numbers and the criterion under it), and on Einstellungen ›
Vorbereitungszeit, as a card under the clinic's statements. Without a follow-up the line
says so; without a baseline, that.

Both numbers are the clinic's own; the platform computes the difference and nothing else.
The turnaround it measures from the report lifecycle (first draft to approval) stays a
separate figure on both pages, as before: a different quantity, never set against the
stated minutes.

## Tests

`apps/web/e2e/patient-tabs.spec.ts`: the presenter's arithmetic and signs; a browser pass
over the seeded record (the three tabs, what each shows and hides, the folded markers and
their unfolding, the keyboard, a fragment set on the page and one carried by the address);
and the owner's figure after two statements. The primary workflow, the language pass and the
"Seit zuletzt" story open the tab they need. The web smoke reads the whole record in the
server's HTML, as before.
