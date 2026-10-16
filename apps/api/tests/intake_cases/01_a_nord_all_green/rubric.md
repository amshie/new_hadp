# 01 — Labor Nord, every value green

**Layout A** (table: Parameter · Ergebnis · Einheit · Referenzbereich), SI units, decimal comma,
date of birth and sampling date in the header. Text layer present.

**What must hold**

- Every one of the six values maps to a catalog KPI, is in its canonical unit, lies inside the
  TEST bounds, carries a readable reference interval, is dated inside the issue window, is not
  a duplicate, and has confidence ≥ 0.9 → **status green** for all six, no reasons.
- One-sided references are carried one-sided: LDL has an upper bound only, HDL a lower only.
- `normalized_value` equals the written number exactly (no conversion, factor 1).
- The batch's patient check passes: the document's date of birth is the record's.

**Why it matters** — the only case where "confirm all green" would confirm everything; the
baseline every other case deviates from.
