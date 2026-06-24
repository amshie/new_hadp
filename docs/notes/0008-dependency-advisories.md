# 0008 — Accepted dependency advisories (pip-audit allowlist)

CI's `dependency-scan` job (`.github/workflows/ci.yml`) is **blocking**: a new advisory fails the
build. The IDs below are **known** advisories in transitive Python dependencies, explicitly
allow-listed via `pip-audit --ignore-vuln` so the gate stays green for *current* state while *new*
issues still fail. They are accepted only for the synthetic-data-only Alpha and must be cleared
before any real-data / pilot go-live.

| ID              | Package   | Note                                                            |
| --------------- | --------- | --------------------------------------------------------------- |
| CVE-2025-71176  | pytest    | Dev/test-only dependency; not in the runtime surface.           |
| PYSEC-2026-161  | starlette | Via FastAPI; fix requires a starlette major bump.               |
| CVE-2025-54121  | starlette | Via FastAPI; multipart/upload handling.                         |
| CVE-2025-62727  | starlette | Via FastAPI.                                                    |
| CVE-2026-48818  | starlette | Via FastAPI.                                                    |
| CVE-2026-48817  | starlette | Via FastAPI.                                                    |
| CVE-2026-54283  | starlette | Via FastAPI.                                                    |
| CVE-2026-54282  | starlette | Via FastAPI.                                                    |

## Follow-up (own slice)

Upgrade `starlette` (and `fastapi`/`pytest` as required) to fix-versioned releases, then **remove the
corresponding `--ignore-vuln` entries** from CI. This is a dependency upgrade with breaking-change
risk (starlette 0.46 → 1.x; FastAPI pins a starlette range), so it gets its own branch + PR with the
full test suite + `make smoke`, per the "never an unrequested major-version upgrade" rule. Dependabot
(`.github/dependabot.yml`) will also open PRs as fixes land.
