"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Icon } from "@/components/Icon";
import { ToastProvider, useToast } from "@/components/Toaster";

import { login } from "./actions";

type AuthState = "signin" | "twofactor" | "locked" | "signedout";

function AuthInner() {
  const toast = useToast();
  const router = useRouter();
  const [state, setState] = useState<AuthState>("signin");
  const [email, setEmail] = useState("s.johnson@meridian-health.eu");
  const [showPassword, setShowPassword] = useState(false);
  const codeRefs = useRef<Array<HTMLInputElement | null>>([]);

  const goTwofactor = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!e.currentTarget.reportValidity()) return;
    setState("twofactor");
    window.setTimeout(() => codeRefs.current[0]?.focus(), 60);
  };

  const submitCode = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const code = codeRefs.current.map((i) => i?.value ?? "").join("");
    if (code.length !== 6) {
      toast("Bitte geben Sie alle sechs Ziffern ein.");
      return;
    }
    const result = await login(email);
    if (result && !result.ok) toast(result.error);
  };

  const onCodeInput = (index: number, value: string, el: HTMLInputElement) => {
    el.value = value.replace(/\D/g, "").slice(0, 1);
    if (el.value && index < 5) codeRefs.current[index + 1]?.focus();
  };
  const onCodeKey = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    const el = e.currentTarget;
    if (e.key === "Backspace" && !el.value && index > 0)
      codeRefs.current[index - 1]?.focus();
    if (e.key === "ArrowLeft" && index > 0)
      codeRefs.current[index - 1]?.focus();
    if (e.key === "ArrowRight" && index < 5)
      codeRefs.current[index + 1]?.focus();
  };
  const onCodePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const digits = (e.clipboardData.getData("text") || "")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!digits) return;
    e.preventDefault();
    digits.split("").forEach((d, i) => {
      const el = codeRefs.current[i];
      if (el) el.value = d;
    });
    codeRefs.current[Math.min(digits.length, 6) - 1]?.focus();
  };

  const cls = (s: AuthState) => `auth-state${state === s ? " is-active" : ""}`;

  return (
    <main className="auth-page">
      <section className="auth-brand" aria-labelledby="auth-brand-title">
        <a className="brand" href="/login" aria-label="HADP Startseite">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-copy">
            <strong>HADP</strong>
            <small>Health Analytics</small>
          </span>
        </a>

        <div className="auth-message">
          <span className="kicker">Klinischer Arbeitsbereich</span>
          <h1 id="auth-brand-title">
            Gesundheitsdaten verstehen. Entscheidungen nachvollziehbar
            dokumentieren.
          </h1>
          <p>
            Ein ruhiger, quellengebundener Workspace für Longevity- und
            Präventionskliniken – mit menschlicher Prüfung vor jeder Freigabe.
          </p>
        </div>

        <div className="auth-trust" aria-label="Sicherheitsmerkmale">
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="lock" />
            </span>
            <span>
              Mehrstufige Anmeldung (geplant) und zeitlich begrenzte Sitzungen
            </span>
          </div>
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="reports" />
            </span>
            <span>
              Zugriffe und Änderungen werden für das Audit protokolliert
            </span>
          </div>
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="shieldCheck" />
            </span>
            <span>
              Für sensible Gesundheitsdaten und EU-Datenresidenz konzipiert
            </span>
          </div>
        </div>
      </section>

      <section className="auth-main" id="auth-content" aria-label="Anmeldung">
        <div className="auth-wrap">
          <div className="auth-card">
            {/* signin */}
            <section className={cls("signin")} aria-labelledby="signin-title">
              <div className="eyebrow">Klinischer Zugang</div>
              <h2 id="signin-title">Willkommen zurück</h2>
              <p className="auth-sub">
                Melden Sie sich an, um Patientendaten zu prüfen und Berichte
                freizugeben.
              </p>

              <form className="auth-form" onSubmit={goTwofactor}>
                <label className="field">
                  <span className="field-label">Geschäftliche E-Mail</span>
                  <span className="input-wrap">
                    <Icon name="mail" className="input-icon" />
                    <input
                      className="input has-leading"
                      type="email"
                      name="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="username"
                      required
                    />
                  </span>
                </label>

                <label className="field">
                  <span className="field-label">
                    <span>Passwort</span>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        toast(
                          "Passwort-Wiederherstellung ist im statischen Prototyp nicht angebunden.",
                        );
                      }}
                    >
                      Passwort vergessen?
                    </a>
                  </span>
                  <span className="input-wrap">
                    <Icon name="lock" className="input-icon" />
                    <input
                      className="input has-leading has-trailing"
                      id="password"
                      type={showPassword ? "text" : "password"}
                      name="password"
                      placeholder="Mindestens 12 Zeichen"
                      autoComplete="current-password"
                      required
                    />
                    <button
                      className="input-action"
                      type="button"
                      aria-controls="password"
                      aria-pressed={showPassword}
                      onClick={() => setShowPassword((v) => !v)}
                    >
                      {showPassword ? "Ausblenden" : "Anzeigen"}
                    </button>
                  </span>
                </label>

                <label className="checkbox">
                  <input type="checkbox" name="trusted-device" />
                  <span>
                    Dieses persönliche Gerät 30 Tage merken. Nicht auf gemeinsam
                    genutzten Geräten verwenden.
                  </span>
                </label>

                <button className="btn btn-primary btn-block" type="submit">
                  Weiter zur Bestätigung
                </button>

                <div className="divider">oder</div>
                <button
                  className="btn btn-secondary btn-block"
                  type="button"
                  onClick={() =>
                    toast("Klinik-SSO ist als spätere Integration vorgesehen.")
                  }
                >
                  <Icon name="building" />
                  Mit Klinik-SSO fortfahren (geplant)
                </button>

                <div className="notice notice-brand">
                  <Icon name="shieldInfo" />
                  <span>
                    Der Zugriff auf Patientendaten ist zweckgebunden und wird
                    protokolliert.
                  </span>
                </div>
              </form>
            </section>

            {/* twofactor */}
            <section
              className={cls("twofactor")}
              aria-labelledby="twofactor-title"
            >
              <div className="eyebrow">Zwei-Faktor-Bestätigung (Demo)</div>
              <h2 id="twofactor-title">Identität bestätigen</h2>
              <p className="auth-sub">
                Prototyp-Ansicht: Der Code wird in dieser Pilotumgebung nicht
                geprüft. Die produktive Zwei-Faktor-Anmeldung ist geplant.
              </p>

              <form onSubmit={submitCode}>
                <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend className="sr-only">
                    Sechsstelliger Bestätigungscode
                  </legend>
                  <div className="code-inputs">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <input
                        key={i}
                        ref={(el) => {
                          codeRefs.current[i] = el;
                        }}
                        inputMode="numeric"
                        autoComplete={i === 0 ? "one-time-code" : undefined}
                        maxLength={1}
                        aria-label={`Ziffer ${i + 1}`}
                        onChange={(e) =>
                          onCodeInput(i, e.target.value, e.target)
                        }
                        onKeyDown={(e) => onCodeKey(i, e)}
                        onPaste={onCodePaste}
                      />
                    ))}
                  </div>
                </fieldset>
                <p className="card-subtitle" style={{ marginBottom: "18px" }}>
                  Kein Zugriff auf die App?{" "}
                  <a
                    href="#"
                    style={{
                      color: "var(--brand-700)",
                      fontWeight: 750,
                      textDecoration: "none",
                    }}
                    onClick={(e) => {
                      e.preventDefault();
                      toast(
                        "Backup-Codes werden in der Produktivversion über den Identity Provider verwaltet.",
                      );
                    }}
                  >
                    Backup-Code verwenden
                  </a>
                </p>
                <button className="btn btn-primary btn-block" type="submit">
                  Bestätigen und anmelden
                </button>
                <div className="auth-link-line">
                  <button type="button" onClick={() => setState("signin")}>
                    ← Zurück zur Anmeldung
                  </button>
                </div>
              </form>
            </section>

            {/* locked */}
            <section className={cls("locked")} aria-labelledby="locked-title">
              <div className="eyebrow">Sitzung gesperrt</div>
              <div className="auth-identity">
                <div className="avatar" aria-hidden="true">
                  SJ
                </div>
                <strong id="locked-title">Dr. Sarah Johnson</strong>
                <span>Clinician · Meridian Longevity</span>
              </div>
              <div
                className="notice notice-warning"
                style={{ marginBottom: "17px" }}
              >
                <Icon name="lock" />
                <span>
                  Die Sitzung wurde nach 15 Minuten Inaktivität gesperrt. Nicht
                  gespeicherte Eingaben bleiben erhalten.
                </span>
              </div>
              <form
                className="auth-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!e.currentTarget.reportValidity()) return;
                  router.push("/worklist");
                }}
              >
                <label className="field">
                  <span className="field-label">Passwort</span>
                  <input
                    className="input"
                    type="password"
                    autoComplete="current-password"
                    required
                  />
                </label>
                <button className="btn btn-primary btn-block" type="submit">
                  Sitzung entsperren
                </button>
              </form>
              <div className="auth-link-line">
                Nicht Ihre Sitzung?{" "}
                <button type="button" onClick={() => setState("signedout")}>
                  Abmelden
                </button>
              </div>
            </section>

            {/* signedout */}
            <section
              className={cls("signedout")}
              aria-labelledby="signedout-title"
            >
              <div className="success-lock" aria-hidden="true">
                <Icon name="check" style={{ width: "26px", height: "26px" }} />
              </div>
              <h2 id="signedout-title" style={{ textAlign: "center" }}>
                Sicher abgemeldet
              </h2>
              <p className="auth-sub" style={{ textAlign: "center" }}>
                Die Sitzung wurde beendet und im Audit-Protokoll erfasst.
                Schließen Sie diesen Tab auf gemeinsam genutzten Geräten.
              </p>
              <div
                className="notice notice-brand"
                style={{ marginBottom: "17px" }}
              >
                <Icon name="reports" />
                <span>
                  Abgemeldet um <span className="num">14:52</span> · Sitzung{" "}
                  <span className="num">00:42:18</span>
                </span>
              </div>
              <button
                className="btn btn-primary btn-block"
                type="button"
                onClick={() => setState("signin")}
              >
                Erneut anmelden
              </button>
            </section>

            <div className="auth-legal">
              © {new Date().getFullYear()} HADP · <a href="#">Datenschutz</a> ·{" "}
              <a href="#">Nutzungsbedingungen</a>
            </div>
          </div>

          <details className="prototype-switcher">
            <summary>Prototyp-Zustände anzeigen</summary>
            <div className="prototype-switcher-buttons">
              <button type="button" onClick={() => setState("signin")}>
                Anmeldung
              </button>
              <button type="button" onClick={() => setState("twofactor")}>
                2FA
              </button>
              <button type="button" onClick={() => setState("locked")}>
                Gesperrt
              </button>
              <button type="button" onClick={() => setState("signedout")}>
                Abgemeldet
              </button>
            </div>
          </details>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <ToastProvider>
      <AuthInner />
    </ToastProvider>
  );
}
