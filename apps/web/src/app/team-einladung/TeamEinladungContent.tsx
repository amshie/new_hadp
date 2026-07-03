"use client";

import { useState, useTransition } from "react";

import { redeemStaffInvitationAction } from "./actions";

// The colleague creates their own account (name + e-mail) and joins the clinic team. The
// role was set by the inviting owner and is applied server-side — it is never chosen here.
// Success, invalid-link, and error states are explicit; the invalid state is neutral.
export function TeamEinladungContent({
  tenant,
  token,
}: {
  tenant: string;
  token: string;
}) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [state, setState] = useState<
    { kind: "form" } | { kind: "done" } | { kind: "error"; message: string }
  >({ kind: "form" });
  const [pending, startTransition] = useTransition();

  if (state.kind === "done") {
    return (
      <p style={{ lineHeight: 1.55 }}>
        <strong>Willkommen im Team.</strong>
        <br />
        Ihr Zugang wurde eingerichtet. Sie können sich nun mit Ihrer
        E-Mail-Adresse in Ihrem Klinik-Arbeitsbereich anmelden.
      </p>
    );
  }

  const canSubmit = displayName.trim().length > 0 && email.trim().length > 2;
  const field: React.CSSProperties = {
    width: "100%",
    padding: "9px 11px",
    borderRadius: "8px",
    border: "1px solid var(--border-subtle, #dfe5e7)",
    fontSize: "14px",
    marginTop: "4px",
  };

  return (
    <div>
      <p style={{ lineHeight: 1.55 }}>
        Ihre Klinik hat Sie eingeladen, dem Team beizutreten. Bitte richten Sie
        Ihren Zugang ein. Ihre Rolle wurde von Ihrer Klinik festgelegt.
      </p>
      <label style={{ display: "block", margin: "16px 0", lineHeight: 1.4 }}>
        Name
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          autoComplete="name"
          style={field}
        />
      </label>
      <label style={{ display: "block", margin: "16px 0", lineHeight: 1.4 }}>
        E-Mail-Adresse
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          style={field}
        />
      </label>
      {state.kind === "error" && (
        <p role="alert" style={{ color: "#b3261e", lineHeight: 1.5 }}>
          {state.message}
        </p>
      )}
      <button
        type="button"
        disabled={!canSubmit || pending}
        onClick={() =>
          startTransition(async () => {
            const res = await redeemStaffInvitationAction({
              tenant,
              token,
              display_name: displayName.trim(),
              email: email.trim(),
            });
            setState(
              res.ok ? { kind: "done" } : { kind: "error", message: res.error },
            );
          })
        }
        style={{
          padding: "10px 18px",
          borderRadius: "9px",
          border: "1px solid #0f766e",
          background: canSubmit ? "#0f766e" : "#e5e9ea",
          color: canSubmit ? "#fff" : "#9aa6aa",
          fontWeight: 600,
          cursor: canSubmit ? "pointer" : "not-allowed",
        }}
      >
        Zugang einrichten
      </button>
    </div>
  );
}
