"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  changeMemberRole,
  createStaffInvitation,
  removeMember,
  revokeStaffInvitation,
  type StaffRole,
} from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Owner-side staff administration. Server-side authorization is the real control (the API
// gates STAFF_INVITE_CREATE to owners and rejects everything else with 403); these actions
// map failures to German copy and refresh the list. The one-time invite URL is returned to
// the caller exactly once.

const ROLES = new Set(["owner", "clinician", "assistant", "medical_director"]);

export type CreateResult =
  | { ok: true; url: string; role: string }
  | { ok: false; error: string };

export async function createStaffInviteAction(
  role: string,
): Promise<CreateResult> {
  if (!ROLES.has(role)) return { ok: false, error: "Ungültige Rolle." };
  try {
    const inv = await createStaffInvitation(role as StaffRole);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true, url: inv.invitation_url, role: inv.role };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export type RevokeResult = { ok: true } | { ok: false; error: string };

export async function revokeStaffInviteAction(
  invitationId: string,
): Promise<RevokeResult> {
  if (!isUuid(invitationId))
    return { ok: false, error: "Ungültige Einladung." };
  try {
    await revokeStaffInvitation(invitationId);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export type MemberActionResult = { ok: true } | { ok: false; error: string };

export async function changeMemberRoleAction(
  membershipId: string,
  role: string,
): Promise<MemberActionResult> {
  if (!isUuid(membershipId) || !ROLES.has(role))
    return { ok: false, error: "Ungültige Eingabe." };
  try {
    await changeMemberRole(membershipId, role as StaffRole);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export async function removeMemberAction(
  membershipId: string,
): Promise<MemberActionResult> {
  if (!isUuid(membershipId)) return { ok: false, error: "Ungültige Eingabe." };
  try {
    await removeMember(membershipId);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

function safeMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403)
      return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
    if (e.status === 409) {
      if (e.message.includes("own membership"))
        return "Die eigene Mitgliedschaft kann nicht geändert werden.";
      if (e.message.includes("at least one owner"))
        return "Die Klinik benötigt mindestens einen Inhaber.";
      return "Diese Einladung ist nicht mehr ausstehend.";
    }
    if (e.status === 429)
      return "Zu viele Anfragen. Bitte später erneut versuchen.";
  }
  return "Die Aktion konnte nicht ausgeführt werden. Bitte erneut versuchen.";
}
