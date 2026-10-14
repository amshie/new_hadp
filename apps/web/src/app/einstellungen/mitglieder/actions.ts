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
import { getMessages } from "@/lib/i18n/server";
import type { Messages } from "@/lib/i18n/messages";
import { isUuid } from "@/lib/uuid";

// Owner-side staff administration. Server-side authorization is the real control (the API
// gates STAFF_INVITE_CREATE to owners and rejects everything else with 403); these actions
// map failures to copy in the language of the interface (lib/i18n) and refresh the list. The one-time invite URL is returned to
// the caller exactly once.

const ROLES = new Set(["owner", "clinician", "assistant", "medical_director"]);

type Errors = Messages["membersPage"]["errors"];

async function errors(): Promise<Errors> {
  return (await getMessages()).membersPage.errors;
}

export type CreateResult =
  | { ok: true; url: string; role: string }
  | { ok: false; error: string };

export async function createStaffInviteAction(
  role: string,
  label?: string,
): Promise<CreateResult> {
  const t = await errors();
  if (!ROLES.has(role)) return { ok: false, error: t.invalidRole };
  const note = (label ?? "").trim();
  if (note.length > 200) return { ok: false, error: t.invalidInput };
  try {
    const inv = await createStaffInvitation(
      role as StaffRole,
      note || undefined,
    );
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true, url: inv.invitation_url, role: inv.role };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}

export type RevokeResult = { ok: true } | { ok: false; error: string };

export async function revokeStaffInviteAction(
  invitationId: string,
): Promise<RevokeResult> {
  const t = await errors();
  if (!isUuid(invitationId)) return { ok: false, error: t.invalidInvitation };
  try {
    await revokeStaffInvitation(invitationId);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}

export type MemberActionResult = { ok: true } | { ok: false; error: string };

export async function changeMemberRoleAction(
  membershipId: string,
  role: string,
): Promise<MemberActionResult> {
  const t = await errors();
  if (!isUuid(membershipId) || !ROLES.has(role))
    return { ok: false, error: t.invalidInput };
  try {
    await changeMemberRole(membershipId, role as StaffRole);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}

export async function removeMemberAction(
  membershipId: string,
): Promise<MemberActionResult> {
  const t = await errors();
  if (!isUuid(membershipId)) return { ok: false, error: t.invalidInput };
  try {
    await removeMember(membershipId);
    revalidatePath("/einstellungen/mitglieder");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}

function safeMessage(e: unknown, t: Errors): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403) return t.forbidden;
    if (e.status === 409) {
      if (e.message.includes("own membership")) return t.ownMembership;
      if (e.message.includes("at least one owner")) return t.lastOwner;
      return t.notPending;
    }
    if (e.status === 429) return t.tooMany;
  }
  return t.failed;
}
