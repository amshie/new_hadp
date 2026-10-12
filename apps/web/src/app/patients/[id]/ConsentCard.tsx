"use client";

import { useState, useTransition, type CSSProperties } from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import type { ConsentState } from "@/lib/api";
import { CONSENT_OPTIONS, type ConsentPurpose } from "@/lib/consentCopy";

import { recordConsentAction } from "./consent-actions";

// Consent state of one patient, per purpose of the closed vocabulary, with the two staff
// operations: document a consent, document a withdrawal. Both append a new event; nothing is
// edited. The state shown is the rule the release gate applies (latest event is a grant).

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};

const btnSec: CSSProperties = {
  height: "32px",
  padding: "0 12px",
  whiteSpace: "nowrap",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
  fontFamily: "var(--font-text)",
  fontSize: "12.5px",
  fontWeight: 600,
  cursor: "pointer",
};

const btnPri: CSSProperties = {
  ...btnSec,
  border: "1px solid var(--brand)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
};

const CHANNEL_LABELS: Record<string, string> = {
  in_person: "vor Ort erklärt",
};

function fmtDay(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function stateLine(state: ConsentState | undefined): string {
  const event = state?.last_event;
  if (!event) return "Nicht dokumentiert";
  const how = CHANNEL_LABELS[event.channel] ?? event.channel;
  const what = event.event_type === "granted" ? "Erteilt" : "Widerrufen";
  return `${what} am ${fmtDay(event.recorded_at)} (${how}) · Textversion ${event.consent_text_version}`;
}

export function ConsentCard({
  patientId,
  consents,
  canRecord,
}: {
  patientId: string;
  consents: ConsentState[];
  canRecord: boolean;
}) {
  const [confirm, setConfirm] = useState<{
    purpose: ConsentPurpose;
    label: string;
    kind: "grant" | "withdraw";
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const byPurpose = new Map(consents.map((c) => [c.purpose, c]));

  const close = () => {
    setConfirm(null);
    setError(null);
  };

  const run = () => {
    if (!confirm) return;
    startTransition(async () => {
      const res = await recordConsentAction(
        patientId,
        confirm.purpose,
        confirm.kind,
      );
      if (!res.ok) {
        setError(res.error);
        return;
      }
      close();
    });
  };

  return (
    <section
      style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}
      aria-labelledby="consent-heading"
    >
      <div style={{ padding: "20px 22px 14px" }}>
        <h3
          id="consent-heading"
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-lg)",
            color: "var(--text-strong)",
            margin: 0,
          }}
        >
          Einwilligungen
        </h3>
        <p
          style={{
            margin: "6px 0 0",
            fontSize: "12.5px",
            lineHeight: 1.5,
            color: "var(--text-muted)",
            maxWidth: "88ch",
          }}
        >
          Stand je Zweck. Jeder Eintrag ist ein neuer, zugeordneter und
          auditierter Vermerk — frühere Einträge werden nie geändert.
          {!canRecord &&
            " Das Dokumentieren ist dem Praxisteam vorbehalten (Nur-Lese-Ansicht)."}
        </p>
      </div>

      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {CONSENT_OPTIONS.map((option) => {
          const state = byPurpose.get(option.purpose);
          const active = state?.active === true;
          return (
            <li
              key={option.purpose}
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
                padding: "13px 22px",
                borderTop: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ minWidth: "240px", flex: "1 1 320px" }}>
                <div
                  style={{
                    fontSize: "13.5px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                  }}
                >
                  {option.label}
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "var(--text-muted)",
                    marginTop: "2px",
                  }}
                >
                  {option.desc}
                </div>
              </div>
              <div
                style={{
                  flex: "1 1 260px",
                  fontSize: "12.5px",
                  color: "var(--text-body)",
                }}
              >
                <strong style={{ color: "var(--text-strong)" }}>
                  {active ? "Aktiv" : "Nicht aktiv"}
                </strong>
                {" — "}
                {stateLine(state)}
              </div>
              {canRecord && (
                <button
                  type="button"
                  style={active ? btnSec : btnPri}
                  disabled={pending}
                  onClick={() =>
                    setConfirm({
                      purpose: option.purpose,
                      label: option.label,
                      kind: active ? "withdraw" : "grant",
                    })
                  }
                >
                  {active
                    ? "Widerruf dokumentieren"
                    : "Einwilligung dokumentieren"}
                </button>
              )}
            </li>
          );
        })}
      </ul>
      <p
        style={{
          margin: 0,
          padding: "10px 22px 16px",
          borderTop: "1px solid var(--border-subtle)",
          fontSize: "11.5px",
          lineHeight: 1.5,
          color: "var(--text-faint)",
        }}
      >
        Synthetische Demo: Zwecke und Einwilligungstext sind Platzhalter.
        Technisch durchgesetzt wird derzeit nur die Freigabe geprüfter Berichte
        (ohne aktive Einwilligung keine Freigabe; ein Widerruf entzieht
        bestehende Zugriffslinks). Die übrigen Zwecke werden dokumentiert, aber
        noch nicht technisch durchgesetzt.
      </p>

      {confirm && (
        <Dialog
          onClose={close}
          labelledBy="consent-dialog-title"
          lockScroll
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "500px",
            maxWidth: "100%",
            ...cardStyle,
            padding: "22px",
          }}
        >
          <h3
            id="consent-dialog-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: "var(--text-xl)",
              color: "var(--text-strong)",
              margin: 0,
            }}
          >
            {confirm.kind === "grant"
              ? "Einwilligung dokumentieren?"
              : "Widerruf dokumentieren?"}
          </h3>
          <p
            style={{
              margin: "10px 0 0",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            <strong style={{ color: "var(--text-strong)" }}>
              {confirm.label}.
            </strong>{" "}
            {confirm.kind === "grant"
              ? "Sie dokumentieren, dass die Person diesem Zweck vor Ort zugestimmt hat. Der Vermerk wird Ihnen zugeordnet und auditiert; er lässt sich nicht ändern, nur durch einen Widerruf ergänzen."
              : "Sie dokumentieren, dass die Person ihre Einwilligung vor Ort widerrufen hat. Der Vermerk wird Ihnen zugeordnet und auditiert; die frühere Einwilligung bleibt als Eintrag erhalten."}
            {confirm.kind === "withdraw" &&
              confirm.purpose === "report_release" &&
              " Bestehende Zugriffslinks der Person werden sofort ungültig; eine neue Freigabe ist erst nach erneuter Einwilligung möglich."}
          </p>
          {error && (
            <p
              role="alert"
              style={{
                margin: "12px 0 0",
                fontSize: "12.5px",
                color: "var(--danger, #b3261e)",
              }}
            >
              {error}
            </p>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
              marginTop: "20px",
            }}
          >
            <button
              type="button"
              style={btnSec}
              disabled={pending}
              onClick={close}
            >
              Abbrechen
            </button>
            <button
              type="button"
              style={btnPri}
              disabled={pending}
              onClick={run}
            >
              {confirm.kind === "grant"
                ? "Dokumentieren"
                : "Widerruf dokumentieren"}
            </button>
          </div>
        </Dialog>
      )}
    </section>
  );
}
