"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  useTransition,
  type ReactNode,
} from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import type {
  MemberOut,
  RolePermissions,
  StaffInvitationListItem,
} from "@/lib/api";
import { ago, day } from "@/lib/format";
import { fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { initialsOf } from "@/lib/identity";
import { capabilityMatrix, MATRIX_ROLES } from "@/lib/roleCapabilities";

import {
  changeMemberRoleAction,
  createStaffInviteAction,
  removeMemberAction,
  revokeStaffInviteAction,
} from "./actions";

// Team & Rollen (docs/notes/0016, part 2). Who works in the clinic, in what role, and when
// they last acted; the open invitations; and what each role may do — read from the API's
// authorization matrix. Changing a role and removing a member ask first; both are recorded by
// the API. Names and e-mail addresses are shown as recorded. The page follows the interface
// language (lib/i18n); the names of the roles are the dictionary's own (`roles`).
const ROLE_ORDER = ["clinician", "assistant", "medical_director", "owner"];

export function MitgliederContent({
  members,
  invitations,
  permissions,
  selfUserId,
  now,
}: {
  members: MemberOut[];
  invitations: StaffInvitationListItem[];
  permissions: RolePermissions[] | null;
  selfUserId: string;
  now: number;
}) {
  const router = useRouter();
  const { locale, t: messages } = useI18n();
  const t = messages.membersPage;
  const roleLabels: Record<string, string> = messages.roles;
  const roleName = (role: string) => roleLabels[role] ?? role;
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const run = (action: () => Promise<{ ok: boolean; error?: string }>) =>
    startTransition(async () => {
      setError(null);
      const res = await action();
      if (res.ok) router.refresh();
      else setError(res.error ?? null);
    });

  const changeRole = (m: MemberOut, newRole: string) => {
    if (newRole === m.role) return;
    const question = fill(t.roleConfirm, {
      name: m.display_name,
      from: roleName(m.role),
      to: roleName(newRole),
    });
    if (!window.confirm(question)) return;
    run(() => changeMemberRoleAction(m.membership_id, newRole));
  };

  const remove = (m: MemberOut) => {
    if (!window.confirm(fill(t.removeConfirm, { name: m.display_name })))
      return;
    run(() => removeMemberAction(m.membership_id));
  };

  const revoke = (id: string) => {
    if (!window.confirm(t.pending.revokeConfirm)) return;
    run(() => revokeStaffInviteAction(id));
  };

  const counts = ROLE_ORDER.map((role) => ({
    role,
    n: members.filter((m) => m.role === role).length,
  })).filter((c) => c.n > 0);
  const open = invitations.filter(
    (i) => i.status === "pending" && Date.parse(i.expires_at) > now,
  );

  return (
    <div className="vb-team">
      <div className="vb-ov-pagehead">
        <div style={{ minWidth: 0 }}>
          <span className="vb-ov-eyebrow">{t.eyebrow}</span>
          <h1 className="vb-ov-h1">{messages.settings.members.title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <button
          type="button"
          className="vb-ov-btn primary vb-team-invite"
          onClick={() => setInviting(true)}
        >
          {t.invite.open}
        </button>
      </div>

      {error && (
        <p role="alert" className="vb-team-error">
          {error}
        </p>
      )}

      <section className="vb-ov-card" aria-labelledby="team-members">
        <div className="vb-ov-head">
          <h2 id="team-members" className="vb-ov-h2">
            {t.team}{" "}
            <span className="vb-ov-mono" style={{ fontWeight: 400 }}>
              {members.length}
            </span>
          </h2>
          <div className="vb-team-counts">
            {counts.map((c) => (
              <span key={c.role} className="vb-ov-tag">
                {fill(t.roleCount, { role: roleName(c.role), n: c.n })}
              </span>
            ))}
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="vb-team-table">
            <thead>
              <tr>
                <th scope="col">{t.columns.person}</th>
                <th scope="col">{t.columns.role}</th>
                <th scope="col">{t.columns.lastActive}</th>
                <th scope="col">
                  <span className="sr-only">{t.columns.actions}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => {
                const isSelf = m.user_id === selfUserId;
                return (
                  <tr key={m.membership_id}>
                    <td>
                      <div className="vb-ov-pat">
                        <span className="vb-ov-av" aria-hidden="true">
                          {initialsOf(m.display_name)}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <b>
                            {m.display_name}
                            {isSelf && (
                              <span className="vb-team-me">{t.you}</span>
                            )}
                          </b>
                          <span>{m.email}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      {isSelf ? (
                        <span className="vb-ov-tag">{roleName(m.role)}</span>
                      ) : (
                        <select
                          className="vb-team-role"
                          aria-label={fill(t.roleOf, { name: m.display_name })}
                          value={m.role}
                          disabled={pending}
                          onChange={(e) => changeRole(m, e.target.value)}
                        >
                          {ROLE_ORDER.map((r) => (
                            <option key={r} value={r}>
                              {roleName(r)}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="vb-ov-mono">
                      {m.last_active_at
                        ? ago(m.last_active_at, now, messages.dashboard.time)
                        : t.never}
                    </td>
                    <td className="vb-team-actions">
                      {!isSelf && (
                        <RowMenu label={fill(t.more, { name: m.display_name })}>
                          <Link
                            href={`/einstellungen/audit?actor=${m.user_id}`}
                            prefetch={false}
                          >
                            {t.showInTrail}
                          </Link>
                          <button
                            type="button"
                            className="danger"
                            disabled={pending}
                            onClick={() => remove(m)}
                          >
                            {t.remove}
                          </button>
                        </RowMenu>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="vb-ov-note vb-team-note">{t.note}</p>
      </section>

      <section className="vb-ov-card" aria-labelledby="team-invitations">
        <div className="vb-ov-head">
          <h2 id="team-invitations" className="vb-ov-h2">
            {t.pending.title}{" "}
            <span className="vb-ov-mono" style={{ fontWeight: 400 }}>
              {open.length}
            </span>
          </h2>
        </div>
        <div className="vb-ov-body">
          {open.length === 0 ? (
            <p className="vb-ov-tier-empty" style={{ padding: 0 }}>
              {t.pending.none}
            </p>
          ) : (
            <ul className="vb-ov-srclist">
              {open.map((inv) => {
                const what = inv.label
                  ? `${roleName(inv.role)} · ${inv.label}`
                  : roleName(inv.role);
                return (
                  <li key={inv.invitation_id}>
                    <div>
                      <b>{roleName(inv.role)}</b>
                      {inv.label && <> · {inv.label}</>}
                      <small>
                        {inv.created_by
                          ? fill(t.pending.created, {
                              day: day(inv.created_at, locale),
                              name: inv.created_by.display_name,
                            })
                          : fill(t.pending.createdNoName, {
                              day: day(inv.created_at, locale),
                            })}
                      </small>
                      <small>
                        {fill(t.pending.expires, {
                          day: day(inv.expires_at, locale),
                        })}
                      </small>
                    </div>
                    <button
                      type="button"
                      className="vb-ov-btn"
                      disabled={pending}
                      aria-label={fill(t.pending.revokeOf, { what })}
                      onClick={() => revoke(inv.invitation_id)}
                    >
                      {t.pending.revoke}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <RoleMatrix permissions={permissions} />

      {inviting && (
        <InviteDialog
          onClose={() => {
            setInviting(false);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}

// "Was eine Rolle darf": the API's authorization matrix, a line per group of its actions.
function RoleMatrix({
  permissions,
}: {
  permissions: RolePermissions[] | null;
}) {
  const { t: messages } = useI18n();
  const t = messages.membersPage.matrix;
  const roles: Record<string, string> = messages.roles;
  return (
    <section className="vb-ov-card" aria-labelledby="team-matrix">
      <div className="vb-ov-head">
        <div>
          <h2 id="team-matrix" className="vb-ov-h2">
            {t.title}
          </h2>
          <p className="vb-ov-note">{t.note}</p>
        </div>
      </div>
      <div className="vb-ov-body" style={{ overflowX: "auto" }}>
        {permissions == null ? (
          <p className="vb-ov-unavailable">{t.unavailable}</p>
        ) : (
          <table className="vb-team-matrix">
            <caption className="sr-only">{t.caption}</caption>
            <thead>
              <tr>
                <th scope="col">{t.capability}</th>
                {MATRIX_ROLES.map((role) => (
                  <th key={role} scope="col">
                    {roles[role] ?? role}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {capabilityMatrix(permissions).map((row) => (
                <tr key={row.key}>
                  <th scope="row">{t.capabilities[row.key]}</th>
                  {row.allowed.map((yes, i) => (
                    <td key={MATRIX_ROLES[i]} data-allowed={yes}>
                      <span aria-hidden="true">{yes ? "✓" : "–"}</span>
                      <span className="sr-only">{yes ? t.yes : t.no}</span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// The "⋯" button of a row: a short list of what can be done with this member. Escape and a
// click elsewhere close it; Escape gives the focus back to the button.
function RowMenu({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    box.current
      ?.querySelector<HTMLElement>(".vb-team-menu a, .vb-team-menu button")
      ?.focus();
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return (
    <div className="vb-team-menuwrap" ref={box}>
      <button
        ref={button}
        type="button"
        className="vb-team-kebab"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">⋯</span>
      </button>
      {open && <div className="vb-team-menu">{children}</div>}
    </div>
  );
}

// Inviting a colleague: whom it is for (a label only), the role, then the link — shown once.
function InviteDialog({ onClose }: { onClose: () => void }) {
  const { t: messages } = useI18n();
  const t = messages.membersPage.invite;
  const roles: Record<string, string> = messages.roles;
  const [label, setLabel] = useState("");
  const [role, setRole] = useState("clinician");
  const [link, setLink] = useState<{ url: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const first = useRef<HTMLInputElement>(null);

  const create = () =>
    startTransition(async () => {
      setError(null);
      const res = await createStaffInviteAction(role, label);
      if (res.ok) setLink({ url: res.url, role: res.role });
      else setError(res.error);
    });

  return (
    <Dialog
      onClose={onClose}
      labelledBy="invite-title"
      describedBy="invite-note"
      initialFocusRef={first}
      backdropClassName="vb-team-backdrop"
      dialogClassName="vb-team-dialog"
    >
      <h2 id="invite-title" className="vb-ov-h2">
        {t.title}
      </h2>
      <p
        id="invite-note"
        className="vb-ov-note"
        style={{ margin: "4px 0 14px" }}
      >
        {t.note}
      </p>
      {link ? (
        <div className="vb-team-link">
          <p>
            {t.createdBefore} <strong>{roles[link.role] ?? link.role}</strong>{" "}
            {t.createdAfter} <strong>{t.once}</strong>.
          </p>
          <input
            readOnly
            value={link.url}
            onFocus={(e) => e.currentTarget.select()}
            aria-label={t.link}
          />
          <div className="vb-team-dialog-actions">
            <button
              type="button"
              className="vb-ov-btn primary"
              onClick={onClose}
            >
              {t.done}
            </button>
          </div>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <div className="vb-team-field">
            <label htmlFor="invite-label">{t.label}</label>
            <input
              id="invite-label"
              ref={first}
              type="text"
              maxLength={200}
              autoComplete="off"
              value={label}
              aria-describedby="invite-label-help"
              onChange={(e) => setLabel(e.target.value)}
            />
            <small id="invite-label-help">{t.labelHelp}</small>
          </div>
          <div className="vb-team-field">
            <label htmlFor="invite-role">{t.role}</label>
            <select
              id="invite-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLE_ORDER.map((r) => (
                <option key={r} value={r}>
                  {roles[r] ?? r}
                </option>
              ))}
            </select>
          </div>
          {error && (
            <p role="alert" className="vb-team-error">
              {error}
            </p>
          )}
          <div className="vb-team-dialog-actions">
            <button type="button" className="vb-ov-btn" onClick={onClose}>
              {t.cancel}
            </button>
            <button
              type="submit"
              className="vb-ov-btn primary"
              disabled={pending}
            >
              {t.create}
            </button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
