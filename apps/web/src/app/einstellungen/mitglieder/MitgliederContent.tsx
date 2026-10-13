"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { MemberOut, StaffInvitationListItem } from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";

import {
  changeMemberRoleAction,
  createStaffInviteAction,
  removeMemberAction,
  revokeStaffInviteAction,
} from "./actions";

// The page follows the interface language (lib/i18n); the names of the roles are the
// dictionary's own (`roles`), as in the shell. Names and e-mail addresses are shown as they
// are recorded, and the date of an invitation keeps its form.
const ROLE_ORDER = ["clinician", "assistant", "medical_director", "owner"];

const card: React.CSSProperties = {
  border: "1px solid var(--border-subtle, #dfe5e7)",
  borderRadius: "12px",
  padding: "18px 20px",
  marginBottom: "18px",
  background: "var(--surface, #fff)",
};

export function MitgliederContent({
  members,
  invitations,
  selfUserId,
}: {
  members: MemberOut[];
  invitations: StaffInvitationListItem[];
  selfUserId: string;
}) {
  const router = useRouter();
  const messages = useI18n().t;
  const t = messages.membersPage;
  const roleLabels: Record<string, string> = messages.roles;
  const [role, setRole] = useState("clinician");
  const [link, setLink] = useState<{ url: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const invite = () =>
    startTransition(async () => {
      setError(null);
      setLink(null);
      const res = await createStaffInviteAction(role);
      if (res.ok) setLink({ url: res.url, role: res.role });
      else setError(res.error);
    });

  const revoke = (id: string) =>
    startTransition(async () => {
      setError(null);
      const res = await revokeStaffInviteAction(id);
      if (res.ok) router.refresh();
      else setError(res.error);
    });

  const changeRole = (membershipId: string, newRole: string) =>
    startTransition(async () => {
      setError(null);
      const res = await changeMemberRoleAction(membershipId, newRole);
      if (res.ok) router.refresh();
      else setError(res.error);
    });

  const remove = (membershipId: string, name: string) =>
    startTransition(async () => {
      setError(null);
      if (!window.confirm(fill(t.removeConfirm, { name }))) return;
      const res = await removeMemberAction(membershipId);
      if (res.ok) router.refresh();
      else setError(res.error);
    });

  return (
    <div style={{ maxWidth: "760px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>
        {messages.settings.members.title}
      </h1>
      <p
        style={{
          color: "var(--text-muted, #5b6b70)",
          fontSize: "13px",
          marginBottom: "22px",
          lineHeight: 1.5,
        }}
      >
        {t.lead}
      </p>

      <section aria-label={t.team} style={{ marginBottom: "26px" }}>
        <strong style={{ display: "block", margin: "6px 0 12px" }}>
          {t.team}
        </strong>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {members.map((m) => {
            const isSelf = m.user_id === selfUserId;
            return (
              <li
                key={m.membership_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  // On a phone the role and the button go below the name; the address
                  // breaks rather than running under them.
                  flexWrap: "wrap",
                  gap: "12px",
                  padding: "12px 14px",
                  border: "1px solid var(--border-subtle, #dfe5e7)",
                  borderRadius: "9px",
                  marginBottom: "8px",
                }}
              >
                <span
                  style={{
                    fontSize: "14px",
                    minWidth: 0,
                    overflowWrap: "anywhere",
                  }}
                >
                  <strong>{m.display_name}</strong>
                  <span
                    style={{
                      color: "var(--text-muted, #5b6b70)",
                      marginLeft: "10px",
                      fontSize: "12px",
                    }}
                  >
                    {m.email}
                    {isSelf ? t.you : ""}
                  </span>
                </span>
                <span
                  style={{ display: "flex", gap: "8px", alignItems: "center" }}
                >
                  {isSelf ? (
                    <span style={{ fontSize: "13px", fontWeight: 600 }}>
                      {roleLabels[m.role] ?? m.role}
                    </span>
                  ) : (
                    <>
                      <label
                        style={{ fontSize: "12px" }}
                        aria-label={fill(t.roleOf, { name: m.display_name })}
                      >
                        <select
                          value={m.role}
                          disabled={pending}
                          onChange={(e) =>
                            changeRole(m.membership_id, e.target.value)
                          }
                          style={{
                            padding: "6px 8px",
                            borderRadius: "7px",
                            border: "1px solid var(--border-subtle, #dfe5e7)",
                            fontSize: "13px",
                          }}
                        >
                          {ROLE_ORDER.map((r) => (
                            <option key={r} value={r}>
                              {roleLabels[r]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        onClick={() => remove(m.membership_id, m.display_name)}
                        disabled={pending}
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
                        {t.remove}
                      </button>
                    </>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section style={card} aria-label={t.invite.title}>
        <strong style={{ display: "block", marginBottom: "12px" }}>
          {t.invite.title}
        </strong>
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <label style={{ fontSize: "13px" }}>
            {t.invite.role}{" "}
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{
                padding: "8px 10px",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle, #dfe5e7)",
                fontSize: "14px",
              }}
            >
              {ROLE_ORDER.map((r) => (
                <option key={r} value={r}>
                  {roleLabels[r]}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={invite}
            disabled={pending}
            style={{
              padding: "9px 16px",
              borderRadius: "9px",
              border: "1px solid #0f766e",
              background: "#0f766e",
              color: "#fff",
              fontWeight: 600,
              cursor: pending ? "wait" : "pointer",
            }}
          >
            {t.invite.create}
          </button>
        </div>

        {link && (
          <div
            style={{
              marginTop: "16px",
              padding: "12px 14px",
              borderRadius: "9px",
              background: "rgba(15,118,110,0.06)",
              border: "1px solid rgba(15,118,110,0.25)",
            }}
          >
            <p style={{ margin: "0 0 8px", fontSize: "13px", lineHeight: 1.5 }}>
              {t.invite.createdBefore}{" "}
              <strong>{roleLabels[link.role] ?? link.role}</strong>{" "}
              {t.invite.createdAfter} <strong>{t.invite.once}</strong>.
            </p>
            <input
              readOnly
              value={link.url}
              onFocus={(e) => e.currentTarget.select()}
              aria-label={t.invite.link}
              style={{
                width: "100%",
                padding: "8px 10px",
                borderRadius: "7px",
                border: "1px solid var(--border-subtle, #dfe5e7)",
                fontSize: "12px",
                fontFamily: "var(--font-mono, monospace)",
              }}
            />
          </div>
        )}
      </section>

      {error && (
        <p role="alert" style={{ color: "#b3261e", lineHeight: 1.5 }}>
          {error}
        </p>
      )}

      <section aria-label={t.pending.title}>
        <strong style={{ display: "block", margin: "6px 0 12px" }}>
          {t.pending.title}
        </strong>
        {invitations.length === 0 ? (
          <p style={{ color: "var(--text-muted, #5b6b70)", fontSize: "13px" }}>
            {t.pending.none}
          </p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {invitations.map((inv) => (
              <li
                key={inv.invitation_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                  padding: "12px 14px",
                  border: "1px solid var(--border-subtle, #dfe5e7)",
                  borderRadius: "9px",
                  marginBottom: "8px",
                }}
              >
                <span style={{ fontSize: "14px" }}>
                  <strong>{roleLabels[inv.role] ?? inv.role}</strong>
                  <span
                    style={{
                      color: "var(--text-muted, #5b6b70)",
                      marginLeft: "10px",
                      fontSize: "12px",
                    }}
                  >
                    {fill(t.pending.validUntil, {
                      day: inv.expires_at.slice(0, 10),
                    })}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => revoke(inv.invitation_id)}
                  disabled={pending}
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
                  {t.pending.revoke}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
