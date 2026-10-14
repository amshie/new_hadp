// Seit zuletzt (docs/notes/0024): what arrived or moved in a record since the person last
// opened it. The API says what and when, for the records the person has opened; this module
// only puts the latest change first. Nothing here rates, ranks or sums — the order is time.
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/changes.spec.ts).

import type { ChangeRow } from "../api";

function time(iso: string): number {
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : 0;
}

// Newest change first; the same instant by name.
export function presentChanges(rows: ChangeRow[]): ChangeRow[] {
  return [...rows].sort(
    (a, b) =>
      time(b.changed_at) - time(a.changed_at) ||
      a.display_name.localeCompare(b.display_name, "de"),
  );
}
