import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

// The dashboard's shared patterns, held to one source each (docs/notes/0021): a page header,
// an audit stepper, an empty state and a card are classes and components, not markup a page
// writes again for itself. Pure: the sources are read, nothing is rendered.

const WEB = join(__dirname, "..");

function files(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files(path, out);
    else if (/\.tsx$/.test(name)) out.push(path);
  }
  return out;
}

const sources = files(join(WEB, "src")).map((path) => ({
  path: path.slice(WEB.length + 1),
  text: readFileSync(path, "utf8"),
}));

test("every settings page heads with the one header", () => {
  const offenders: string[] = [];
  for (const { path, text } of sources) {
    if (!path.startsWith("src/app/einstellungen/")) continue;
    for (const m of text.matchAll(/<h1\b[^>]*>/g)) {
      if (!m[0].includes('className="vb-ov-h1"'))
        offenders.push(`${path}: ${m[0]}`);
    }
  }
  expect(offenders).toEqual([]);
});

test("no page carries its own card, stepper or empty state", () => {
  const offenders: string[] = [];
  for (const { path, text } of sources) {
    if (/const cardStyle\b/.test(text)) offenders.push(`${path}: cardStyle`);
    if (/vb-audit-step/.test(text) && !path.endsWith("AuditSteps.tsx"))
      offenders.push(`${path}: stepper markup`);
    if (/"vb-empty/.test(text) && !path.endsWith("EmptyState.tsx"))
      offenders.push(`${path}: empty-state markup`);
    if (/[`"]audit-(step|card|line)|vb-ov-wlempty|vb-ov-tier-empty/.test(text))
      offenders.push(`${path}: a class that no longer exists`);
  }
  expect(offenders).toEqual([]);
});
