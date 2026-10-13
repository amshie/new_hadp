"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  approveDeletionRequest,
  cancelDeletionRequest,
  executeDeletionRequest,
  rejectDeletionRequest,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import type { Messages } from "@/lib/i18n/messages";
import { isUuid } from "@/lib/uuid";

// Erasure-request decisions. Server-side authorization is the real control (the API gates
// decide to the medical director and cancel to the owner-requester); these actions map
// failures to copy in the language of the interface (lib/i18n) and refresh the queue.

export type DecisionResult = { ok: true } | { ok: false; error: string };

type Errors = Messages["deletionRequestsPage"]["errors"];

async function errors(): Promise<Errors> {
  return (await getMessages()).deletionRequestsPage.errors;
}

async function run(
  requestId: string,
  fn: (id: string) => Promise<unknown>,
): Promise<DecisionResult> {
  const t = await errors();
  if (!isUuid(requestId)) return { ok: false, error: t.invalid };
  try {
    await fn(requestId);
    revalidatePath("/einstellungen/loeschantraege");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
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
export async function executeDeletionAction(
  id: string,
): Promise<DecisionResult> {
  const t = await errors();
  if (!isUuid(id)) return { ok: false, error: t.invalid };
  try {
    await executeDeletionRequest(id);
    // The erasure changes patient counts/listings across the app.
    revalidatePath("/einstellungen/loeschantraege");
    revalidatePath("/patients");
    revalidatePath("/overview");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e, t) };
  }
}

function safeMessage(e: unknown, t: Errors): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403) return t.forbidden;
    if (e.status === 404) return t.notFound;
    if (e.status === 409) {
      if (e.message.includes("pending")) return t.notOpen;
      if (e.message.includes("requester")) return t.requesterOnly;
      return t.wrongStatus;
    }
  }
  return t.failed;
}
