"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Icon, type IconName } from "@/components/Icon";
import { useToast } from "@/components/Toaster";
import type { WorklistView } from "@/lib/presenters/worklist";

const TABS: { key: string; label: string }[] = [
  { key: "open", label: "Offene Reviews" },
  { key: "approved", label: "Genehmigt" },
  { key: "released", label: "Freigegeben" },
  { key: "all", label: "Alle" },
];

const GATED = (
  <span
    style={{ color: "var(--muted-2)", fontSize: "11px" }}
    title="Noch nicht verfügbar"
  >
    —
  </span>
);

function Row({ item }: { item: WorklistView }) {
  const router = useRouter();
  const toast = useToast();
  const open = () => {
    if (item.open && item.reviewUrl) router.push(item.reviewUrl);
    else toast("Für diesen Patienten existiert noch kein Berichtsentwurf.");
  };
  return (
    <tr
      tabIndex={0}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      }}
    >
      <td data-label="Patient">
        <div className="patient-cell">
          <div className="patient-avatar">{item.initials}</div>
          <div>
            <div className="patient-name">{item.name}</div>
            <div className="patient-meta">
              {item.ref} · {item.profile}
            </div>
          </div>
        </div>
      </td>
      <td data-label="Assessment">
        <div className="assessment-cell">
          <strong>{item.assessment}</strong>
        </div>
      </td>
      <td data-label="Aufmerksamkeit">{GATED}</td>
      <td data-label="Datenqualität">{GATED}</td>
      <td data-label="Status">
        <span className={`badge ${item.statusBadge}`}>{item.statusLabel}</span>
      </td>
      <td data-label="Aktualisiert">
        <span
          className="num"
          style={{ fontSize: "10.5px", color: "var(--muted)" }}
        >
          {item.updatedLabel}
        </span>
      </td>
      <td data-label="Aktion">
        <a
          className="row-action"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            open();
          }}
        >
          {item.open ? "Prüfen →" : "Ansehen →"}
        </a>
      </td>
    </tr>
  );
}

export function WorklistContent({ rows }: { rows: WorklistView[] }) {
  const toast = useToast();
  const [filter, setFilter] = useState("open");
  const [term, setTerm] = useState("");

  const counts = useMemo(
    () => ({
      open: rows.filter((r) => r.statusGroup === "open").length,
      approved: rows.filter((r) => r.statusGroup === "approved").length,
      released: rows.filter((r) => r.statusGroup === "released").length,
      none: rows.filter((r) => r.statusGroup === "none").length,
      all: rows.length,
    }),
    [rows],
  );

  const tabCount = (key: string) =>
    key === "all" ? counts.all : (counts[key as keyof typeof counts] ?? 0);

  const visible = useMemo(
    () =>
      rows.filter((r) => {
        const matchesFilter = filter === "all" || r.statusGroup === filter;
        const haystack = `${r.name} ${r.ref} ${r.profile}`.toLowerCase();
        return matchesFilter && haystack.includes(term.toLowerCase());
      }),
    [rows, filter, term],
  );

  const stats: {
    tone: string;
    icon: IconName;
    value: number;
    label: string;
    help: string;
  }[] = [
    {
      tone: "warning",
      icon: "calendar",
      value: counts.open,
      label: "Offene Reviews",
      help: "Klinische Prüfung ausstehend",
    },
    {
      tone: "",
      icon: "download",
      value: counts.none,
      label: "Ohne Entwurf",
      help: "Noch kein Bericht erstellt",
    },
    {
      tone: "info",
      icon: "people2",
      value: counts.approved,
      label: "Genehmigt",
      help: "Warten auf Freigabe",
    },
    {
      tone: "neutral",
      icon: "bars",
      value: counts.all,
      label: "Patienten im Mandanten",
      help: "Tenant-bezogen, RLS-geschützt",
    },
  ];

  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">Klinischer Arbeitsbereich</div>
          <h1>Guten Nachmittag, Dr. Johnson</h1>
          <p>
            <strong style={{ color: "var(--brand-700)" }}>
              {counts.open} {counts.open === 1 ? "Assessment" : "Assessments"}
            </strong>{" "}
            {counts.open === 1 ? "wartet" : "warten"} auf Ihre Prüfung.
            Quellengebundene Entwürfe müssen vor jeder Freigabe geprüft werden.
          </p>
        </div>
        <div className="page-actions">
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() =>
              toast("Der Import-Workflow folgt im nächsten vertikalen Slice.")
            }
          >
            <Icon name="download" />
            Daten importieren
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() =>
              toast(
                "Die Patienteneinladung ist noch nicht mit einem Backend verbunden.",
              )
            }
          >
            <Icon name="patients" />
            Patient hinzufügen
          </button>
        </div>
      </header>

      <section className="stats-grid" aria-label="Tagesübersicht">
        {stats.map((s) => (
          <article className={`card stat-card ${s.tone}`.trim()} key={s.label}>
            <div className="stat-top">
              <span className="stat-icon">
                <Icon name={s.icon} />
              </span>
              <span className="stat-value">{s.value}</span>
            </div>
            <div className="stat-label">{s.label}</div>
            <div className="stat-help">{s.help}</div>
          </article>
        ))}
      </section>

      <div className="section-header">
        <div>
          <h2>Klinische Arbeitsliste</h2>
          <p>
            Nach Status sortiert; keine automatische Diagnose oder
            Therapieempfehlung.
          </p>
        </div>
      </div>

      <section
        className="card worklist-card"
        aria-labelledby="worklist-heading"
      >
        <h2 className="sr-only" id="worklist-heading">
          Arbeitsliste
        </h2>
        <div className="card-toolbar">
          <div className="tabs" role="tablist" aria-label="Arbeitslistenfilter">
            {TABS.map((t) => (
              <button
                key={t.key}
                className="tab"
                role="tab"
                aria-selected={filter === t.key}
                onClick={() => setFilter(t.key)}
              >
                {t.label} <span className="count">{tabCount(t.key)}</span>
              </button>
            ))}
          </div>
          <div className="toolbar-actions">
            <label className="input-wrap toolbar-search">
              <span className="sr-only">
                Patienten in der Arbeitsliste suchen
              </span>
              <Icon name="search" className="input-icon" />
              <input
                className="input has-leading"
                type="search"
                placeholder="Patient oder ID suchen"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
              />
            </label>
            <button
              className="icon-btn"
              type="button"
              aria-label="Sortierung ändern"
              onClick={() => toast("Die Liste ist nach Status sortiert.")}
            >
              <Icon name="sort" />
            </button>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table worklist-table">
            <caption className="sr-only">
              Patienten und Assessments, die bearbeitet werden müssen
            </caption>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Assessment</th>
                <th>Aufmerksamkeit</th>
                <th>Datenqualität</th>
                <th>Status</th>
                <th>Aktualisiert</th>
                <th>
                  <span className="sr-only">Aktion</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <Row key={item.patientId} item={item} />
              ))}
            </tbody>
          </table>
          {visible.length === 0 && (
            <div className="empty-state">
              <strong>Keine passenden Vorgänge</strong>Ändern Sie den Filter
              oder den Suchbegriff.
            </div>
          )}
        </div>
      </section>

      <section className="dashboard-grid" style={{ marginTop: "14px" }}>
        <article className="card activity-card">
          <h2 className="card-title">Letzte Aktivität</h2>
          <p className="card-subtitle">
            Audit-relevante Ereignisse · Beispiel, noch nicht an den Audit-Feed
            angebunden.
          </p>
          <div className="activity-list">
            <div className="activity-item">
              <span className="activity-icon">
                <Icon name="docText" />
              </span>
              <div className="activity-copy">
                <strong>Berichtsentwurf erstellt</strong> · quellengebunden,
                nicht freigegeben
              </div>
              <time className="activity-time">vor 2 h</time>
            </div>
            <div className="activity-item">
              <span className="activity-icon">
                <Icon name="check" />
              </span>
              <div className="activity-copy">
                <strong>Review signiert</strong> durch Dr. Johnson
              </div>
              <time className="activity-time">vor 3 T</time>
            </div>
          </div>
        </article>

        <article className="card quality-card">
          <h2 className="card-title">Datenqualität heute</h2>
          <p className="card-subtitle">
            Deterministische Vollständigkeit · Beispiel, Modell noch nicht
            freigegeben.
          </p>
          <div className="quality-list">
            <div>
              <div className="quality-item-head">
                <strong>Verifizierte Beobachtungen</strong>
                <span className="num">—</span>
              </div>
              <div className="progress">
                <span style={{ width: "0%" }} />
              </div>
            </div>
          </div>
          <button
            className="btn btn-secondary btn-block"
            type="button"
            style={{ marginTop: "18px" }}
            onClick={() =>
              toast("Die Importprüfung ist als nächster MVP-Screen vorgesehen.")
            }
          >
            Importprüfung öffnen
          </button>
        </article>
      </section>
    </>
  );
}
