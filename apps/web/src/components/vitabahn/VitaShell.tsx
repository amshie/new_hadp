"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type ReactNode } from "react";

// VitaBahn dashboard shell (ADR-0005): sidebar + topbar + theme toggle, a faithful
// port of the Claude Design comp's chrome. Wraps the /overview, /patients and
// /patients/[id] screens. Synthetic Alpha only.

type NavKey = "uebersicht" | "patienten";

const THEME_KEY = "vb-theme";

function NavItem({
  active,
  onClick,
  icon,
  label,
  trailing,
  implemented = true,
}: {
  active?: boolean;
  onClick?: () => void;
  icon: ReactNode;
  label: string;
  trailing?: ReactNode;
  implemented?: boolean;
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
    border: "none",
    cursor: "pointer",
    textAlign: "left",
    fontFamily: "var(--font-text)",
    fontSize: "var(--text-sm)",
    fontWeight: active ? 600 : 500,
    background: active ? "rgba(37,199,156,0.12)" : "transparent",
    color: active ? "#fff" : "var(--slate-300)",
  };
  return (
    <button
      type="button"
      className="vb-nav"
      onClick={onClick}
      style={style}
      title={implemented ? undefined : "Im Prototyp noch nicht umgesetzt"}
      aria-current={active ? "page" : undefined}
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
      {trailing}
    </button>
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
  children,
}: {
  nav: NavKey;
  crumb: string;
  crumbParent?: { label: string; href: string };
  children: ReactNode;
}) {
  const router = useRouter();
  // Lazy-init from localStorage so a returning dark-mode user doesn't get a light flash on
  // client navigations. SSR has no localStorage and renders light; suppressHydrationWarning on
  // the root covers the intentional server/client data-theme difference.
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem(THEME_KEY) === "dark";
    } catch {
      return false;
    }
  });

  const toggleTheme = () => {
    setDark((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(THEME_KEY, next ? "dark" : "light");
      } catch {
        /* ignore */
      }
      return next;
    });
  };

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
      suppressHydrationWarning
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
        aria-label="Hauptnavigation"
        style={{
          width: "256px",
          flexShrink: 0,
          background: "var(--slate-900)",
          display: "flex",
          flexDirection: "column",
          position: "sticky",
          top: 0,
          height: "100vh",
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
        </div>

        <nav style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
          <div style={navLabelStyle()}>Arbeitsbereich</div>

          <NavItem
            active={nav === "uebersicht"}
            onClick={() => router.push("/overview")}
            icon={stroke(
              <>
                <rect x="3" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" />
              </>,
              { width: 1.8 },
            )}
            label="Übersicht"
          />
          <NavItem
            active={nav === "patienten"}
            onClick={() => router.push("/patients")}
            icon={stroke(
              <>
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </>,
            )}
            label="Patienten"
          />
          <NavItem
            implemented={false}
            icon={stroke(
              <>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M7 10l5 5 5-5" />
                <path d="M12 15V3" />
              </>,
            )}
            label="Importe"
          />
          <NavItem
            implemented={false}
            icon={stroke(
              <>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
                <path d="M8 13h8" />
                <path d="M8 17h6" />
              </>,
            )}
            label="Berichte"
          />

          <div style={navLabelStyle("6px")}>Verwaltung</div>
          <NavItem
            implemented={false}
            icon={stroke(
              <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />,
            )}
            label="Regeln"
          />
          <NavItem
            implemented={false}
            icon={stroke(
              <>
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M9 12l2 2 4-4" />
              </>,
            )}
            label="Audit-Protokoll"
          />
          <NavItem
            implemented={false}
            icon={stroke(
              <>
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </>,
            )}
            label="Einstellungen"
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
                Pilotumgebung
              </span>
            </div>
            <div
              style={{
                fontSize: "11.5px",
                lineHeight: 1.45,
                color: "var(--slate-400)",
              }}
            >
              Synthetische Beispieldaten · keine reale Patientenversorgung.
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
              SJ
            </div>
            <div style={{ flex: 1, lineHeight: 1.2 }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#fff" }}>
                Dr. Sarah Johnson
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--slate-500)",
                  letterSpacing: "0.04em",
                }}
              >
                Clinician
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ============ MAIN ============ */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header
          style={{
            position: "sticky",
            top: 0,
            zIndex: 20,
            height: "62px",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 32px",
            background: "color-mix(in srgb, var(--bg-page) 86%, transparent)",
            backdropFilter: "blur(10px)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <div
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
            <span style={{ color: "var(--text-faint)" }}>Arbeitsbereich</span>
            <span style={{ color: "var(--text-faint)" }}>/</span>
            {crumbParent && (
              <>
                <Link
                  href={crumbParent.href}
                  className="vb-crumblink"
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
            <span style={{ color: "var(--text-strong)", fontWeight: 600 }}>
              {crumb}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              type="button"
              className="vb-iconbtn"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "9px",
                height: "38px",
                padding: "0 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--surface-card)",
                cursor: "pointer",
                color: "var(--text-body)",
                fontFamily: "var(--font-text)",
              }}
            >
              <svg
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
              <span
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--text-strong)",
                  whiteSpace: "nowrap",
                }}
              >
                Meridian Longevity
              </span>
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "999px",
                  background: "var(--vital-400)",
                  margin: "0 1px",
                }}
              />
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--text-faint)"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Theme wechseln"
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

            <button
              type="button"
              aria-label="Benachrichtigungen"
              className="vb-iconbtn"
              style={{
                position: "relative",
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
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--text-muted)"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              <span
                style={{
                  position: "absolute",
                  top: "8px",
                  right: "9px",
                  width: "7px",
                  height: "7px",
                  borderRadius: "999px",
                  background: "var(--rose-400)",
                  border: "1.5px solid var(--surface-card)",
                }}
              />
            </button>

            <div
              style={{
                width: "1px",
                height: "26px",
                background: "var(--border-subtle)",
                margin: "0 2px",
              }}
            />

            <div
              className="vb-userchip"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "4px 6px 4px 4px",
                borderRadius: "var(--radius-pill)",
                cursor: "pointer",
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
                SJ
              </div>
              <div style={{ lineHeight: 1.2, paddingRight: "4px" }}>
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                  }}
                >
                  Dr. Sarah Johnson
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    color: "var(--text-faint)",
                    letterSpacing: "0.04em",
                  }}
                >
                  Clinician
                </div>
              </div>
            </div>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: "auto" }}>
          <div
            style={{
              maxWidth: "1340px",
              margin: "0 auto",
              padding: "30px 32px 56px",
            }}
          >
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
