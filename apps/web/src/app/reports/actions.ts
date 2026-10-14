"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

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
import { fill } from "@/lib/i18n/fill";
import { getMessages } from "@/lib/i18n/server";
import type { Messages } from "@/lib/i18n/messages";
import { REJECTION_REASONS, type RejectionReason } from "@/lib/rejectionCopy";
import { isUuid } from "@/lib/uuid";

// Real Freigabe lifecycle (Gate G2 closed): server-side calls into the governed API.
// The API enforces role, lifecycle, and the consent gate (deny-by-default, audited);
// these actions only translate outcomes into safe copy, in the language of the interface
// (lib/i18n), and refresh the page.

export type ReportActionResult =
  | { ok: true; patientViewUrl?: string }
  | { ok: false; error: string };

type Errors = Messages["reportPage"]["errors"];

async function errors(): Promise<Errors> {
  return (await getMessages()).reportPage.errors;
}

function safeMessage(e: unknown, t: Errors): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return t.forbidden;
    // Drafting and release are throttled per user; the refusal says so and what to do.
    if (e.status === 429) return t.tooMany;
    if (e.status === 409) {
      const detail = e.message;
      if (detail.includes("consent")) return t.noConsent;
      if (detail.includes("approved before release")) return t.notApproved;
      if (detail.includes("already rejected")) return t.alreadyRejected;
      if (detail.includes("correction has replaced")) return t.citesReplaced;
      if (detail.includes("cannot approve")) return t.evidenceHidden;
      return t.wrongStatus;
    }
  }
  return t.failed;
}

function guard(reportId: string, path: string, t: Errors): string | null {
  if (!isUuid(reportId)) return t.invalidReport;
  if (!path.startsWith("/")) return t.invalidPath;
  return null;
}

// The action redirects on success, so it only ever returns a refusal.
export type GenerateReportResult = { ok: false; error: string };

// Draft generation is the entry into the Freigabe lifecycle: the API builds the
// source-grounded draft (deterministic provider, evidence-validated, audited) and the
// caller lands on the review surface. Nothing is approved or released here.
//
// The way on is a redirect from here, not a `router.push` by the caller once the action
// has answered: the revalidation below refreshes the page the caller is on, and a push
// issued after it was at times dropped by the router (the report page was rendered, the
// address never changed). A redirect is applied together with the refresh.
export async function generateReportAction(
  patientId: string,
): Promise<GenerateReportResult> {
  const t = await errors();
  if (!isUuid(patientId)) return { ok: false, error: t.invalidPatient };
  let reportId: string;
  try {
    const report = await generateReport(patientId);
    if (!isUuid(report.report_id)) return { ok: false, error: t.failed };
    reportId = report.report_id;
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.forbidden };
      if (e.status === 422) return { ok: false, error: t.noPublished };
      if (e.status === 409) return { ok: false, error: t.unsupported };
    }
    // Everything else — a throttled request among it — is worded where the other report
    // actions word it.
    return { ok: false, error: safeMessage(e, t) };
  }
  revalidatePath(`/patients/${patientId}`);
  redirect(`/patients/${patientId}/assessments/${reportId}`);
}

// Rework of a report (edit): the API re-validates the evidence binding and refuses restricted
// intended-use language; after an approved/released/rejected version it opens a NEW version
// and leaves the prior one as a preserved record. Nothing is approved here.
export async function editReportAction(
  reportId: string,
  path: string,
  statements: ReportStatementInput[],
): Promise<ReportActionResult> {
  const t = await errors();
  const invalid = guard(reportId, path, t);
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
  if (!wellFormed) return { ok: false, error: t.statementShape };
  try {
    await editReport(reportId, statements);
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      const restricted = e.message.match(/restricted language[^:]*: (.+)$/);
      if (restricted)
        return {
          ok: false,
          error: fill(t.restricted, { terms: restricted[1] ?? "" }),
        };
      if (e.message.includes("correction has replaced"))
        return { ok: false, error: t.editReplaced };
      if (e.message.includes("evidence"))
        return { ok: false, error: t.editEvidence };
    }
    return { ok: false, error: safeMessage(e, t) };
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
  const t = await errors();
  const invalid = guard(reportId, path, t);
  if (invalid) return { ok: false, error: invalid };
  try {
    await redraftReport(reportId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 422)
      return { ok: false, error: t.noPublished };
    return { ok: false, error: safeMessage(e, t) };
  }
  revalidatePath(path);
  return { ok: true };
}

export async function approveReportAction(
  reportId: string,
  path: string,
): Promise<ReportActionResult> {
  const t = await errors();
  const invalid = guard(reportId, path, t);
  if (invalid) return { ok: false, error: invalid };
  try {
    await approveReport(reportId);
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
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
  const t = await errors();
  const invalid = guard(reportId, path, t);
  if (invalid) return { ok: false, error: invalid };
  // Server-action arguments arrive from the client: only the closed vocabulary passes.
  if (!REJECTION_REASONS.some((r) => r.reason === reason))
    return { ok: false, error: t.chooseReason };
  try {
    await rejectReport(reportId, reason);
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
  revalidatePath(path);
  return { ok: true };
}

export async function releaseReportAction(
  reportId: string,
  path: string,
): Promise<ReportActionResult> {
  const t = await errors();
  const invalid = guard(reportId, path, t);
  if (invalid) return { ok: false, error: invalid };
  try {
    const released = await releaseReport(reportId);
    revalidatePath(path);
    return { ok: true, patientViewUrl: released.patient_view_url };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}
