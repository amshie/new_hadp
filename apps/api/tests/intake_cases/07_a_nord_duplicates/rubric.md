# 07 — Labor Nord, duplicates against the record and inside the batch

**Layout A.** The record already holds HbA1c 5,4 % and LDL 3,1 mmol/L for the same day; the
proposal also lists HbA1c twice.

**What must hold**

- HbA1c and LDL → `duplicate_of_published` (red): same KPI, same day, same text, same unit.
- Glucose → green (not in the record).
- The second HbA1c → `duplicate_in_batch` (red); the first occurrence carries the published
  duplicate, not the batch one.

**Why it matters** — a repeated report must not add a second row to the record; the human sees
the duplicate and rejects it, nothing is dropped silently.
