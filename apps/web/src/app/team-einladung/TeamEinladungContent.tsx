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
      <p>
        <strong>Willkommen im Team.</strong>
        <br />
        Ihr Zugang wurde eingerichtet. Sie können sich nun mit Ihrer
        E-Mail-Adresse in Ihrem Klinik-Arbeitsbereich anmelden.
      </p>
    );
  }

  const canSubmit = displayName.trim().length > 0 && email.trim().length > 2;

  return (
    <div>
      <p>
        Ihre Klinik hat Sie eingeladen, dem Team beizutreten. Bitte richten Sie
        Ihren Zugang ein. Ihre Rolle wurde von Ihrer Klinik festgelegt.
      </p>
      <label className="vb-auth-field">
        <span className="field-label">Name</span>
        <input
          className="vb-auth-input"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          autoComplete="name"
        />
      </label>
      <label className="vb-auth-field">
        <span className="field-label">E-Mail-Adresse</span>
        <input
          className="vb-auth-input"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
      </label>
      {state.kind === "error" && (
        <p role="alert" className="vb-pub-error">
          {state.message}
        </p>
      )}
      <button
        type="button"
        className="vb-ov-btn primary vb-pub-btn"
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
      >
        Zugang einrichten
      </button>
    </div>
  );
}
