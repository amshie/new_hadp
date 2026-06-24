# ADR-0001: Technology stack — split Python (FastAPI) + TypeScript (Next.js)

- Status: Accepted
- Date: 2026-06-21
- Deciders: Engineering (foundation milestone)

## Context

`CLAUDE.md` mandates a modular monolith with asynchronous workers and names a split
stack: Next.js/React/TypeScript on the frontend and Python/FastAPI/Pydantic/
SQLAlchemy 2/Alembic on the backend, PostgreSQL, a Redis-backed job queue, and
S3-compatible object storage. It also requires this decision to be recorded here and
forbids changing the stack without superseding this ADR.

The core product work is laboratory-data normalization: exact-decimal arithmetic,
unit conversion (UCUM-style), terminology mapping (LOINC-style), and conservative
supersession matching for corrected reports. This is the highest patient-safety-risk
surface in the product, and Python's decimal, scientific, and data-handling ecosystem
is a good fit. The clinical workspace UI benefits from the React/Next.js ecosystem.

## Decision

Adopt the split stack exactly as `CLAUDE.md` specifies:

- **Frontend:** Next.js (App Router) + React + TypeScript (strict mode).
- **Backend:** Python + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic.
- **Database:** PostgreSQL, with row-level security as defense-in-depth for
  tenant-scoped tables.
- **Background jobs:** Redis-backed queue with explicit retries and idempotency.
- **Object storage:** S3-compatible (MinIO locally; an EU-region bucket in
  production), behind a `BlobStore` interface.
- **API contract:** OpenAPI emitted by FastAPI; the TypeScript client is generated
  from it (`openapi-typescript`). The frontend never hand-duplicates API types.
- **Toolchain:** `uv` for Python, `pnpm` workspaces for TypeScript, Docker Compose
  for local infra, `make` for the canonical command surface.

We use **synchronous** SQLAlchemy 2.0 (psycopg 3 driver). The pilot's load does not
need async DB I/O, and synchronous sessions make explicit transaction boundaries and
deterministic tests simpler — fewer event-loop foot-guns on the highest-risk code.

## Consequences

- Two language/type ecosystems for a small team. Mitigated by: a single generated
  API contract as the seam, `make` unifying commands, and CI running both toolchains.
- The OpenAPI document is the source of truth for cross-language types. Drift is
  prevented by generating the client (`make gen-client`), never editing it by hand.
- RLS requires the application to connect as a **non-superuser** role (`hadp_app`)
  so policies actually apply; migrations/admin run as the owning superuser. This is
  what makes tenant isolation testable rather than merely asserted.

## Documented fallback (per CLAUDE.md)

If team depth or velocity cannot sustain two ecosystems, the fallback is a single
TypeScript stack (Next.js with a typed server layer). Choosing it **supersedes this
ADR** with a new ADR recording the trigger and migration plan. We do not silently
drift toward it.

## Alternatives considered

- **Single TypeScript stack now.** Lower operational surface, but moves the
  highest-risk numeric/lab-normalization work into an ecosystem less suited to exact
  decimals and scientific tooling, against the contract's stated rationale. Rejected
  for the pilot; retained as the documented fallback above.
- **Microservices / event-sourcing.** Explicitly out of scope in `CLAUDE.md`;
  unjustified operational complexity for a pilot. Rejected.
