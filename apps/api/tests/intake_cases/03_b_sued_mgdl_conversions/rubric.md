# 03 — MVZ Labor Süd, mg/dl with approved and unapproved conversions

**Layout B** (two-column "Klinische Chemie" list), conventional units, decimal comma,
"Norm:" prefix on the reference. Text layer present.

**What must hold**

- LDL, HDL, total cholesterol and glucose convert to mmol/L by the **approved** factors
  (0.0258598 and 0.0555) with exact decimal arithmetic — `normalized_value` is the full product
  (128 × 0.0258598 = 3.3100544), never rounded; the reference bounds convert by the same factor.
- Triglycerides (mg/dl) and creatinine (mg/dl) have **no approved conversion** → `unit_unknown`
  (red), no normalized value, bounds carried as written. Converting them would need a signed
  factor; guessing one is a patient-safety bug.
- Everything converted is green.

**Why it matters** — the conversion table is the only place a number changes; this case pins
every factor the intake may apply and refuses every one it may not.
