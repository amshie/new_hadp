import { setLocaleBeforeSignIn } from "@/app/einstellungen/actions";
import { Icon } from "@/components/Icon";
import { BrandMark } from "@/components/vitabahn/BrandMark";
import { PublicScope } from "@/components/vitabahn/PublicScope";
import { signInMode } from "@/lib/api";
import { LOCALES } from "@/lib/i18n/locales";
import { LANGUAGE_NAMES } from "@/lib/i18n/messages";
import { getLocale, getMessages } from "@/lib/i18n/server";

import { SignInForm } from "./SignInForm";

// The sign-in page shows the sign-in this deployment actually has. Outside production that is
// the development sign-in (an existing account's e-mail address, no credential); in production
// no identity provider is connected yet, and the page says so instead of offering a form.
// Asked per request — never decided at build time.
//
// The page is on the dashboard's design system (styles/vitabahn.css, `.vb-auth-*`): the same
// mark, type and tokens the person sees once signed in (docs/notes/0017).
export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const mode = await signInMode();
  const locale = await getLocale();
  const messages = await getMessages();
  const t = messages.login;

  return (
    <PublicScope>
      <main className="vb-auth">
        <section className="vb-auth-brand" aria-labelledby="auth-brand-title">
          <a className="vb-auth-logo" href="/login" aria-label={t.homeAria}>
            <BrandMark onDark />
          </a>

          <div className="vb-auth-message">
            <span className="vb-auth-kicker">{t.kicker}</span>
            <h1 id="auth-brand-title">{t.title}</h1>
            <p>{t.lead}</p>
          </div>

          <ul className="vb-auth-trust" aria-label={t.trustAria}>
            <li>
              <span className="vb-auth-trust-icon" aria-hidden="true">
                <Icon name="lock" />
              </span>
              <span>{t.sessionsLimited}</span>
            </li>
            <li>
              <span className="vb-auth-trust-icon" aria-hidden="true">
                <Icon name="reports" />
              </span>
              <span>{t.audited}</span>
            </li>
            {mode === "development" && (
              <li>
                <span className="vb-auth-trust-icon" aria-hidden="true">
                  <Icon name="shieldCheck" />
                </span>
                <span>{t.pilot}</span>
              </li>
            )}
          </ul>
        </section>

        <section
          className="vb-auth-main"
          id="auth-content"
          aria-label={t.sectionAria}
        >
          <div className="vb-auth-card">
            <div className="vb-ov-eyebrow">{t.eyebrow}</div>
            {mode === "development" && (
              <>
                <h2>{t.heading}</h2>
                <p className="vb-auth-sub">{t.devNote}</p>
                <SignInForm />
              </>
            )}
            {mode === "none" && (
              <>
                <h2>{t.noneHeading}</h2>
                <p className="vb-auth-sub">{t.noneNote}</p>
              </>
            )}
            {mode === "unreachable" && (
              <>
                <h2>{t.unreachableHeading}</h2>
                <p className="vb-auth-sub">{t.unreachableNote}</p>
                <a className="vb-ov-btn vb-auth-block" href="/login">
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
              className="vb-auth-languages"
            >
              {LOCALES.map((option) => (
                <button
                  key={option}
                  type="submit"
                  name="locale"
                  value={option}
                  lang={option}
                  aria-pressed={option === locale}
                  className="vb-ov-btn"
                >
                  {LANGUAGE_NAMES[option]}
                </button>
              ))}
            </form>

            <div className="vb-auth-legal">
              © {new Date().getFullYear()} HADP
            </div>
          </div>
        </section>
      </main>
    </PublicScope>
  );
}
