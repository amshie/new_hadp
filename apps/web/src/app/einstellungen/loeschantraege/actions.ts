"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  approveDeletionRequest,
  cancelDeletionRequest,
  rejectDeletionRequest,
} from "@/lib/api";
import { isUuid } from "@/lib/uuid";

// Erasure-request decisions. Server-side authorization is the real control (the API gates
// decide to the medical director and cancel to the owner-requester); these actions map
// failures to German copy and refresh the queue.

export type DecisionResult = { ok: true } | { ok: false; error: string };

async function run(
  requestId: string,
  fn: (id: string) => Promise<unknown>,
): Promise<DecisionResult> {
  if (!isUuid(requestId)) return { ok: false, error: "Ungültige Anfrage." };
  try {
    await fn(requestId);
    revalidatePath("/einstellungen/loeschantraege");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export async function approveDeletionAction(
  id: string,
): Promise<DecisionResult> {
  return run(id, approveDeletionRequest);
}
export async function rejectDeletionAction(
  id: string,
): Promise<DecisionResult> {
  return run(id, rejectDeletionRequest);
}
export async function cancelDeletionAction(
  id: string,
): Promise<DecisionResult> {
  return run(id, cancelDeletionRequest);
}

function safeMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403)
      return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
    if (e.status === 404) return "Die Anfrage wurde nicht gefunden.";
    if (e.status === 409) {
      if (e.message.includes("pending"))
        return "Die Anfrage ist nicht mehr offen.";
      if (e.message.includes("requester"))
        return "Nur die anfragende Person kann zurückziehen.";
      return "Die Anfrage kann in diesem Status nicht bearbeitet werden.";
    }
  }
  return "Die Aktion konnte nicht ausgeführt werden. Bitte erneut versuchen.";
}
