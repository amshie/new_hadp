"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  ApiError,
  recordPreparationStatement,
  type PreparationStatementInput,
} from "@/lib/api";

const PATH = "/einstellungen/vorbereitungszeit";

const KINDS = ["baseline", "follow_up"] as const;
const BASES = ["estimate", "timed_sample"] as const;

// A whole number in a range, written with digits only — "30", not "30,5" or "30 min".
function whole(
  value: FormDataEntryValue | null,
  min: number,
  max: number,
): number | null {
  if (typeof value !== "string" || !/^[0-9]{1,6}$/.test(value.trim()))
    return null;
  const n = Number(value.trim());
  return n >= min && n <= max ? n : null;
}

// The clinic's own statement of its preparation time. The API authorizes (owner only),
// validates again and records it; this action checks the form and says in which way an
// input was not usable. The outcome travels in the URL as one of a closed set of codes.
export async function recordStatementAction(formData: FormData): Promise<void> {
  const kind = KINDS.find((k) => k === formData.get("kind"));
  const basis = BASES.find((b) => b === formData.get("basis"));
  const minutes = whole(formData.get("median_minutes"), 1, 600);
  const rawSample = formData.get("sample_size");
  const sampleGiven = typeof rawSample === "string" && rawSample.trim() !== "";
  const sample = sampleGiven ? whole(rawSample, 1, 100000) : null;

  if (!kind || !basis) redirect(`${PATH}?fehler=eingabe`);
  if (minutes === null) redirect(`${PATH}?fehler=minuten`);
  // A timed sample says over how many appointments; an estimate has no sample.
  if (basis === "timed_sample" && sample === null)
    redirect(`${PATH}?fehler=stichprobe`);
  if (basis === "estimate" && sampleGiven)
    redirect(`${PATH}?fehler=schaetzung`);

  const input: PreparationStatementInput = {
    kind,
    basis,
    median_minutes: minutes,
    sample_size: basis === "timed_sample" ? sample : null,
  };
  try {
    await recordPreparationStatement(input);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect(`${PATH}?fehler=rolle`);
    if (e instanceof ApiError && e.status === 422)
      redirect(`${PATH}?fehler=eingabe`);
    redirect(`${PATH}?fehler=allgemein`);
  }
  revalidatePath(PATH);
  redirect(`${PATH}?gespeichert=1`);
}
