// ESLint for the web app (flat config): the language rules (@eslint/js), TypeScript's
// (typescript-eslint), React's rules of hooks, and jsx-a11y for accessibility. Not
// eslint-config-next: its Next plugin pulls in `braces` (through fast-glob) with a high
// advisory and no fixed release, which the dependency scan rightly refuses. Run by
// `pnpm lint`, so by `make lint` and CI — with no warning allowed: the tree is clean, and a
// warning left standing is a warning nobody reads.
import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

const config = tseslint.config(
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "test-results/**",
      "playwright-report/**",
      "next-env.d.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  reactHooks.configs["recommended-latest"],
  jsxA11y.flatConfigs.recommended,
  {
    rules: {
      // A label's text may sit three elements deep (the consent purposes of the dialog to
      // add a patient: label > span > span > text). Two, the default, misses it; the
      // browser test finds those checkboxes by the name their label gives them.
      "jsx-a11y/label-has-associated-control": ["error", { depth: 3 }],
    },
  },
  {
    // The configuration files and scripts run in Node, not in the browser.
    files: ["**/*.mjs"],
    languageOptions: {
      globals: { process: "readonly", console: "readonly" },
    },
  },
);

export default config;
