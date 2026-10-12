"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  importDocument,
  uploadDocument,
  type DocumentImportResult,
} from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Laboratory file intake from the patient page: the original file is stored first (API:
// content inspection, checksum, idempotent re-upload), then read by a structured reader into
// the import pipeline. The API enforces role, tenant, the one-patient rule and exactly-once;
// these actions only pass the file on and translate outcomes into safe German copy. Error
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

const REFUSALS: Record<string, string> = {
  unsupported_format:
    "Für dieses Dateiformat gibt es kein Einleseprogramm (unterstützt: CSV im HADP-Layout, LDT 2, LDT 3).",
  multiple_patients:
    "Die Datei enthält Befunde für mehr als eine Person. Eine Datei muss genau eine Person betreffen.",
  unidentified_patient:
    "Die Datei nennt nicht genau eine Person. Eine Datei muss genau eine Person betreffen.",
  patient_mismatch: "Die Datei nennt ein anderes Geburtsdatum als diese Akte.",
  checksum_mismatch:
    "Die Prüfsumme der LDT-Datei stimmt nicht — die Datei ist beschädigt oder unvollständig.",
  malformed_record: "Die LDT-Datei ist unvollständig oder nicht formatgerecht.",
  malformed_object: "Die LDT-Datei ist unvollständig oder nicht formatgerecht.",
  unsupported_ldt_version: "Diese LDT-Version wird nicht gelesen.",
  unsupported_record_type:
    "Die LDT-Datei enthält eine Satzart, die nicht gelesen wird (nur Laborbefunde).",
  unsupported_report_kind:
    "Die LDT-Datei enthält eine Satzart, die nicht gelesen wird (nur Laborbefunde).",
  unsupported_layout:
    "Der Tabellenkopf enthält nicht die erwarteten Spalten (Analyt, Wert, Abnahmedatum).",
  ambiguous_header: "Der Tabellenkopf nennt eine Spalte doppelt.",
  malformed_table:
    "Eine Zeile hat nicht so viele Felder wie der Tabellenkopf (häufig: Dezimalkomma in einer kommagetrennten Datei).",
  missing_field: "In einer Zeile fehlt Analyt, Wert oder Datum.",
  unsupported_date:
    "Ein Datum ist nicht eindeutig lesbar (erwartet: TT.MM.JJJJ oder JJJJ-MM-TT).",
  implausible_date: "Ein Datum liegt außerhalb der plausiblen Spanne.",
  unsupported_time: "Eine Uhrzeit ist nicht lesbar (erwartet: HH:MM).",
  empty_document: "Die Datei enthält keine Laborwerte.",
  too_many_values:
    "Die Datei enthält mehr Werte, als ein einzelner Befund hat.",
  document_unavailable:
    "Die gespeicherte Originaldatei ist nicht lesbar. Bitte erneut hochladen.",
};

// The API detail is "<code>: <position and field names>" — never file content. The code picks
// the German text; a line number, if the detail names one, is passed on.
function refusalMessage(detail: string): string {
  const code = detail.split(":", 1)[0]?.trim() ?? "";
  const line = detail.match(/\bline (\d+)\b/)?.[1];
  const where = line ? ` (Zeile ${line})` : "";
  const known = REFUSALS[code];
  if (known) return `${known}${where} Es wurde nichts übernommen.`;
  return /^[a-z_]+$/.test(code)
    ? `Die Datei konnte nicht eingelesen werden (Grund: ${code})${where}. Es wurde nichts übernommen.`
    : "Die Datei konnte nicht eingelesen werden. Es wurde nichts übernommen.";
}

function uploadMessage(e: ApiError): string {
  if (e.status === 403) return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
  if (e.status === 404) return "Diese Akte ist nicht verfügbar.";
  if (e.status === 429)
    return "Zu viele Uploads in kurzer Zeit. Bitte kurz warten.";
  if (e.status === 409 && e.message.startsWith("document_other_patient"))
    return "Diese Datei ist bereits bei einer anderen Akte dieser Klinik gespeichert und wird hier nicht noch einmal angenommen.";
  if (e.status === 422) {
    if (e.message.includes("empty")) return "Die Datei ist leer.";
    if (e.message.includes("too large")) return "Die Datei ist zu groß.";
    if (e.message.includes("UTF-8"))
      return "Die Datei ist keine lesbare Textdatei (UTF-8 erwartet).";
    return "Dieser Dateityp wird nicht angenommen (CSV, LDT oder Text).";
  }
  return "Upload fehlgeschlagen. Bitte erneut versuchen.";
}

async function runImport(
  patientId: string,
  documentId: string,
): Promise<LabImportResult> {
  try {
    const result = await importDocument(patientId, documentId);
    return { ok: true, result };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403)
        return {
          ok: false,
          stored: true,
          error: "Das Einlesen ist Ihrer Rolle nicht erlaubt.",
        };
      if (e.status === 429)
        return {
          ok: false,
          stored: true,
          error: "Zu viele Importe in kurzer Zeit. Bitte kurz warten.",
        };
      if (e.status === 422 || e.status === 409)
        return { ok: false, stored: true, error: refusalMessage(e.message) };
    }
    return {
      ok: false,
      stored: true,
      error: "Einlesen fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
}

export async function uploadLabFileAction(
  patientId: string,
  form: FormData,
): Promise<LabImportResult> {
  if (!isUuid(patientId))
    return { ok: false, stored: false, error: "Ungültige Patientenreferenz." };
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0)
    return { ok: false, stored: false, error: "Bitte eine Datei wählen." };
  if (file.size > MAX_BYTES)
    return {
      ok: false,
      stored: false,
      error: "Die Datei ist zu groß (höchstens 5 MB).",
    };
  // The stored file name is bounded (255 characters); refuse here rather than fail there.
  if (file.name.length > 200)
    return {
      ok: false,
      stored: false,
      error: "Der Dateiname ist zu lang (höchstens 200 Zeichen).",
    };
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
        e instanceof ApiError
          ? uploadMessage(e)
          : "Upload fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
  const outcome = await runImport(patientId, documentId);
  // The file is stored either way: the list of documents has changed.
  revalidatePath(`/patients/${patientId}`);
  return outcome;
}

// Read a document that is stored but was not imported (a refused or interrupted earlier try).
export async function importStoredDocumentAction(
  patientId: string,
  documentId: string,
): Promise<LabImportResult> {
  if (!isUuid(patientId) || !isUuid(documentId))
    return { ok: false, stored: true, error: "Ungültige Referenz." };
  const outcome = await runImport(patientId, documentId);
  revalidatePath(`/patients/${patientId}`);
  return outcome;
}
