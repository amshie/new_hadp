# HADP — Physician-Governed Longevity Analytics

A GDPR-first, multi-tenant, **physician-governed, audit-first decision-support** workspace for
longevity, functional-medicine, concierge, and preventive-care clinics (DACH/EU). It aggregates
laboratory data with full provenance, shows longitudinal change against the laboratory's own
reference intervals, lets a **clinician author** a per-patient, per-axis interpretation (recorded
append-only with its evidence), and requires a **medical-director lock before any patient release**.

> **Intended-use boundary.** A documentation / decision-**support** product — **not** an autonomous
> medical decision-maker. The engine **validates and records; it never derives** a verdict or a
> score: the per-axis verdicts (CIS, Actionability) and the tri-state cells are **authored by a
> qualified clinician**, gated by a medical director. No autonomous diagnosis, treatment advice,
> risk prediction, biological-age, or unified/health score. The MDR/MDSW classification of this
> governance model is an **open, pending determination** (see
> [`docs/adr/0003-adopt-hadp-governance-doctrine.md`](docs/adr/0003-adopt-hadp-governance-doctrine.md)
> and [`docs/regulatory/INTENDED_USE.md`](docs/regulatory/INTENDED_USE.md)). **Synthetic data only**
> in development and tests — never commit or import real patient data.

The binding project contract is [`CLAUDE.md`](CLAUDE.md); the product model is set by
[ADR-0003](docs/adr/0003-adopt-hadp-governance-doctrine.md).

## Layout

```
apps/
  api/      FastAPI backend (modular monolith): identity, tenancy, patients,
            consents, documents, imports, observations, interpretation, kpi,
            derivations, reports, audit, ...
  web/      Next.js + TypeScript clinic/patient web app
  worker/   Redis-backed background jobs (imports, reports)
packages/
  api-client/   TypeScript client generated from the backend OpenAPI document
  config/       Shared TS config
infra/, docs/, scripts/, tests/
```

## Quick start (local, synthetic data only)

Prerequisites: Docker, Node ≥ 20 + `pnpm`, and [`uv`](https://docs.astral.sh/uv/).

```bash
make bootstrap     # install deps, create .env.local
make db-up         # start Postgres (:55433), Redis (:56379), MinIO (:59000/59001)
make db-init       # create the non-superuser app role + test database
make migrate       # apply migrations to the dev database
make seed          # load synthetic tenants / users / patients / lab data
make api-dev       # FastAPI on :8000   (separate shell)
make web-dev       # Next.js on :3000   (separate shell)
```

> Ports are deliberately non-default to avoid colliding with the read-only `hadp-alpha`
> reference stack (host port 55432). **Never** run `docker compose down -v`.

## Verify

```bash
make db-up && make db-init && make migrate-test   # provision infra + test DB
make test                                          # unit + integration + RLS isolation
make check                                         # format-check + lint + typecheck + test
```

The end-to-end vertical spike (Milestone 0.5) is exercised by
`apps/api/tests/test_spike_vertical.py`: one synthetic lab value travels
upload → normalized observation → clinician timeline → source-grounded draft →
clinician approval → patient view, with no patient release of unapproved content.

## Documentation

- [`docs/adr/`](docs/adr) — architecture decisions (start with ADR-0001)
- [`docs/regulatory/`](docs/regulatory) — intended use, classification register, ownership
- [`docs/security/`](docs/security) — threat model, data-flow
- [`docs/product/`](docs/product) — workflow specification
- [`docs/notes/`](docs/notes) — build lessons (one per file)
