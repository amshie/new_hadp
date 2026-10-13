"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { AddPatientDialog } from "@/components/vitabahn/AddPatientDialog";
import { clickable } from "@/components/vitabahn/interactive";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type {
  DirectoryView,
  DirectoryRowView,
} from "@/lib/presenters/dashboard";

// VitaBahn Patienten directory (ADR-0006, real-data path). Consumes the governed DirectoryView
// (real patients + worklist). Patient name/age/status/last-assessment are real. The founder-approved
// Risiko and Datenqualität columns are kept VISIBLE but honestly GATED — there is no compliant real
// source (an autonomous patient risk score is register-BLOCKED; no data-quality engine exists), so
// they show "n. v." rather than fabricated values (ADR-0006). Programm/cohort tabs are dropped (no field).

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

// A column that is kept visible and has no value: no approved source exists for it (ADR-0006).
function Gated() {
  const t = useI18n().t.patients;
  return (
    <span
      title={t.gatedTitle}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "11px",
        color: "var(--text-faint)",
      }}
    >
      {t.notAvailable}
    </span>
  );
}

// The tabs of the directory, by the group a patient's latest report is in (never by its
// label, which differs by language).
type TabKey = "all" | "open" | "released" | "none";
const TABS: TabKey[] = ["all", "open", "released", "none"];

function inTab(r: DirectoryRowView, tab: TabKey): boolean {
  if (tab === "all") return true;
  if (tab === "open") return r.group === "review";
  return r.group === tab;
}

export function PatientsContent({
  view,
  tenantName,
}: {
  view: DirectoryView;
  tenantName: string;
}) {
  const router = useRouter();
  const t = useI18n().t.patients;
  const [tab, setTab] = useState<TabKey>("all");
  const [term, setTerm] = useState("");

  const counts: Record<TabKey, number> = useMemo(
    () => ({
      all: view.rows.length,
      open: view.rows.filter((r) => inTab(r, "open")).length,
      released: view.rows.filter((r) => inTab(r, "released")).length,
      none: view.rows.filter((r) => inTab(r, "none")).length,
    }),
    [view.rows],
  );

  const visible = useMemo(() => {
    const q = term.toLowerCase();
    return view.rows.filter((r) => {
      const hay = `${r.name} ${r.ref}`.toLowerCase();
      return inTab(r, tab) && hay.includes(q);
    });
  }, [view.rows, tab, term]);

  const chips: { value: ReactNode; label: string; help: string }[] = [
    {
      value: view.total,
      label: t.chips.total.label,
      help: t.chips.total.help,
    },
    {
      value: view.withReport,
      label: t.chips.withReport.label,
      help: t.chips.withReport.help,
    },
    {
      value: view.openAssessments,
      label: t.chips.open.label,
      help: t.chips.open.help,
    },
    {
      value: t.notAvailable,
      label: t.chips.quality.label,
      help: t.chips.quality.help,
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
      <div
        style={{
          marginBottom: "28px",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "20px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ minWidth: 0 }}>
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
            {fill(t.kicker, { clinic: tenantName })}
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
            {t.title}
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
              {byCount(t.count, view.total)}
            </span>{" "}
            {t.lead}
          </p>
        </div>
        <AddPatientDialog />
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
            {t.directory.title}
          </h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: "0 0 16px",
            }}
          >
            {t.directory.note}
          </p>
          {view.rows.length > 0 && (
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
                {TABS.map((key) => {
                  const active = tab === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setTab(key)}
                      style={tabBtn(active)}
                    >
                      {t.tabs[key]}{" "}
                      <span style={tabBadge(active)}>{counts[key]}</span>
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
                  aria-label={t.search}
                  value={term}
                  onChange={(e) => setTerm(e.target.value)}
                  placeholder={t.search}
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
          )}
        </div>

        {view.rows.length === 0 ? (
          <div style={{ textAlign: "center", padding: "56px 24px 60px" }}>
            <div
              aria-hidden="true"
              style={{
                display: "inline-flex",
                width: "44px",
                height: "44px",
                borderRadius: "999px",
                background: "var(--brand-soft)",
                border: "1px solid var(--brand-border)",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: "12px",
              }}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--brand)"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M19 8v6M22 11h-6" />
              </svg>
            </div>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "var(--text-lg)",
                color: "var(--text-strong)",
                marginBottom: "6px",
              }}
            >
              {t.emptyTitle}
            </div>
            <p
              style={{
                fontSize: "13px",
                color: "var(--text-muted)",
                maxWidth: "44ch",
                margin: "0 auto 18px",
                lineHeight: 1.55,
              }}
            >
              {t.emptyNote}
            </p>
            <AddPatientDialog
              trigger={(open) => (
                <button
                  type="button"
                  onClick={open}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "8px",
                    height: "38px",
                    padding: "0 18px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--brand-border)",
                    background: "var(--brand)",
                    color: "var(--text-on-brand)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {t.firstRecord}
                </button>
              )}
            />
          </div>
        ) : (
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
                <span style={colLabel}>{t.columns.patient}</span>
                <span style={colLabel}>{t.columns.age}</span>
                <span style={colLabel}>{t.columns.risk}</span>
                <span style={colLabel}>{t.columns.quality}</span>
                <span style={colLabel}>{t.columns.lastAssessment}</span>
                <span style={colLabel}>{t.columns.status}</span>
              </div>
              {visible.map((p) => {
                const sm = p.statusBadge;
                return (
                  <div
                    key={p.patientId}
                    className="vb-row"
                    {...clickable(
                      () => router.push(`/patients/${p.patientId}`),
                      fill(t.openRow, { name: p.name, ref: p.ref }),
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
                    <div>
                      <Gated />
                    </div>
                    <div>
                      <Gated />
                    </div>
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
                    {t.noneTitle}
                  </div>
                  <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                    {t.noneNote}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {view.rows.length > 0 && (
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
              {fill(t.showing, { shown: visible.length, total: view.total })}
            </span>
          </div>
        )}
      </div>
    </>
  );
}
