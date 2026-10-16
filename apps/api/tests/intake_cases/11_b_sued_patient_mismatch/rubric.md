# 11 — MVZ Labor Süd, another patient's report

**Layout B.** The report prints date of birth 30.07.1968; the record says 12.03.1970.

**What must hold**

- The batch check fails with `patient_mismatch` (red) and **every** value is red, however
  clean it is otherwise (LDL and HbA1c would both be green on the right patient).
- Nothing about the values themselves changes: mapping, conversion and bounds still run and are
  recorded, so a reviewer sees that only the patient is wrong.

**Why it matters** — the most dangerous failure of a document intake is a correct value in the
wrong record; the document's own identification is checked against the record before anything
can be confirmed.
