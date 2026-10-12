"use server";

import { revalidatePath } from "next/cache";

import { ApiError, resolveReviewItem } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Review-queue resolution (Phase 1C): an attributable human decision per item. The API
// enforces the clinician-only role, tenant scope, and the publish/reject semantics
// (REJECT is immediate and fail-closed; PUBLISH takes effect with the last open item).

export type ResolveResult =
  | { ok: true; observationStatus: string }
  | { ok: false; error: string };

export async function resolveReviewItemAction(
  reviewItemId: string,
  decision: "publish" | "reject",
  path: string,
): Promise<ResolveResult> {
  if (!isUuid(reviewItemId)) return { ok: false, error: "Ungültige Referenz." };
  if (!path.startsWith("/")) return { ok: false, error: "Ungültiger Pfad." };
  try {
    const res = await resolveReviewItem(reviewItemId, decision);
    revalidatePath(path);
    return { ok: true, observationStatus: res.observation_review_status };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403)
        return {
          ok: false,
          error: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
        };
      if (e.status === 409 && e.message.startsWith("supersession_conflict"))
        return {
          ok: false,
          error:
            "Der Wert, den diese Korrektur ersetzen soll, wurde bereits durch eine andere Korrektur ersetzt. Dieser Wert kann nur abgelehnt werden.",
        };
      if (e.status === 409)
        return {
          ok: false,
          error:
            "Bereits entschieden oder nicht mehr offen — Ansicht wird aktualisiert.",
        };
    }
    return {
      ok: false,
      error: "Aktion fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
}
