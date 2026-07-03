"use server";

import { ApiError, redeemInvitation } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Patient-side consent capture (P2, docs/notes/0010 §5): redeems the single-use
// invitation, which appends the GRANTED report_release consent event server-side.
// Every non-redeemable state is the same neutral message (no oracle).

export type RedeemResult = { ok: true } | { ok: false; error: string };

const NEUTRAL_INVALID =
  "Dieser Einladungslink ist nicht oder nicht mehr gültig. Bitte wenden Sie sich an Ihre Klinik.";

export async function redeemInvitationAction(
  tenant: string,
  token: string,
): Promise<RedeemResult> {
  if (!isUuid(tenant) || !token) return { ok: false, error: NEUTRAL_INVALID };
  try {
    await redeemInvitation(tenant, token);
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 404) return { ok: false, error: NEUTRAL_INVALID };
      if (e.status === 429)
        return {
          ok: false,
          error: "Zu viele Versuche. Bitte versuchen Sie es später erneut.",
        };
    }
    return {
      ok: false,
      error:
        "Die Einwilligung konnte nicht erfasst werden. Bitte erneut versuchen.",
    };
  }
}
