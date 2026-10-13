"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  checkDuplicates,
  createDeletionRequest,
  createInvitation,
  createPatient,
  type CreatePatientInput,
  type DeletionReason,
} from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

// Server-side bridge for the onboarding wizard. The session cookie is httpOnly on the
// app origin, so creation must run server-side (deny-by-default; the API enforces auth,
// tenant scope, the duplicate guard, and date plausibility). The API forces
// is_synthetic=True — created patients are always synthetic demo records.

const MIN_BIRTH_YEAR = 1900;

export type PatientDraftInput = {
  display_name: string;
  external_ref?: string | null;
  date_of_birth?: string | null;
};

export type OnboardingConsent = NonNullable<
  CreatePatientInput["consents"]
>[number];

// Mirrors the API boundary rules (the API remains authoritative); the messages are in the
// language of the interface (lib/i18n). Returns null when the draft is valid.
function validateDraft(
  input: PatientDraftInput,
  t: Messages["addPatient"]["errors"],
): string | null {
  const name = input.display_name.trim();
  if (!name) return t.nameRequired;
  if (name.length > 200) return t.nameTooLong;
  const dob = input.date_of_birth?.trim();
  if (dob) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dob)) return t.dobInvalid;
    if (dob > new Date().toISOString().slice(0, 10)) return t.dobFuture;
    if (Number(dob.slice(0, 4)) < MIN_BIRTH_YEAR)
      return fill(t.dobTooEarly, { year: MIN_BIRTH_YEAR });
  }
  if ((input.external_ref?.trim().length ?? 0) > 120) return t.refTooLong;
  return null;
}

export type AddPatientResult =
  | { ok: true; id: string }
  | { ok: false; error: string; code?: "duplicate_patient" };

export async function addPatient(
  input: PatientDraftInput & {
    consents?: OnboardingConsent[];
    allow_duplicate?: boolean;
  },
): Promise<AddPatientResult> {
  const t = (await getMessages()).addPatient.errors;
  const invalid = validateDraft(input, t);
  if (invalid) return { ok: false, error: invalid };
  try {
    const patient = await createPatient({
      display_name: input.display_name.trim(),
      external_ref: input.external_ref?.trim() || null,
      date_of_birth: input.date_of_birth?.trim() || null,
      consents: input.consents ?? [],
      allow_duplicate: input.allow_duplicate ?? false,
    });
    revalidatePath("/overview");
    revalidatePath("/patients");
    return { ok: true, id: patient.id };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403)
        return { ok: false, error: t.signInAgain };
      if (e.code === "duplicate_patient")
        return { ok: false, code: "duplicate_patient", error: t.duplicate };
      return { ok: false, error: t.checkInput };
    }
    return { ok: false, error: t.failed };
  }
}

export type DuplicateCandidateView = {
  id: string;
  displayName: string;
  externalRef: string | null;
  dateOfBirth: string | null;
  matchBasis: "external_ref" | "name_dob" | "name";
};

export type DuplicateCheckResult =
  | {
      ok: true;
      candidates: DuplicateCandidateView[];
      hasStrongMatch: boolean;
    }
  | { ok: false; error: string };

// Pre-create duplicate probe, tenant-scoped by the API (explicit filter + RLS): a twin
// in another tenant is invisible by construction. The probe is a UX aid — the API's
// duplicate guard on create is the enforcing boundary either way.
export async function checkPatientDuplicates(
  input: PatientDraftInput,
): Promise<DuplicateCheckResult> {
  const t = (await getMessages()).addPatient;
  const invalid = validateDraft(input, t.errors);
  if (invalid) return { ok: false, error: invalid };
  try {
    const res = await checkDuplicates({
      display_name: input.display_name.trim(),
      date_of_birth: input.date_of_birth?.trim() || null,
      external_ref: input.external_ref?.trim() || null,
    });
    return {
      ok: true,
      hasStrongMatch: res.has_strong_match,
      candidates: res.candidates.map((c) => ({
        id: c.id,
        displayName: c.display_name,
        externalRef: c.external_ref ?? null,
        dateOfBirth: c.date_of_birth ?? null,
        matchBasis: c.match_basis,
      })),
    };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      return { ok: false, error: t.errors.signInAgain };
    return { ok: false, error: t.duplicates.unavailable };
  }
}

const DELETION_REASONS = new Set<DeletionReason>([
  "patient_request",
  "withdrawn_consent",
  "data_minimization",
]);

export type RequestDeletionResult = { ok: true } | { ok: false; error: string };

// Owner-only: open a patient-erasure request (the medical director then decides it on the
// Löschanträge queue). Server-side authorization is the control — the API gates
// PRIVACY_REQUEST_CREATE to owners. No data is deleted here; this only files the request.
export async function requestPatientDeletion(
  patientId: string,
  reason: DeletionReason,
): Promise<RequestDeletionResult> {
  const t = (await getMessages()).patientPage;
  if (!isUuid(patientId)) return { ok: false, error: t.invalidPatient };
  if (!DELETION_REASONS.has(reason))
    return { ok: false, error: t.deletion.errors.invalidReason };
  try {
    await createDeletionRequest(patientId, reason);
    revalidatePath("/einstellungen/loeschantraege");
    revalidatePath(`/patients/${patientId}`);
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403)
        return { ok: false, error: t.notAllowed };
      if (e.status === 409)
        return { ok: false, error: t.deletion.errors.alreadyOpen };
    }
    return { ok: false, error: t.deletion.errors.failed };
  }
}

export type InviteResult =
  | { ok: true; url: string; expiresAt: string }
  | { ok: false; error: string };

// Mints a single-use synthetic invitation (P1/P3, docs/notes/0010). The one-time URL
// is shown exactly once in the dialog for MANUAL, secure out-of-band sharing — no
// automatic delivery exists in the Alpha. The API stores only the token hash.
export async function createInvitationAction(
  patientId: string,
): Promise<InviteResult> {
  const t = (await getMessages()).addPatient.invitationErrors;
  if (!isUuid(patientId)) return { ok: false, error: t.invalidPatient };
  try {
    const invitation = await createInvitation(patientId);
    return {
      ok: true,
      url: invitation.invitation_url,
      expiresAt: invitation.expires_at,
    };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.notAllowed };
      if (e.status === 429) return { ok: false, error: t.tooMany };
    }
    return { ok: false, error: t.failed };
  }
}
