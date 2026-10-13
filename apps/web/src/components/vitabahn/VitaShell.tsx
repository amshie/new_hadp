"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

import { signOut } from "@/app/login/actions";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { initialsOf, roleName, type ShellIdentity } from "@/lib/identity";

import { chooseTheme, useDarkTheme } from "./theme";

// VitaBahn dashboard shell (ADR-0005): sidebar + topbar + theme toggle, a faithful
// port of the Claude Design comp's chrome. Wraps the /overview, /patients and
// /patients/[id] screens. Synthetic Alpha only.
//
// The comp is a desktop layout. On a narrow screen (styles/vitabahn.css, NARROW below) the
// sidebar leaves the row and becomes a drawer the topbar's menu button opens; the page then
// has the whole width.

type NavKey = "uebersicht" | "patienten" | "review" | "einstellungen";

// The width at which the sidebar becomes a drawer — the same as in styles/vitabahn.css.
const NARROW = "(max-width: 900px)";

// A navigation entry is a link to a page that exists — nothing else is listed.
function NavItem({
  active,
  href,
  icon,
  label,
  onNavigate,
}: {
  active?: boolean;
  href: string;
  icon: ReactNode;
  label: string;
  onNavigate: () => void;
}) {
  const style: CSSProperties = {
    position: "relative",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    width: "100%",
    padding: "10px 12px",
    marginBottom: "2px",
    borderRadius: "var(--radius-sm)",
    textDecoration: "none",
    fontFamily: "var(--font-text)",
    fontSize: "var(--text-sm)",
    fontWeight: active ? 600 : 500,
    background: active ? "rgba(37,199,156,0.12)" : "transparent",
    color: active ? "#fff" : "var(--slate-300)",
  };
  return (
    <Link
      href={href}
      className="vb-nav"
      style={style}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
    >
      {active && (
        <span
          style={{
            position: "absolute",
            left: "-12px",
            top: "9px",
            bottom: "9px",
            width: "3px",
            borderRadius: "0 3px 3px 0",
            background: "var(--vital-400)",
          }}
        />
      )}
      {icon}
      <span style={{ flex: 1 }}>{label}</span>
    </Link>
  );
}

function navLabelStyle(marginTop?: string): CSSProperties {
  return {
    fontFamily: "var(--font-mono)",
    fontSize: "10px",
    letterSpacing: "0.16em",
    textTransform: "uppercase",
    color: "var(--slate-500)",
    padding: "14px 10px 8px",
    marginTop,
  };
}

export function VitaShell({
  nav,
  crumb,
  crumbParent,
  identity,
  translated = false,
  children,
}: {
  nav: NavKey;
  crumb: string;
  crumbParent?: { label: string; href: string };
  identity?: ShellIdentity | null;
  // Whether the page inside (and the crumbs it names) follows the interface language. The
  // pages are translated one after another: until a page is, what it shows is German, and
  // says so — a screen reader would otherwise read German with another language's sounds.
  translated?: boolean;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const personName = identity?.name ?? "—";
  const personRole = roleName(t.roles, identity?.role);
  const contentLang = translated ? undefined : "de";
  const clinicName = identity?.tenantName ?? "—";
  const personInitials = initialsOf(personName);
  const dark = useDarkTheme();

  // The drawer on a narrow screen. Escape and its close button give the focus back to the
  // button that opened it — once it is closed, as the page behind is inert until then.
  // Growing past the narrow width closes it too, so the page behind it is never left inert
  // beside a sidebar that is back in the row.
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const refocusMenuButton = useRef(false);
  const closeMenu = () => setMenuOpen(false);
  const dismissMenu = () => {
    refocusMenuButton.current = true;
    setMenuOpen(false);
  };

  useEffect(() => {
    if (!menuOpen) {
      if (refocusMenuButton.current) menuButton.current?.focus();
      refocusMenuButton.current = false;
      return;
    }
    closeButton.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") dismissMenu();
    };
    const narrow = window.matchMedia(NARROW);
    const onWidth = () => {
      if (!narrow.matches) setMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    narrow.addEventListener("change", onWidth);
    return () => {
      document.removeEventListener("keydown", onKey);
      narrow.removeEventListener("change", onWidth);
    };
  }, [menuOpen]);

  const toggleTheme = () => chooseTheme(!dark);

  const stroke = (
    d: ReactNode,
    { size = 19, width = 1.7 }: { size?: number; width?: number } = {},
  ) => (
    <svg
      aria-hidden="true"
      focusable="false"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {d}
    </svg>
  );

  return (
    <div
      className="vb-scope"
      data-theme={dark ? "dark" : "light"}
      style={{
        display: "flex",
        minHeight: "100vh",
        width: "100%",
        background: "var(--bg-page)",
        color: "var(--text-body)",
        fontFamily: "var(--font-text)",
        WebkitFontSmoothing: "antialiased",
      }}
    >
      {/* ============ SIDEBAR ============ */}
      <aside
        id="vb-sidebar"
        className="vb-sidebar"
        data-open={menuOpen}
        aria-label={t.shell.navAria}
        style={{
          background: "var(--slate-900)",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div
          style={{
            padding: "22px 20px 18px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "var(--radius-md)",
              background:
                "linear-gradient(150deg, var(--teal-500), var(--teal-700))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 12px rgba(9,50,45,0.5)",
            }}
          >
            <svg width="24" height="24" viewBox="0 0 64 64" fill="none">
              <path
                d="M13 22 L30 53 L55 9"
                stroke="#fff"
                strokeWidth="6.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="55" cy="9" r="5" fill="var(--vital-300)" />
            </svg>
          </div>
          <div style={{ lineHeight: 1.1 }}>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 800,
                fontSize: "18px",
                letterSpacing: "-0.01em",
                color: "#fff",
              }}
            >
              HADP
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "9.5px",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "var(--slate-400)",
                marginTop: "3px",
              }}
            >
              Health Analytics
            </div>
          </div>
          <button
            ref={closeButton}
            type="button"
            className="vb-menuclose"
            onClick={dismissMenu}
            aria-label={t.shell.closeMenu}
          >
            {stroke(<path d="M18 6 6 18M6 6l12 12" />, { size: 18 })}
          </button>
        </div>

        <nav style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
          <div style={navLabelStyle()}>{t.shell.workspace}</div>

          <NavItem
            active={nav === "uebersicht"}
            onNavigate={closeMenu}
            href="/overview"
            icon={stroke(
              <>
                <rect x="3" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" />
              </>,
              { width: 1.8 },
            )}
            label={t.shell.overview}
          />
          <NavItem
            active={nav === "patienten"}
            onNavigate={closeMenu}
            href="/patients"
            icon={stroke(
              <>
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </>,
            )}
            label={t.shell.patients}
          />
          <NavItem
            active={nav === "review"}
            onNavigate={closeMenu}
            href="/review-queue"
            icon={stroke(
              <>
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </>,
            )}
            label={t.shell.reviewQueue}
          />

          <div style={navLabelStyle("6px")}>{t.shell.administration}</div>
          <NavItem
            active={nav === "einstellungen"}
            onNavigate={closeMenu}
            href="/einstellungen"
            icon={stroke(
              <>
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </>,
            )}
            label={t.shell.settings}
          />
        </nav>

        <div style={{ padding: "12px" }}>
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.03)",
              borderRadius: "var(--radius-md)",
              padding: "12px 14px",
              marginBottom: "10px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "7px",
                marginBottom: "6px",
              }}
            >
              <span
                style={{
                  width: "7px",
                  height: "7px",
                  borderRadius: "999px",
                  background: "var(--amber-400)",
                  animation: "vb-pulse 2.4s ease-in-out infinite",
                }}
              />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--amber-400)",
                  fontWeight: 600,
                }}
              >
                {t.shell.pilot}
              </span>
            </div>
            <div
              style={{
                fontSize: "11.5px",
                lineHeight: 1.45,
                color: "var(--slate-400)",
              }}
            >
              {t.shell.pilotNote}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "11px",
              padding: "8px 6px 4px",
              borderTop: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "999px",
                background:
                  "linear-gradient(145deg, var(--teal-400), var(--teal-600))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
                fontSize: "12px",
                color: "#fff",
              }}
            >
              {personInitials}
            </div>
            <div style={{ flex: 1, lineHeight: 1.2 }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#fff" }}>
                {personName}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--slate-500)",
                  letterSpacing: "0.04em",
                }}
              >
                {personRole}
              </div>
            </div>
            <form action={signOut}>
              <button
                type="submit"
                style={{
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: "8px",
                  background: "transparent",
                  color: "var(--slate-400)",
                  fontSize: "11px",
                  padding: "5px 8px",
                  cursor: "pointer",
                }}
              >
                {t.shell.signOut}
              </button>
            </form>
          </div>
        </div>
      </aside>
      {menuOpen && (
        <div className="vb-backdrop" aria-hidden="true" onClick={closeMenu} />
      )}

      {/* ============ MAIN ============ */}
      <div
        inert={menuOpen}
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header
          className="vb-topbar"
          style={{
            position: "sticky",
            top: 0,
            zIndex: 20,
            height: "62px",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "color-mix(in srgb, var(--bg-page) 86%, transparent)",
            backdropFilter: "blur(10px)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <button
            ref={menuButton}
            type="button"
            className="vb-menubtn vb-iconbtn"
            onClick={() => setMenuOpen(true)}
            aria-label={t.shell.menu}
            aria-controls="vb-sidebar"
            aria-expanded={menuOpen}
          >
            {stroke(<path d="M4 7h16M4 12h16M4 17h16" />, { size: 18 })}
          </button>
          <div
            className="vb-crumbs"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "9px",
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              letterSpacing: "0.03em",
              whiteSpace: "nowrap",
            }}
          >
            <span
              className="vb-crumb-root"
              style={{ color: "var(--text-faint)" }}
            >
              {t.shell.workspace}
            </span>
            <span
              className="vb-crumb-root"
              style={{ color: "var(--text-faint)" }}
            >
              /
            </span>
            {crumbParent && (
              <>
                <Link
                  href={crumbParent.href}
                  className="vb-crumblink vb-crumb-parent"
                  lang={contentLang}
                  style={{
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    textDecoration: "none",
                  }}
                >
                  {crumbParent.label}
                </Link>
                <span style={{ color: "var(--text-faint)", margin: "0 2px" }}>
                  /
                </span>
              </>
            )}
            <span
              lang={contentLang}
              className="vb-crumb-current"
              style={{ color: "var(--text-strong)", fontWeight: 600 }}
            >
              {crumb}
            </span>
          </div>

          <div className="vb-topbar-tools">
            <div
              className="vb-clinic"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "9px",
                height: "38px",
                padding: "0 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--surface-card)",
                color: "var(--text-body)",
                fontFamily: "var(--font-text)",
              }}
            >
              <svg
                aria-hidden="true"
                focusable="false"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--brand)"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z" />
                <path d="M2 21c0-3 1.85-5.36 5.08-6" />
              </svg>
              <span className="sr-only">{t.shell.clinic}</span>
              <span
                className="vb-clinic-name"
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--text-strong)",
                  whiteSpace: "nowrap",
                }}
              >
                {clinicName}
              </span>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label={t.shell.toggleTheme}
              className="vb-iconbtn"
              style={{
                width: "38px",
                height: "38px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--surface-card)",
                cursor: "pointer",
              }}
            >
              {dark ? (
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--vital-300)"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
                </svg>
              ) : (
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--slate-600)"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>

            <div
              className="vb-topbar-divider"
              style={{
                width: "1px",
                height: "26px",
                background: "var(--border-subtle)",
                margin: "0 2px",
              }}
            />

            <div
              className="vb-topbar-person"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "4px 6px 4px 4px",
                borderRadius: "var(--radius-pill)",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "999px",
                  background:
                    "linear-gradient(145deg, var(--teal-400), var(--teal-600))",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  fontSize: "12px",
                  color: "#fff",
                }}
              >
                {personInitials}
              </div>
              <div style={{ lineHeight: 1.2, paddingRight: "4px" }}>
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                  }}
                >
                  {personName}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    color: "var(--text-faint)",
                    letterSpacing: "0.04em",
                  }}
                >
                  {personRole}
                </div>
              </div>
            </div>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: "auto" }}>
          <div
            lang={contentLang}
            className="vb-content"
            style={{
              maxWidth: "1340px",
              margin: "0 auto",
            }}
          >
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
