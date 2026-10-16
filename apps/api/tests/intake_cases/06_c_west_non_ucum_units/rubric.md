# 06 — Praxislabor West, units the platform does not know

**Layout C**, text layer present. Units a German report may print that are not UCUM, or UCUM
but not approved for conversion.

**What must hold**

- Glucose "mg%" → `unit_unknown` (red).
- HbA1c "mmol/mol" (IFCC) → `unit_unknown` (red): no approved factor to %.
- Ferritin "ng/ml" → red (canonical is ug/L; no approved factor), **and** its reference "s.o." is
  not a number → `reference_unreadable` (yellow) recorded beside it; the value stays red.
- LDL in mmol/L → green.

**Why it matters** — an unknown unit is never normalized by magnitude or by resemblance; the
human sees the red and edits or rejects.
