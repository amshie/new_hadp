# 0008 — Dependency advisories

CI's `dependency-scan` job (`.github/workflows/ci.yml`) is **blocking**: an advisory fails the
build. This note records the state of that gate.

## Python (`pip-audit`) — CLEARED

The Python allowlist is **gone**. It previously carried one dev-only `pytest` advisory and seven
transitive `starlette` (via FastAPI) advisories, accepted for the synthetic-data Alpha pending an
upgrade slice. That slice landed:

| Package   | Was      | Now     | Notes                                                          |
| --------- | -------- | ------- | -------------------------------------------------------------- |
| fastapi   | 0.115.14 | 0.139.0 | Required to reach a starlette 1.x that clears the advisories.  |
| starlette | 0.46.2   | 1.3.1   | Major 0.x→1.x bump; floor pinned directly in `pyproject.toml`. |
| pytest    | 8.4.2    | 9.1.1   | Dev-only; CVE-2025-71176 fixed in 9.0.3.                       |

`pip-audit` (no `--ignore-vuln` flags) now reports **no known vulnerabilities**. The advisory IDs
recorded in the earlier revision of this note shifted in the upstream DB between the Alpha and the
upgrade (two starlette IDs were withdrawn, two new ones — PYSEC-2026-248/249 — appeared); the upgrade
to starlette 1.3.1 clears **all** of them, current and superseded, so no ID list is maintained here.

### Forward signal (non-blocking)

starlette 1.x emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead.` under the test client. Tests pass today on `httpx>=0.27,<0.29`.
Migrating the test client to `httpx2` is a separate, non-security follow-up — do it when a future
starlette drops the `httpx` path, not before.

## JavaScript (`pnpm audit`) — partially cleared, one accepted moderate

The gate is `pnpm audit --audit-level high` (blocking on high/critical only; Dependabot reports
moderate). Both current JS advisories are **moderate** and sit in **dev/build tooling**, not the
runtime patient-data surface.

- **postcss** (`<8.5.10`, via `next`) — **CLEARED** with a `pnpm.overrides` floor of `>=8.5.10`
  (patch bump; the production `next build` passes on it).
- **js-yaml** (`>=4.0.0 <=4.1.1`, via `openapi-typescript > @redocly/openapi-core`) —
  **accepted (moderate, dev-tooling); blocked upstream.** js-yaml runs only in the offline client
  generator (`make gen-client`); it never touches request or patient data. The upgrade was
  attempted and confirmed **not resolvable today** (2026-07-03):
  - js-yaml 4.2.0 removed the `types.merge` API (the merge-key handling the DoS advisory concerns).
    `@redocly/openapi-core@1.34.15` reads `js_yaml.types.merge` at load, so any js-yaml `>=4.2.0`
    override crashes `gen-client`.
  - Bumping `openapi-typescript` does **not** help: even the latest (`7.13.0`) still pins
    `@redocly/openapi-core ^1.34.6` (resolves to 1.34.15), so the broken `types.merge` read remains.
  - `@redocly/openapi-core@2.x` **fixed** the js-yaml issue (declares `js-yaml ^4.2.0`), but
    overriding Redocly to 2.x breaks `openapi-typescript`, which imports Redocly's internal
    `./lib/ref-utils.js` — a subpath 2.x removed from its `exports` map
    (`ERR_PACKAGE_PATH_NOT_EXPORTED`).
  - So the advisory clears only when **`openapi-typescript` ships a release that adopts
    `@redocly/openapi-core` 2.x** (not out yet), or the client generator is swapped for a different
    tool. Both are out of scope for a security-hygiene slice; forcing it now would require a fragile
    `pnpm patch` of Redocly's internals, which is not warranted for a moderate dev-tooling advisory.
    Dependabot likewise reports "security_update_not_possible". Re-check when `openapi-typescript`
    releases a redocly-2.x version.

## Standing rule

Both gates must be clear (Python: zero advisories; JS: zero high/critical) before any real-data /
pilot go-live. The js-yaml moderate above is blocked upstream (see the investigation note) and must
be closed before that gate — re-check when `openapi-typescript` releases a `@redocly/openapi-core`
2.x version. Re-review on any dependency change. Dependabot (`.github/dependabot.yml`) continues to
open PRs as fixes land.
