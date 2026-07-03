"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { signOut } from "@/app/login/actions";

import { Icon, type IconName } from "./Icon";
import { ToastProvider, useToast } from "./Toaster";

export type NavKey =
  | "overview"
  | "patients"
  | "imports"
  | "reports"
  | "rules"
  | "audit"
  | "settings";

const NOT_IMPLEMENTED = "Diese Ansicht ist im Prototyp noch nicht umgesetzt.";

function NavLink({
  icon,
  label,
  count,
  active,
  href,
}: {
  icon: IconName;
  label: string;
  count?: number;
  active?: boolean;
  href?: string;
}) {
  const toast = useToast();
  const content = (
    <>
      <Icon name={icon} />
      {label}
      {count != null && <span className="nav-count">{count}</span>}
    </>
  );
  if (active && href) {
    return (
      <Link className="nav-link" href={href} aria-current="page">
        {content}
      </Link>
    );
  }
  if (href) {
    return (
      <Link className="nav-link" href={href}>
        {content}
      </Link>
    );
  }
  return (
    <a
      className="nav-link"
      href="#"
      onClick={(e) => {
        e.preventDefault();
        toast(NOT_IMPLEMENTED);
      }}
    >
      {content}
    </a>
  );
}

function Sidebar({ active }: { active: NavKey }) {
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
          count={3}
          active={active === "overview"}
          href="/overview"
        />
        <NavLink
          icon="patients"
          label="Patienten"
          active={active === "patients"}
        />
        <NavLink
          icon="download"
          label="Importe"
          count={2}
          active={active === "imports"}
        />
        <NavLink
          icon="reports"
          label="Berichte"
          active={active === "reports"}
        />
      </nav>

      <div className="nav-label" style={{ marginTop: "12px" }}>
        Verwaltung
      </div>
      <nav className="nav">
        <NavLink icon="rules" label="Regeln" active={active === "rules"} />
        <NavLink
          icon="auditlog"
          label="Audit-Protokoll"
          active={active === "audit"}
        />
        <NavLink
          icon="settings"
          label="Einstellungen"
          active={active === "settings"}
        />
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-card">
        <strong>Pilotumgebung</strong>Synthetische Beispieldaten · keine reale
        Patientenversorgung
      </div>
      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">
          SJ
        </div>
        <div className="meta">
          <strong>Dr. Sarah Johnson</strong>
          <span>Clinician</span>
        </div>
      </div>
    </aside>
  );
}

function UserMenu() {
  const toast = useToast();
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
          <strong>Dr. Sarah Johnson</strong>
          <span>Clinician</span>
        </span>
        <span className="avatar" aria-hidden="true">
          SJ
        </span>
      </button>
      <div className={`menu${open ? "" : " hidden"}`} role="menu">
        <a
          href="#"
          role="menuitem"
          onClick={(e) => {
            e.preventDefault();
            toast(NOT_IMPLEMENTED);
          }}
        >
          <Icon name="account" />
          Konto
        </a>
        <a
          href="#"
          role="menuitem"
          onClick={(e) => {
            e.preventDefault();
            toast(NOT_IMPLEMENTED);
          }}
        >
          <Icon name="myAudit" />
          Mein Audit-Log
        </a>
        <div className="menu-sep" />
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

function Topbar({ breadcrumbs }: { breadcrumbs: ReactNode }) {
  const toast = useToast();
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
      <button
        className="clinic-switch"
        type="button"
        onClick={() =>
          toast("Der Klinikwechsel ist im Prototyp nur visuell dargestellt.")
        }
      >
        <Icon name="building" />
        <span>Meridian Longevity</span>
        <Icon name="chevronDown" style={{ width: "14px", height: "14px" }} />
      </button>
      <button
        className="icon-btn"
        type="button"
        aria-label="Benachrichtigungen"
        onClick={() =>
          toast("Keine weiteren Benachrichtigungen in diesem Prototyp.")
        }
      >
        <Icon name="bell" />
      </button>
      <UserMenu />
    </header>
  );
}

export function AppShell({
  active,
  breadcrumbs,
  children,
}: {
  active: NavKey;
  breadcrumbs: ReactNode;
  children: ReactNode;
}) {
  return (
    <ToastProvider>
      <a className="skip-link" href="#main-content">
        Zum Hauptinhalt springen
      </a>
      <div className="app-shell">
        <Sidebar active={active} />
        <div className="app-main">
          <Topbar breadcrumbs={breadcrumbs} />
          <main className="content" id="main-content">
            {children}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
