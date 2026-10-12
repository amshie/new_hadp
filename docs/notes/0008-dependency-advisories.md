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

## JavaScript (`pnpm audit`) — CLEARED

The gate is `pnpm audit --audit-level high` (blocking on high/critical only; Dependabot reports
moderate). As of 2026-10-12 `pnpm audit` reports **no known vulnerabilities** at any level.

- **postcss** (`<8.5.10`, via `next`) — cleared earlier with a `pnpm.overrides` floor of `>=8.5.10`.
- **js-yaml** (via `openapi-typescript > @redocly/openapi-core`) — **cleared 2026-10-12.** It had
  been accepted as a moderate, dev-tooling advisory that could not be resolved (2026-07-03): js-yaml
  `>=4.2.0` removed the `types.merge` API that `@redocly/openapi-core@1.34.15` read at load, and
  Redocly 2.x broke `openapi-typescript`. Upstream has since fixed it inside the 1.x line:
  `@redocly/openapi-core@1.34.20` depends on `js-yaml 4.3.2`, within `openapi-typescript`'s
  `^1.34.6` range. A lockfile update was enough; `pnpm gen:client` and the client contract test
  pass on it.

## 2026-10-12 — advisories published since the last merge

`dependency-scan` had been red on every pull request since August 2026: new advisories landed
after the last merge, and no upgrade had followed. Cleared by lockfile updates only (no direct
constraint changed except the `next` floor):

| Package               | Was     | Now     | Where                                   |
| --------------------- | ------- | ------- | --------------------------------------- |
| pyjwt                 | 2.13.0  | 2.15.1  | `apps/api`, `apps/worker` (transitive)  |
| cryptography          | 49.0.0  | 50.0.2  | `apps/api`, `apps/worker` (transitive)  |
| urllib3               | 2.7.0   | 2.8.0   | `apps/api` (transitive, via botocore)   |
| anyio                 | 4.14.0  | 4.14.2  | `apps/api` (transitive)                 |
| next                  | 15.5.19 | 15.5.27 | `apps/web` (floor raised to `^15.5.27`) |
| sharp                 | 0.34.5  | 0.35.5  | via `next`                              |
| postcss               | 8.5.16  | 8.5.29  | via `next`                              |
| nanoid                | 3.3.14  | 3.3.20  | via `postcss`                           |
| source-map-js         | 1.2.1   | 1.2.2   | via `postcss`                           |
| brace-expansion       | 2.1.1   | 2.1.7   | dev tooling                             |
| @redocly/openapi-core | 1.34.15 | 1.34.20 | client generator                        |
| js-yaml               | 4.1.1   | 4.3.2   | client generator                        |

The `pip-audit` step runs first in the job, so while it failed the JS step never ran — the JS
advisories (two critical and several high in `next`) were invisible in CI. `apps/worker` is not
audited by CI at all; its lockfile was updated here by hand.

## Standing rule

Both gates must be clear (Python: zero advisories; JS: zero high/critical) before any real-data /
pilot go-live. Re-review on any dependency change, and do not let the gate stay red across pull
requests: a failing first step hides everything behind it. Dependabot (`.github/dependabot.yml`) continues to
open PRs as fixes land.

## 2026-10-13 — Mako, and two scanners that did not agree

GitHub's Dependabot reported `Mako` 1.3.12 (a transitive dependency of Alembic) for
GHSA-5639-2j2p-m4mx — a path traversal through a drive-letter URI on Windows in `TemplateLookup`,
fixed in 1.4.2 — and the image scan added with the container job (grype) reported the same.
**`pip-audit`, the gate in CI, passed on the same commit.** The gate above is therefore not "zero
advisories" but "zero advisories that `pip-audit`'s source lists"; the Dependabot alerts and the
image scan have to be read beside it.

Fixed by refreshing the lockfile for Mako alone (`uv lock --upgrade-package mako`: 1.3.12 → 1.4.3;
nothing else moved). The platform does not run on Windows and Alembic's templates are its own, so
the advisory was not reachable here; the bump keeps the alert list empty, which is what makes a
new alert visible.
