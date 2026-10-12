"use client";

import Link from "next/link";
import { useRef, useState, useTransition, type CSSProperties } from "react";

import type { SourceDocument } from "@/lib/api";

import {
  importStoredDocumentAction,
  uploadLabFileAction,
  type LabImportResult,
} from "./lab-actions";

// Laboratory files of one patient (ingestion tier 1): upload a structured file, have it read
// into the import pipeline, and see what each stored file became. Counts and metadata only —
// values appear on the timeline and in the review queue, never here. Nothing is published
// without the pipeline's rules and, where they say so, a human decision.

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

function countsLine(c: Counts): string {
  return [
    `${c.published_count} veröffentlicht`,
    `${c.review_count} zur Prüfung`,
    `${c.duplicate_count} bereits vorhanden`,
    `${c.not_imported_count} nicht übernommen`,
  ].join(" · ");
}

function fmtWhen(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })}, ${d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`;
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
  const formRef = useRef<HTMLFormElement>(null);
  const [outcome, setOutcome] = useState<LabImportResult | null>(null);
  const [pending, startTransition] = useTransition();

  const upload = (form: HTMLFormElement) => {
    const data = new FormData(form);
    startTransition(async () => {
      setOutcome(null);
      setOutcome(await uploadLabFileAction(patientId, data));
      formRef.current?.reset();
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
          Labordaten
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
          Strukturierte Labordatei (CSV im HADP-Layout, LDT 2 oder LDT 3) für
          genau diese Akte. Die Originaldatei wird gespeichert und dann
          eingelesen; die Werte werden unverändert übernommen. Nicht eindeutige
          Werte gehen in die Review-Queue — sie werden erst nach einer
          klinischen Entscheidung veröffentlicht.
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
            <input
              type="file"
              name="file"
              required
              accept=".csv,.ldt,.txt"
              aria-label="Labordatei wählen"
              disabled={pending}
              style={{ fontSize: "12.5px", color: "var(--text-body)" }}
            />
            <button type="submit" style={btnPri} disabled={pending}>
              {pending ? "Wird eingelesen …" : "Hochladen und einlesen"}
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
            Hochladen und Einlesen ist dem Praxisteam vorbehalten
            (Nur-Lese-Ansicht).
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
              ? `Eingelesen (${outcome.result.parser_name} v${outcome.result.parser_version}): `
              : "Diese Datei wurde bereits eingelesen — Ergebnis des ersten Einlesens: "}
            {countsLine(outcome.result)}.
            {outcome.result.review_count > 0 && (
              <>
                {" "}
                <Link href="/review-queue">Zur Review-Queue</Link>
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
            {outcome.stored &&
              " Die Originaldatei ist gespeichert und unten aufgeführt."}
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
          Für diese Akte ist noch keine Labordatei gespeichert.
        </div>
      ) : (
        <>
          <table
            style={{ width: "100%", borderCollapse: "collapse" }}
            aria-label="Gespeicherte Labordateien"
          >
            <thead>
              <tr>
                <th style={{ ...thStyle, paddingLeft: "22px" }}>Datei</th>
                <th style={thStyle}>Hochgeladen</th>
                <th style={thStyle}>Einleseprogramm</th>
                <th style={{ ...thStyle, paddingRight: "22px" }}>Ergebnis</th>
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
                      countsLine(doc.imported)
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>Gespeichert, nicht eingelesen</span>
                        {canImport && (
                          <button
                            type="button"
                            style={btnSec}
                            disabled={pending}
                            onClick={() => readStored(doc.id)}
                          >
                            Einlesen
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
            „Bereits vorhanden“: Der Wert liegt für diese Analyse und
            Abnahmezeit schon identisch vor und wurde nicht doppelt übernommen.
            „Nicht übernommen“: Ergebnis ohne Zahlenwert oder ohne Abnahmedatum
            (zum Beispiel Textbefund, noch ausstehend). Die Zahlen zeigen den
            Stand beim Einlesen.
          </p>
        </>
      )}
    </section>
  );
}
