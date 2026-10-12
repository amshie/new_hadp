"use client";

import { useState, useTransition, type FormEvent } from "react";

import { Icon } from "@/components/Icon";

import { login } from "./actions";

// The development sign-in: the e-mail address of an account that exists, nothing else. It is
// rendered only where the API offers it (outside production) and says what it is — there is
// no password or second factor to ask for until a production identity provider is connected.
export function SignInForm() {
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

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
    <form className="auth-form" onSubmit={submit}>
      <label className="field">
        <span className="field-label">E-Mail-Adresse</span>
        <span className="input-wrap">
          <Icon name="mail" className="input-icon" />
          <input
            className="input has-leading"
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
        <div className="notice notice-danger" role="alert" id="sign-in-error">
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}

      <button
        className="btn btn-primary btn-block"
        type="submit"
        disabled={pending}
      >
        {pending ? "Anmeldung läuft …" : "Anmelden"}
      </button>

      <div className="notice notice-brand">
        <Icon name="shieldInfo" />
        <span>
          Der Zugriff auf Patientendaten ist zweckgebunden und wird
          protokolliert.
        </span>
      </div>
    </form>
  );
}
