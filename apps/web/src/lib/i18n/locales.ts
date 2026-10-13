// The languages of the interface. German is the default (the pilot's clinics); English is
// offered beside it. A person chooses under Einstellungen; the choice is kept in a cookie on
// that device (lib/i18n/server.ts reads it, app/einstellungen/actions.ts writes it).
//
// The interface only: what was recorded — report statements, laboratory names, the names of
// people — stays in the language it was recorded in.
export const LOCALES = ["de", "en"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "de";
export const LOCALE_COOKIE = "hadp_locale";

export function isLocale(value: unknown): value is Locale {
  return (
    typeof value === "string" && (LOCALES as readonly string[]).includes(value)
  );
}
