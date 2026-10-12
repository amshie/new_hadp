"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition, type CSSProperties } from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import type { DataExport } from "@/lib/api";

// Data export for one patient (GDPR Art. 15 access / Art. 20 portability) — the owner's tool
// to answer a data subject's request. The API builds the file on request and stores nothing;
// the list below is read from the audit trail. The card says what the file holds and what it
// leaves out, so nobody hands it over as more than it is.

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

const ERRORS: Record<string, string> = {
  patient_erased: "Diese Akte wurde gelöscht; es gibt nichts zu exportieren.",
  export_too_large:
    "Die gespeicherten Originaldateien sind zu groß für eine einzelne Datei.",
  storage_unavailable:
    "Eine gespeicherte Originaldatei konnte gerade nicht gelesen werden. Es wurde keine Datei erstellt — bitte später erneut versuchen.",
  cross_origin: "Die Anfrage wurde abgelehnt. Bitte die Seite neu laden.",
};

function errorMessage(status: number, code: string): string {
  if (ERRORS[code]) return ERRORS[code];
  if (status === 403) return "Diese Aktion ist Ihrer Rolle nicht erlaubt.";
  if (status === 404) return "Diese Akte ist nicht verfügbar.";
  if (status === 429)
    return "Zu viele Datenauskünfte in kurzer Zeit. Bitte später erneut versuchen.";
  return "Die Datenauskunft konnte nicht erstellt werden. Bitte erneut versuchen.";
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

export function DataExportCard({
  patientId,
  exports,
}: {
  patientId: string;
  exports: DataExport[];
}) {
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
        setError(errorMessage(0, ""));
        setConfirming(false);
        return;
      }
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { code?: string };
        setError(errorMessage(res.status, body.code ?? ""));
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
        setError(errorMessage(0, ""));
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
          Datenauskunft
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
          Eine Datei mit den zu dieser Person gespeicherten Daten, für eine
          Auskunft (Art. 15 DSGVO) oder eine Datenübertragung (Art. 20 DSGVO):
          Stammdaten, Einwilligungsvermerke, alle Werte, die in diese Akte
          eingelesenen Originaldateien und die freigegebenen Berichtsfassungen.{" "}
          <strong style={{ color: "var(--text-strong)" }}>
            Nicht enthalten
          </strong>{" "}
          sind unter anderem nicht freigegebene Berichtsfassungen, die
          Arbeitsdokumentation zur Interpretation, Prüfentscheidungen, das
          Audit-Protokoll, Angaben zum Personal und gespeicherte Dateien, die
          nie in diese Akte eingelesen wurden — die vollständige Liste steht in
          der Datei selbst. Ob diese Teile zu einer vollständigen Auskunft
          gehören, ist rechtlich noch zu klären.
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
            Datenauskunft erstellen
          </button>
          {done && (
            <span
              role="status"
              style={{ fontSize: "12.5px", color: "var(--text-strong)" }}
            >
              Datei erstellt und heruntergeladen.
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
          <span style={{ color: "var(--text-muted)" }}>
            Für diese Akte wurde noch keine Datenauskunft erstellt.
          </span>
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
              Bisher erstellt (aus dem Audit-Protokoll)
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {exports.map((entry) => (
                <li
                  key={`${entry.exported_at}-${entry.checksum_sha256}`}
                  style={{ padding: "4px 0", lineHeight: 1.5 }}
                >
                  {fmtWhen(entry.exported_at)} · {fmtSize(entry.byte_size)} ·{" "}
                  {entry.observations} Werte · {entry.source_files}{" "}
                  Originaldateien
                  {entry.source_files_missing + entry.source_files_changed >
                    0 &&
                    ` (${entry.source_files_missing + entry.source_files_changed} nicht mehr unverändert im Speicher)`}
                  {entry.source_documents_not_imported > 0 &&
                    ` (${entry.source_documents_not_imported} nie eingelesen, nicht enthalten)`}{" "}
                  · {entry.released_report_versions} Berichtsfassungen ·{" "}
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
            Datenauskunft erstellen?
          </h3>
          <p
            style={{
              margin: "10px 0 0",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            Die Datei enthält personenbezogene Gesundheitsdaten dieser Person
            und wird auf dieses Gerät heruntergeladen. Bewahren Sie sie
            geschützt auf und geben Sie sie nur an die betroffene Person weiter.
            Die Erstellung wird Ihnen zugeordnet und auditiert; in der Plattform
            wird keine Kopie der Datei gespeichert.
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
              Abbrechen
            </button>
            <button
              type="button"
              style={btnPri}
              disabled={pending}
              onClick={run}
            >
              {pending ? "Wird erstellt …" : "Erstellen und herunterladen"}
            </button>
          </div>
        </Dialog>
      )}
    </section>
  );
}
