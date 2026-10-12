# Structured laboratory import — supported formats (ingestion tier 1)

Status: **built on synthetic data, 2026-10-12.** No real laboratory has been connected. The readers
were written against published format descriptions and self-authored synthetic files — **not**
against a file from a pilot laboratory. The LDT 3 reader was additionally run over the KBV's own
published test files (fictional patients; see `docs/data-governance/THIRD_PARTY_DATA.md`). Treat
every statement below as "what the reader does", not as "what a given laboratory sends".

## What a reader does — and does not do

A reader turns a stored source document into rows for the existing import pipeline
(`modules/imports/service.py:ingest_values`). It only **transports** source values:

- analyte name, value, unit, and reference bounds are passed on **verbatim** (a decimal comma is not
  rewritten; the original stays the original);
- every row carries a **source locator** (`line N` in the file) and the reader's name and version;
- nothing is normalized, converted, or interpreted by a reader — that stays with
  `modules/imports/normalize.py` and the human review queue.

Three outcomes exist, and none of them hides data:

| Outcome          | When                                                            | Effect                                                                       |
| ---------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Refused**      | The file cannot be read structurally (see the lists below).     | Nothing is imported — a file is read whole or not at all. HTTP 422, audited. |
| **Imported**     | A row with a value and a date.                                  | Normal pipeline: published, or held in the review queue with its reasons.    |
| **Not imported** | LDT only: a result the pipeline cannot carry (see each format). | Recorded as a rejected import row (locator + reason) and counted.            |

Endpoint: `POST /api/v1/patients/{patient_id}/documents/{document_id}/import` (care staff). A
document is imported **at most once**; a repeat returns the first import (HTTP 200) and writes
nothing. The document must belong to that patient. The format is chosen by inspecting the bytes,
never by file name or declared content type. A PDF has no reader. A refused import leaves an
`import.refused` audit event with the refusal code only (never file content).

Common to all readers:

- A carried field that is too long for its column, or contains a control character (a NUL byte, for
  example), refuses the file. Nothing is truncated or cleaned.
- A sampling date before 1900 or later than tomorrow (UTC) refuses the file — it is almost always a
  misread layout.
- Laboratory files carry wall-clock times without a zone (CSV, LDT 2). They are read in
  `LAB_LOCAL_TIMEZONE` (default `Europe/Berlin` — an assumption that fits the DACH pilot and nothing
  else). A date without a time stays date-only. A time that falls into a daylight-saving gap or
  repeats at the change back is held for review (`ambiguous_local_time`).

What normalization then requires (it applies to manual entry as well):

- A value is a number only if it is a plain decimal: ASCII digits, an optional sign, `.` or `,` as
  the decimal separator, an optional small exponent. `NaN`, `Infinity`, digit-group underscores
  (`3_4`) and other scripts' digits are **not** numbers and go to review (`unparseable_value`).
- A reference bound the source gives but that is not such a number goes to review
  (`unparseable_reference`) instead of silently turning a two-sided interval into a one-sided one.

## CSV — `hadp-csv` version 1

A UTF-8 table with a header line. This is **our** layout, not a laboratory standard: a laboratory's
own CSV export only works if its header uses these names.

- Delimiter: `;`, `,` or TAB — the one under which the header carries every required column.
- Columns are found by header name (case-insensitive); unknown columns are ignored.
- **Every row must have exactly as many cells as the header.** A row with one cell too many is what
  an unquoted decimal comma in a comma-separated file looks like; it is refused, never read by
  position.

| Field          | Required | Header names                                                               |
| -------------- | -------- | -------------------------------------------------------------------------- |
| Analyte name   | yes      | `Analyt`, `Analyse`, `Parameter`, `Bezeichnung`, `Analyte`, `Test`, `Name` |
| Value          | yes      | `Wert`, `Ergebnis`, `Value`, `Result`                                      |
| Date           | yes      | `Datum`, `Abnahmedatum`, `Date`, `Collected_on`                            |
| Unit           | no       | `Einheit`, `Unit`                                                          |
| Reference low  | no       | `Referenz_von`, `Referenz_unten`, `Reference_low`                          |
| Reference high | no       | `Referenz_bis`, `Referenz_oben`, `Reference_high`                          |
| Reference text | no       | `Referenzbereich`, `Reference_text`                                        |
| Time           | no       | `Uhrzeit`, `Abnahmezeit`, `Time`                                           |

- Dates: `YYYY-MM-DD` or `DD.MM.YYYY`. A slash date (`06/10/2025`) is ambiguous and refused.
- Times: `HH:MM` or `HH:MM:SS`.
- Refused: a header without the required columns, two columns for one field, a row whose cell count
  differs from the header's, an empty name / value / date, unbalanced quoting, more than 2000 values.

## LDT 2 — `ldt2-8201` version 1

Reads **Labor-Bericht records (8201)** of the KBV LDT 2 format, written against the KBV
"Datensatzbeschreibung LDT" (LDT1014.01; LDT1001.02 for its date order).

Read per test (a test starts at field 8410): 8411 name (else the 8410 ident), 8420 value, 8421
unit, 8461 / 8462 reference bounds, 8460 reference text, 8432 sampling date, 8433 sampling time.

Held for review, by the source's own status:

| Source                                      | Review reason                                  |
| ------------------------------------------- | ---------------------------------------------- |
| Befundart 8401 = `V` (preliminary)          | `preliminary_report`                           |
| Teststatus 8418 = `B` (already reported)    | `previously_reported`                          |
| Teststatus 8418 = `K` (corrected)           | `corrected_result`                             |
| A result text 8480 or note 8470 on the test | `source_comment`                               |
| A note on the whole report (8490)           | `source_comment` on every value of that report |

Not imported (recorded and counted): a test without 8420 — `text_result`, or `result_pending` when
8418 = `F`; a value without a sampling date — `no_sampling_date` (the report date is never used in
its place).

Refused: a line that is not exactly the line format (wrong length, no CR LF — including the last
line); not exactly one package header (8220); **no package trailer (8221) after the reports — the
file was cut off**; an LDT version other than LDT1014.01 / LDT1001.02; a character set other than
9106 = 2, 3, 4 (or plain ASCII when undeclared); any report record other than 8201 (8202, 8203,
8204 …); a result field outside a test; a field repeated inside a test; reports for more than one
patient; several reports that name no patient; a date of birth that differs from the patient
record (HTTP 409).

## LDT 3 — `ldt3-8205` version 1

Reads **report records (8205 "Befund")** of the current KBV format, written against the KBV "LDT 3
Satzbeschreibung" v3.2.20. LDT 3 is a tree: an attribute line (a field 8100–8299) is always
followed by its object (`8002 Obj_nnnn` … `8003 Obj_nnnn`). The file declares its own version
(field 0001), so the LDT 2 and LDT 3 readers are chosen by content.

Read per report: the patient (Obj_0045 → Obj_0047; date of birth 3103); every material (Obj_0037)
with its sampling timestamp (8219 → Obj_0054: date 7278, time 7279, zone 7273); every
clinical-chemistry result (Obj_0035 → Obj_0060): 8411 name (else the 8410 ident), and per written
value 7306 (how it is written) → 8420 value, 8419 unit system, 8421 unit, reference range
(Obj_0042: 8461 / 8462 bounds, 8460 text).

Three rules decide what a value means, and each is fail-closed:

- **When.** A result names its sample by 7364; its time is the sampling time of the material with
  that identifier — an exact instant, because LDT 3 states the zone (`UTC+2`). If two materials
  share the identifier with different times, or the result's samples disagree, there is no time.
  The measurement time (8225) and the report time are never used instead. The record description
  names 7364 in both objects but states no explicit join rule; the join is our reading of the
  tables, confirmed on the KBV test files.
- **Which value.** One measurement may be written in several unit systems. If exactly one written
  value is in SI units (8419 = 1) it is carried and the others are recorded as not imported
  (`alternate_unit_value`); otherwise every written value is imported and held for review
  (`multiple_result_values`).
- **Which range.** A value with several reference ranges, a range whose bounds name another unit
  than the value, or a range that follows no value, gets **no** bounds and is held for review
  (`ambiguous_reference`).

Held for review, by the source's own status:

| Source                                                                             | Review reason                                  |
| ---------------------------------------------------------------------------------- | ---------------------------------------------- |
| Ergebnisstatus 8418 = `03` (technically validated) or `10`                         | `preliminary_report`                           |
| Ergebnisstatus 8418 = `04` or `08` (corrected)                                     | `corrected_result`                             |
| Ergebnisstatus 8418 = `07` (already reported)                                      | `previously_reported`                          |
| A note or attention message anywhere on the result (Obj_0068, Obj_0026)            | `source_comment`                               |
| A text value written next to the number                                            | `source_comment`                               |
| A note or attention message on the report, the order or a sample (not attachments) | `source_comment` on every value of that report |
| A time without a zone that is not exactly one instant                              | `ambiguous_local_time`                         |

Values written as a number (7306 = `01`) or a number with a measuring limit (`02` / `03`, e.g.
`<0.5`) are carried verbatim; the latter are not publishable as numbers and reach the review queue
through normalization.

Not imported (recorded and counted): 8418 = `02` — `result_pending`; 8418 = `01`, `09`, `11`, `12` —
`no_result`; no numeric value (7306 = `04`–`08`, `99`) — `text_result`; no single sampling time —
`no_sampling_date`; the other writings of a value carried in SI units — `alternate_unit_value`; any
other result object (microbiology, cytology, blood group, tumour, "other") —
`unsupported_result_type`.

Refused: a line that is not exactly the line format; an object or record that is not closed
properly, or an object that follows no attribute line; a version other than LDT3.2.x; a trailer
that is not exactly the **checksum** (field 9300, SHA-1 over everything before that line) or whose
checksum does not match; any record other than 8205 between header and trailer (for example an
order, 8215); **a report that does not name exactly one person** (an animal or environmental
sample is not a patient's report); two range specifications (8424) in one range object; an unknown
result status or time-zone notation; reports for more than one patient; a date of birth that
differs from the patient record (HTTP 409).

## Upload

An LDT file is accepted at upload by content inspection: **every** line must be a well-formed line
of the format. It is stored under the fixed content type `application/x-ldt`; the type the client
declared is neither trusted nor kept. Anything else still needs an allow-listed content type.

## Known limits (all formats)

- **One file, one patient.** A laboratory transfer file usually carries reports for many patients;
  such a file is refused. Matching reports to patients across a clinic is a separate feature. The
  only identity check against the patient record is the date of birth, and only when both the file
  and the record have one.
- **Text results are not carried** (the pipeline holds numeric observations only).
- **A reviewer cannot open the source file in the product yet.** `source_comment` asks a human to
  read the source, but no route serves the stored document; until the upload / review UI exists the
  original file has to be read outside the product.
- **Not read:** the laboratory's own limit indicator (8422), specimen details other than the
  sampling time, body measurements, attachments. LDT 3's range specification (8424) is not
  interpreted — whether it distinguishes kinds of ranges has not been verified.
- **Laboratory attention messages hold a value for review.** In the KBV example files every result
  flagged high or low carries one; if a laboratory does the same, its flagged values wait for a
  human while unflagged ones publish.
- **No supersession and no duplicate detection.** A corrected or repeated value is held for review;
  it is not matched to the value it replaces. A final report that repeats the values of an earlier
  partial report without marking them imports them again.
- **Exactly-once rests on a row lock** on the source document; there is no unique index on the
  import job's idempotency key.
- **LDT 2: the record length (8100) is not checked**; every line's own length is. LDT 3 has a file
  checksum, which is checked — it detects damage, not forgery.
- **LDT 3 minor versions:** only 3.2.x is accepted; the reader was checked against 3.2.20.
- The patient's name in the file is compared in memory only (one-patient check) and is never
  stored outside the original file.
