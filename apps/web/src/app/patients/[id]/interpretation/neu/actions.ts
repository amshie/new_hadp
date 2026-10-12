"use server";

import { revalidatePath } from "next/cache";

import { ApiError, authorInterpretation, type RunAuthorIn } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Authoring bridge (Phase 1C): submits the WHOLE clinician-authored run. The API is
// the authority — closed vocabularies at the boundary (422), run shape + fail-closed
// evidence resolution at the service (409), clinician-only role, required authorship.

export type AuthorRunResult = { ok: true } | { ok: false; error: string };

export async function authorRunAction(
  patientId: string,
  body: RunAuthorIn,
  path: string,
): Promise<AuthorRunResult> {
  if (!isUuid(patientId))
    return { ok: false, error: "Ungültige Patientenreferenz." };
  if (!path.startsWith("/")) return { ok: false, error: "Ungültiger Pfad." };
  try {
    await authorInterpretation(patientId, body);
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
            "Eingaben unvollständig oder außerhalb der geschlossenen Vokabulare.",
        };
      if (e.status === 409) {
        if (e.message.includes("correction has replaced"))
          return {
            ok: false,
            error:
              "Ein gewählter Beleg wurde inzwischen vom Labor korrigiert. Bitte die Seite neu laden und die Belege erneut wählen.",
          };
        if (e.message.includes("evidence"))
          return {
            ok: false,
            error:
              "Belege nicht auflösbar: jeder Beleg muss eine veröffentlichte Beobachtung dieser Patientin sein.",
          };
        return {
          ok: false,
          error: "Run-Struktur unvollständig (6 Domänen × 3 Zellen).",
        };
      }
    }
    return {
      ok: false,
      error: "Erfassen fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
  revalidatePath(path);
  return { ok: true };
}
