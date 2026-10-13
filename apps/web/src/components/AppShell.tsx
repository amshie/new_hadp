"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { signOut } from "@/app/login/actions";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { initialsOf, roleName, type ShellIdentity } from "@/lib/identity";

import { Icon, type IconName } from "./Icon";
import { ToastProvider } from "./Toaster";

// The same four destinations as the dashboard shell (VitaShell): every entry leads somewhere.
export type NavKey = "overview" | "patients" | "review" | "settings";

function NavLink({
  icon,
  label,
  active,
  href,
}: {
  icon: IconName;
  label: string;
  active?: boolean;
  href: string;
}) {
  return (
    <Link
      className="nav-link"
      href={href}
      aria-current={active ? "page" : undefined}
    >
      <Icon name={icon} />
      {label}
    </Link>
  );
}

function Sidebar({
  active,
  identity,
}: {
  active: NavKey;
  identity?: ShellIdentity | null;
}) {
  const { t } = useI18n();
  return (
    <aside className="sidebar" aria-label={t.shell.navAria}>
      <Link className="brand" href="/overview" aria-label={t.shell.brandAria}>
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-copy">
          <strong>HADP</strong>
          <small>Health Analytics</small>
        </span>
      </Link>

      <div className="nav-label">{t.shell.workspace}</div>
      <nav className="nav">
        <NavLink
          icon="overview"
          label={t.shell.overview}
          active={active === "overview"}
          href="/overview"
        />
        <NavLink
          icon="patients"
          label={t.shell.patients}
          active={active === "patients"}
          href="/patients"
        />
        <NavLink
          icon="check"
          label={t.shell.reviewQueue}
          active={active === "review"}
          href="/review-queue"
        />
      </nav>

      <div className="nav-label" style={{ marginTop: "12px" }}>
        {t.shell.administration}
      </div>
      <nav className="nav">
        <NavLink
          icon="settings"
          label={t.shell.settings}
          active={active === "settings"}
          href="/einstellungen"
        />
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-card">
        <strong>{t.shell.pilot}</strong>
        {t.shell.pilotNote}
      </div>
      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">
          {initialsOf(identity?.name ?? "—")}
        </div>
        <div className="meta">
          <strong>{identity?.name ?? "—"}</strong>
          <span>{roleName(t.roles, identity?.role)}</span>
        </div>
      </div>
    </aside>
  );
}

// Who is signed in, and the way out. Sign-out is the only account action that exists, so it
// is a button — not a menu with one entry.
function TopbarUser({ identity }: { identity?: ShellIdentity | null }) {
  const { t } = useI18n();
  return (
    <div className="topbar-user">
      <span className="user-copy">
        <strong>{identity?.name ?? "—"}</strong>
        <span>{roleName(t.roles, identity?.role)}</span>
      </span>
      <span className="avatar" aria-hidden="true">
        {initialsOf(identity?.name ?? "—")}
      </span>
      <form action={signOut}>
        <button className="btn btn-secondary btn-sm" type="submit">
          <Icon name="logout" />
          {t.shell.signOut}
        </button>
      </form>
    </div>
  );
}

function Topbar({
  breadcrumbs,
  identity,
}: {
  breadcrumbs: ReactNode;
  identity?: ShellIdentity | null;
}) {
  const { t } = useI18n();
  return (
    <header className="topbar">
      <Link
        className="brand mobile-brand"
        href="/overview"
        aria-label={t.shell.brandAria}
      >
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-copy">
          <strong style={{ color: "var(--ink)" }}>HADP</strong>
          <small>Health Analytics</small>
        </span>
      </Link>
      {/* Named by the page inside, which is not translated yet. */}
      <div lang="de" style={{ display: "contents" }}>
        {breadcrumbs}
      </div>
      <div className="topbar-spacer" />
      <div className="clinic-name">
        <Icon name="building" />
        <span className="sr-only">{t.shell.clinic}</span>
        <span>{identity?.tenantName ?? "—"}</span>
      </div>
      <TopbarUser identity={identity} />
    </header>
  );
}

export function AppShell({
  active,
  breadcrumbs,
  identity,
  children,
}: {
  active: NavKey;
  breadcrumbs: ReactNode;
  identity?: ShellIdentity | null;
  children: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <ToastProvider>
      <a className="skip-link" href="#main-content">
        {t.shell.skipLink}
      </a>
      <div className="app-shell">
        <Sidebar active={active} identity={identity} />
        <div className="app-main">
          <Topbar breadcrumbs={breadcrumbs} identity={identity} />
          {/* The page inside this shell is still German (lib/i18n: page by page). */}
          <main className="content" id="main-content" lang="de">
            {children}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
