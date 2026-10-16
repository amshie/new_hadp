# Lab intake agent

Status: **slice 1 of 5, synthetic data only (2026-10-16).** Built: the data model, the
deterministic checks, the one write, eleven golden cases. **Not built yet:** the agent and its MCP
tools (slice 2), the confirmation screen and the step that makes a confirmed value an observation
(slice 3), the extraction providers and their evaluation (slice 4), shadow mode and the error-rate
report (slice 5). Nothing in this slice writes to the patient record, and nothing confirms a value.

A laboratory report arrives as a PDF. A model **proposes** structured values from it. Deterministic
code **checks** each proposal and records what it found. A clinician **confirms** — and only then
does a value become an observation like any other. Every confirmation and correction is kept, so
the error rate of the proposals can later be measured per laboratory and per field.

The regulatory position of the product is an open determination
([`docs/regulatory/INTENDED_USE.md`](../regulatory/INTENDED_USE.md)); this agent extracts and
confirms, it interprets nothing. No reference-interval comparison, no clinical wording.

## The one rule

**The model proposes; deterministic code checks; a human releases.** This is enforced by what
exists, not by what the model is told: the agent will have read tools and exactly one write,
`create_pending_batch`, which writes into `pending_values`. There is no function on the agent's
side that writes an observation, so a hallucination or an instruction hidden in a PDF cannot cross
the gate — the door does not exist. A proposal that tries to carry a `status`, a `kpi_code` or
`checks` is refused whole (`modules/intake/schemas.py`, `extra="forbid"`).

## Data model (migration `0023_lab_intake`)

| Table                     | Scope                              | Written by                           | What it holds                                                                                                                                                                                                                                                                                   |
| ------------------------- | ---------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source_documents`        | tenant, RLS (existing)             | upload                               | The PDF itself, stored before anything reads it; checksum, idempotent re-upload.                                                                                                                                                                                                                |
| `intake_batches`          | tenant, RLS, **append-only**       | `intake.service`                     | One extraction run over one document: provider, `model_id`, `prompt_version`, page count, the date of birth and issue date the document names, the batch-level check (patient match).                                                                                                           |
| `pending_values`          | tenant, RLS, **append-only**       | `intake.service`                     | One proposed value: analyte, value, unit and reference **as written**, sampling date (date-only when the document names only a day), page and bounding box, the model's confidence; then what the checks computed: `kpi_code`, canonical unit, normalized value and bounds, `checks`, `status`. |
| `kpi_plausibility_bounds` | global, read-only for the app role | seed from `bounds_data.py` only      | Per KPI: hard bounds outside which a value cannot be a reading from a living person, and the relative change beyond which a human looks. **Ships empty** — a bound is a clinical statement and is recorded with who signed it.                                                                  |
| `observations`            | tenant, RLS (existing)             | a clinician's confirmation (slice 3) | The record. A confirmed value becomes an observation with `source_record_locator` = page and box, and a reference to its pending value. The timeline, interpretation and reports read observations only; they never read pending values.                                                        |

A pending value is never updated. What a human decides about it is a separate append-only record
(slice 3). The audit trail gets `intake.batch_proposed` per batch: identifiers and counts only.

## The deterministic checks (`modules/intake/checks.py`, ruleset `intake-checks-1`)

Every value runs through the same twelve checks in a fixed order; each records pass / fail /
skipped and a reason from a closed set. The status is computed from the reasons, never proposed:

| Status     | Meaning for the reviewer                           | Produced by                                                                                                                                                                                                                                                                               |
| ---------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **green**  | every check passed and confidence ≥ 0.9; one click | —                                                                                                                                                                                                                                                                                         |
| **yellow** | must be viewed before it is confirmed              | `unmapped_analyte`, `plausibility_not_configured`, `implausible_delta`, `date_in_future`, `date_after_issue`, `date_outside_window`, `reference_unreadable`, `low_confidence`, `patient_dob_not_proposed`                                                                                 |
| **red**    | must be corrected or rejected                      | `page_out_of_range`, `no_page_text`, `analyte_not_on_page`, `value_not_on_page`, `unit_not_on_page`, `value_not_a_number`, `unit_missing`, `unit_unknown`, `outside_hard_bounds`, `date_missing`, `date_before_birth`, `duplicate_of_published`, `duplicate_in_batch`, `patient_mismatch` |

The checks, in order: **patient match** (the document's date of birth against the record — on the
batch and on every value), **page cited**, **on the page** (analyte, value and unit stand verbatim
on the cited page; a value must stand as a number of its own, so "5,1" is not found in "15,1" and
"51" is not found in "5,1"), **mapping** (an exact catalog alias, never a guess), **value** (one
plain number, readable one way only), **unit** (the KPI's canonical unit, or an approved exact
conversion factor from `imports/normalize.py`; everything else is unknown), **reference** (the
laboratory's bounds carried whole or not at all, converted by the same factor as the value, never
compared), **plausibility** (signed hard bounds; no bounds → yellow), **delta** (against the last
published value of the same KPI in the same unit, when a threshold is signed), **date** (not
missing, not before birth, not in the future, inside 90 days before the issue date),
**duplicate** (same KPI or name, day, text and unit already published, or twice in the batch),
**confidence**.

The page texts come from the stored PDF's text layer (`documents/pdf_text.py`, pdfplumber), read by
the service itself — never from the agent. A scanned page has no text layer: until OCR runs as an
explicit step (slice 4), every value on it is red with `no_page_text`.

## What the golden cases show (`apps/api/tests/intake_cases/`)

Eleven synthetic reports in three invented German layouts, one of them a scan. Two findings worth
knowing before a pilot laboratory is connected:

- **The catalog's aliases are English.** A German report's _Kreatinin_, _Harnsäure_, _Triglyceride_,
  _TSH_ do not resolve and are yellow. German aliases are a signed addition, per name
  (go-live decision 7), not an engineering default.
- **Unit spellings are three.** `µg/L`, `mg%`, `mmol/mol`, `ng/ml`, `mg/dl` for triglycerides or
  creatinine — all red `unit_unknown`, because only the four approved factors convert anything.
  Each further factor is a signed decision.

## Adding a laboratory format

A format is a fixture, not a parser: the model reads the layout, the checks do not care about it.
To add one, add a case under `tests/intake_cases/` with a synthetic `report.pdf` (extend
`generate_fixtures.py` with a layout), the `pages.json` its reader produces, a `patient.json`, a
fixed `proposal.json`, a `rubric.md` saying what must hold, and regenerate `expected.json` on
purpose. Never a real report, never a real person.
