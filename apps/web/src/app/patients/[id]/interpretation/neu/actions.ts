"use server";

import { revalidatePath } from "next/cache";

import { ApiError, authorInterpretation, type RunAuthorIn } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

// Authoring bridge (Phase 1C): submits the WHOLE clinician-authored run. The API is
// the authority — closed vocabularies at the boundary (422), run shape + fail-closed
// evidence resolution at the service (409), clinician-only role, required authorship.
// What it answers is in the language of the interface (lib/i18n).

export type AuthorRunResult = { ok: true } | { ok: false; error: string };

export async function authorRunAction(
  patientId: string,
  body: RunAuthorIn,
  path: string,
): Promise<AuthorRunResult> {
  const t = (await getMessages()).interpretation.errors;
  if (!isUuid(patientId)) return { ok: false, error: t.invalidPatient };
  if (!path.startsWith("/")) return { ok: false, error: t.invalidPath };
  try {
    await authorInterpretation(patientId, body);
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.forbidden };
      if (e.status === 422) return { ok: false, error: t.vocabulary };
      if (e.status === 409) {
        if (e.message.includes("correction has replaced"))
          return { ok: false, error: t.evidenceReplaced };
        if (e.message.includes("evidence"))
          return { ok: false, error: t.evidenceUnresolved };
        return { ok: false, error: t.shape };
      }
    }
    return { ok: false, error: t.failed };
  }
  revalidatePath(path);
  return { ok: true };
}
