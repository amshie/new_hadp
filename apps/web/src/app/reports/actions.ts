"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  approveReport,
  editReport,
  redraftReport,
  generateReport,
  rejectReport,
  releaseReport,
  type ReportStatementInput,
} from "@/lib/api";
import { REJECTION_REASONS, type RejectionReason } from "@/lib/rejectionCopy";
import { isUuid } from "@/lib/uuid";

// Real Freigabe lifecycle (Gate G2 closed): server-side calls into the governed API.
// The API enforces role, lifecycle, and the consent gate (deny-by-default, audited);
// these actions only translate outcomes into safe German copy and refresh the page.

export type ReportActionResult =
  | { ok: true; patientViewUrl?: string }
  | { ok: false; error: string };

function safeMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
    if (e.status === 409) {
      const detail = e.message;
      if (detail.includes("consent")) {
        return "Keine aktive Einwilligung (report_release) für diese Patientin hinterlegt.";
      }
      if (detail.includes("approved before release")) {
        return "Der Bericht ist noch nicht genehmigt.";
      }
      if (detail.includes("already rejected")) {
        return "Der Bericht wurde bereits zurückgewiesen.";
      }
      if (detail.includes("correction has replaced")) {
        return "Nicht möglich: Ein zitierter Wert wurde vom Labor korrigiert. Bitte einen neuen Entwurf aus den aktuellen Werten erstellen.";
      }
      if (detail.includes("cannot approve")) {
        return "Genehmigung nicht möglich: nicht jeder Beleg ist einsehbar.";
      }
      return "Aktion im aktuellen Berichtsstatus nicht möglich.";
    }
  }
  return "Aktion fehlgeschlagen. Bitte erneut versuchen.";
}

function guard(reportId: string, path: string): string | null {
  if (!isUuid(reportId)) return "Ungültige Berichtsreferenz.";
  if (!path.startsWith("/")) return "Ungültiger Pfad.";
  return null;
}

export type GenerateReportResult =
  | { ok: true; reviewUrl: string }
  | { ok: false; error: string };

// Draft generation is the entry into the Freigabe lifecycle: the API builds the
// source-grounded draft (deterministic provider, evidence-validated, audited) and the
// caller lands on the review surface. Nothing is approved or released here.
export async function generateReportAction(
  patientId: string,
): Promise<GenerateReportResult> {
  if (!isUuid(patientId))
    return { ok: false, error: "Ungültige Patientenreferenz." };
  try {
    const report = await generateReport(patientId);
    if (!isUuid(report.report_id))
      return {
        ok: false,
        error: "Aktion fehlgeschlagen. Bitte erneut versuchen.",
      };
    revalidatePath(`/patients/${patientId}`);
    return {
      ok: true,
      reviewUrl: `/patients/${patientId}/assessments/${report.report_id}`,
    };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403)
        return {
          ok: false,
          error: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
        };
      if (e.status === 422)
        return {
          ok: false,
          error:
            "Kein Entwurf möglich: Es liegen keine veröffentlichten Beobachtungen vor.",
        };
      if (e.status === 409)
        return {
          ok: false,
          error:
            "Kein Entwurf möglich: Nicht jede Aussage ließ sich mit einer Quelle belegen.",
        };
    }
    return {
      ok: false,
      error: "Aktion fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
}

// Rework of a report (edit): the API re-validates the evidence binding and refuses restricted
// intended-use language; after an approved/released/rejected version it opens a NEW version
// and leaves the prior one as a preserved record. Nothing is approved here.
export async function editReportAction(
  reportId: string,
  path: string,
  statements: ReportStatementInput[],
): Promise<ReportActionResult> {
  const invalid = guard(reportId, path);
  if (invalid) return { ok: false, error: invalid };
  // Server-action arguments arrive from the client: check the shape before using it.
  const wellFormed =
    Array.isArray(statements) &&
    statements.length > 0 &&
    statements.every(
      (s) =>
        typeof s?.id === "string" &&
        s.id.length > 0 &&
        typeof s.text === "string" &&
        s.text.trim().length > 0 &&
        Array.isArray(s.evidence_observation_ids) &&
        s.evidence_observation_ids.length > 0 &&
        s.evidence_observation_ids.every(isUuid),
    );
  if (!wellFormed)
    return {
      ok: false,
      error: "Jede Aussage braucht einen Text und mindestens einen Beleg.",
    };
  try {
    await editReport(reportId, statements);
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      const restricted = e.message.match(/restricted language[^:]*: (.+)$/);
      if (restricted)
        return {
          ok: false,
          error: `Nicht gespeichert: Der Text enthält für Berichte nicht zulässige Begriffe (${restricted[1]}).`,
        };
      if (e.message.includes("correction has replaced"))
        return {
          ok: false,
          error:
            "Nicht gespeichert: Ein zitierter Wert wurde vom Labor korrigiert. Bitte die betroffene Aussage entfernen oder einen neuen Entwurf erstellen.",
        };
      if (e.message.includes("evidence"))
        return {
          ok: false,
          error:
            "Nicht gespeichert: Nicht jeder Beleg ist einsehbar. Bitte die betroffene Aussage entfernen.",
        };
    }
    return { ok: false, error: safeMessage(e) };
  }
  revalidatePath(path);
  return { ok: true };
}

// A new draft version from the values that stand — the way on once a laboratory correction
// has replaced a cited value. For a released report this withdraws patient access until the
// new version is approved and released again (the API revokes the link).
export async function redraftReportAction(
  reportId: string,
  path: string,
): Promise<ReportActionResult> {
  const invalid = guard(reportId, path);
  if (invalid) return { ok: false, error: invalid };
  try {
    await redraftReport(reportId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 422)
      return {
        ok: false,
        error:
          "Kein Entwurf möglich: Es liegen keine veröffentlichten Beobachtungen vor.",
      };
    return { ok: false, error: safeMessage(e) };
  }
  revalidatePath(path);
  return { ok: true };
}

export async function approveReportAction(
  reportId: string,
  path: string,
): Promise<ReportActionResult> {
  const invalid = guard(reportId, path);
  if (invalid) return { ok: false, error: invalid };
  try {
    await approveReport(reportId);
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
  revalidatePath(path);
  return { ok: true };
}

// A rejection names its reason from the closed vocabulary — never free text, so nothing about
// the patient can end up in the record or the audit trail through this field.
export async function rejectReportAction(
  reportId: string,
  path: string,
  reason: RejectionReason,
): Promise<ReportActionResult> {
  const invalid = guard(reportId, path);
  if (invalid) return { ok: false, error: invalid };
  // Server-action arguments arrive from the client: only the closed vocabulary passes.
  if (!REJECTION_REASONS.some((r) => r.reason === reason))
    return { ok: false, error: "Bitte einen Grund wählen." };
  try {
    await rejectReport(reportId, reason);
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
  revalidatePath(path);
  return { ok: true };
}

export async function releaseReportAction(
  reportId: string,
  path: string,
): Promise<ReportActionResult> {
  const invalid = guard(reportId, path);
  if (invalid) return { ok: false, error: invalid };
  try {
    const released = await releaseReport(reportId);
    revalidatePath(path);
    return { ok: true, patientViewUrl: released.patient_view_url };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}
