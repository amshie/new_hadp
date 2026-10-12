"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { signOut } from "@/app/login/actions";
import { initialsOf, type ShellIdentity } from "@/lib/identity";

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
  return (
    <aside className="sidebar" aria-label="Hauptnavigation">
      <Link className="brand" href="/overview" aria-label="HADP Übersicht">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-copy">
          <strong>HADP</strong>
          <small>Health Analytics</small>
        </span>
      </Link>

      <div className="nav-label">Arbeitsbereich</div>
      <nav className="nav">
        <NavLink
          icon="overview"
          label="Übersicht"
          active={active === "overview"}
          href="/overview"
        />
        <NavLink
          icon="patients"
          label="Patienten"
          active={active === "patients"}
          href="/patients"
        />
        <NavLink
          icon="check"
          label="Review-Queue"
          active={active === "review"}
          href="/review-queue"
        />
      </nav>

      <div className="nav-label" style={{ marginTop: "12px" }}>
        Verwaltung
      </div>
      <nav className="nav">
        <NavLink
          icon="settings"
          label="Einstellungen"
          active={active === "settings"}
          href="/einstellungen"
        />
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-card">
        <strong>Pilotumgebung</strong>Synthetische Beispieldaten · keine reale
        Patientenversorgung
      </div>
      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">
          {initialsOf(identity?.name ?? "—")}
        </div>
        <div className="meta">
          <strong>{identity?.name ?? "—"}</strong>
          <span>{identity?.roleLabel ?? "—"}</span>
        </div>
      </div>
    </aside>
  );
}

// Who is signed in, and the way out. Sign-out is the only account action that exists, so it
// is a button — not a menu with one entry.
function TopbarUser({ identity }: { identity?: ShellIdentity | null }) {
  return (
    <div className="topbar-user">
      <span className="user-copy">
        <strong>{identity?.name ?? "—"}</strong>
        <span>{identity?.roleLabel ?? "—"}</span>
      </span>
      <span className="avatar" aria-hidden="true">
        {initialsOf(identity?.name ?? "—")}
      </span>
      <form action={signOut}>
        <button className="btn btn-secondary btn-sm" type="submit">
          <Icon name="logout" />
          Abmelden
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
  return (
    <header className="topbar">
      <Link
        className="brand mobile-brand"
        href="/overview"
        aria-label="HADP Übersicht"
      >
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-copy">
          <strong style={{ color: "var(--ink)" }}>HADP</strong>
          <small>Health Analytics</small>
        </span>
      </Link>
      {breadcrumbs}
      <div className="topbar-spacer" />
      <div className="clinic-name">
        <Icon name="building" />
        <span className="sr-only">Mandant: </span>
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
  return (
    <ToastProvider>
      <a className="skip-link" href="#main-content">
        Zum Hauptinhalt springen
      </a>
      <div className="app-shell">
        <Sidebar active={active} identity={identity} />
        <div className="app-main">
          <Topbar breadcrumbs={breadcrumbs} identity={identity} />
          <main className="content" id="main-content">
            {children}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
