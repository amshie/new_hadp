# Patient data export — format `hadp-patient-export`, version 1

Status: **built on synthetic data, 2026-10-12.** Not legal advice: what a complete answer to a
subject-access request (GDPR Art. 15) or a portability request (Art. 20) must contain is a
determination for the clinic's data protection officer and counsel. This document describes what
the product produces and — just as important — what it leaves out.

## What it is

The clinic is the controller and answers a data subject's request; the platform gives it the tool.
An **owner** opens the patient page, presses "Datenauskunft erstellen", confirms, and the browser
downloads one ZIP file for that one patient. Handing the file to the person happens outside the
product.

- Endpoint: `POST /api/v1/patients/{patient_id}/data-export` — owner only, tenant-scoped (a patient
  of another clinic is a 404), rate-limited (5 per 10 minutes per user, across patients). Refused
  for an erased record (409 `patient_erased`), when the original files to ship exceed 100 MB
  together (409 `export_too_large`), and when a stored file cannot be read because storage does
  not answer (503 `storage_unavailable`) — an outage never produces a thinner package.
- The package is **built on request and never stored** — there is no copy to retain or to lose.
  Its record is the audit event `privacy.export`: who, when, for which patient, the counts, the
  size and the SHA-256 checksum of the file (so a file that was handed over can be recognized
  later). No content is audited. An export refused for a record that exists (409, 503) leaves
  `privacy.export_refused` with the refusal code and the patient id; a request for a record that
  does not exist in this clinic (404) leaves nothing, like any other such request.
- `GET /api/v1/patients/{patient_id}/data-exports` lists the exports generated so far, read from
  the audit trail (owner only).
- There is no `DataExportRequest` table: an export has no lifecycle (it is generated or refused in
  one request), so the audit event is the whole record.

## Three rules

1. **Only a file a reader imported into this record is shipped.** The import is the only identity
   check the product has — one person per file, and the date of birth when both the file and the
   record carry one. It is a weak check (see "Known limits"), but it is a check. A file that was
   merely uploaded here — refused as another person's report, a file for several patients, a
   format without a reader, a file that values were only typed from by hand — never passed it:
   neither its content, nor its name, nor its id is in the package. Only their number is given;
   a value typed by hand from such a file is included and marked `source_document_withheld`.
2. **A failure is a failure.** If storage cannot answer, the export fails. A file that definitely
   no longer exists, or whose bytes no longer match the checksum recorded at upload, is listed
   without content, and the cover note counts it.
3. **Things are called what they are.** A value the platform computed is marked as computed, with
   its formula and inputs — and marked again when a laboratory correction has replaced one of
   those inputs. A released report version that the clinic later withdrew or replaced is marked
   as withdrawn.

## What the package contains

| Entry                            | Content                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| `LIESMICH.txt`                   | German cover note: what the file is, what it holds, how to read a value, what is not |
|                                  | included.                                                                            |
| `export.json`                    | Everything in machine-readable form (UTF-8 JSON), see below.                         |
| `documents/<document id>/<name>` | The stored original source files, byte for byte.                                     |

`export.json`:

- `format`, `format_version`, `generated_at`, `synthetic`, `controller` (clinic id and name).
- `patient` — id, name, external reference, date of birth, when the record was created.
- `consent_events` — the append-only stream as recorded: purpose, grant or withdrawal, consent text
  version, channel, time.
- `observations` — every value held for the patient, each with:
  - `computed` — false for a value a source reported, true for one the platform computed from
    other values (`derivation`: formula id and version, algorithm, the input values, and
    `input_replaced` when a laboratory correction has since replaced an input);
  - the **source representation** as the source wrote it (`original_name`, `original_value`,
    `original_unit`, `reference_text`) — never altered (for a computed value these hold the result
    of the computation);
  - the normalized representation where one exists, with the normalization version, the mapping
    (`metric_code`, `kpi_code`, `mapping_confidence`) and the measurement context the source
    supplied (method, protocol, device, versions). `reference_low` / `reference_high` are the
    source's bounds as numbers — in `normalized_unit` when a normalized value exists, otherwise
    in the source's own unit (`original_unit`); `reference_text` is what the source wrote;
  - when it was sampled (`observed_at`; a day only when the source named only a day) and received;
  - where it came from (`source_document_id`, `source_record_locator`); `source_document_withheld`
    is true when the value cites a stored file that is not part of the package (rule 1);
  - its **review state** — `published`, `pending` (waiting for a clinical decision) or `rejected`.
    A value that is not published is the person's data too; it is included with its state said;
  - correction lineage (`supersedes_observation_id`, `superseded_by_observation_id`).
- `source_documents` — the files a reader imported into this record: metadata and the path inside
  the package. `file` is null, with `file_problem` `missing` or `checksum_mismatch`, when the
  stored file no longer exists or no longer matches the checksum recorded at upload.
- `source_documents_not_imported` — how many files are stored for this record without ever having
  been read into it. A number only (rule 1).
- `released_reports` — every report version that **passed the release gate** (the current one and
  earlier ones), with its statements, the observations each statement cites, `withdrawn`, and
  where the wording comes from (the drafting component and its version; whether a clinician
  revised it by hand).
- `not_included` — the list below, in machine-readable form.

Decimal values are strings (no binary rounding). Instants are ISO 8601 in UTC.

## What it does not contain

Listed inside the package itself, in `export.json` and in `LIESMICH.txt`:

- report drafts and versions that were not released to the person;
- the clinic's interpretation runs (unreleased working documentation);
- individual review decisions (the resulting state of each value is included);
- stored files that no reader imported into this record (rule 1);
- technical records of each import (the files that were read are included);
- the audit trail of accesses and changes;
- requests to erase or export the record;
- names and identifiers of clinic staff;
- invitations and access links (stored only as one-way hashes).

**Why:** nothing unreleased leaves the product except through the two-tier physician gate
(clinician approval, medical-director release). An export that carried drafts or interpretation
runs to the person would be a second, ungated release path. Whether those items nevertheless
belong in a complete Art. 15 answer is an open DPO/counsel question — until it is decided, the
card and the cover note say plainly that the file may not be the complete answer.

## Known limits

- **Completeness is not decided** (above). The file is honest about its scope; it is not a
  certified Art. 15 response.
- **No delivery to the person inside the product.** The owner downloads the file and hands it
  over by the clinic's own secure means.
- **Built in memory** (about twice the size of the files while it is assembled), hence the 100 MB
  cap on original files and a per-user rate limit; concurrent exports are not otherwise bounded.
  A larger record needs a streamed or asynchronous build.
- **Whose file it is rests on the import's check, and that check is weak.** A single-patient
  file imported into the wrong record is exported as that record's, like the values read from it.
  This happens when the file or the record carries no date of birth (the date is optional when a
  patient is created), when two people share a date of birth — the name in the file is not
  compared — and always for a CSV, which names no person at all
  (`docs/product/LAB_IMPORT_FORMATS.md`).
- **A missing object must be reported as missing by storage.** With credentials that may not list
  the bucket, S3 answers "access denied" for an object that does not exist; the export then fails
  (503) on every attempt for that record instead of listing the file as missing.
- **A file that was never imported is left out even if it is the person's own** (a PDF has no
  reader). The package gives the number; the clinic has to hand such a file over separately.
- **A released version counts as released even if the person never opened it** (the link was not
  passed on, or consent was withdrawn right after).
- **A throttled export attempt is traced without the user**: the shared rate limiter records
  `rate_limited` with the action only.
- **Only the owner** can generate an export; there is no two-person step as there is for erasure.
- **No CSV.** A spreadsheet-ready table was left out on purpose: a value or analyte name that
  starts with `=`, `+`, `-` or `@` can run as a formula when the file is opened, and neutralizing
  it would alter the data. `export.json` is the single machine-readable form.
- **Placeholders travel with the data**: consent purposes and the consent text version are the
  synthetic-Alpha placeholders.
