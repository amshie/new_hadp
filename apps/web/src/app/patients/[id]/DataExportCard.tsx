"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition, type CSSProperties } from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import type { DataExport } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";

// Data export for one patient (GDPR Art. 15 access / Art. 20 portability) — the owner's tool
// to answer a data subject's request. The API builds the file on request and stores nothing;
// the list below is read from the audit trail. The card says what the file holds and what it
// leaves out, so nobody hands it over as more than it is.
//
// The card follows the interface language (lib/i18n); dates and sizes keep their German form
// (ADR-0007: formats are decided on their own).

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};

const btnSec: CSSProperties = {
  height: "36px",
  padding: "0 14px",
  whiteSpace: "nowrap",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
  fontFamily: "var(--font-text)",
  fontSize: "12.5px",
  fontWeight: 600,
  cursor: "pointer",
};

const btnPri: CSSProperties = {
  ...btnSec,
  border: "1px solid var(--brand)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
};

// Keyed by the code the route answers with (lib/i18n: patientPage.dataExport.errors).
function errorMessage(
  status: number,
  code: string,
  page: Messages["patientPage"],
): string {
  const t = page.dataExport.errors;
  const coded = [
    "patient_erased",
    "export_too_large",
    "storage_unavailable",
    "cross_origin",
  ] as const;
  const known = coded.find((c) => c === code);
  if (known) return t[known];
  if (status === 403) return page.notAllowed;
  if (status === 404) return page.recordUnavailable;
  if (status === 429) return t.tooMany;
  return t.failed;
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

export function DataExportCard({
  patientId,
  exports,
}: {
  patientId: string;
  exports: DataExport[];
}) {
  const page = useI18n().t.patientPage;
  const t = page.dataExport;
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pending, startTransition] = useTransition();

  const run = () => {
    startTransition(async () => {
      setError(null);
      setDone(false);
      let res: Response;
      try {
        res = await fetch(`/patients/${patientId}/datenauskunft`, {
          method: "POST",
        });
      } catch {
        setError(errorMessage(0, "", page));
        setConfirming(false);
        return;
      }
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { code?: string };
        setError(errorMessage(res.status, body.code ?? "", page));
        setConfirming(false);
        return;
      }
      // Hand the file to the browser's download; nothing is kept in the page afterwards.
      const name =
        /filename="([^"]+)"/.exec(
          res.headers.get("content-disposition") ?? "",
        )?.[1] ?? "datenauskunft.zip";
      let blob: Blob;
      try {
        blob = await res.blob();
      } catch {
        // The transfer broke off: no partial file is offered.
        setError(errorMessage(0, "", page));
        setConfirming(false);
        return;
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Give the browser time to start the download before the object URL goes away.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setConfirming(false);
      setDone(true);
      router.refresh();
    });
  };

  return (
    <section
      style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}
      aria-labelledby="data-export-heading"
    >
      <div style={{ padding: "20px 22px 16px" }}>
        <h3
          id="data-export-heading"
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
          {t.noteBefore}{" "}
          <strong style={{ color: "var(--text-strong)" }}>
            {t.notIncluded}
          </strong>{" "}
          {t.noteAfter}
        </p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "12px",
            marginTop: "14px",
          }}
        >
          <button
            type="button"
            style={btnPri}
            disabled={pending}
            onClick={() => {
              setError(null);
              setDone(false);
              setConfirming(true);
            }}
          >
            {t.create}
          </button>
          {done && (
            <span
              role="status"
              style={{ fontSize: "12.5px", color: "var(--text-strong)" }}
            >
              {t.done}
            </span>
          )}
        </div>
        {error && (
          <p
            role="alert"
            style={{
              margin: "12px 0 0",
              fontSize: "12.5px",
              color: "var(--danger, #b3261e)",
            }}
          >
            {error}
          </p>
        )}
      </div>

      <div
        style={{
          padding: "12px 22px 18px",
          borderTop: "1px solid var(--border-subtle)",
          fontSize: "12.5px",
          color: "var(--text-body)",
        }}
      >
        {exports.length === 0 ? (
          <span style={{ color: "var(--text-muted)" }}>{t.none}</span>
        ) : (
          <>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "9.5px",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--text-faint)",
                marginBottom: "6px",
              }}
            >
              {t.history}
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {exports.map((entry) => (
                <li
                  key={`${entry.exported_at}-${entry.checksum_sha256}`}
                  style={{ padding: "4px 0", lineHeight: 1.5 }}
                >
                  {fmtWhen(entry.exported_at)} · {fmtSize(entry.byte_size)} ·{" "}
                  {byCount(t.values, entry.observations)} ·{" "}
                  {byCount(t.files, entry.source_files)}
                  {entry.source_files_missing + entry.source_files_changed >
                    0 &&
                    fill(t.filesChanged, {
                      n:
                        entry.source_files_missing + entry.source_files_changed,
                    })}
                  {entry.source_documents_not_imported > 0 &&
                    fill(t.filesNeverRead, {
                      n: entry.source_documents_not_imported,
                    })}{" "}
                  · {byCount(t.versions, entry.released_report_versions)} ·{" "}
                  <span
                    title={entry.checksum_sha256}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--text-faint)",
                    }}
                  >
                    SHA-256 {entry.checksum_sha256.slice(0, 12)}…
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {confirming && (
        <Dialog
          onClose={() => setConfirming(false)}
          labelledBy="data-export-dialog-title"
          lockScroll
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "500px",
            maxWidth: "100%",
            ...cardStyle,
            padding: "22px",
          }}
        >
          <h3
            id="data-export-dialog-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: "var(--text-xl)",
              color: "var(--text-strong)",
              margin: 0,
            }}
          >
            {t.confirmTitle}
          </h3>
          <p
            style={{
              margin: "10px 0 0",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            {t.confirmNote}
          </p>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
              marginTop: "20px",
            }}
          >
            <button
              type="button"
              style={btnSec}
              disabled={pending}
              onClick={() => setConfirming(false)}
            >
              {page.cancel}
            </button>
            <button
              type="button"
              style={btnPri}
              disabled={pending}
              onClick={run}
            >
              {pending ? t.creating : t.confirm}
            </button>
          </div>
        </Dialog>
      )}
    </section>
  );
}
