# 09 — Praxislabor West, dates that cannot be right as written

**Layout C** with a sampling date per line; issue date 20.09.2026; "today" is 16.10.2026.

**What must hold**

- HbA1c (18.09.2026) → green.
- LDL (05.01.2027) → `date_in_future` (yellow).
- Glucose (01.05.2026) → more than 90 days before the issue date → `date_outside_window` (yellow).
- HDL (01.01.1965) → before the patient's birth → `date_before_birth` (red).
- Total cholesterol with no date in the proposal → `date_missing` (red): a value without a
  sampling date cannot enter the record (no date is ever invented).

**Why it matters** — a date is provenance; a value with a wrong date lands on the wrong point of
the timeline and misleads every later comparison.
