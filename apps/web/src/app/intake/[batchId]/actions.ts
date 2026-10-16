"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  confirmGreenIntake,
  decideIntakeValue,
  type IntakeDecisionInput,
} from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

// The clinician's decisions on proposed values. The API enforces the clinician-only role,
// the tenant, one decision per value, "red is never confirmed" and the checks on a correction;
// these actions pass a decision on and put the answer into the interface's wording.

type Wording = Messages["intakePage"];

export type DecideResult =
  | { ok: true; decision: string; observationId: string | null }
  | { ok: false; error: string };

function decisionError(e: unknown, t: Wording): string {
  if (!(e instanceof ApiError)) return t.errors.failed;
  if (e.status === 403) return t.errors.notAllowed;
  if (e.status === 422) return t.errors.invalid;
  if (e.status === 409) {
    const code = e.message.split(":", 1)[0]?.trim() ?? "";
    if (code === "already_decided") return t.errors.alreadyDecided;
    if (code === "red_value") return t.errors.redValue;
    if (code === "no_change") return t.errors.noChange;
    if (code === "date_missing") return t.errors.dateMissing;
    if (code === "checks_failed") {
      const codes = e.message.slice(e.message.indexOf(":") + 1).split(",");
      const reasons: Record<string, string> = t.reasons;
      return fill(t.errors.checksFailed, {
        reasons: codes
          .map((c) => c.trim())
          .filter(Boolean)
          .map((c) => reasons[c] ?? c)
          .join(", "),
      });
    }
  }
  return t.errors.failed;
}

export async function decideIntakeValueAction(
  batchId: string,
  body: IntakeDecisionInput,
): Promise<DecideResult> {
  const t = (await getMessages()).intakePage;
  if (!isUuid(batchId) || !isUuid(body.pending_value_id))
    return { ok: false, error: t.errors.invalid };
  try {
    const out = await decideIntakeValue(batchId, body);
    revalidatePath(`/intake/${batchId}`);
    return {
      ok: true,
      decision: out.decision,
      observationId: out.observation_id ?? null,
    };
  } catch (e) {
    return { ok: false, error: decisionError(e, t) };
  }
}

export type ConfirmGreenResult =
  | { ok: true; confirmed: number }
  | { ok: false; error: string };

export async function confirmGreenAction(
  batchId: string,
  screenSeconds: number | null,
): Promise<ConfirmGreenResult> {
  const t = (await getMessages()).intakePage;
  if (!isUuid(batchId)) return { ok: false, error: t.errors.invalid };
  try {
    const out = await confirmGreenIntake(batchId, screenSeconds);
    revalidatePath(`/intake/${batchId}`);
    return { ok: true, confirmed: out.confirmed };
  } catch (e) {
    return { ok: false, error: decisionError(e, t) };
  }
}
