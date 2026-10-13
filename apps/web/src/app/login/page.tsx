import { setLocaleBeforeSignIn } from "@/app/einstellungen/actions";
import { Icon } from "@/components/Icon";
import { signInMode } from "@/lib/api";
import { LOCALES } from "@/lib/i18n/locales";
import { LANGUAGE_NAMES } from "@/lib/i18n/messages";
import { getLocale, getMessages } from "@/lib/i18n/server";

import { SignInForm } from "./SignInForm";

// The sign-in page shows the sign-in this deployment actually has. Outside production that is
// the development sign-in (an existing account's e-mail address, no credential); in production
// no identity provider is connected yet, and the page says so instead of offering a form.
// Asked per request — never decided at build time.
export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const mode = await signInMode();
  const locale = await getLocale();
  const messages = await getMessages();
  const t = messages.login;

  return (
    <main className="auth-page">
      <section className="auth-brand" aria-labelledby="auth-brand-title">
        <a className="brand" href="/login" aria-label={t.homeAria}>
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-copy">
            <strong>HADP</strong>
            <small>Health Analytics</small>
          </span>
        </a>

        <div className="auth-message">
          <span className="kicker">{t.kicker}</span>
          <h1 id="auth-brand-title">{t.title}</h1>
          <p>{t.lead}</p>
        </div>

        <div className="auth-trust" aria-label={t.trustAria}>
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="lock" />
            </span>
            <span>{t.sessionsLimited}</span>
          </div>
          <div className="auth-trust-item">
            <span className="auth-trust-icon" aria-hidden="true">
              <Icon name="reports" />
            </span>
            <span>{t.audited}</span>
          </div>
          {mode === "development" && (
            <div className="auth-trust-item">
              <span className="auth-trust-icon" aria-hidden="true">
                <Icon name="shieldCheck" />
              </span>
              <span>{t.pilot}</span>
            </div>
          )}
        </div>
      </section>

      <section
        className="auth-main"
        id="auth-content"
        aria-label={t.sectionAria}
      >
        <div className="auth-wrap">
          <div className="auth-card">
            <div className="eyebrow">{t.eyebrow}</div>
            {mode === "development" && (
              <>
                <h2>{t.heading}</h2>
                <p className="auth-sub">{t.devNote}</p>
                <SignInForm />
              </>
            )}
            {mode === "none" && (
              <>
                <h2>{t.noneHeading}</h2>
                <p className="auth-sub" style={{ marginBottom: 0 }}>
                  {t.noneNote}
                </p>
              </>
            )}
            {mode === "unreachable" && (
              <>
                <h2>{t.unreachableHeading}</h2>
                <p className="auth-sub">{t.unreachableNote}</p>
                <a className="btn btn-secondary btn-block" href="/login">
                  {t.retry}
                </a>
              </>
            )}

            {/* The language can be chosen before signing in, too: an English reader's first
                screen is this one. The same choice as under Einstellungen. */}
            <form
              action={setLocaleBeforeSignIn}
              role="group"
              aria-label={messages.language.choose}
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "8px",
                marginTop: "18px",
              }}
            >
              {LOCALES.map((option) => (
                <button
                  key={option}
                  type="submit"
                  name="locale"
                  value={option}
                  lang={option}
                  aria-pressed={option === locale}
                  className="btn btn-secondary btn-sm"
                  style={
                    option === locale
                      ? { fontWeight: 700 }
                      : { fontWeight: 400 }
                  }
                >
                  {LANGUAGE_NAMES[option]}
                </button>
              ))}
            </form>

            <div className="auth-legal">© {new Date().getFullYear()} HADP</div>
          </div>
        </div>
      </section>
    </main>
  );
}
