"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { clickable } from "@/components/vitabahn/interactive";
import {
  ATTN_META,
  PATIENTS,
  PATIENT_COHORT,
  PATIENT_STATUS_META,
  initials,
  type PatientStatus,
} from "@/lib/demo/dashboard";

// VitaBahn Patienten directory (ADR-0005). Synthetic Alpha. The Risiko indicator
// and the per-row Datenqualität percentage are founder-approved surfaces (ADR-0005).

const PGRID =
  "minmax(210px,2fr) 80px minmax(150px,1.3fr) 104px minmax(140px,1.1fr) minmax(170px,1.4fr) 116px";

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};
const colLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "10px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};

function qColor(q: number) {
  return q >= 90
    ? "var(--vital-500)"
    : q >= 70
      ? "var(--amber-500)"
      : "var(--rose-500)";
}

const TABS: { key: "alle" | PatientStatus; label: string }[] = [
  { key: "alle", label: "Alle" },
  { key: "aktiv", label: "Aktiv" },
  { key: "onboarding", label: "Onboarding" },
  { key: "pausiert", label: "Pausiert" },
  { key: "archiviert", label: "Archiviert" },
];

const upArrow = (
  <svg
    width="11"
    height="11"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M7 17L17 7M9 7h8v8" />
  </svg>
);

interface Chip {
  label: string;
  value: ReactNode;
  delta: ReactNode;
  help: string;
  iconBg: string;
  icon: ReactNode;
}
const CHIPS: Chip[] = [
  {
    label: "Gesamt",
    value: "148",
    delta: (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "3px",
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--vital-500)",
          paddingBottom: "4px",
        }}
      >
        {upArrow}+6 · 30T
      </span>
    ),
    help: "Im Mandanten · RLS-geschützt",
    iconBg: "var(--brand-soft)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--teal-600)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    label: "Aktiv betreut",
    value: "132",
    delta: (
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--text-muted)",
          paddingBottom: "4px",
        }}
      >
        89%
      </span>
    ),
    help: "Laufende Programme",
    iconBg: "rgba(20,169,130,0.12)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--vital-500)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
  {
    label: "Offene Assessments",
    value: "7",
    delta: (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "3px",
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--amber-500)",
          paddingBottom: "4px",
        }}
      >
        {upArrow}+3
      </span>
    ),
    help: "Prüfung ausstehend",
    iconBg: "rgba(201,136,28,0.12)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--amber-500)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    label: "Ø Datenqualität",
    value: (
      <>
        94
        <span style={{ fontSize: "18px", color: "var(--text-muted)" }}>%</span>
      </>
    ),
    delta: (
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--vital-500)",
          paddingBottom: "4px",
        }}
      >
        verifiziert
      </span>
    ),
    help: "Über alle Beobachtungen",
    iconBg: "var(--brand-soft)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--teal-600)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
  },
];

export function PatientsContent() {
  const router = useRouter();
  const [pTab, setPTab] = useState<"alle" | PatientStatus>("alle");
  const [term, setTerm] = useState("");

  const visible = useMemo(() => {
    const byTab =
      pTab === "alle" ? PATIENTS : PATIENTS.filter((p) => p.status === pTab);
    const q = term.toLowerCase();
    return byTab.filter((p) =>
      `${p.name} ${p.id} ${p.program}`.toLowerCase().includes(q),
    );
  }, [pTab, term]);

  const tabBtn = (active: boolean): CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "7px",
    padding: "7px 13px",
    borderRadius: "var(--radius-pill)",
    fontFamily: "var(--font-text)",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
    border: "1px solid " + (active ? "var(--brand-border)" : "transparent"),
    background: active ? "var(--brand-soft)" : "transparent",
    color: active ? "var(--brand)" : "var(--text-muted)",
  });
  const tabBadge = (active: boolean): CSSProperties => ({
    fontFamily: "var(--font-mono)",
    fontSize: "10.5px",
    fontWeight: 600,
    padding: "1px 7px",
    borderRadius: "var(--radius-pill)",
    background: active ? "var(--brand)" : "var(--surface-sunken)",
    color: active ? "var(--text-on-brand)" : "var(--text-muted)",
  });

  return (
    <>
      {/* header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "24px",
          flexWrap: "wrap",
          marginBottom: "28px",
        }}
      >
        <div style={{ minWidth: "280px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--brand)",
              fontWeight: 500,
              marginBottom: "10px",
            }}
          >
            Mandant · Meridian Longevity
          </div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-3xl)",
              letterSpacing: "var(--tracking-tight)",
              color: "var(--text-strong)",
              margin: "0 0 10px",
              lineHeight: 1.05,
            }}
          >
            Patienten
          </h1>
          <p
            style={{
              fontSize: "var(--text-md)",
              lineHeight: 1.5,
              color: "var(--text-muted)",
              margin: 0,
              maxWidth: "64ch",
            }}
          >
            <span style={{ color: "var(--text-strong)", fontWeight: 600 }}>
              148 Patienten
            </span>{" "}
            · tenant-bezogen, RLS-geschützt · pseudonymisierte, synthetische
            Beispieldaten.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexShrink: 0 }}>
          <button
            type="button"
            className="vb-btn-sec"
            title="Im Prototyp noch nicht umgesetzt"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "42px",
              padding: "0 16px",
              whiteSpace: "nowrap",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-card)",
              color: "var(--text-strong)",
              fontFamily: "var(--font-text)",
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
            Daten importieren
          </button>
          <button
            type="button"
            className="vb-btn-pri"
            title="Im Prototyp noch nicht umgesetzt"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "42px",
              padding: "0 18px",
              whiteSpace: "nowrap",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--brand)",
              background: "var(--brand)",
              color: "var(--text-on-brand)",
              fontFamily: "var(--font-text)",
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 1px 2px rgba(12,18,20,0.12)",
            }}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
            Patient hinzufügen
          </button>
        </div>
      </div>

      {/* stat chips */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(212px, 1fr))",
          gap: "16px",
          marginBottom: "16px",
        }}
      >
        {CHIPS.map((c) => (
          <div key={c.label} style={{ ...cardStyle, padding: "18px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "14px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10.5px",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  fontWeight: 500,
                }}
              >
                {c.label}
              </span>
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "var(--radius-sm)",
                  background: c.iconBg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {c.icon}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "9px",
                marginBottom: "6px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "34px",
                  lineHeight: 1,
                  color: "var(--text-strong)",
                  letterSpacing: "-0.02em",
                }}
              >
                {c.value}
              </span>
              {c.delta}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {c.help}
            </div>
          </div>
        ))}
      </div>

      {/* directory */}
      <div style={{ ...cardStyle, overflow: "hidden" }}>
        <div style={{ padding: "20px 22px 0" }}>
          <h3
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-lg)",
              color: "var(--text-strong)",
              margin: "0 0 3px",
              letterSpacing: "-0.01em",
            }}
          >
            Patientenverzeichnis
          </h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: "0 0 16px",
            }}
          >
            Pseudonymisiert · keine automatische Diagnose oder
            Therapieempfehlung.
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              flexWrap: "wrap",
              marginBottom: "4px",
            }}
          >
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {TABS.map((t) => {
                const active = pTab === t.key;
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setPTab(t.key)}
                    style={tabBtn(active)}
                  >
                    {t.label}{" "}
                    <span style={tabBadge(active)}>
                      {PATIENT_COHORT[t.key]}
                    </span>
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <svg
                  aria-hidden="true"
                  focusable="false"
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--text-faint)"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{
                    position: "absolute",
                    left: "11px",
                    pointerEvents: "none",
                  }}
                >
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <input
                  className="vb-input"
                  type="text"
                  aria-label="Patient oder ID suchen"
                  value={term}
                  onChange={(e) => setTerm(e.target.value)}
                  placeholder="Patient oder ID suchen"
                  style={{
                    height: "36px",
                    width: "220px",
                    padding: "0 12px 0 33px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    background: "var(--surface-sunken)",
                    color: "var(--text-strong)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>
              <button
                type="button"
                aria-label="Filter"
                className="vb-iconbtn"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "7px",
                  height: "36px",
                  padding: "0 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--surface-card)",
                  cursor: "pointer",
                  color: "var(--text-body)",
                  fontFamily: "var(--font-text)",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M22 3H2l8 9.46V19l4 2v-8.54z" />
                </svg>
                Filter
              </button>
            </div>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <div style={{ minWidth: "1180px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: PGRID,
                alignItems: "center",
                gap: "16px",
                padding: "14px 22px 10px",
                borderBottom: "1px solid var(--border-subtle)",
                marginTop: "14px",
              }}
            >
              <span style={colLabel}>Patient</span>
              <span style={colLabel}>Alter</span>
              <span style={colLabel}>Programm</span>
              <span style={colLabel}>Risiko</span>
              <span style={colLabel}>Datenqualität</span>
              <span style={colLabel}>Letztes Assessment</span>
              <span style={colLabel}>Status</span>
            </div>

            {visible.map((p) => {
              const sm = PATIENT_STATUS_META[p.status];
              const am = ATTN_META[p.risk];
              const qc = qColor(p.q);
              return (
                <div
                  key={p.id}
                  className="vb-row"
                  {...clickable(
                    () => router.push(`/patients/${p.id}`),
                    `Patient ${p.name}, ${p.id} öffnen`,
                  )}
                  style={{
                    display: "grid",
                    gridTemplateColumns: PGRID,
                    alignItems: "center",
                    gap: "16px",
                    padding: "13px 22px",
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "11px",
                      minWidth: 0,
                    }}
                  >
                    <div
                      style={{
                        width: "34px",
                        height: "34px",
                        flexShrink: 0,
                        borderRadius: "999px",
                        background: "var(--brand-soft)",
                        border: "1px solid var(--brand-border)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--teal-600)",
                      }}
                    >
                      {initials(p.name)}
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: "13.5px",
                          fontWeight: 600,
                          color: "var(--text-strong)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {p.name}
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "var(--text-faint)",
                        }}
                      >
                        {p.id}
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                      color: "var(--text-muted)",
                    }}
                  >
                    {p.age} · {p.sex}
                  </div>
                  <div
                    style={{
                      fontSize: "13px",
                      color: "var(--text-body)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {p.program}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "7px",
                    }}
                  >
                    <span
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "999px",
                        flexShrink: 0,
                        background: am.c,
                      }}
                    />
                    <span
                      style={{
                        fontSize: "12.5px",
                        fontWeight: 500,
                        color: am.c,
                      }}
                    >
                      {am.label}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "9px",
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        height: "6px",
                        borderRadius: "999px",
                        background: "var(--surface-sunken)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: "999px",
                          width: p.q + "%",
                          background: qc,
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        minWidth: "34px",
                        textAlign: "right",
                        color: qc,
                      }}
                    >
                      {p.q}%
                    </span>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "13px",
                        color: "var(--text-body)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {p.last}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--text-faint)",
                      }}
                    >
                      {p.when}
                    </div>
                  </div>
                  <div>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        padding: "3px 10px",
                        borderRadius: "999px",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        color: sm.fg,
                        background: sm.bg,
                        border: "1px solid " + sm.bd,
                      }}
                    >
                      {sm.label}
                    </span>
                  </div>
                </div>
              );
            })}

            {visible.length === 0 && (
              <div style={{ textAlign: "center", padding: "54px 20px" }}>
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "var(--text-lg)",
                    color: "var(--text-strong)",
                    marginBottom: "6px",
                  }}
                >
                  Keine Patienten in dieser Ansicht
                </div>
                <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                  Wählen Sie einen anderen Filter oder ändern Sie die Suche.
                </div>
              </div>
            )}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
            padding: "14px 22px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--text-muted)",
            }}
          >
            Zeige 1–{visible.length} von {PATIENT_COHORT[pTab]}
          </span>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              disabled
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                height: "34px",
                padding: "0 13px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--surface-card)",
                color: "var(--text-muted)",
                fontFamily: "var(--font-text)",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "not-allowed",
                opacity: 0.6,
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M15 18l-6-6 6-6" />
              </svg>
              Zurück
            </button>
            <button
              type="button"
              className="vb-btn-next"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                height: "34px",
                padding: "0 13px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
                background: "var(--surface-card)",
                color: "var(--text-strong)",
                fontFamily: "var(--font-text)",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Weiter
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
