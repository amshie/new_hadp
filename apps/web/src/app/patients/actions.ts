"use server";

import { revalidatePath } from "next/cache";

import { ApiError, createPatient } from "@/lib/api";

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
