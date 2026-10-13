"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { Locale } from "./locales";
import type { Messages } from "./messages";

// The interface language for client components. The root layout reads the person's choice
// on the server and hands the wording of THAT language down — the other language never
// reaches the browser. A client component asks with useI18n().
const I18nContext = createContext<{ locale: Locale; t: Messages } | null>(null);

export function I18nProvider({
  locale,
  messages,
  children,
}: {
  locale: Locale;
  messages: Messages;
  children: ReactNode;
}) {
  const value = useMemo(() => ({ locale, t: messages }), [locale, messages]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): { locale: Locale; t: Messages } {
  const value = useContext(I18nContext);
  // No fallback: a component outside the provider would show German to someone who chose
  // English, and nobody would notice.
  if (!value) throw new Error("useI18n() is used outside <I18nProvider>");
  return value;
}
