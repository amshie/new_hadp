"use server";

import { revalidatePath } from "next/cache";

import { ApiError, resolveReviewItem } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

// Review-queue resolution (Phase 1C): an attributable human decision per item. The API
// enforces the clinician-only role, tenant scope, and the publish/reject semantics
// (REJECT is immediate and fail-closed; PUBLISH takes effect with the last open item).
// What it answers is in the language of the interface (lib/i18n).

export type ResolveResult =
  | { ok: true; observationStatus: string }
  | { ok: false; error: string };

export async function resolveReviewItemAction(
  reviewItemId: string,
  decision: "publish" | "reject",
  path: string,
): Promise<ResolveResult> {
  const t = (await getMessages()).reviewQueue.errors;
  if (!isUuid(reviewItemId)) return { ok: false, error: t.invalidReference };
  if (!path.startsWith("/")) return { ok: false, error: t.invalidPath };
  try {
    const res = await resolveReviewItem(reviewItemId, decision);
    revalidatePath(path);
    return { ok: true, observationStatus: res.observation_review_status };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.forbidden };
      if (e.status === 409 && e.message.startsWith("supersession_conflict"))
        return { ok: false, error: t.supersessionConflict };
      if (e.status === 409) return { ok: false, error: t.conflict };
    }
    return { ok: false, error: t.failed };
  }
}
