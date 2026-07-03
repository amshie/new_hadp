# 0008 — Dependency advisories

CI's `dependency-scan` job (`.github/workflows/ci.yml`) is **blocking**: an advisory fails the
build. This note records the state of that gate.

## Python (`pip-audit`) — CLEARED

The Python allowlist is **gone**. It previously carried one dev-only `pytest` advisory and seven
transitive `starlette` (via FastAPI) advisories, accepted for the synthetic-data Alpha pending an
upgrade slice. That slice landed:

| Package   | Was     | Now     | Notes                                                              |
| --------- | ------- | ------- | ----------------------------------------------------------------- |
| fastapi   | 0.115.14 | 0.139.0 | Required to reach a starlette 1.x that clears the advisories.      |
| starlette | 0.46.2  | 1.3.1   | Major 0.x→1.x bump; floor pinned directly in `pyproject.toml`.     |
| pytest    | 8.4.2   | 9.1.1   | Dev-only; CVE-2025-71176 fixed in 9.0.3.                           |

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
  **accepted (moderate, dev-tooling)**. It **cannot** be force-upgraded in place: js-yaml 4.2.0
  removed the `types.merge` API (the very merge-key handling the DoS advisory concerns), and
  `@redocly/openapi-core@1.34.15` reads `types.merge` at load time, so a `>=4.2.0` override crashes
  client generation (`make gen-client`). Dependabot likewise reports "security_update_not_possible".
  The clean fix is an `openapi-typescript` major upgrade whose bundled Redocly supports js-yaml 4.2.0
  — a dev-tooling change that can alter generated client output, so it gets its **own** slice, not
  this security one. js-yaml runs only in the offline client generator; it never touches request or
  patient data.

## Standing rule

Both gates must be clear (Python: zero advisories; JS: zero high/critical) before any real-data /
pilot go-live, and the js-yaml moderate above must be closed by the `openapi-typescript` upgrade
slice before that gate. Re-review on any dependency change. Dependabot (`.github/dependabot.yml`)
continues to open PRs as fixes land.
