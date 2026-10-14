import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { fill } from "@/lib/i18n/fill";
import type { Locale } from "@/lib/i18n/locales";
import type { Messages } from "@/lib/i18n/messages";

// Formatting for the overview and the settings. Every time is measured from the moment the server put the
// page together (`now`), never from the browser's clock: the server's and the browser's
// rendering then read the same, and "waiting since" means the same on every screen.

export const intlLocale = (locale: Locale) =>
  locale === "en" ? "en-GB" : "de-DE";

export function ago(
  iso: string | null | undefined,
  now: number,
  w: Messages["dashboard"]["time"],
): string {
  const then = iso ? Date.parse(iso) : NaN;
  if (!Number.isFinite(then)) return "—";
  const mins = Math.max(0, Math.round((now - then) / 60000));
  if (mins < 1) return w.now;
  if (mins < 60) return fill(w.minutes, { n: mins });
  const hours = Math.round(mins / 60);
  if (hours < 24) return fill(w.hours, { n: hours });
  const days = Math.round(hours / 24);
  if (days === 1) return w.yesterday;
  return fill(w.days, { n: days });
}

// "Mittwoch, 14.10.2026" on the clinic's calendar.
export function longDay(at: number, locale: Locale): string {
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: CLINIC_TIME_ZONE,
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(at);
}

// "14.10.2026" on the clinic's calendar.
export function day(iso: string | null | undefined, locale: Locale): string {
  const at = iso ? Date.parse(iso) : NaN;
  if (!Number.isFinite(at)) return "—";
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: CLINIC_TIME_ZONE,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(at);
}

// A calendar day as the API sends it ("2026-10-12"), shown short: "12.10.".
export function shortDay(date: string, locale: Locale): string {
  const [, m, d] = date.split("-").map(Number);
  if (!m || !d) return date;
  return locale === "en" ? `${d}/${m}` : `${d}.${m}.`;
}

// "08:12" on the clinic's wall clock.
export function clock(at: number, locale: Locale): string {
  return new Intl.DateTimeFormat(intlLocale(locale), {
    timeZone: CLINIC_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
  }).format(at);
}

// An elapsed time, in the unit that reads best: minutes, hours, then days with one decimal.
export function duration(
  seconds: number,
  locale: Locale,
  w: Messages["overview"]["duration"],
): string {
  const minutes = seconds / 60;
  if (minutes < 60)
    return fill(w.minutes, { n: Math.max(1, Math.round(minutes)) });
  const hours = minutes / 60;
  if (hours < 48) return fill(w.hours, { n: Math.round(hours) });
  const days = new Intl.NumberFormat(intlLocale(locale), {
    maximumFractionDigits: 1,
  }).format(hours / 24);
  return fill(w.days, { n: days });
}
