# 04 — MVZ Labor Süd, impossible values

**Layout B.** Three values; two cannot be readings from a living person under the TEST bounds.

**What must hold**

- HbA1c "54 %" → `outside_hard_bounds` (red). (A real report would carry 54 mmol/mol; the
  check does not guess that — it refuses the number under the unit written.)
- LDL "0,0 mg/dl" → converts to 0 mmol/L, below the hard low of 0.1 → red.
- Glucose "520 mg/dl" → 28.86 mmol/L, inside the hard bounds → green: high, but possible, and
  the intake makes no statement about it (reference-interval comparison is out of scope).

**Why it matters** — the plausibility check is a gate against misreadings, not a clinical
flag; this case shows exactly where it fires and where it stays silent.
