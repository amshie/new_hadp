"use server";

import { revalidatePath } from "next/cache";

import { endOtherSessions } from "@/lib/api";

// Ending every other session of the signed-in account. The API acts on the caller's own
// account only and records it; this returns how many ended, or that it failed.
export async function endOtherSessionsAction(): Promise<
  { ok: true; ended: number } | { ok: false }
> {
  try {
    const { ended } = await endOtherSessions();
    revalidatePath("/einstellungen/sicherheit");
    return { ok: true, ended };
  } catch {
    return { ok: false };
  }
}
