// The clinic's wall clock, for pages rendered on the server — whose own zone is not the
// reader's. One zone for the DACH pilot: the one the API reads laboratory times in
// (LAB_LOCAL_TIMEZONE) and the patient view names.
export const CLINIC_TIME_ZONE = "Europe/Berlin";

const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

const wallClock = new Intl.DateTimeFormat("en-CA", {
  timeZone: CLINIC_TIME_ZONE,
  hourCycle: "h23",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

// How far the clinic's wall clock is ahead of UTC at an instant, in milliseconds.
function offsetAt(instant: number): number {
  const parts = wallClock.formatToParts(new Date(instant));
  const part = (type: string) =>
    Number(parts.find((p) => p.type === type)?.value);
  const wall = Date.UTC(
    part("year"),
    part("month") - 1,
    part("day"),
    part("hour"),
    part("minute"),
    part("second"),
  );
  return wall - Math.floor(instant / 1000) * 1000;
}

// A calendar day ("2026-10-12") -> the instant it begins on the clinic's wall clock, or the
// instant the day `addDays` later begins. Undefined when the text is not a real day of this
// century — "2026-02-30" is not one, and neither is a date with a time.
export function clinicDayStart(
  day: string | undefined,
  addDays = 0,
): Date | undefined {
  const match = DAY.exec(day ?? "");
  if (!match) return undefined;
  const [year, month, date] = [
    Number(match[1]),
    Number(match[2]),
    Number(match[3]),
  ];
  const real = new Date(Date.UTC(year, month - 1, date));
  if (
    year < 2000 ||
    year > 2099 ||
    real.getUTCMonth() !== month - 1 ||
    real.getUTCDate() !== date
  )
    return undefined;
  const midnight = Date.UTC(year, month - 1, date + addDays);
  // Wall-clock midnight is UTC midnight less the zone's offset at that moment. Looked up
  // twice: the first guess can lie on the other side of a clock change.
  const guess = midnight - offsetAt(midnight);
  return new Date(midnight - offsetAt(guess));
}

const stamp = new Intl.DateTimeFormat("de-DE", {
  timeZone: CLINIC_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZoneName: "short",
});

// "12.10.2026, 18:40:32 MESZ". The zone is part of every time: one hour a year happens twice.
export function clinicTime(iso: string): string {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? iso : stamp.format(at);
}
