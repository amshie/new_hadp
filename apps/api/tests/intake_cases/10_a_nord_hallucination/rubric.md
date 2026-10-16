# 10 — Labor Nord, values the model did not read from the page

**Layout A.** The proposal contains a misread value, a value that is not on the page at all, and
a value citing a page the document does not have.

**What must hold**

- HbA1c and LDL → green (on the page, as written).
- Glucose proposed as "51" where the page says "5,1" → `value_not_on_page` (red): a number must
  stand on the page as a number of its own; "51" is not a substring match of "5,1".
- Ferritin "85 µg/L" → `analyte_not_on_page` (red) — the page has no ferritin; also
  `unit_unknown`, since "µg/L" is not a spelling the platform maps to "ug/L" (a recorded gap).
- HDL citing page 3 of a 1-page document → `page_out_of_range` (red); the verbatim check is
  skipped because there is no page to check against.

**Why it matters** — this is the hallucination gate at the moment of writing, not at
evaluation time: a value that is not on the cited page is red before any human sees it.
