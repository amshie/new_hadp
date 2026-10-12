import { Icon } from "@/components/Icon";
import { signInMode } from "@/lib/api";

import { SignInForm } from "./SignInForm";

// The sign-in page shows the sign-in this deployment actually has. Outside production that is
// the development sign-in (an existing account's e-mail address, no credential); in production
// no identity provider is connected yet, and the page says so instead of offering a form.
// Asked per request — never decided at build time.
export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const mode = await signInMode();

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

        <div className="auth-trust" aria-label="Merkmale dieser Umgebung">
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="lock" />
            </span>
            <span>Sitzungen sind zeitlich begrenzt</span>
          </div>
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="reports" />
            </span>
            <span>
              Zugriffe und Änderungen werden für das Audit protokolliert
            </span>
          </div>
          {mode === "development" && (
            <div className="auth-trust-item">
              <span className="auth-trust-icon" aria-hidden="true">
                <Icon name="shieldCheck" />
              </span>
              <span>
                Pilotumgebung mit synthetischen Beispieldaten – keine reale
                Patientenversorgung
              </span>
            </div>
          )}
        </div>
      </section>

      <section className="auth-main" id="auth-content" aria-label="Anmeldung">
        <div className="auth-wrap">
          <div className="auth-card">
            <div className="eyebrow">Klinischer Zugang</div>
            {mode === "development" && (
              <>
                <h2>Anmelden</h2>
                <p className="auth-sub">
                  Pilotumgebung mit synthetischen Beispieldaten. Die Anmeldung
                  erfolgt hier ohne Passwort – mit der E-Mail-Adresse eines
                  eingerichteten Kontos.
                </p>
                <SignInForm />
              </>
            )}
            {mode === "none" && (
              <>
                <h2>Anmeldung nicht eingerichtet</h2>
                <p className="auth-sub" style={{ marginBottom: 0 }}>
                  Für diese Umgebung ist kein Anmeldeverfahren eingerichtet.
                  Eine Anmeldung ist derzeit nicht möglich.
                </p>
              </>
            )}
            {mode === "unreachable" && (
              <>
                <h2>Anmeldung derzeit nicht möglich</h2>
                <p className="auth-sub">
                  Der Anmeldedienst ist nicht erreichbar. Bitte versuchen Sie es
                  in einigen Minuten erneut.
                </p>
                <a className="btn btn-secondary btn-block" href="/login">
                  Erneut versuchen
                </a>
              </>
            )}

            <div className="auth-legal">© {new Date().getFullYear()} HADP</div>
          </div>
        </div>
      </section>
    </main>
  );
}
