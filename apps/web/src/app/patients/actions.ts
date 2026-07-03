"use server";

import { revalidatePath } from "next/cache";

import { ApiError, createInvitation, createPatient } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

export type AddPatientResult =
  | { ok: true; id: string }
  | { ok: false; error: string };

// Server-side bridge for the "+ Patient hinzufügen" dialog. The session cookie is httpOnly on the
// app origin, so creation must run server-side (deny-by-default; the API enforces auth + tenant).
// The API forces is_synthetic=True — created patients are always synthetic demo records. On
// success we revalidate the screens whose counts/lists change.
export async function addPatient(input: {
  display_name: string;
  external_ref?: string | null;
  date_of_birth?: string | null;
}): Promise<AddPatientResult> {
  const name = input.display_name.trim();
  if (!name) return { ok: false, error: "Bitte einen Namen angeben." };
  try {
    const patient = await createPatient({
      display_name: name,
      external_ref: input.external_ref?.trim() || null,
      date_of_birth: input.date_of_birth?.trim() || null,
    });
    revalidatePath("/overview");
    revalidatePath("/patients");
    return { ok: true, id: patient.id };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403)
        return { ok: false, error: "Nicht berechtigt. Bitte erneut anmelden." };
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
