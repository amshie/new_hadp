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

// Mirrors the API boundary rules (the API remains authoritative); message strings are
// the UI language. Returns null when the draft is valid.
function validateDraft(input: PatientDraftInput): string | null {
  const name = input.display_name.trim();
  if (!name) return "Bitte einen Namen angeben.";
  if (name.length > 200) return "Der Name darf höchstens 200 Zeichen haben.";
  const dob = input.date_of_birth?.trim();
  if (dob) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dob))
      return "Bitte ein gültiges Geburtsdatum angeben.";
    if (dob > new Date().toISOString().slice(0, 10))
      return "Das Geburtsdatum darf nicht in der Zukunft liegen.";
    if (Number(dob.slice(0, 4)) < MIN_BIRTH_YEAR)
      return `Bitte ein Geburtsdatum ab ${MIN_BIRTH_YEAR} angeben.`;
  }
  if ((input.external_ref?.trim().length ?? 0) > 120)
    return "Die externe ID darf höchstens 120 Zeichen haben.";
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
  const invalid = validateDraft(input);
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
        return { ok: false, error: "Nicht berechtigt. Bitte erneut anmelden." };
      if (e.code === "duplicate_patient")
        return {
          ok: false,
          code: "duplicate_patient",
          error:
            "Im Mandanten existiert bereits ein Eintrag mit diesen Angaben.",
        };
      return {
        ok: false,
        error: "Anlegen fehlgeschlagen. Bitte Eingaben prüfen.",
      };
    }
    return {
      ok: false,
      error: "Anlegen fehlgeschlagen. Bitte erneut versuchen.",
    };
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
  const invalid = validateDraft(input);
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
      return { ok: false, error: "Nicht berechtigt. Bitte erneut anmelden." };
    return { ok: false, error: "Duplikatprüfung derzeit nicht verfügbar." };
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
  if (!isUuid(patientId))
    return { ok: false, error: "Ungültige Patientenreferenz." };
  if (!DELETION_REASONS.has(reason))
    return { ok: false, error: "Ungültiger Grund." };
  try {
    await createDeletionRequest(patientId, reason);
    revalidatePath("/einstellungen/loeschantraege");
    revalidatePath(`/patients/${patientId}`);
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403)
        return {
          ok: false,
          error: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
        };
      if (e.status === 409)
        return {
          ok: false,
          error:
            "Für diesen Patienten besteht bereits ein offener Löschantrag.",
        };
    }
    return {
      ok: false,
      error: "Löschantrag fehlgeschlagen. Bitte erneut versuchen.",
    };
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
  if (!isUuid(patientId))
    return { ok: false, error: "Ungültige Patientenreferenz." };
  try {
    const invitation = await createInvitation(patientId);
    return {
      ok: true,
      url: invitation.invitation_url,
      expiresAt: invitation.expires_at,
    };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403)
        return {
          ok: false,
          error: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
        };
      if (e.status === 429)
        return {
          ok: false,
          error: "Zu viele Einladungen. Bitte später erneut.",
        };
    }
    return {
      ok: false,
      error: "Einladung fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
}
