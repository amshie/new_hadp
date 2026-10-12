"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import { Dialog } from "@/components/vitabahn/Dialog";
import {
  addPatient,
  checkPatientDuplicates,
  createInvitationAction,
  type DuplicateCandidateView,
  type OnboardingConsent,
} from "@/app/patients/actions";
import { CONSENT_OPTIONS, type ConsentPurpose } from "@/lib/consentCopy";

// VitaBahn patient onboarding wizard (docs/notes/0011). Replaces the flat "+ Patient
// hinzufügen" form with a guided, validated flow:
//   1 Identität   — name / date of birth / external reference, inline validation
//   2 Einwilligung — optional in-person consent capture on the existing CLOSED purpose
//                    vocabulary (append-only ConsentEvent stream, recorded atomically
//                    with the create; the invitation link stays the patient-side path)
//   3 Prüfung      — review summary + tenant-scoped duplicate candidates; a STRONG
//                    match requires an explicit "create anyway" confirmation (the API
//                    enforces the same rule with 409 duplicate_patient)
//   ✓ Erfolg       — open record / mint invitation (one-time URL) / add another
// Draft state lives in React only — nothing is persisted client-side beyond the
// session, and closing with entered data asks before discarding.

const MIN_BIRTH_YEAR = 1900;
const STEPS = ["Identität", "Einwilligung", "Prüfung"] as const;

type Step = 1 | 2 | 3 | "done";

type DupState =
  | { status: "idle" }
  | { status: "pending"; forSig: string }
  | {
      status: "done";
      forSig: string;
      candidates: DuplicateCandidateView[];
      hasStrongMatch: boolean;
    }
  | { status: "failed"; forSig: string };

type InviteState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "done"; url: string; expiresAt: string }
  | { status: "failed"; error: string };

// ---- shared styles (VitaBahn tokens; inline styles are the vb idiom) ----

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
  boxSizing: "border-box",
};
const invalidInputStyle: CSSProperties = {
  ...inputStyle,
  border: "1px solid var(--rose-500)",
};
const fieldErrorStyle: CSSProperties = {
  display: "block",
  marginTop: "5px",
  fontSize: "12px",
  color: "var(--rose-500)",
};
const hintStyle: CSSProperties = {
  display: "block",
  marginTop: "5px",
  fontSize: "11.5px",
  color: "var(--text-faint)",
};
const baseBtn: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "8px",
  height: "38px",
  padding: "0 16px",
  borderRadius: "var(--radius-sm)",
  fontFamily: "var(--font-text)",
  fontSize: "13.5px",
  fontWeight: 600,
  cursor: "pointer",
};
const btnPrimary: CSSProperties = {
  ...baseBtn,
  border: "1px solid var(--brand-border)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
};
const btnSecondary: CSSProperties = {
  ...baseBtn,
  border: "1px solid var(--border-default)",
  background: "transparent",
  color: "var(--text-body)",
};
const alertStyle: CSSProperties = {
  fontSize: "12.5px",
  color: "var(--rose-500)",
  background: "rgba(194,74,74,0.10)",
  border: "1px solid rgba(194,74,74,0.30)",
  borderRadius: "var(--radius-sm)",
  padding: "9px 12px",
  marginBottom: "14px",
};

function formatDateDe(iso: string | null): string {
  if (!iso) return "—";
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

function ageFrom(dobIso: string): number | null {
  const dob = new Date(`${dobIso}T00:00:00`);
  if (Number.isNaN(dob.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const beforeBirthday =
    now.getMonth() < dob.getMonth() ||
    (now.getMonth() === dob.getMonth() && now.getDate() < dob.getDate());
  if (beforeBirthday) age -= 1;
  return age >= 0 ? age : null;
}

const MATCH_LABEL: Record<DuplicateCandidateView["matchBasis"], string> = {
  external_ref: "Gleiche externe ID",
  name_dob: "Name + Geburtsdatum",
  name: "Gleicher Name",
};

function StepIndicator({ step }: { step: Step }) {
  const activeIndex = step === "done" ? STEPS.length : step - 1;
  return (
    <ol
      aria-label="Schritte"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        listStyle: "none",
        margin: "0 0 20px",
        padding: 0,
      }}
    >
      {STEPS.map((label, i) => {
        const done = i < activeIndex;
        const active = i === activeIndex;
        return (
          <li
            key={label}
            aria-current={active ? "step" : undefined}
            aria-label={`${i + 1}. ${label}${done ? " – abgeschlossen" : ""}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "7px",
              flex: i < STEPS.length - 1 ? 1 : "none",
              minWidth: 0,
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: "22px",
                height: "22px",
                flexShrink: 0,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "999px",
                fontFamily: "var(--font-mono)",
                fontSize: "10.5px",
                fontWeight: 600,
                color: done
                  ? "var(--text-on-brand)"
                  : active
                    ? "var(--brand)"
                    : "var(--text-faint)",
                background: done
                  ? "var(--brand)"
                  : active
                    ? "var(--brand-soft)"
                    : "var(--surface-sunken)",
                border:
                  "1px solid " +
                  (done || active
                    ? "var(--brand-border)"
                    : "var(--border-default)"),
              }}
            >
              {done ? "✓" : i + 1}
            </span>
            <span
              style={{
                fontSize: "11.5px",
                fontWeight: 600,
                whiteSpace: "nowrap",
                color: active
                  ? "var(--text-strong)"
                  : done
                    ? "var(--text-body)"
                    : "var(--text-faint)",
              }}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <span
                aria-hidden="true"
                style={{
                  flex: 1,
                  height: "1px",
                  minWidth: "12px",
                  margin: "0 4px",
                  background: done
                    ? "var(--brand-border)"
                    : "var(--border-subtle)",
                }}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function AddPatientDialog({
  trigger,
}: {
  // Optional custom trigger (e.g. the empty-state CTA); defaults to the header button.
  trigger?: (open: () => void) => ReactNode;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>(1);
  const [confirmDiscard, setConfirmDiscard] = useState(false);

  // Step 1 — identity.
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [ref, setRef] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    dob?: string;
    ref?: string;
  }>({});

  // Step 2 — consents (explicit opt-in; nothing preselected).
  const [consents, setConsents] = useState<Record<ConsentPurpose, boolean>>({
    report_release: false,
    data_source_connect: false,
    analytics: false,
  });

  // Step 3 — duplicates + submit.
  const [dup, setDup] = useState<DupState>({ status: "idle" });
  const [allowDuplicate, setAllowDuplicate] = useState(false);
  const [pending, setPending] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Success step.
  const [created, setCreated] = useState<{ id: string; name: string } | null>(
    null,
  );
  const [invite, setInvite] = useState<InviteState>({ status: "idle" });
  const [copied, setCopied] = useState(false);

  const nameRef = useRef<HTMLInputElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const discardCancelRef = useRef<HTMLButtonElement>(null);
  // Bumped on close/reset so async results that land late are dropped, never applied
  // to a closed or reused dialog.
  const reqId = useRef(0);

  const todayIso = new Date().toISOString().slice(0, 10);
  const dirty =
    name !== "" ||
    dob !== "" ||
    ref !== "" ||
    Object.values(consents).some(Boolean);

  const dupSig = `${name.trim().toLowerCase()}|${dob}|${ref.trim()}`;

  function resetAll() {
    reqId.current += 1;
    setStep(1);
    setConfirmDiscard(false);
    setName("");
    setDob("");
    setRef("");
    setFieldErrors({});
    setConsents({
      report_release: false,
      data_source_connect: false,
      analytics: false,
    });
    setDup({ status: "idle" });
    setAllowDuplicate(false);
    setPending(false);
    setSubmitError(null);
    setCreated(null);
    setInvite({ status: "idle" });
    setCopied(false);
  }

  function hardClose() {
    reqId.current += 1;
    setOpen(false);
  }

  // Escape / backdrop-independent close request: entered data is never discarded
  // silently — a dirty wizard asks first (a second Escape confirms).
  function requestClose() {
    if (step === "done" || !dirty) {
      hardClose();
      return;
    }
    if (confirmDiscard) {
      hardClose();
      return;
    }
    setConfirmDiscard(true);
  }

  // Move focus with the step: data entry starts in the name field, later steps start
  // at their heading (the Dialog primitive handles initial mount + focus return).
  const mounted = useRef(false);
  useEffect(() => {
    if (!open) {
      mounted.current = false;
      return;
    }
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    if (step === 1) nameRef.current?.focus();
    else headingRef.current?.focus();
  }, [step, open]);

  // The discard prompt replaces the form: move focus onto its safe default so keyboard
  // users are not left on an unmounted control (and back when they keep editing).
  useEffect(() => {
    if (!open) return;
    if (confirmDiscard) discardCancelRef.current?.focus();
    else if (mounted.current) {
      if (step === 1) nameRef.current?.focus();
      else headingRef.current?.focus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmDiscard]);

  function validateIdentity(): boolean {
    const errors: { name?: string; dob?: string; ref?: string } = {};
    if (!name.trim()) errors.name = "Bitte einen Namen angeben.";
    else if (name.trim().length > 200)
      errors.name = "Der Name darf höchstens 200 Zeichen haben.";
    if (dob) {
      if (dob > todayIso)
        errors.dob = "Das Geburtsdatum darf nicht in der Zukunft liegen.";
      else if (Number(dob.slice(0, 4)) < MIN_BIRTH_YEAR)
        errors.dob = `Bitte ein Geburtsdatum ab ${MIN_BIRTH_YEAR} angeben.`;
    }
    if (ref.trim().length > 120)
      errors.ref = "Die externe ID darf höchstens 120 Zeichen haben.";
    setFieldErrors(errors);
    if (errors.name) nameRef.current?.focus();
    return Object.keys(errors).length === 0;
  }

  // Fire-and-store duplicate probe; step 3 waits for it before enabling submit. The
  // probe is a UX aid — the API enforces the strong-duplicate rule on create anyway.
  function runDuplicateCheck(sig: string) {
    const myReq = reqId.current;
    setDup({ status: "pending", forSig: sig });
    setAllowDuplicate(false);
    void checkPatientDuplicates({
      display_name: name,
      date_of_birth: dob || null,
      external_ref: ref || null,
    }).then((res) => {
      if (reqId.current !== myReq) return;
      if (res.ok)
        setDup({
          status: "done",
          forSig: sig,
          candidates: res.candidates,
          hasStrongMatch: res.hasStrongMatch,
        });
      else setDup({ status: "failed", forSig: sig });
    });
  }

  function goNext() {
    setSubmitError(null);
    if (step === 1) {
      if (!validateIdentity()) return;
      if (dup.status === "idle" || ("forSig" in dup && dup.forSig !== dupSig))
        runDuplicateCheck(dupSig);
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    }
  }

  function goBack() {
    setSubmitError(null);
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  }

  async function submit() {
    if (pending) return;
    const myReq = (reqId.current += 1);
    setPending(true);
    setSubmitError(null);
    const chosen: OnboardingConsent[] = CONSENT_OPTIONS.filter(
      (o) => consents[o.purpose],
    ).map((o) => ({ purpose: o.purpose, channel: "in_person" }));
    const result = await addPatient({
      display_name: name,
      external_ref: ref || null,
      date_of_birth: dob || null,
      consents: chosen,
      allow_duplicate: allowDuplicate,
    });
    if (reqId.current !== myReq) return;
    setPending(false);
    if (result.ok) {
      setCreated({ id: result.id, name: name.trim() });
      setStep("done");
      router.refresh();
      return;
    }
    if (result.code === "duplicate_patient") {
      // Race with a parallel create: refresh the candidates and require the explicit
      // confirmation again — never a silent retry.
      runDuplicateCheck(dupSig);
    }
    setSubmitError(result.error);
  }

  async function mintInvitation() {
    if (!created || invite.status === "pending") return;
    const myReq = reqId.current;
    setInvite({ status: "pending" });
    const res = await createInvitationAction(created.id);
    if (reqId.current !== myReq) return;
    if (res.ok)
      setInvite({ status: "done", url: res.url, expiresAt: res.expiresAt });
    else setInvite({ status: "failed", error: res.error });
  }

  async function copyInviteUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable (permissions): the URL stays selectable in the field.
    }
  }

  const dupReady = dup.status === "done" && dup.forSig === dupSig;
  const dupStale =
    (dup.status === "done" || dup.status === "failed") && dup.forSig !== dupSig;
  const strongMatch = dupReady && dup.hasStrongMatch;
  const submitBlocked =
    pending ||
    dup.status === "pending" ||
    dupStale ||
    dup.status === "idle" ||
    (strongMatch && !allowDuplicate);

  // Re-probe when the user edited identity fields after the last check and returns to
  // the review step (goNext from step 1 also handles the common path).
  useEffect(() => {
    if (open && step === 3 && dupStale && !pending) runDuplicateCheck(dupSig);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, dupStale, open]);

  const selectedConsents = CONSENT_OPTIONS.filter((o) => consents[o.purpose]);

  const summaryRow = (label: string, value: ReactNode) => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "140px 1fr",
        gap: "12px",
        padding: "9px 0",
        borderBottom: "1px solid var(--border-subtle)",
        fontSize: "13px",
      }}
    >
      <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ color: "var(--text-strong)", minWidth: 0 }}>{value}</span>
    </div>
  );

  const openWizard = () => {
    resetAll();
    setOpen(true);
  };

  return (
    <>
      {trigger ? (
        trigger(openWizard)
      ) : (
        <button type="button" onClick={openWizard} style={btnPrimary}>
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
      )}

      {open && (
        <Dialog
          onClose={requestClose}
          labelledBy="add-patient-title"
          describedBy="add-patient-subtitle"
          initialFocusRef={nameRef}
          closeOnBackdrop={false}
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(15,23,28,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "100%",
            maxWidth: "560px",
            maxHeight: "min(86vh, 760px)",
            overflowY: "auto",
            background: "var(--surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-lg)",
            padding: "24px",
          }}
        >
          {confirmDiscard ? (
            <div>
              <h2
                id="add-patient-title"
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                  margin: "0 0 6px",
                }}
              >
                Eingaben verwerfen?
              </h2>
              <p
                id="add-patient-subtitle"
                style={{
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  margin: "0 0 18px",
                  lineHeight: 1.5,
                }}
              >
                Die bisherigen Angaben werden nicht gespeichert.
              </p>
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  ref={discardCancelRef}
                  onClick={() => setConfirmDiscard(false)}
                  style={btnSecondary}
                >
                  Weiter bearbeiten
                </button>
                <button
                  type="button"
                  onClick={hardClose}
                  style={{
                    ...baseBtn,
                    border: "1px solid rgba(194,74,74,0.45)",
                    background: "rgba(194,74,74,0.10)",
                    color: "var(--rose-500)",
                  }}
                >
                  Verwerfen
                </button>
              </div>
            </div>
          ) : step === "done" && created ? (
            <div>
              <div
                aria-hidden="true"
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "999px",
                  background: "var(--brand-soft)",
                  border: "1px solid var(--brand-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "12px",
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--brand)"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
              <h2
                id="add-patient-title"
                ref={headingRef}
                tabIndex={-1}
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                  margin: "0 0 4px",
                  outline: "none",
                }}
              >
                Patient angelegt
              </h2>
              <p
                id="add-patient-subtitle"
                style={{
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  margin: "0 0 16px",
                  lineHeight: 1.5,
                }}
              >
                <span style={{ color: "var(--text-strong)", fontWeight: 600 }}>
                  {created.name}
                </span>{" "}
                · synthetischer Demodatensatz ·{" "}
                {selectedConsents.length > 0
                  ? `${selectedConsents.length} Einwilligung${selectedConsents.length === 1 ? "" : "en"} dokumentiert`
                  : "keine Einwilligungen dokumentiert"}
                .
              </p>

              <div
                style={{
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px 16px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    fontSize: "12.5px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                    marginBottom: "4px",
                  }}
                >
                  Einladung zur eigenständigen Einwilligung
                </div>
                <p
                  style={{
                    fontSize: "12.5px",
                    color: "var(--text-muted)",
                    margin: "0 0 10px",
                    lineHeight: 1.5,
                  }}
                >
                  Die Person kann Einwilligungen auch selbst über einen
                  einmaligen Einladungslink erteilen.
                </p>
                {invite.status === "done" ? (
                  <div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <input
                        className="vb-input"
                        type="text"
                        readOnly
                        value={invite.url}
                        aria-label="Einladungslink"
                        onFocus={(e) => e.currentTarget.select()}
                        style={{
                          ...inputStyle,
                          fontFamily: "var(--font-mono)",
                          fontSize: "11.5px",
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => void copyInviteUrl(invite.url)}
                        style={{ ...btnSecondary, flexShrink: 0 }}
                      >
                        {copied ? "Kopiert" : "Kopieren"}
                      </button>
                    </div>
                    <span style={hintStyle}>
                      Gültig bis{" "}
                      {new Date(invite.expiresAt).toLocaleString("de-DE", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}{" "}
                      · wird nur einmal angezeigt — bitte sicher und persönlich
                      übermitteln.
                    </span>
                  </div>
                ) : (
                  <div>
                    <button
                      type="button"
                      onClick={() => void mintInvitation()}
                      disabled={invite.status === "pending"}
                      style={{
                        ...btnSecondary,
                        opacity: invite.status === "pending" ? 0.7 : 1,
                      }}
                    >
                      {invite.status === "pending"
                        ? "Wird erstellt …"
                        : "Einladungslink erstellen"}
                    </button>
                    {invite.status === "failed" && (
                      <span role="alert" style={fieldErrorStyle}>
                        {invite.error}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "10px",
                  flexWrap: "wrap",
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    resetAll();
                    setOpen(true);
                  }}
                  style={btnSecondary}
                >
                  Weitere Person anlegen
                </button>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={hardClose}
                    style={btnSecondary}
                  >
                    Schließen
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const id = created.id;
                      hardClose();
                      router.push(`/patients/${id}`);
                    }}
                    style={btnPrimary}
                  >
                    Akte öffnen
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div>
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
                id="add-patient-subtitle"
                style={{
                  fontSize: "12.5px",
                  color: "var(--text-muted)",
                  margin: "0 0 16px",
                }}
              >
                Synthetische Demodaten · kein realer Patient.
              </p>

              <StepIndicator step={step} />

              {step === 1 && (
                // noValidate: the wizard owns validation (styled German inline messages);
                // the native required/min/max attributes stay for semantics and pickers.
                <form
                  noValidate
                  onSubmit={(e) => {
                    e.preventDefault();
                    goNext();
                  }}
                >
                  <h3
                    ref={headingRef}
                    tabIndex={-1}
                    style={{
                      fontSize: "13.5px",
                      fontWeight: 700,
                      color: "var(--text-strong)",
                      margin: "0 0 12px",
                      outline: "none",
                    }}
                  >
                    Identität &amp; Stammdaten
                  </h3>
                  <div style={{ marginBottom: "14px" }}>
                    <label htmlFor="ap-name" style={labelStyle}>
                      Name{" "}
                      <span
                        aria-hidden="true"
                        style={{ color: "var(--rose-500)" }}
                      >
                        *
                      </span>
                    </label>
                    <input
                      id="ap-name"
                      ref={nameRef}
                      className="vb-input"
                      type="text"
                      required
                      aria-invalid={fieldErrors.name ? true : undefined}
                      aria-describedby={
                        fieldErrors.name ? "ap-name-error" : undefined
                      }
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        if (fieldErrors.name)
                          setFieldErrors((f) => ({ ...f, name: undefined }));
                      }}
                      placeholder="z. B. Maria Beispiel"
                      style={fieldErrors.name ? invalidInputStyle : inputStyle}
                    />
                    {fieldErrors.name && (
                      <span
                        id="ap-name-error"
                        role="alert"
                        style={fieldErrorStyle}
                      >
                        {fieldErrors.name}
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      marginBottom: "6px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: "180px" }}>
                      <label htmlFor="ap-dob" style={labelStyle}>
                        Geburtsdatum{" "}
                        <span
                          style={{
                            color: "var(--text-faint)",
                            fontWeight: 500,
                          }}
                        >
                          (optional)
                        </span>
                      </label>
                      <input
                        id="ap-dob"
                        className="vb-input"
                        type="date"
                        max={todayIso}
                        min={`${MIN_BIRTH_YEAR}-01-01`}
                        aria-invalid={fieldErrors.dob ? true : undefined}
                        aria-describedby={
                          fieldErrors.dob ? "ap-dob-error" : undefined
                        }
                        value={dob}
                        onChange={(e) => {
                          setDob(e.target.value);
                          if (fieldErrors.dob)
                            setFieldErrors((f) => ({ ...f, dob: undefined }));
                        }}
                        style={fieldErrors.dob ? invalidInputStyle : inputStyle}
                      />
                      {fieldErrors.dob && (
                        <span
                          id="ap-dob-error"
                          role="alert"
                          style={fieldErrorStyle}
                        >
                          {fieldErrors.dob}
                        </span>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: "180px" }}>
                      <label htmlFor="ap-ref" style={labelStyle}>
                        Externe ID{" "}
                        <span
                          style={{
                            color: "var(--text-faint)",
                            fontWeight: 500,
                          }}
                        >
                          (optional)
                        </span>
                      </label>
                      <input
                        id="ap-ref"
                        className="vb-input"
                        type="text"
                        aria-invalid={fieldErrors.ref ? true : undefined}
                        aria-describedby={
                          fieldErrors.ref ? "ap-ref-error" : "ap-ref-hint"
                        }
                        value={ref}
                        onChange={(e) => {
                          setRef(e.target.value);
                          if (fieldErrors.ref)
                            setFieldErrors((f) => ({ ...f, ref: undefined }));
                        }}
                        placeholder="z. B. SYN-0042"
                        style={fieldErrors.ref ? invalidInputStyle : inputStyle}
                      />
                      {fieldErrors.ref ? (
                        <span
                          id="ap-ref-error"
                          role="alert"
                          style={fieldErrorStyle}
                        >
                          {fieldErrors.ref}
                        </span>
                      ) : (
                        <span id="ap-ref-hint" style={hintStyle}>
                          Referenz Ihres Praxissystems.
                        </span>
                      )}
                    </div>
                  </div>
                  <p style={{ ...hintStyle, margin: "0 0 16px" }}>
                    Vor dem Anlegen wird im Mandanten auf mögliche Duplikate
                    geprüft.
                  </p>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: "10px",
                    }}
                  >
                    <button
                      type="button"
                      onClick={requestClose}
                      style={btnSecondary}
                    >
                      Abbrechen
                    </button>
                    <button type="submit" style={btnPrimary}>
                      Weiter
                    </button>
                  </div>
                </form>
              )}

              {step === 2 && (
                <div>
                  <h3
                    ref={headingRef}
                    tabIndex={-1}
                    style={{
                      fontSize: "13.5px",
                      fontWeight: 700,
                      color: "var(--text-strong)",
                      margin: "0 0 4px",
                      outline: "none",
                    }}
                  >
                    Einwilligungen{" "}
                    <span
                      style={{ color: "var(--text-faint)", fontWeight: 500 }}
                    >
                      (optional)
                    </span>
                  </h3>
                  <p
                    style={{
                      fontSize: "12.5px",
                      color: "var(--text-muted)",
                      margin: "0 0 14px",
                      lineHeight: 1.55,
                    }}
                  >
                    Vor Ort erteilte Einwilligungen werden mit Zeitstempel,
                    Zweck und erfassender Person dokumentiert (unveränderliches
                    Protokoll). Alternativ kann die Person sie später selbst
                    über den Einladungslink erteilen.
                  </p>
                  <div
                    style={{
                      display: "grid",
                      gap: "8px",
                      marginBottom: "14px",
                    }}
                  >
                    {CONSENT_OPTIONS.map((o) => {
                      const checked = consents[o.purpose];
                      return (
                        <label
                          key={o.purpose}
                          style={{
                            display: "flex",
                            gap: "10px",
                            alignItems: "flex-start",
                            padding: "11px 12px",
                            borderRadius: "var(--radius-md)",
                            border:
                              "1px solid " +
                              (checked
                                ? "var(--brand-border)"
                                : "var(--border-subtle)"),
                            background: checked
                              ? "var(--brand-soft)"
                              : "var(--surface-sunken)",
                            cursor: "pointer",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) =>
                              setConsents((c) => ({
                                ...c,
                                [o.purpose]: e.target.checked,
                              }))
                            }
                            style={{
                              marginTop: "2px",
                              accentColor: "var(--brand)",
                            }}
                          />
                          <span style={{ minWidth: 0 }}>
                            <span
                              style={{
                                display: "block",
                                fontSize: "13px",
                                fontWeight: 600,
                                color: "var(--text-strong)",
                              }}
                            >
                              {o.label}
                            </span>
                            <span
                              style={{
                                display: "block",
                                fontSize: "12px",
                                color: "var(--text-muted)",
                                lineHeight: 1.5,
                              }}
                            >
                              {o.desc}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                  <p style={{ ...hintStyle, margin: "0 0 16px" }}>
                    Erfassung: persönlich vor Ort · Zweckkatalog der
                    Pilotumgebung (synthetische Daten).
                  </p>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: "10px",
                    }}
                  >
                    <button type="button" onClick={goBack} style={btnSecondary}>
                      Zurück
                    </button>
                    <button type="button" onClick={goNext} style={btnPrimary}>
                      Weiter
                    </button>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div>
                  <h3
                    ref={headingRef}
                    tabIndex={-1}
                    style={{
                      fontSize: "13.5px",
                      fontWeight: 700,
                      color: "var(--text-strong)",
                      margin: "0 0 12px",
                      outline: "none",
                    }}
                  >
                    Prüfen &amp; Bestätigen
                  </h3>
                  <div style={{ marginBottom: "16px" }}>
                    {summaryRow("Name", name.trim())}
                    {summaryRow(
                      "Geburtsdatum",
                      dob ? (
                        <>
                          {formatDateDe(dob)}
                          {ageFrom(dob) !== null && (
                            <span style={{ color: "var(--text-muted)" }}>
                              {" "}
                              · {ageFrom(dob)} Jahre
                            </span>
                          )}
                        </>
                      ) : (
                        "—"
                      ),
                    )}
                    {summaryRow(
                      "Externe ID",
                      ref.trim() ? (
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "12.5px",
                          }}
                        >
                          {ref.trim()}
                        </span>
                      ) : (
                        "—"
                      ),
                    )}
                    {summaryRow(
                      "Einwilligungen",
                      selectedConsents.length > 0 ? (
                        <span
                          style={{
                            display: "flex",
                            gap: "6px",
                            flexWrap: "wrap",
                          }}
                        >
                          {selectedConsents.map((o) => (
                            <span
                              key={o.purpose}
                              style={{
                                display: "inline-flex",
                                padding: "2px 9px",
                                borderRadius: "999px",
                                fontSize: "11.5px",
                                fontWeight: 600,
                                color: "var(--brand)",
                                background: "var(--brand-soft)",
                                border: "1px solid var(--brand-border)",
                              }}
                            >
                              {o.label}
                            </span>
                          ))}
                        </span>
                      ) : (
                        "Keine dokumentiert"
                      ),
                    )}
                  </div>

                  {/* Duplicate panel */}
                  {dup.status === "pending" || dupStale ? (
                    <div
                      style={{
                        fontSize: "12.5px",
                        color: "var(--text-muted)",
                        border: "1px dashed var(--border-default)",
                        borderRadius: "var(--radius-md)",
                        padding: "10px 12px",
                        marginBottom: "14px",
                      }}
                    >
                      Duplikatprüfung läuft …
                    </div>
                  ) : dup.status === "failed" ? (
                    <div
                      role="status"
                      style={{
                        fontSize: "12.5px",
                        color: "var(--text-muted)",
                        border: "1px solid var(--border-default)",
                        borderRadius: "var(--radius-md)",
                        padding: "10px 12px",
                        marginBottom: "14px",
                      }}
                    >
                      Duplikatprüfung derzeit nicht verfügbar.{" "}
                      <button
                        type="button"
                        onClick={() => runDuplicateCheck(dupSig)}
                        style={{
                          border: "none",
                          background: "none",
                          padding: 0,
                          color: "var(--brand)",
                          fontWeight: 600,
                          fontSize: "12.5px",
                          cursor: "pointer",
                          textDecoration: "underline",
                        }}
                      >
                        Erneut prüfen
                      </button>
                    </div>
                  ) : dupReady && dup.candidates.length > 0 ? (
                    <div
                      role="alert"
                      style={{
                        border:
                          "1px solid " +
                          (dup.hasStrongMatch
                            ? "rgba(194,74,74,0.35)"
                            : "rgba(191,146,42,0.4)"),
                        background: dup.hasStrongMatch
                          ? "rgba(194,74,74,0.07)"
                          : "rgba(191,146,42,0.08)",
                        borderRadius: "var(--radius-md)",
                        padding: "12px 14px",
                        marginBottom: "14px",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "12.5px",
                          fontWeight: 700,
                          color: "var(--text-strong)",
                          marginBottom: "6px",
                        }}
                      >
                        {dup.hasStrongMatch
                          ? "Möglicherweise bereits vorhanden"
                          : "Ähnlicher Eintrag im Mandanten"}
                      </div>
                      <div style={{ display: "grid", gap: "6px" }}>
                        {dup.candidates.map((c) => (
                          <div
                            key={c.id}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "10px",
                              flexWrap: "wrap",
                              fontSize: "12.5px",
                              padding: "7px 10px",
                              borderRadius: "var(--radius-sm)",
                              background: "var(--surface-card)",
                              border: "1px solid var(--border-subtle)",
                            }}
                          >
                            <span
                              style={{
                                fontWeight: 600,
                                color: "var(--text-strong)",
                              }}
                            >
                              {c.displayName}
                            </span>
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "11px",
                                color: "var(--text-muted)",
                              }}
                            >
                              {formatDateDe(c.dateOfBirth)}
                              {c.externalRef ? ` · ${c.externalRef}` : ""}
                            </span>
                            <span
                              style={{
                                fontSize: "10.5px",
                                fontWeight: 600,
                                padding: "1px 7px",
                                borderRadius: "999px",
                                color: "var(--text-muted)",
                                background: "var(--surface-sunken)",
                                border: "1px solid var(--border-default)",
                              }}
                            >
                              {MATCH_LABEL[c.matchBasis]}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                const id = c.id;
                                hardClose();
                                router.push(`/patients/${id}`);
                              }}
                              style={{
                                marginLeft: "auto",
                                border: "none",
                                background: "none",
                                padding: 0,
                                color: "var(--brand)",
                                fontWeight: 600,
                                fontSize: "12px",
                                cursor: "pointer",
                                textDecoration: "underline",
                              }}
                            >
                              Akte öffnen
                            </button>
                          </div>
                        ))}
                      </div>
                      {dup.hasStrongMatch && (
                        <label
                          style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "flex-start",
                            marginTop: "10px",
                            fontSize: "12.5px",
                            color: "var(--text-strong)",
                            cursor: "pointer",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={allowDuplicate}
                            onChange={(e) =>
                              setAllowDuplicate(e.target.checked)
                            }
                            style={{
                              marginTop: "2px",
                              accentColor: "var(--rose-500)",
                            }}
                          />
                          <span>
                            Trotzdem neu anlegen — es handelt sich um eine
                            andere Person.
                          </span>
                        </label>
                      )}
                    </div>
                  ) : dupReady ? (
                    <div
                      style={{
                        fontSize: "12.5px",
                        color: "var(--text-muted)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                        padding: "10px 12px",
                        marginBottom: "14px",
                      }}
                    >
                      Keine Übereinstimmungen im Mandanten gefunden.
                    </div>
                  ) : null}

                  {submitError && (
                    <div role="alert" style={alertStyle}>
                      {submitError}
                    </div>
                  )}

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: "10px",
                    }}
                  >
                    <button
                      type="button"
                      onClick={goBack}
                      disabled={pending}
                      style={{
                        ...btnSecondary,
                        cursor: pending ? "default" : "pointer",
                      }}
                    >
                      Zurück
                    </button>
                    <button
                      type="button"
                      onClick={() => void submit()}
                      disabled={submitBlocked}
                      style={{
                        ...btnPrimary,
                        opacity: submitBlocked ? 0.6 : 1,
                        cursor: submitBlocked ? "default" : "pointer",
                      }}
                    >
                      {pending ? "Wird angelegt …" : "Patient anlegen"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </Dialog>
      )}
    </>
  );
}
