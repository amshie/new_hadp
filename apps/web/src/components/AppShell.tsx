"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

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

function UserMenu({ identity }: { identity?: ShellIdentity | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="user-menu" ref={ref}>
      <button
        className="user-menu-button"
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="user-copy">
          <strong>{identity?.name ?? "—"}</strong>
          <span>{identity?.roleLabel ?? "—"}</span>
        </span>
        <span className="avatar" aria-hidden="true">
          {initialsOf(identity?.name ?? "—")}
        </span>
      </button>
      <div className={`menu${open ? "" : " hidden"}`} role="menu">
        <form action={signOut} role="none">
          <button className="danger" role="menuitem" type="submit">
            <Icon name="logout" />
            Abmelden
          </button>
        </form>
      </div>
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
      <UserMenu identity={identity} />
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
