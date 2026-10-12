"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { KpiConfig } from "@/lib/api";

import {
  clearKpiReferenceAction,
  resetKpiConfigAction,
  setKpiConfigAction,
  setKpiReferenceAction,
} from "./actions";

// German labels for the six closed domain axes (ADR-0003) and the four catalog tiers.
const DOMAIN_LABELS: Record<string, string> = {
  metabolic: "Metabolisch",
  immune_inflammation: "Immun & Entzündung",
  cardiovascular: "Kardiovaskulär",
  neurocognitive: "Neurokognitiv",
  musculoskeletal: "Muskuloskelettal",
  regenerative_capacity: "Regenerative Kapazität",
};
const DOMAIN_ORDER = [
  "metabolic",
  "immune_inflammation",
  "cardiovascular",
  "neurocognitive",
  "musculoskeletal",
  "regenerative_capacity",
];
const TIER_LABELS: Record<string, string> = {
  core: "Core",
  extended: "Erweitert",
  specialist: "Spezialisiert",
  research: "Forschung",
};
const RESTRICTED_TIERS = new Set(["specialist", "research"]);

const muted = "var(--text-muted, #5b6b70)";
const border = "1px solid var(--border-subtle, #dfe5e7)";

export function KpiConfigContent({ rows }: { rows: KpiConfig[] }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null); // kpi_code currently saving
  const [pending, startTransition] = useTransition();

  const run = (
    kpiCode: string,
    action: () => Promise<{ ok: boolean; error?: string }>,
  ) =>
    startTransition(async () => {
      setError(null);
      setBusy(kpiCode);
      const res = await action();
      setBusy(null);
      if (res.ok) router.refresh();
      else setError(res.error ?? "Die Aktion konnte nicht ausgeführt werden.");
    });

  const toggleEnabled = (row: KpiConfig, enabled: boolean) =>
    run(row.kpi_code, () =>
      setKpiConfigAction(row.kpi_code, enabled, row.effective_patient_visible),
    );

  const togglePatientVisible = (row: KpiConfig, patientVisible: boolean) =>
    run(row.kpi_code, () =>
      setKpiConfigAction(row.kpi_code, row.effective_enabled, patientVisible),
    );

  const reset = (row: KpiConfig) =>
    run(row.kpi_code, () => resetKpiConfigAction(row.kpi_code));

  // Per-KPI reference-interval draft inputs (keyed by kpi_code). Absent entry => show the current
  // stored reference (or empty); a present entry is the owner's in-progress edit.
  const [refDraft, setRefDraft] = useState<
    Record<string, { low: string; high: string }>
  >({});
  const draftFor = (row: KpiConfig) =>
    refDraft[row.kpi_code] ?? {
      low: row.reference_low ?? "",
      high: row.reference_high ?? "",
    };
  const setDraft = (
    code: string,
    part: Partial<{ low: string; high: string }>,
  ) =>
    setRefDraft((d) => ({
      ...d,
      [code]: { ...(d[code] ?? { low: "", high: "" }), ...part },
    }));
  const saveReference = (row: KpiConfig) => {
    const { low, high } = draftFor(row);
    run(row.kpi_code, () => setKpiReferenceAction(row.kpi_code, low, high));
  };
  const clearReference = (row: KpiConfig) => {
    setRefDraft((d) => {
      const next = { ...d };
      delete next[row.kpi_code];
      return next;
    });
    run(row.kpi_code, () => clearKpiReferenceAction(row.kpi_code));
  };

  const activeCount = rows.filter((r) => r.effective_enabled).length;
  const byDomain = DOMAIN_ORDER.map((axis) => ({
    axis,
    items: rows.filter((r) => r.primary_domain_axis === axis),
  })).filter((g) => g.items.length > 0);

  return (
    <div style={{ maxWidth: "820px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>Kennzahlen</h1>
      <p
        style={{
          color: muted,
          fontSize: "13px",
          marginBottom: "6px",
          lineHeight: 1.55,
        }}
      >
        Legen Sie fest, welche Kennzahlen für Ihre Klinik aktiv sind und ob sie
        für Patient:innen sichtbar sein dürfen. Diese Auswahl gilt nur für Ihre
        Klinik; der gemeinsame Kennzahlen-Katalog bleibt unverändert.
      </p>
      <p style={{ color: muted, fontSize: "12.5px", marginBottom: "22px" }}>
        {activeCount} von {rows.length} Kennzahlen aktiv.
      </p>

      {error && (
        <p
          role="alert"
          style={{ color: "#b3261e", lineHeight: 1.5, marginBottom: "16px" }}
        >
          {error}
        </p>
      )}

      {byDomain.map((group) => (
        <section
          key={group.axis}
          aria-label={DOMAIN_LABELS[group.axis]}
          style={{ marginBottom: "26px" }}
        >
          <strong
            style={{
              display: "block",
              margin: "6px 0 12px",
              fontSize: "15px",
              color: "var(--text-strong, #17292f)",
            }}
          >
            {DOMAIN_LABELS[group.axis] ?? group.axis}
          </strong>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {group.items.map((row) => {
              const restricted = RESTRICTED_TIERS.has(row.tier);
              const saving = pending && busy === row.kpi_code;
              return (
                <li
                  key={row.kpi_code}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    padding: "12px 14px",
                    border,
                    borderRadius: "9px",
                    marginBottom: "8px",
                    opacity: saving ? 0.6 : 1,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "14px",
                    }}
                  >
                    <span style={{ minWidth: 0 }}>
                      <span style={{ fontSize: "14px", fontWeight: 600 }}>
                        {row.display_name}
                      </span>
                      <span
                        style={{
                          marginLeft: "10px",
                          fontSize: "11px",
                          padding: "2px 7px",
                          borderRadius: "999px",
                          background: "rgba(15,118,110,0.08)",
                          color: "#0f766e",
                        }}
                      >
                        {TIER_LABELS[row.tier] ?? row.tier}
                      </span>
                      {row.is_overridden && (
                        <span
                          style={{
                            marginLeft: "8px",
                            fontSize: "11.5px",
                            color: muted,
                          }}
                          title="Weicht vom Standard ab"
                        >
                          · Angepasst
                        </span>
                      )}
                    </span>

                    <span
                      style={{
                        display: "flex",
                        gap: "16px",
                        alignItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <label
                        style={{
                          fontSize: "13px",
                          display: "flex",
                          gap: "6px",
                          alignItems: "center",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={row.effective_enabled}
                          disabled={pending}
                          onChange={(e) => toggleEnabled(row, e.target.checked)}
                        />
                        Aktiv
                      </label>
                      <label
                        style={{
                          fontSize: "13px",
                          display: "flex",
                          gap: "6px",
                          alignItems: "center",
                          color: restricted ? muted : "inherit",
                        }}
                        title={
                          restricted
                            ? "Spezialisierte und Forschungs-Kennzahlen sind nie für Patient:innen sichtbar."
                            : undefined
                        }
                      >
                        <input
                          type="checkbox"
                          checked={row.effective_patient_visible}
                          disabled={pending || restricted}
                          onChange={(e) =>
                            togglePatientVisible(row, e.target.checked)
                          }
                        />
                        Für Patient:innen
                      </label>
                      {row.is_overridden ? (
                        <button
                          type="button"
                          onClick={() => reset(row)}
                          disabled={pending}
                          style={{
                            padding: "5px 11px",
                            borderRadius: "8px",
                            border,
                            background: "transparent",
                            color: muted,
                            fontSize: "12.5px",
                            cursor: pending ? "wait" : "pointer",
                          }}
                        >
                          Zurücksetzen
                        </button>
                      ) : (
                        <span style={{ width: "88px" }} aria-hidden="true" />
                      )}
                    </span>
                  </div>
                  {row.canonical_unit && (
                    <ReferenceEditor
                      row={row}
                      draft={draftFor(row)}
                      pending={pending}
                      onLow={(v) => setDraft(row.kpi_code, { low: v })}
                      onHigh={(v) => setDraft(row.kpi_code, { high: v })}
                      onSave={() => saveReference(row)}
                      onClear={() => clearReference(row)}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

// Per-KPI clinic reference editor. A NEUTRAL, clinic-defined interval (never an "optimal" target):
// it only backs the within/above/below marker as a FALLBACK when a lab result carries no reference
// of its own, and never overwrites the lab-provided reference. Entered in the KPI's canonical unit.
function ReferenceEditor({
  row,
  draft,
  pending,
  onLow,
  onHigh,
  onSave,
  onClear,
}: {
  row: KpiConfig;
  draft: { low: string; high: string };
  pending: boolean;
  onLow: (v: string) => void;
  onHigh: (v: string) => void;
  onSave: () => void;
  onClear: () => void;
}) {
  const numberInput: React.CSSProperties = {
    width: "72px",
    padding: "5px 7px",
    borderRadius: "7px",
    border,
    fontSize: "13px",
  };
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexWrap: "wrap",
        fontSize: "12.5px",
        color: muted,
      }}
    >
      <span>Klinikdefinierte Referenz:</span>
      <label aria-label={`Unterer Referenzwert für ${row.display_name}`}>
        <input
          type="number"
          step="any"
          inputMode="decimal"
          value={draft.low}
          disabled={pending}
          onChange={(e) => onLow(e.target.value)}
          style={numberInput}
        />
      </label>
      <span aria-hidden="true">–</span>
      <label aria-label={`Oberer Referenzwert für ${row.display_name}`}>
        <input
          type="number"
          step="any"
          inputMode="decimal"
          value={draft.high}
          disabled={pending}
          onChange={(e) => onHigh(e.target.value)}
          style={numberInput}
        />
      </label>
      <span>{row.canonical_unit}</span>
      <button
        type="button"
        onClick={onSave}
        disabled={pending}
        style={{
          padding: "5px 11px",
          borderRadius: "8px",
          border: "1px solid #0f766e",
          background: "#0f766e",
          color: "#fff",
          fontSize: "12.5px",
          fontWeight: 600,
          cursor: pending ? "wait" : "pointer",
        }}
      >
        Speichern
      </button>
      {row.reference_low !== null && (
        <button
          type="button"
          onClick={onClear}
          disabled={pending}
          style={{
            padding: "5px 11px",
            borderRadius: "8px",
            border,
            background: "transparent",
            color: muted,
            fontSize: "12.5px",
            cursor: pending ? "wait" : "pointer",
          }}
        >
          Entfernen
        </button>
      )}
      <span style={{ color: "var(--text-muted, #5b6b70)", opacity: 0.85 }}>
        · greift nur, wenn das Labor keine Referenz liefert
      </span>
    </div>
  );
}
