"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { DeletionRequestView } from "@/lib/api";

import {
  approveDeletionAction,
  cancelDeletionAction,
  executeDeletionAction,
  rejectDeletionAction,
} from "./actions";

// Owner + medical-director queue for patient-erasure requests (docs/notes/0012). The medical
// director approves/rejects a pending request; the owner may withdraw their own pending one.
// Execution of an approved request (the irreversible erasure) is not yet wired — an approved
// row shows an explanatory "ausstehend" state. Server-side authorization is the control.

const REASON_LABELS: Record<string, string> = {
  patient_request: "Betroffenenanfrage (Art. 17)",
  withdrawn_consent: "Einwilligung widerrufen",
  data_minimization: "Datenminimierung",
};

const STATUS_META: Record<string, { label: string; fg: string; bg: string }> = {
  pending: { label: "Offen", fg: "#8b641d", bg: "rgba(139,100,29,0.12)" },
  approved: { label: "Freigegeben", fg: "#1f6f5c", bg: "rgba(31,111,92,0.12)" },
  rejected: { label: "Abgelehnt", fg: "#a54840", bg: "rgba(165,72,64,0.12)" },
  cancelled: {
    label: "Zurückgezogen",
    fg: "#5b6b70",
    bg: "rgba(91,107,112,0.10)",
  },
  executed: { label: "Ausgeführt", fg: "#17292f", bg: "rgba(23,41,47,0.10)" },
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
      else setError(res.error ?? "Aktion fehlgeschlagen.");
    });

  return (
    <div style={{ maxWidth: "820px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>Löschanträge</h1>
      <p
        style={{
          color: "var(--text-muted, #5b6b70)",
          fontSize: "13px",
          marginBottom: "22px",
          lineHeight: 1.55,
        }}
      >
        Anträge auf Löschung von Patientendaten. Ein Antrag wird von der
        Inhaberin oder dem Inhaber gestellt und von der Ärztlichen Leitung
        geprüft (Vier-Augen-Prinzip). Die eigentliche, unwiderrufliche Löschung
        anonymisiert den Datensatz und wird gesondert ausgeführt.
      </p>

      {error && (
        <p role="alert" style={{ color: "#b3261e", lineHeight: 1.5 }}>
          {error}
        </p>
      )}

      {requests.length === 0 ? (
        <p style={{ color: "var(--text-muted, #5b6b70)", fontSize: "13px" }}>
          Keine Löschanträge vorhanden.
        </p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {requests.map((r) => {
            const sm = STATUS_META[r.status] ?? STATUS_META.pending!;
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
                    {r.patient_erased
                      ? "Gelöschter Datensatz"
                      : r.patient_display_name}
                  </strong>
                  <span
                    style={{
                      color: "var(--text-muted, #5b6b70)",
                      marginLeft: "10px",
                      fontSize: "12px",
                    }}
                  >
                    {REASON_LABELS[r.reason_category] ?? r.reason_category} ·
                    beantragt {fmt(r.requested_at)}
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
                    {sm.label}
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
                            `Daten von „${r.patient_display_name}" jetzt endgültig und unwiderruflich löschen? Der Datensatz wird anonymisiert; abgeleitete Daten, Dokumente und Berichte werden gelöscht. Dies kann nicht rückgängig gemacht werden.`,
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
                        Endgültig löschen
                      </button>
                    ) : (
                      <span
                        style={{
                          fontSize: "12px",
                          color: "var(--text-muted, #5b6b70)",
                        }}
                      >
                        Ausführung ausstehend
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
                            `Löschung für „${r.patient_display_name}" freigeben? Die Ausführung erfolgt gesondert und ist unwiderruflich.`,
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
                        Freigeben
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
                        Ablehnen
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
                      Zurückziehen
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
