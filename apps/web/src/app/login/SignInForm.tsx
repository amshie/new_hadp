"use client";

import { useState, useTransition, type FormEvent } from "react";

import { Icon } from "@/components/Icon";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { useHydrated } from "@/lib/useHydrated";

import { login } from "./actions";

// The development sign-in: the e-mail address of an account that exists, nothing else. It is
// rendered only where the API offers it (outside production) and says what it is — there is
// no password or second factor to ask for until a production identity provider is connected.
export function SignInForm() {
  const t = useI18n().t.login;
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  // Until the page is hydrated the form would submit natively and put the address into the URL.
  const hydrated = useHydrated();

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = String(
      new FormData(e.currentTarget).get("email") ?? "",
    ).trim();
    if (!email || pending) return;
    startTransition(async () => {
      setError(null);
      // On success the action redirects and never returns.
      const result = await login(email);
      if (result && !result.ok) setError(result.error);
    });
  };

  return (
    <form className="vb-auth-form" onSubmit={submit}>
      <label className="vb-auth-field">
        <span className="field-label">{t.emailLabel}</span>
        <span className="vb-auth-inputwrap">
          <Icon name="mail" className="vb-auth-inputicon" />
          <input
            className="vb-auth-input"
            type="email"
            name="email"
            autoComplete="username"
            readOnly={pending}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "sign-in-error" : undefined}
            required
          />
        </span>
      </label>

      {error && (
        <div
          className="vb-auth-notice is-error"
          role="alert"
          id="sign-in-error"
        >
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}

      <button
        className="vb-ov-btn primary vb-auth-block"
        type="submit"
        disabled={pending || !hydrated}
      >
        {pending ? t.pending : t.submit}
      </button>

      <div className="vb-auth-notice">
        <Icon name="shieldInfo" />
        <span>{t.purposeNote}</span>
      </div>
    </form>
  );
}
