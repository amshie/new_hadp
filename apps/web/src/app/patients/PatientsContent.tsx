"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { clickable } from "@/components/vitabahn/interactive";
import type {
  DirectoryView,
  DirectoryRowView,
} from "@/lib/presenters/dashboard";

// VitaBahn Patienten directory (ADR-0005, real-data path). Consumes the governed DirectoryView
// (real patients + worklist). Patient name/age/status/last-assessment are real. The founder-approved
// Risiko and Datenqualität columns are kept VISIBLE but honestly GATED — there is no compliant real
// source (an autonomous patient risk score is register-BLOCKED; no data-quality engine exists), so
// they show "n. v." rather than fabricated values (ADR-0005). Programm/cohort tabs are dropped (no field).

const PGRID = "minmax(220px,2fr) 70px 96px 110px minmax(150px,1.3fr) 120px";

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

const GATED = (
  <span
    title="Kein zugelassener Echtdaten-Indikator (ADR-0005)"
    style={{
      fontFamily: "var(--font-mono)",
      fontSize: "11px",
      color: "var(--text-faint)",
    }}
  >
    n. v.
  </span>
);

const TABS: { key: string; label: string }[] = [
  { key: "alle", label: "Alle" },
  { key: "offen", label: "Offene Reviews" },
  { key: "freigegeben", label: "Freigegeben" },
  { key: "ohne", label: "Ohne Bericht" },
];

function rowGroup(r: DirectoryRowView): string {
  if (r.statusLabel === "In Prüfung") return "offen";
  if (r.statusLabel === "Freigegeben") return "freigegeben";
  if (r.statusLabel === "Kein Entwurf") return "ohne";
  return "andere";
}

export function PatientsContent({ view }: { view: DirectoryView }) {
  const router = useRouter();
  const [tab, setTab] = useState("alle");
  const [term, setTerm] = useState("");

  const counts = useMemo(
    () => ({
      alle: view.rows.length,
      offen: view.rows.filter((r) => rowGroup(r) === "offen").length,
      freigegeben: view.rows.filter((r) => rowGroup(r) === "freigegeben")
        .length,
      ohne: view.rows.filter((r) => rowGroup(r) === "ohne").length,
    }),
    [view.rows],
  );

  const visible = useMemo(() => {
    const q = term.toLowerCase();
    return view.rows.filter((r) => {
      const matchTab = tab === "alle" || rowGroup(r) === tab;
      const hay = `${r.name} ${r.ref}`.toLowerCase();
      return matchTab && hay.includes(q);
    });
  }, [view.rows, tab, term]);

  const chips: { value: ReactNode; label: string; help: string }[] = [
    {
      value: view.total,
      label: "Gesamt",
      help: "Im Mandanten · RLS-geschützt",
    },
    {
      value: view.withReport,
      label: "Mit Bericht",
      help: "Mindestens ein Berichtsentwurf",
    },
    {
      value: view.openAssessments,
      label: "Offene Assessments",
      help: "Klinische Prüfung ausstehend",
    },
    {
      value: "n. v.",
      label: "Ø Datenqualität",
      help: "Kein Datenqualitätsmodell (Gate G1)",
    },
  ];

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
      <div style={{ marginBottom: "28px" }}>
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
            {view.total} {view.total === 1 ? "Patientin" : "Patienten"}
          </span>{" "}
          · tenant-bezogen, RLS-geschützt · pseudonymisierte, synthetische
          Beispieldaten.
        </p>
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
        {chips.map((c) => (
          <div key={c.label} style={{ ...cardStyle, padding: "18px" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10.5px",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--text-muted)",
                fontWeight: 500,
                marginBottom: "12px",
              }}
            >
              {c.label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "34px",
                lineHeight: 1,
                color: "var(--text-strong)",
                letterSpacing: "-0.02em",
                marginBottom: "6px",
              }}
            >
              {c.value}
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
            Therapieempfehlung. Risiko- und Datenqualitäts-Spalten sind in der
            Echtdaten-Ansicht deaktiviert (kein zugelassener Quell-/Modellwert —
            ADR-0005).
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
                const active = tab === t.key;
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    style={tabBtn(active)}
                  >
                    {t.label}{" "}
                    <span style={tabBadge(active)}>
                      {counts[t.key as keyof typeof counts] ?? 0}
                    </span>
                  </button>
                );
              })}
            </div>
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
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <div style={{ minWidth: "860px" }}>
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
              <span style={colLabel}>Risiko</span>
              <span style={colLabel}>Datenqualität</span>
              <span style={colLabel}>Letztes Assessment</span>
              <span style={colLabel}>Status</span>
            </div>
            {visible.map((p) => {
              const sm = p.statusBadge;
              return (
                <div
                  key={p.patientId}
                  className="vb-row"
                  {...clickable(
                    () => router.push(`/patients/${p.patientId}`),
                    `Patient ${p.name}, ${p.ref} öffnen`,
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
                      {p.initials}
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
                        {p.ref}
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
                    {p.age}
                  </div>
                  <div>{GATED}</div>
                  <div>{GATED}</div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                      color: "var(--text-muted)",
                    }}
                  >
                    {p.lastAssessment}
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
            Zeige {visible.length} von {view.total}
          </span>
        </div>
      </div>
    </>
  );
}
