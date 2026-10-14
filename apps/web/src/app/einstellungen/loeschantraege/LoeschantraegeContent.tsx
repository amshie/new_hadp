"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { EmptyState } from "@/components/vitabahn/EmptyState";
import type { DeletionRequestView } from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";

import {
  approveDeletionAction,
  cancelDeletionAction,
  executeDeletionAction,
  rejectDeletionAction,
} from "./actions";
import { sectionEyebrow } from "../SettingsFrame";

// Owner + medical-director queue for patient-erasure requests (docs/notes/0012). The medical
// director approves/rejects a pending request; the owner may withdraw their own pending one.
// Execution of an approved request (the irreversible erasure) is not yet wired — an approved
// row shows an explanatory "ausstehend" state. Server-side authorization is the control.
// The page follows the interface language (lib/i18n); a patient's name is shown as it is
// recorded, and a date keeps its form (TT.MM.JJJJ).

// The colours of a request's status; its words are the dictionary's.
const STATUS_COLOURS: Record<string, { fg: string; bg: string }> = {
  pending: { fg: "#8b641d", bg: "rgba(139,100,29,0.12)" },
  approved: { fg: "#1f6f5c", bg: "rgba(31,111,92,0.12)" },
  rejected: { fg: "#a54840", bg: "rgba(165,72,64,0.12)" },
  cancelled: { fg: "#5b6b70", bg: "rgba(91,107,112,0.10)" },
  executed: { fg: "#17292f", bg: "rgba(23,41,47,0.10)" },
};

function fmt(iso: string | null): string {
  if (!iso) return "—";
  const d = iso.slice(0, 10).split("-");
  return d.length === 3 ? `${d[2]}.${d[1]}.${d[0]}` : iso;
}

export function LoeschantraegeContent({
  requests,
  role,
  selfUserId,
}: {
  requests: DeletionRequestView[];
  role: string;
  selfUserId: string;
}) {
  const router = useRouter();
  const messages = useI18n().t;
  const t = messages.deletionRequestsPage;
  const reasons: Record<string, string> = messages.patientPage.deletion.reasons;
  const statuses: Record<string, string> = t.status;
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const isMedicalDirector = role === "medical_director";
  const isOwner = role === "owner";

  const act = (
    fn: (id: string) => Promise<{ ok: boolean; error?: string }>,
    id: string,
    confirmMsg?: string,
  ) =>
    startTransition(async () => {
      setError(null);
      if (confirmMsg && !window.confirm(confirmMsg)) return;
      const res = await fn(id);
      if (res.ok) router.refresh();
      else setError(res.error ?? t.errors.failedShort);
    });

  return (
    <div style={{ maxWidth: "820px" }}>
      <div className="vb-set-head">
        <span className="vb-ov-eyebrow">
          {sectionEyebrow("deletionRequests", messages)}
        </span>
        <h1 className="vb-ov-h1">{messages.settings.deletionRequests.title}</h1>
        <p className="vb-ov-lead">{t.lead}</p>
      </div>

      {error && (
        <p role="alert" style={{ color: "#b3261e", lineHeight: 1.5 }}>
          {error}
        </p>
      )}

      {requests.length === 0 ? (
        <div className="vb-ov-card">
          <EmptyState>{t.none}</EmptyState>
        </div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {requests.map((r) => {
            const sm = STATUS_COLOURS[r.status] ?? STATUS_COLOURS.pending!;
            const isRequester = r.requested_by_user_id === selfUserId;
            const canDecide = isMedicalDirector && r.status === "pending";
            const canCancel = isOwner && r.status === "pending" && isRequester;
            return (
              <li
                key={r.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "14px",
                  flexWrap: "wrap",
                  padding: "13px 15px",
                  border: "1px solid var(--border-subtle, #dfe5e7)",
                  borderRadius: "10px",
                  marginBottom: "9px",
                }}
              >
                <span style={{ fontSize: "14px", minWidth: 0 }}>
                  <strong>
                    {r.patient_erased ? t.erased : r.patient_display_name}
                  </strong>
                  <span
                    style={{
                      color: "var(--text-muted, #5b6b70)",
                      marginLeft: "10px",
                      fontSize: "12px",
                    }}
                  >
                    {reasons[r.reason_category] ?? r.reason_category} ·{" "}
                    {fill(t.requested, { day: fmt(r.requested_at) })}
                  </span>
                </span>
                <span
                  style={{
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      padding: "3px 10px",
                      borderRadius: "999px",
                      color: sm.fg,
                      background: sm.bg,
                    }}
                  >
                    {statuses[r.status] ?? r.status}
                  </span>
                  {r.status === "approved" &&
                    (isMedicalDirector || isOwner ? (
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() =>
                          act(
                            executeDeletionAction,
                            r.id,
                            fill(t.executeConfirm, {
                              name: r.patient_display_name,
                            }),
                          )
                        }
                        style={{
                          padding: "6px 12px",
                          borderRadius: "8px",
                          border: "1px solid #b3261e",
                          background: "#b3261e",
                          color: "#fff",
                          fontWeight: 600,
                          fontSize: "13px",
                          cursor: pending ? "wait" : "pointer",
                        }}
                      >
                        {t.execute}
                      </button>
                    ) : (
                      <span
                        style={{
                          fontSize: "12px",
                          color: "var(--text-muted, #5b6b70)",
                        }}
                      >
                        {t.executionPending}
                      </span>
                    ))}
                  {canDecide && (
                    <>
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() =>
                          act(
                            approveDeletionAction,
                            r.id,
                            fill(t.approveConfirm, {
                              name: r.patient_display_name,
                            }),
                          )
                        }
                        style={{
                          padding: "6px 12px",
                          borderRadius: "8px",
                          border: "1px solid #1f6f5c",
                          background: "#1f6f5c",
                          color: "#fff",
                          fontWeight: 600,
                          fontSize: "13px",
                          cursor: pending ? "wait" : "pointer",
                        }}
                      >
                        {t.approve}
                      </button>
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => act(rejectDeletionAction, r.id)}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "8px",
                          border: "1px solid #b3261e",
                          background: "transparent",
                          color: "#b3261e",
                          fontWeight: 600,
                          fontSize: "13px",
                          cursor: pending ? "wait" : "pointer",
                        }}
                      >
                        {t.reject}
                      </button>
                    </>
                  )}
                  {canCancel && (
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => act(cancelDeletionAction, r.id)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-strong, #cbd6d9)",
                        background: "transparent",
                        color: "var(--ink, #17292f)",
                        fontWeight: 600,
                        fontSize: "13px",
                        cursor: pending ? "wait" : "pointer",
                      }}
                    >
                      {t.cancel}
                    </button>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
