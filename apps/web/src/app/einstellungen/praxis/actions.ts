"use server";

import { revalidatePath } from "next/cache";

import { ApiError, updateClinicProfile } from "@/lib/api";

// Saving the clinic profile (owner). The API authorizes and validates; this maps its answer to
// a code the page words in its language.
export type SaveResult =
  | { ok: true }
  | { ok: false; error: "invalid" | "forbidden" | "failed" };

export async function saveClinicProfileAction(
  name: string,
  address: string,
): Promise<SaveResult> {
  const cleanName = name.trim();
  const cleanAddress = address.trim();
  if (!cleanName || cleanName.length > 200 || cleanAddress.length > 300)
    return { ok: false, error: "invalid" };
  try {
    await updateClinicProfile({
      name: cleanName,
      address: cleanAddress || null,
    });
    revalidatePath("/", "layout");
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      return { ok: false, error: "forbidden" };
    if (e instanceof ApiError && e.status === 422)
      return { ok: false, error: "invalid" };
    return { ok: false, error: "failed" };
  }
}
