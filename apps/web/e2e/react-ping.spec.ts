import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

// The React the app is built with keeps a ping that arrives while it renders (docs/notes/0027).
//
// React Flight calls a waiting render back synchronously when the data is already there; when
// that render is "suspended with delay" — a navigation that keeps the old page on screen —
// the React Next.js 15.5 bundles dropped the ping, and the navigation never completed (about
// one click in a hundred). patches/next@15.5.27.patch records it instead, as React upstream
// does. No browser: the builds of react-dom the router uses are read as installed.

// The ping, in the shape each build writes it: the render phase is detected, and its ping is
// recorded rather than dropped.
const KEPT = {
  production:
    /\? 0 === \(executionContext & 2\)\s*\? prepareFreshStack\(root, 0\)\s*: \(workInProgressRootPingedLanes \|= pingedLanes\)/,
  development:
    /\? \(executionContext & RenderContext\) === NoContext\s*\? prepareFreshStack\(root, 0\)\s*: \(workInProgressRootPingedLanes \|= pingedLanes\)/,
};

for (const build of ["production", "development"] as const) {
  test(`the ${build} build of the router's React keeps a ping during the render phase`, () => {
    const file = require.resolve(
      `next/dist/compiled/react-dom/cjs/react-dom-client.${build}.js`,
    );
    const source = readFileSync(file, "utf8");
    const start = source.indexOf("function pingSuspendedRoot(");
    expect(start, "pingSuspendedRoot not found").toBeGreaterThan(-1);
    // The function is a few dozen lines; its branch on the render phase is inside the first
    // 2,000 characters in every build.
    const body = source.slice(start, start + 2_000);
    expect(body).toMatch(KEPT[build]);
  });
}
