"use client";

import Link from "next/link";
import { useRef, useState, useTransition, type CSSProperties } from "react";

import type { SourceDocument } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import { useHydrated } from "@/lib/useHydrated";

import {
  importStoredDocumentAction,
  uploadLabFileAction,
  type LabImportResult,
} from "./lab-actions";

// Laboratory files of one patient (ingestion tier 1): upload a structured file, have it read
// into the import pipeline, and see what each stored file became. Counts and metadata only —
// values appear on the timeline and in the review queue, never here. Nothing is published
// without the pipeline's rules and, where they say so, a human decision.
//
// The card follows the interface language (lib/i18n); dates and sizes keep their German form
// (ADR-0007: formats are decided on their own).

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "10px 14px",
  fontFamily: "var(--font-mono)",
  fontSize: "9.5px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
  borderBottom: "1px solid var(--border-subtle)",
};

const tdStyle: CSSProperties = {
  padding: "11px 14px",
  fontSize: "12.5px",
  color: "var(--text-body)",
  borderBottom: "1px solid var(--border-subtle)",
  verticalAlign: "top",
};

const btnPri: CSSProperties = {
  height: "36px",
  padding: "0 14px",
  whiteSpace: "nowrap",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--brand)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
  fontFamily: "var(--font-text)",
  fontSize: "12.5px",
  fontWeight: 600,
  cursor: "pointer",
};

const btnSec: CSSProperties = {
  ...btnPri,
  height: "30px",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
};

interface Counts {
  published_count: number;
  review_count: number;
  duplicate_count: number;
  not_imported_count: number;
}

function countsLine(
  c: Counts,
  t: Messages["patientPage"]["lab"]["counts"],
): string {
  return [
    fill(t.published, { n: c.published_count }),
    fill(t.review, { n: c.review_count }),
    fill(t.duplicate, { n: c.duplicate_count }),
    fill(t.notImported, { n: c.not_imported_count }),
  ].join(" · ");
}

// On the clinic's wall clock, whatever zone the server or the reader's device is in: the same
// text on the server and in the browser, and the same time for everyone who reads the page.
function fmtWhen(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: CLINIC_TIME_ZONE,
  })}, ${d.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: CLINIC_TIME_ZONE,
  })}`;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024)
    return `${kb.toLocaleString("de-DE", { maximumFractionDigits: 1 })} kB`;
  return `${(kb / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} MB`;
}

export function LabDocumentsCard({
  patientId,
  documents,
  canImport,
}: {
  patientId: string;
  documents: SourceDocument[];
  canImport: boolean;
}) {
  const t = useI18n().t.patientPage.lab;
  const formRef = useRef<HTMLFormElement>(null);
  const [outcome, setOutcome] = useState<LabImportResult | null>(null);
  // The name of the chosen file, shown beside the button (the native control's own wording
  // follows the browser, not the page).
  const [fileName, setFileName] = useState<string | null>(null);
  // Until the page is hydrated the form would submit natively: a reload that drops the chosen
  // file and puts its name into the URL.
  const hydrated = useHydrated();
  const [pending, startTransition] = useTransition();

  const upload = (form: HTMLFormElement) => {
    const data = new FormData(form);
    startTransition(async () => {
      setOutcome(null);
      setOutcome(await uploadLabFileAction(patientId, data));
      formRef.current?.reset();
      setFileName(null);
    });
  };

  const readStored = (documentId: string) => {
    startTransition(async () => {
      setOutcome(null);
      setOutcome(await importStoredDocumentAction(patientId, documentId));
    });
  };

  return (
    <section
      style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}
      aria-labelledby="lab-documents-heading"
    >
      <div style={{ padding: "20px 22px 16px" }}>
        <h3
          id="lab-documents-heading"
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-lg)",
            color: "var(--text-strong)",
            margin: 0,
          }}
        >
          {t.title}
        </h3>
        <p
          style={{
            margin: "6px 0 0",
            fontSize: "12.5px",
            lineHeight: 1.5,
            color: "var(--text-muted)",
            maxWidth: "88ch",
          }}
        >
          {t.note}
        </p>

        {canImport ? (
          <form
            ref={formRef}
            onSubmit={(e) => {
              e.preventDefault();
              upload(e.currentTarget);
            }}
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "12px",
              marginTop: "14px",
            }}
          >
            <span className="vb-file">
              <input
                id="lab-file"
                type="file"
                name="file"
                required
                accept=".csv,.ldt,.txt"
                aria-label={t.choose}
                disabled={pending}
                onChange={(e) =>
                  setFileName(e.currentTarget.files?.[0]?.name ?? null)
                }
              />
              <label className="vb-ov-btn" htmlFor="lab-file">
                {t.choose}
              </label>
              <span
                className={`vb-file-name${fileName ? " is-chosen" : ""}`}
                aria-live="polite"
              >
                {fileName ?? t.noFile}
              </span>
            </span>
            <button
              type="submit"
              style={btnPri}
              disabled={pending || !hydrated}
            >
              {pending ? t.uploading : t.upload}
            </button>
          </form>
        ) : (
          <p
            style={{
              margin: "12px 0 0",
              fontSize: "12.5px",
              color: "var(--text-faint)",
            }}
          >
            {t.readOnly}
          </p>
        )}

        {outcome && outcome.ok && (
          <div
            role="status"
            style={{
              marginTop: "14px",
              padding: "10px 12px",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              background: "var(--surface-sunken)",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-strong)",
            }}
          >
            {outcome.result.created
              ? fill(t.read, {
                  parser: outcome.result.parser_name,
                  version: outcome.result.parser_version,
                })
              : t.readBefore}
            {countsLine(outcome.result, t.counts)}.
            {outcome.result.review_count > 0 && (
              <>
                {" "}
                <Link href="/review-queue">{t.toQueue}</Link>
              </>
            )}
          </div>
        )}
        {outcome && !outcome.ok && (
          <div
            role="alert"
            style={{
              marginTop: "14px",
              padding: "10px 12px",
              border: "1px solid var(--btn-danger-border)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-strong)",
            }}
          >
            {outcome.error}
            {outcome.stored && t.stored}
          </div>
        )}
      </div>

      {documents.length === 0 ? (
        <div
          style={{
            padding: "18px 22px 22px",
            fontSize: "12.5px",
            color: "var(--text-muted)",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          {t.none}
        </div>
      ) : (
        <>
          <table
            style={{ width: "100%", borderCollapse: "collapse" }}
            aria-label={t.table}
          >
            <thead>
              <tr>
                <th style={{ ...thStyle, paddingLeft: "22px" }}>
                  {t.columns.file}
                </th>
                <th style={thStyle}>{t.columns.uploaded}</th>
                <th style={thStyle}>{t.columns.reader}</th>
                <th style={{ ...thStyle, paddingRight: "22px" }}>
                  {t.columns.result}
                </th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td style={{ ...tdStyle, paddingLeft: "22px" }}>
                    <div
                      style={{
                        fontWeight: 600,
                        color: "var(--text-strong)",
                        wordBreak: "break-word",
                      }}
                    >
                      {doc.filename}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--text-faint)",
                      }}
                    >
                      {fmtSize(doc.byte_size)}
                    </div>
                  </td>
                  <td style={tdStyle}>{fmtWhen(doc.uploaded_at)}</td>
                  <td style={tdStyle}>
                    {doc.imported
                      ? `${doc.imported.parser_name} v${doc.imported.parser_version}`
                      : "—"}
                  </td>
                  <td style={{ ...tdStyle, paddingRight: "22px" }}>
                    {doc.imported ? (
                      countsLine(doc.imported, t.counts)
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>{t.storedNotRead}</span>
                        {canImport && (
                          <button
                            type="button"
                            style={btnSec}
                            disabled={pending}
                            onClick={() => readStored(doc.id)}
                          >
                            {t.readNow}
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p
            style={{
              margin: 0,
              padding: "10px 22px 16px",
              fontSize: "11.5px",
              lineHeight: 1.5,
              color: "var(--text-faint)",
            }}
          >
            {t.legend}
          </p>
        </>
      )}
    </section>
  );
}
