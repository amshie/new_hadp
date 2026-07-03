"use server";

import { ApiError, redeemStaffInvitation } from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Colleague-side onboarding: redeems the single-use staff invitation, which creates the
// user + membership server-side (with the role the owner fixed). Every non-redeemable state
// is the same neutral message (no oracle); a taken e-mail gets its own message.

export type RedeemResult = { ok: true } | { ok: false; error: string };

const NEUTRAL_INVALID =
  "Dieser Einladungslink ist nicht oder nicht mehr gültig. Bitte wenden Sie sich an Ihre Klinik.";

export async function redeemStaffInvitationAction(input: {
  tenant: string;
  token: string;
  display_name: string;
  email: string;
}): Promise<RedeemResult> {
  if (
    !isUuid(input.tenant) ||
    !input.token ||
    !input.display_name ||
    !input.email
  )
    return { ok: false, error: NEUTRAL_INVALID };
  try {
    await redeemStaffInvitation(input);
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError) {
      // A taken email (and every other non-redeemable state) is a neutral 404 by design.
      if (e.status === 404) return { ok: false, error: NEUTRAL_INVALID };
      if (e.status === 422)
        return {
          ok: false,
          error:
            "Bitte geben Sie einen Namen und eine gültige E-Mail-Adresse ein.",
        };
      if (e.status === 429)
        return {
          ok: false,
          error: "Zu viele Versuche. Bitte versuchen Sie es später erneut.",
        };
    }
    return {
      ok: false,
      error:
        "Der Zugang konnte nicht eingerichtet werden. Bitte erneut versuchen.",
    };
  }
}
