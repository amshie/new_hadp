# 02 — Labor Nord, German analyte names, no date of birth printed

**Layout A**, but the report prints the names a German laboratory prints (Kreatinin, Harnsäure,
Triglyceride, TSH) and omits the patient's date of birth.

**What must hold**

- The batch check fails with `patient_dob_not_proposed` (yellow) and every value carries it:
  nothing on this report may be confirmed with one click.
- HbA1c resolves (alias present); Kreatinin, Harnsäure, Triglyceride and TSH do **not** resolve
  → `unmapped_analyte` (yellow), no normalized value, reference bounds carried as written.
- No value is red: an unmapped name is a question for a human, not an error.

**Why it matters** — it records the alias gap honestly: the catalog's aliases are English
display names plus a handful of extras; German reports will map poorly until German aliases are
added and signed (go-live decision 7).
