"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { DEFAULT_LOCALE, type Locale } from "./locales";
import { MESSAGES, type Messages } from "./messages";

// The interface language for client components. The root layout reads the person's choice
// on the server and passes it down; a client component asks with useI18n().
const I18nContext = createContext<{ locale: Locale; t: Messages }>({
  locale: DEFAULT_LOCALE,
  t: MESSAGES[DEFAULT_LOCALE],
});

export function I18nProvider({
  locale,
  children,
}: {
  locale: Locale;
  children: ReactNode;
}) {
  const value = useMemo(() => ({ locale, t: MESSAGES[locale] }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): { locale: Locale; t: Messages } {
  return useContext(I18nContext);
}
