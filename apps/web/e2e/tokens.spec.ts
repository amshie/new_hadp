import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

// The design tokens, held to what they promise (docs/notes/0020): every text colour reads on
// every surface of its theme at WCAG AA (4.5:1), in light and in dark, and no type in the
// dashboard is set under 11px. Pure: the stylesheet is parsed, nothing is rendered.

const WEB = join(__dirname, "..");
const tokens = readFileSync(join(WEB, "src/styles/tokens.css"), "utf8");

// The declarations of one block, `--name: value;`, by name.
function block(source: string, opener: string): Map<string, string> {
  const start = source.indexOf(opener);
  expect(start, `${opener} in tokens.css`).toBeGreaterThanOrEqual(0);
  const open = source.indexOf("{", start);
  let depth = 0;
  let end = open;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  const body = source.slice(open + 1, end).replace(/\/\*[\s\S]*?\*\//g, "");
  const out = new Map<string, string>();
  for (const m of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    out.set(m[1] as string, (m[2] as string).trim());
  }
  return out;
}

// A token's colour, following `var(--other)` until a hex value.
function resolve(name: string, ...scopes: Map<string, string>[]): string {
  let value: string | undefined;
  for (const scope of scopes) {
    value = scope.get(name) ?? value;
  }
  expect(value, `${name} is defined`).toBeDefined();
  const ref = /^var\((--[\w-]+)\)$/.exec(value ?? "");
  if (ref) return resolve(ref[1] as string, ...scopes);
  expect(value, `${name} is a hex colour`).toMatch(/^#[0-9a-f]{6}$/i);
  return value as string;
}

function luminance(hex: string): number {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

const light = block(tokens, ".vb-scope {");
const dark = block(tokens, '.vb-scope[data-theme="dark"] {');

const TEXT = [
  "--text-strong",
  "--text-body",
  "--text-muted",
  "--text-faint",
  "--status-positive-text",
  "--status-warning-text",
  "--status-danger-text",
  "--status-info-text",
  "--brand",
];
const SURFACES = ["--surface-card", "--bg-page", "--surface-sunken"];

for (const [theme, scopes] of [
  ["light", [light]],
  ["dark", [light, dark]],
] as const) {
  test(`every text colour reads on every surface (${theme})`, () => {
    for (const text of TEXT) {
      for (const surface of SURFACES) {
        const ratio = contrast(
          resolve(text, ...scopes),
          resolve(surface, ...scopes),
        );
        expect(
          ratio,
          `${text} on ${surface} (${theme}) is ${ratio.toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });
}

test("the primary button's text reads on the brand colour", () => {
  expect(
    contrast(resolve("--text-on-brand", light), resolve("--brand", light)),
  ).toBeGreaterThanOrEqual(4.5);
});

// Every stylesheet and component of the app: no `font-size` or `fontSize` under 11px.
function files(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) files(path, out);
    else if (/\.(css|tsx)$/.test(name)) out.push(path);
  }
  return out;
}

test("no type is set under 11px", () => {
  const small: string[] = [];
  for (const path of files(join(WEB, "src"))) {
    const text = readFileSync(path, "utf8");
    for (const m of text.matchAll(/font-?[sS]ize:\s*"?(\d+(?:\.\d+)?)px/g)) {
      if (Number(m[1]) < 11)
        small.push(`${path.slice(WEB.length + 1)}: ${m[0]}`);
    }
  }
  expect(small).toEqual([]);
});
