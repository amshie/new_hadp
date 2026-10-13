"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition, type CSSProperties } from "react";

import type { RunAuthorIn } from "@/lib/api";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { fill } from "@/lib/i18n/fill";
import {
  ACTIONABILITY_LABELS,
  ADEQUACY_LABELS,
  CIS_LABELS,
  DOMAIN_AXIS_LABELS,
} from "@/lib/presenters/review";

import { authorRunAction } from "./actions";

// The clinician actively chooses EVERY verdict — no field is pre-selected on a new
// run (an empty "Bitte wählen" is forced choice, not a default judgement). On a
// correction run the latest run prefills and the clinician edits. CIS and
// Actionability are two separate closed selects; the three tri-state cells are
// verdict-free supporting evidence with their own per-axis vocabularies.
//
// The form follows the interface language (ADR-0007). What is CHOSEN in it — the domain axes,
// CIS, Actionability, adequacy, the tri-state axes and their states — is a closed clinical
// vocabulary: German until its English names are confirmed, and marked so.
const GERMAN = "de";

export interface EvidenceOption {
  id: string;
  label: string;
}

export interface PrefillCell {
  tri_state_axis: string;
  state: string;
  endpoint_adequacy: string;
  evidence: string[];
  rationale: string;
}

export interface PrefillDomain {
  domain_axis: string;
  cis_status: string;
  actionability_class: string;
  followup_adequacy: string;
  rationale: string;
  cells: PrefillCell[];
}

const AXES = [
  "metabolic",
  "immune_inflammation",
  "cardiovascular",
  "neurocognitive",
  "musculoskeletal",
  "regenerative_capacity",
] as const;
const TRI_AXES = ["biological", "risk", "functional"] as const;

const TRI_AXIS_LABELS: Record<string, string> = {
  biological: "Biologisch",
  risk: "Risk",
  functional: "Funktional",
};

// Per-axis closed cell vocabularies (mirrors enums.py; the API re-validates).
const CELL_STATES: Record<string, string[]> = {
  biological: ["IMPROVED", "STABLE", "WORSENED", "MIXED", "INDETERMINATE"],
  functional: ["IMPROVED", "STABLE", "WORSENED", "MIXED", "INDETERMINATE"],
  risk: [
    "REDUCED",
    "WORSENED",
    "DOMINANT",
    "UNRESOLVED",
    "CONFLICTING",
    "INDETERMINATE",
  ],
};
const CELL_STATE_LABELS: Record<string, string> = {
  IMPROVED: "Verbessert",
  STABLE: "Stabil",
  WORSENED: "Verschlechtert",
  MIXED: "Gemischt",
  INDETERMINATE: "Unbestimmt",
  REDUCED: "Reduziert",
  DOMINANT: "Dominant",
  UNRESOLVED: "Ungeklärt",
  CONFLICTING: "Widersprüchlich",
};

interface CellDraft {
  state: string;
  endpoint_adequacy: string;
  evidence: string[];
  rationale: string;
}
interface DomainDraft {
  cis_status: string;
  actionability_class: string;
  followup_adequacy: string;
  rationale: string;
  cells: Record<string, CellDraft>;
}

function emptyDraft(): Record<string, DomainDraft> {
  const out: Record<string, DomainDraft> = {};
  for (const axis of AXES) {
    const cells: Record<string, CellDraft> = {};
    for (const tri of TRI_AXES) {
      cells[tri] = {
        state: "",
        endpoint_adequacy: "",
        evidence: [],
        rationale: "",
      };
    }
    out[axis] = {
      cis_status: "",
      actionability_class: "",
      followup_adequacy: "",
      rationale: "",
      cells,
    };
  }
  return out;
}

function fromPrefill(prefill: PrefillDomain[]): Record<string, DomainDraft> {
  const out = emptyDraft();
  for (const d of prefill) {
    const target = out[d.domain_axis];
    if (!target) continue;
    target.cis_status = d.cis_status;
    target.actionability_class = d.actionability_class;
    target.followup_adequacy = d.followup_adequacy;
    target.rationale = d.rationale;
    for (const c of d.cells) {
      if (target.cells[c.tri_state_axis]) {
        target.cells[c.tri_state_axis] = {
          state: c.state,
          endpoint_adequacy: c.endpoint_adequacy,
          evidence: c.evidence,
          rationale: c.rationale,
        };
      }
    }
  }
  return out;
}

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
  padding: "18px 20px",
  marginBottom: "14px",
};
const labelStyle: CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontFamily: "var(--font-mono)",
  textTransform: "uppercase",
  letterSpacing: "0.07em",
  color: "var(--text-faint)",
  marginBottom: "4px",
};
const selectStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-body)",
  fontSize: "13px",
};
const inputStyle: CSSProperties = { ...selectStyle };

export function AuthorRunContent({
  patientId,
  runNumber,
  prefill,
  evidenceOptions,
}: {
  patientId: string;
  runNumber: number | null;
  prefill: PrefillDomain[] | null;
  evidenceOptions: EvidenceOption[];
}) {
  const router = useRouter();
  const [draft, setDraft] = useState<Record<string, DomainDraft>>(
    prefill ? fromPrefill(prefill) : emptyDraft(),
  );
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const t = useI18n().t.interpretation;

  const setDomain = (axis: string, patch: Partial<DomainDraft>) =>
    setDraft((d) => {
      const cur = d[axis];
      if (!cur) return d;
      return { ...d, [axis]: { ...cur, ...patch } };
    });
  const setCell = (axis: string, tri: string, patch: Partial<CellDraft>) =>
    setDraft((d) => {
      const cur = d[axis];
      const cell = cur?.cells[tri];
      if (!cur || !cell) return d;
      return {
        ...d,
        [axis]: {
          ...cur,
          cells: { ...cur.cells, [tri]: { ...cell, ...patch } },
        },
      };
    });

  const validate = (): string | null => {
    if (!reason.trim()) return t.invalid.reason;
    for (const axis of AXES) {
      // Invariant: the draft always contains every axis/cell (constructed above).
      const d = draft[axis]!;
      const where = { axis: DOMAIN_AXIS_LABELS[axis] ?? axis };
      if (!d.cis_status || !d.actionability_class || !d.followup_adequacy)
        return fill(t.invalid.domain, where);
      for (const tri of TRI_AXES) {
        const c = d.cells[tri]!;
        const cell = { ...where, cell: TRI_AXIS_LABELS[tri] ?? tri };
        if (!c.state || !c.endpoint_adequacy) return fill(t.invalid.cell, cell);
        if (c.state !== "INDETERMINATE" && c.evidence.length === 0)
          return fill(t.invalid.evidence, cell);
      }
    }
    return null;
  };

  const submit = () => {
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      return;
    }
    const body: RunAuthorIn = {
      reason: reason.trim(),
      domains: AXES.map((axis) => {
        const d = draft[axis]!;
        return {
          domain_axis: axis as never,
          cis_status: d.cis_status as never,
          actionability_class: d.actionability_class as never,
          followup_adequacy: d.followup_adequacy as never,
          rationale: d.rationale.trim() || null,
          cells: TRI_AXES.map((tri) => {
            const c = d.cells[tri]!;
            return {
              tri_state_axis: tri as never,
              state: c.state,
              endpoint_adequacy: c.endpoint_adequacy as never,
              evidence_refs: c.evidence.map((id) => ({
                kind: "observation",
                id,
              })),
              rationale: c.rationale.trim() || null,
            };
          }),
        };
      }),
    };
    startTransition(async () => {
      const res = await authorRunAction(
        patientId,
        body,
        `/patients/${patientId}`,
      );
      if (!res.ok) {
        setError(res.error);
        return;
      }
      router.push(`/patients/${patientId}`);
    });
  };

  return (
    <div style={{ maxWidth: "980px" }}>
      <div style={{ marginBottom: "16px" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 800,
            fontSize: "var(--text-2xl, 26px)",
            color: "var(--text-strong)",
            margin: 0,
          }}
        >
          {prefill
            ? fill(t.titleCorrection, { run: runNumber ?? "" })
            : t.titleNew}
        </h1>
        <p
          style={{
            margin: "6px 0 0",
            fontSize: "13px",
            color: "var(--text-muted)",
            maxWidth: "88ch",
          }}
        >
          {t.lead}
        </p>
      </div>

      <div style={cardStyle}>
        <label style={labelStyle} htmlFor="run-reason">
          {t.reason}
        </label>
        <input
          id="run-reason"
          style={inputStyle}
          value={reason}
          maxLength={200}
          onChange={(e) => setReason(e.target.value)}
          placeholder={
            prefill ? t.reasonPlaceholderCorrection : t.reasonPlaceholderNew
          }
        />
      </div>

      {AXES.map((axis) => {
        const d = draft[axis]!;
        return (
          <section
            key={axis}
            style={cardStyle}
            aria-label={DOMAIN_AXIS_LABELS[axis] ?? axis}
          >
            <h2
              lang={GERMAN}
              style={{
                margin: "0 0 12px",
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "16px",
                color: "var(--text-strong)",
              }}
            >
              {DOMAIN_AXIS_LABELS[axis] ?? axis}
            </h2>
            {/* Three columns where they fit; on a phone they stack, so a chosen value is read
                whole instead of cut to a few letters. */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "12px",
              }}
            >
              <div>
                <label style={labelStyle} htmlFor={`${axis}-cis`}>
                  {t.cis}
                </label>
                <select
                  id={`${axis}-cis`}
                  style={selectStyle}
                  value={d.cis_status}
                  onChange={(e) =>
                    setDomain(axis, { cis_status: e.target.value })
                  }
                >
                  <option value="">{t.choose}</option>
                  {Object.keys(CIS_LABELS).map((k) => (
                    <option key={k} value={k} lang={GERMAN}>
                      {CIS_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelStyle} htmlFor={`${axis}-actionability`}>
                  {t.actionability}
                </label>
                <select
                  id={`${axis}-actionability`}
                  style={selectStyle}
                  value={d.actionability_class}
                  onChange={(e) =>
                    setDomain(axis, { actionability_class: e.target.value })
                  }
                >
                  <option value="">{t.choose}</option>
                  {Object.keys(ACTIONABILITY_LABELS).map((k) => (
                    <option key={k} value={k} lang={GERMAN}>
                      {ACTIONABILITY_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelStyle} htmlFor={`${axis}-followup`}>
                  {t.followup}
                </label>
                <select
                  id={`${axis}-followup`}
                  style={selectStyle}
                  value={d.followup_adequacy}
                  onChange={(e) =>
                    setDomain(axis, { followup_adequacy: e.target.value })
                  }
                >
                  <option value="">{t.choose}</option>
                  {Object.keys(ADEQUACY_LABELS).map((k) => (
                    <option key={k} value={k} lang={GERMAN}>
                      {ADEQUACY_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ marginTop: "10px" }}>
              <label style={labelStyle} htmlFor={`${axis}-rationale`}>
                {t.rationale}
              </label>
              <input
                id={`${axis}-rationale`}
                style={inputStyle}
                value={d.rationale}
                maxLength={2000}
                onChange={(e) => setDomain(axis, { rationale: e.target.value })}
              />
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "12px",
                marginTop: "14px",
              }}
            >
              {TRI_AXES.map((tri) => {
                const c = d.cells[tri]!;
                return (
                  <div
                    key={tri}
                    role="group"
                    aria-labelledby={`${axis}-${tri}-title`}
                    style={{
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                      padding: "12px",
                    }}
                  >
                    <div
                      id={`${axis}-${tri}-title`}
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        color: "var(--text-strong)",
                        marginBottom: "8px",
                      }}
                    >
                      <span lang={GERMAN}>{TRI_AXIS_LABELS[tri]}</span>{" "}
                      {t.verdictFree}
                    </div>
                    <label style={labelStyle} htmlFor={`${axis}-${tri}-state`}>
                      {t.state}
                    </label>
                    <select
                      id={`${axis}-${tri}-state`}
                      style={selectStyle}
                      value={c.state}
                      onChange={(e) =>
                        setCell(axis, tri, { state: e.target.value })
                      }
                    >
                      <option value="">{t.choose}</option>
                      {(CELL_STATES[tri] ?? []).map((s) => (
                        <option key={s} value={s} lang={GERMAN}>
                          {CELL_STATE_LABELS[s] ?? s}
                        </option>
                      ))}
                    </select>
                    <label
                      style={{ ...labelStyle, marginTop: "8px" }}
                      htmlFor={`${axis}-${tri}-endpoint`}
                    >
                      {t.endpoint}
                    </label>
                    <select
                      id={`${axis}-${tri}-endpoint`}
                      style={selectStyle}
                      value={c.endpoint_adequacy}
                      onChange={(e) =>
                        setCell(axis, tri, {
                          endpoint_adequacy: e.target.value,
                        })
                      }
                    >
                      <option value="">{t.choose}</option>
                      {Object.keys(ADEQUACY_LABELS).map((k) => (
                        <option key={k} value={k} lang={GERMAN}>
                          {ADEQUACY_LABELS[k]}
                        </option>
                      ))}
                    </select>
                    <details style={{ marginTop: "8px" }}>
                      <summary style={{ fontSize: "12px", cursor: "pointer" }}>
                        {fill(t.evidence, { n: c.evidence.length })}
                        {c.state &&
                        c.state !== "INDETERMINATE" &&
                        c.evidence.length === 0
                          ? t.evidenceRequired
                          : ""}
                      </summary>
                      <div
                        style={{
                          maxHeight: "160px",
                          overflowY: "auto",
                          marginTop: "6px",
                        }}
                      >
                        {evidenceOptions.length === 0 && (
                          <p
                            style={{
                              fontSize: "12px",
                              color: "var(--text-muted)",
                            }}
                          >
                            {t.noEvidence}
                          </p>
                        )}
                        {evidenceOptions.map((o) => (
                          <label
                            key={o.id}
                            style={{
                              display: "flex",
                              gap: "6px",
                              fontSize: "12px",
                              padding: "2px 0",
                              cursor: "pointer",
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={c.evidence.includes(o.id)}
                              onChange={(e) =>
                                setCell(axis, tri, {
                                  evidence: e.target.checked
                                    ? [...c.evidence, o.id]
                                    : c.evidence.filter((x) => x !== o.id),
                                })
                              }
                            />
                            <span>{o.label}</span>
                          </label>
                        ))}
                      </div>
                    </details>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      {error && (
        <p
          role="alert"
          style={{ color: "var(--danger, #b3261e)", fontSize: "13px" }}
        >
          {error}
        </p>
      )}
      <div
        style={{
          display: "flex",
          gap: "10px",
          justifyContent: "flex-end",
          marginBottom: "40px",
        }}
      >
        <button
          type="button"
          disabled={pending}
          onClick={() => router.push(`/patients/${patientId}`)}
          style={{
            height: "40px",
            padding: "0 16px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "var(--surface-card)",
            color: "var(--text-strong)",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {t.cancel}
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={submit}
          style={{
            height: "40px",
            padding: "0 18px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--brand)",
            background: "var(--brand)",
            color: "var(--text-on-brand)",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {pending ? t.submitting : t.submit}
        </button>
      </div>
    </div>
  );
}
