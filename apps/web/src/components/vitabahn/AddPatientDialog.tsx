"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import { addPatient } from "@/app/patients/actions";

// VitaBahn "+ Patient hinzufügen". Opens an accessible modal (role=dialog, Escape, focus moved in
// on open + returned to the trigger on close) and creates a SYNTHETIC patient via the server
// action (the API forces is_synthetic=True). On success it revalidates and refreshes so the new
// patient appears in the worklist/directory without a manual reload.

const labelStyle: CSSProperties = {
  display: "block",
  fontSize: "12px",
  fontWeight: 600,
  color: "var(--text-body)",
  marginBottom: "5px",
};
const inputStyle: CSSProperties = {
  width: "100%",
  height: "38px",
  padding: "0 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-sunken)",
  color: "var(--text-strong)",
  fontFamily: "var(--font-text)",
  fontSize: "13.5px",
  outline: "none",
};

export function AddPatientDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [ref, setRef] = useState("");
  const [dob, setDob] = useState("");

  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  // Bumped on every close/submit so a server action that resolves AFTER the dialog was closed (or
  // superseded by a newer submit) is ignored — a stale error/refresh must not land on a closed dialog.
  const reqId = useRef(0);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        return;
      }
      if (e.key === "Tab") {
        // Focus trap: keep Tab/Shift+Tab inside the aria-modal dialog (WCAG 2.2).
        const dlg = dialogRef.current;
        if (!dlg) return;
        const list = Array.from(
          dlg.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        );
        const first = list[0];
        const last = list[list.length - 1];
        if (!first || !last) return;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    const t = window.setTimeout(() => firstFieldRef.current?.focus(), 30);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function reset() {
    setName("");
    setRef("");
    setDob("");
    setError(null);
  }
  function close() {
    reqId.current += 1; // invalidate any in-flight submit
    setOpen(false);
    setPending(false);
    triggerRef.current?.focus();
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Bitte einen Namen angeben.");
      return;
    }
    const myReq = (reqId.current += 1);
    setPending(true);
    setError(null);
    const result = await addPatient({
      display_name: name,
      external_ref: ref || null,
      date_of_birth: dob || null,
    });
    // Dialog was closed or a newer submit started while the action was in flight — drop this result.
    if (reqId.current !== myReq) return;
    if (result.ok) {
      reset();
      close();
      router.refresh();
    } else {
      setPending(false);
      setError(result.error);
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => {
          reset();
          setOpen(true);
        }}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          height: "38px",
          padding: "0 16px",
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
        <svg
          aria-hidden="true"
          focusable="false"
          width="15"
          height="15"
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

      {open && (
        <div
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) close();
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(15,23,28,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-patient-title"
            style={{
              width: "100%",
              maxWidth: "440px",
              background: "var(--surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-lg)",
              padding: "24px",
            }}
          >
            <h2
              id="add-patient-title"
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "var(--text-xl)",
                color: "var(--text-strong)",
                margin: "0 0 4px",
                letterSpacing: "-0.01em",
              }}
            >
              Patient hinzufügen
            </h2>
            <p
              style={{
                fontSize: "12.5px",
                color: "var(--text-muted)",
                margin: "0 0 18px",
              }}
            >
              Synthetische Demodaten · kein realer Patient.
            </p>

            <form onSubmit={submit}>
              <div style={{ marginBottom: "14px" }}>
                <label htmlFor="ap-name" style={labelStyle}>
                  Name <span style={{ color: "var(--rose-500)" }}>*</span>
                </label>
                <input
                  id="ap-name"
                  ref={firstFieldRef}
                  className="vb-input"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="z. B. Maria Beispiel"
                  style={inputStyle}
                />
              </div>
              <div
                style={{ display: "flex", gap: "12px", marginBottom: "14px" }}
              >
                <div style={{ flex: 1 }}>
                  <label htmlFor="ap-ref" style={labelStyle}>
                    Externe ID
                  </label>
                  <input
                    id="ap-ref"
                    className="vb-input"
                    type="text"
                    value={ref}
                    onChange={(e) => setRef(e.target.value)}
                    placeholder="optional"
                    style={inputStyle}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label htmlFor="ap-dob" style={labelStyle}>
                    Geburtsdatum
                  </label>
                  <input
                    id="ap-dob"
                    className="vb-input"
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    style={inputStyle}
                  />
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  style={{
                    fontSize: "12.5px",
                    color: "var(--rose-500)",
                    background: "rgba(194,74,74,0.10)",
                    border: "1px solid rgba(194,74,74,0.30)",
                    borderRadius: "var(--radius-sm)",
                    padding: "9px 12px",
                    marginBottom: "14px",
                  }}
                >
                  {error}
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                  marginTop: "4px",
                }}
              >
                <button
                  type="button"
                  onClick={close}
                  disabled={pending}
                  style={{
                    height: "38px",
                    padding: "0 16px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    background: "transparent",
                    color: "var(--text-body)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: pending ? "default" : "pointer",
                  }}
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  disabled={pending}
                  style={{
                    height: "38px",
                    padding: "0 18px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--brand-border)",
                    background: "var(--brand)",
                    color: "var(--text-on-brand)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: pending ? "default" : "pointer",
                    opacity: pending ? 0.7 : 1,
                  }}
                >
                  {pending ? "Wird angelegt …" : "Anlegen"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
