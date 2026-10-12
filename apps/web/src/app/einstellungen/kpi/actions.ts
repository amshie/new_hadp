"use server";

import { revalidatePath } from "next/cache";

import {
  ApiError,
  clearKpiReference,
  resetKpiConfig,
  setKpiReference,
  updateKpiConfig,
} from "@/lib/api";

// Owner-side per-tenant KPI configuration. Server-side authorization is the real control (the API
// gates KPI_CONFIG_WRITE to owners and rejects everything else with 403); these actions map
// failures to German copy and refresh the list. The global catalog is never touched — only this
// tenant's override rows.

// Replace semantics mirror the API: each write fully specifies enable + patient visibility for the
// KPI. Clinician visibility stays inherited from the catalog in this surface (not managed here).
export type KpiConfigResult = { ok: true } | { ok: false; error: string };

export async function setKpiConfigAction(
  kpiCode: string,
  enabled: boolean,
  patientVisible: boolean,
): Promise<KpiConfigResult> {
  try {
    await updateKpiConfig(kpiCode, {
      enabled,
      patient_visible: patientVisible,
    });
    revalidatePath("/einstellungen/kpi");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export async function resetKpiConfigAction(
  kpiCode: string,
): Promise<KpiConfigResult> {
  try {
    await resetKpiConfig(kpiCode);
    revalidatePath("/einstellungen/kpi");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export async function setKpiReferenceAction(
  kpiCode: string,
  referenceLow: string,
  referenceHigh: string,
): Promise<KpiConfigResult> {
  // Client-side plausibility (the API validates authoritatively): two real, ordered numbers.
  const lo = Number(referenceLow);
  const hi = Number(referenceHigh);
  if (
    !referenceLow.trim() ||
    !referenceHigh.trim() ||
    !Number.isFinite(lo) ||
    !Number.isFinite(hi)
  )
    return { ok: false, error: "Bitte zwei gültige Zahlen eingeben." };
  if (lo >= hi)
    return {
      ok: false,
      error: "Der untere Wert muss kleiner als der obere sein.",
    };
  try {
    await setKpiReference(kpiCode, {
      reference_low: referenceLow.trim(),
      reference_high: referenceHigh.trim(),
    });
    revalidatePath("/einstellungen/kpi");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

export async function clearKpiReferenceAction(
  kpiCode: string,
): Promise<KpiConfigResult> {
  try {
    await clearKpiReference(kpiCode);
    revalidatePath("/einstellungen/kpi");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: safeMessage(e) };
  }
}

function safeMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403)
      return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
    if (e.status === 404) return "Diese Kennzahl ist nicht mehr verfügbar.";
    if (e.status === 422) return "Ungültige Referenzwerte für diese Kennzahl.";
    if (e.status === 409)
      return "Spezialist:innen- und Forschungs-Kennzahlen können nicht für Patient:innen sichtbar gemacht werden.";
    if (e.status === 429)
      return "Zu viele Anfragen. Bitte später erneut versuchen.";
  }
  return "Die Aktion konnte nicht ausgeführt werden. Bitte erneut versuchen.";
}
