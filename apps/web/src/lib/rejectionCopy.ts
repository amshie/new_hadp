// German copy for the closed report-rejection vocabulary (API: ReportRejectionReason). One
// source for the dialog that records a reason and the notices that show it. The values are a
// proposal awaiting the medical director's confirmation; a change is an API migration.

import type { components } from "@hadp/api-client";

export type RejectionReason = components["schemas"]["ReportRejectionReason"];

export const REJECTION_REASONS: {
  reason: RejectionReason;
  label: string;
  desc: string;
}[] = [
  {
    reason: "evidence_insufficient",
    label: "Beleg unzureichend",
    desc: "Eine Aussage ist nicht oder nicht richtig durch ihre Belege gedeckt.",
  },
  {
    reason: "wording",
    label: "Formulierung",
    desc: "Die Formulierung muss geändert werden.",
  },
  {
    reason: "data_incomplete",
    label: "Daten unvollständig",
    desc: "Daten fehlen, oder Werte warten noch in der Review-Queue.",
  },
  {
    reason: "data_changed",
    label: "Daten geändert",
    desc: "Die zugrunde liegenden Daten haben sich nach dem Entwurf geändert.",
  },
  {
    reason: "other",
    label: "Anderer Grund",
    desc: "Der Grund wird außerhalb des Systems mitgeteilt.",
  },
];

// The label and description for a stored reason; null for a value this build does not know
// (shown as its code rather than guessed at).
export function rejectionCopy(
  reason: string | null | undefined,
): { label: string; desc: string } | null {
  if (!reason) return null;
  const known = REJECTION_REASONS.find((r) => r.reason === reason);
  return known
    ? { label: known.label, desc: known.desc }
    : { label: reason, desc: "" };
}
