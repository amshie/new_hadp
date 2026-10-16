# 08 — MVZ Labor Süd, an unusual change against the last published value

**Layout B.** The record holds LDL 2.1 mmol/L (March). The report says LDL 310 mg/dl.

**What must hold**

- LDL converts to 8.016538 mmol/L; relative change 2.817 > TEST threshold 1.5 →
  `implausible_delta` (yellow). Yellow, not red: a large change can be real; a human looks.
- HbA1c 5,6 against 5.4 → change 0.037, under its threshold → green.
- The delta detail names the last value and the relative change so the reviewer sees why.

**Why it matters** — the delta check is context for the reviewer, never a verdict about the
patient; it fires on the number, not on any clinical meaning.
