"use client";

import { useState, useTransition } from "react";

import { redeemInvitationAction } from "./actions";

// Explicit consent capture: nothing is submitted without the checkbox, and no clinical
// content is shown at any point. Success, invalid-link, and error states are designed
// explicitly; the invalid state is neutral (no oracle about why).
export function EinladungContent({
  tenant,
  token,
}: {
  tenant: string;
  token: string;
}) {
  const [checked, setChecked] = useState(false);
  const [state, setState] = useState<
    { kind: "form" } | { kind: "done" } | { kind: "error"; message: string }
  >({ kind: "form" });
  const [pending, startTransition] = useTransition();

  if (state.kind === "done") {
    return (
      <p style={{ lineHeight: 1.55 }}>
        <strong>Vielen Dank — Ihre Einwilligung wurde erfasst.</strong>
        <br />
        Ihr klinisches Team kann Ihnen nun ärztlich freigegebene Berichte über
        einen gesicherten Zugriffslink bereitstellen. Sie können diese Seite
        schließen.
      </p>
    );
  }

  return (
    <div>
      <p style={{ lineHeight: 1.55 }}>
        Ihre Klinik möchte Ihnen ärztlich freigegebene Berichte über einen
        gesicherten Zugriffslink bereitstellen. Dafür wird Ihre Einwilligung
        (Zweck: Berichtsfreigabe) festgehalten — mit Zeitpunkt und Textversion.
        Sie können die Einwilligung jederzeit über Ihre Klinik widerrufen;
        bestehende Zugriffslinks werden dann sofort ungültig.
      </p>
      <label
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "10px",
          margin: "18px 0",
          lineHeight: 1.5,
          cursor: "pointer",
        }}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          style={{ marginTop: "3px" }}
        />
        <span>
          Ich willige ein, dass mir ärztlich freigegebene Berichte über einen
          gesicherten Zugriffslink bereitgestellt werden.
        </span>
      </label>
      {state.kind === "error" && (
        <p role="alert" style={{ color: "#b3261e", lineHeight: 1.5 }}>
          {state.message}
        </p>
      )}
      <button
        type="button"
        disabled={!checked || pending}
        onClick={() =>
          startTransition(async () => {
            const res = await redeemInvitationAction(tenant, token);
            setState(
              res.ok ? { kind: "done" } : { kind: "error", message: res.error },
            );
          })
        }
        style={{
          padding: "10px 18px",
          borderRadius: "9px",
          border: "1px solid #0f766e",
          background: checked ? "#0f766e" : "#e5e9ea",
          color: checked ? "#fff" : "#9aa6aa",
          fontWeight: 600,
          cursor: checked ? "pointer" : "not-allowed",
        }}
      >
        Einwilligung erteilen
      </button>
    </div>
  );
}
