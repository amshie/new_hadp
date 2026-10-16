"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  importDocument,
  proposeIntake,
  uploadDocument,
  type DocumentImportResult,
  type IntakeProposeOut,
} from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

type LabWording = Messages["patientPage"]["lab"];

// Laboratory file intake from the patient page: the original file is stored first (API:
// content inspection, checksum, idempotent re-upload), then read by a structured reader into
// the import pipeline. The API enforces role, tenant, the one-patient rule and exactly-once;
// these actions only pass the file on and put outcomes into safe wording, in the language of
// the interface (lib/i18n). Error
// details from the API name codes and positions, never file content.

// Structured laboratory files are small; this is far above a real report and below the
// server-action body limit (next.config.mjs).
const MAX_BYTES = 5 * 1024 * 1024;

export type LabImportResult =
  | { ok: true; result: DocumentImportResult }
  | { ok: false; error: string; stored: boolean };

// The browser's declared type is unreliable for these files (a CSV arrives as a spreadsheet
// type on some systems, an LDT file as nothing): declare by extension and let the API's content
// inspection decide.
function declaredType(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".csv")) return "text/csv";
  if (lower.endsWith(".txt")) return "text/plain";
  if (lower.endsWith(".pdf")) return "application/pdf";
  return "application/octet-stream";
}

// The API detail is "<code>: <position and field names>" — never file content. The code picks
// the text (lib/i18n: patientPage.lab.refusals, keyed by the API's code); a line number, if
// the detail names one, is passed on.
function refusalMessage(detail: string, t: LabWording): string {
  const code = detail.split(":", 1)[0]?.trim() ?? "";
  const line = detail.match(/\bline (\d+)\b/)?.[1];
  const where = line ? fill(t.errors.line, { line }) : "";
  const known = Object.prototype.hasOwnProperty.call(t.refusals, code)
    ? (t.refusals as Record<string, string>)[code]
    : undefined;
  if (known) return fill(t.errors.nothingTaken, { reason: known, where });
  return /^[a-z_]+$/.test(code)
    ? fill(t.errors.unreadableCode, { code, where })
    : t.errors.unreadable;
}

function uploadMessage(e: ApiError, t: Messages["patientPage"]): string {
  if (e.status === 403) return t.notAllowed;
  if (e.status === 404) return t.recordUnavailable;
  if (e.status === 429) return t.lab.errors.tooManyUploads;
  if (e.status === 409 && e.message.startsWith("document_other_patient"))
    return t.lab.errors.otherPatient;
  if (e.status === 422) {
    if (e.message.includes("empty")) return t.lab.errors.empty;
    if (e.message.includes("too large")) return t.lab.errors.tooLarge;
    if (e.message.includes("UTF-8")) return t.lab.errors.notText;
    return t.lab.errors.wrongType;
  }
  return t.lab.errors.uploadFailed;
}

async function runImport(
  patientId: string,
  documentId: string,
  t: LabWording,
): Promise<LabImportResult> {
  try {
    const result = await importDocument(patientId, documentId);
    return { ok: true, result };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403)
        return { ok: false, stored: true, error: t.errors.importNotAllowed };
      if (e.status === 429)
        return { ok: false, stored: true, error: t.errors.tooManyImports };
      if (e.status === 422 || e.status === 409)
        return { ok: false, stored: true, error: refusalMessage(e.message, t) };
    }
    return { ok: false, stored: true, error: t.errors.importFailed };
  }
}

export async function uploadLabFileAction(
  patientId: string,
  form: FormData,
): Promise<LabImportResult> {
  const t = (await getMessages()).patientPage;
  if (!isUuid(patientId))
    return { ok: false, stored: false, error: t.invalidPatient };
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0)
    return { ok: false, stored: false, error: t.lab.errors.chooseFile };
  if (file.size > MAX_BYTES)
    return { ok: false, stored: false, error: t.lab.errors.tooLarge5 };
  // The stored file name is bounded (255 characters); refuse here rather than fail there.
  if (file.name.length > 200)
    return { ok: false, stored: false, error: t.lab.errors.nameTooLong };
  let documentId: string;
  try {
    const typed = new Blob([await file.arrayBuffer()], {
      type: declaredType(file.name),
    });
    const stored = await uploadDocument(patientId, typed, file.name);
    documentId = stored.id;
  } catch (e) {
    return {
      ok: false,
      stored: false,
      error:
        e instanceof ApiError ? uploadMessage(e, t) : t.lab.errors.uploadFailed,
    };
  }
  const outcome = await runImport(patientId, documentId, t.lab);
  // The file is stored either way: the list of documents has changed.
  revalidatePath(`/patients/${patientId}`);
  return outcome;
}

// Read a document that is stored but was not imported (a refused or interrupted earlier try).
export async function importStoredDocumentAction(
  patientId: string,
  documentId: string,
): Promise<LabImportResult> {
  const t = (await getMessages()).patientPage.lab;
  if (!isUuid(patientId) || !isUuid(documentId))
    return { ok: false, stored: true, error: t.errors.invalidReference };
  const outcome = await runImport(patientId, documentId, t);
  revalidatePath(`/patients/${patientId}`);
  return outcome;
}

// Have a stored PDF read into a proposal (lab intake agent). The API runs the configured
// provider and the checks; nothing is published. The answer names the new proposal.
export type ProposeResult =
  | { ok: true; result: IntakeProposeOut }
  | { ok: false; error: string };

export async function proposeIntakeAction(
  patientId: string,
  documentId: string,
): Promise<ProposeResult> {
  const t = (await getMessages()).patientPage.lab.intake;
  if (!isUuid(patientId) || !isUuid(documentId))
    return { ok: false, error: t.errors.failed };
  try {
    const result = await proposeIntake(patientId, documentId);
    revalidatePath(`/patients/${patientId}`);
    return { ok: true, result };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.errors.notAllowed };
      if (e.status === 429) return { ok: false, error: t.errors.tooMany };
      if (e.status === 422 || e.status === 409)
        return { ok: false, error: t.errors.unreadable };
    }
    return { ok: false, error: t.errors.failed };
  }
}
