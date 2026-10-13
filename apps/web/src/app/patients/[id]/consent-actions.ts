"use server";

import { revalidatePath } from "next/cache";

import { ApiError, grantConsent, withdrawConsent } from "@/lib/api";
import { CONSENT_OPTIONS, type ConsentPurpose } from "@/lib/consentCopy";
import { getMessages } from "@/lib/i18n/server";
import { isUuid } from "@/lib/uuid";

// Consent recorded by staff on the patient page: the person declared it in the practice and a
// staff member documents it. Each call appends a NEW consent event (grant or withdrawal) — the
// API enforces role and tenant, attributes the entry and audits it; a withdrawal of the report
// release consent also revokes the patient's access links in the same transaction.

// The channel vocabulary is still a bounded free string in the API (DPO taxonomy pending);
// what staff record here is always a declaration made in person.
const CHANNEL = "in_person";

export type ConsentActionResult = { ok: true } | { ok: false; error: string };

export async function recordConsentAction(
  patientId: string,
  purpose: ConsentPurpose,
  kind: "grant" | "withdraw",
): Promise<ConsentActionResult> {
  const t = (await getMessages()).patientPage;
  if (!isUuid(patientId)) return { ok: false, error: t.invalidPatient };
  // Server-action arguments arrive from the client: only the closed vocabulary passes.
  if (!CONSENT_OPTIONS.some((o) => o.purpose === purpose))
    return { ok: false, error: t.consent.errors.unknownPurpose };
  if (kind !== "grant" && kind !== "withdraw")
    return { ok: false, error: t.consent.errors.unknownAction };
  try {
    if (kind === "grant") await grantConsent(patientId, purpose, CHANNEL);
    else await withdrawConsent(patientId, purpose, CHANNEL);
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 403) return { ok: false, error: t.notAllowed };
      if (e.status === 404) return { ok: false, error: t.recordUnavailable };
    }
    return { ok: false, error: t.consent.errors.notSaved };
  }
  revalidatePath(`/patients/${patientId}`);
  return { ok: true };
}
