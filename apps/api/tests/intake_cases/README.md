# Intake golden cases

Synthetic laboratory reports for the lab intake agent (`docs/product/INTAKE_AGENT.md`), one
directory per case:

- `input/report.pdf` — drawn by `generate_fixtures.py`; three invented German layouts, one scanned.
- `input/pages.json` — the page texts a reader produced (pdfplumber; tesseract for the scan).
- `input/patient.json` — the record: date of birth, published values, and TEST-ONLY bounds.
- `input/proposal.json` — the fixed proposal the deterministic tests run on: what a model would
  return for this report, including the mistakes the case is about.
- `expected.json` — the checked batch, compared **bit for bit** (`tests/test_intake_cases.py`).
- `rubric.md` — what must hold and why, written by hand.

No real laboratory, no real person, no real value. Regenerate with
`uv run python tests/intake_cases/generate_fixtures.py --write-expected` and review the diff of
every `expected.json` before committing it: a changed expectation is a changed rule.
