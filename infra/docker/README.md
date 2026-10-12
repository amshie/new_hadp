# Container images and the production-shaped stack

> Synthetic data only. Nothing here is a deployment, and nothing here has been run with
> patient data of any kind.

## The images

Three images, each built from the repository root as build context:

| Image         | Dockerfile               | Runs                                      |
| ------------- | ------------------------ | ----------------------------------------- |
| `hadp-api`    | `apps/api/Dockerfile`    | the API (`uvicorn`), and the migrate step |
| `hadp-worker` | `apps/worker/Dockerfile` | the job loop (a labelled skeleton today)  |
| `hadp-web`    | `apps/web/Dockerfile`    | the web app (`next start`)                |

```bash
make images        # builds all three, tagged :local
```

- Dependencies come from the lockfiles only (`uv sync --frozen --no-dev`,
  `pnpm install --frozen-lockfile`); base images are pinned by tag.
- Every image runs as a numeric non-root user and needs no writable file system except `/tmp`
  (the API spools an upload of more than 1 MB there; the stack below mounts a tmpfs).
- **The API image's default is production mode.** Started without its configuration it refuses to
  start; it never comes up in development mode, where the password-less development sign-in
  exists.
- The runtime images carry no package manager: the node image's npm, corepack and yarn and the
  Python images' pip are removed from the container's file system (they are what an image scan
  reports first, and nothing at run time uses them).
- The build context is an allowlist (`.dockerignore`): no `.env*`, no reports, no fixtures and
  no local dependency tree can reach a layer.
- `next build` needs no network: the fonts are packages, and the typed API client is generated
  in the build from the committed `openapi.json`.

## The migrate step — and why it seeds the catalog

A deployment runs, with the **admin** DSN and before the API starts:

```bash
alembic upgrade head && python -m hadp_api.scripts.seed_catalog
```

Both are in the API image, and both read the application's full production configuration (the
configuration guard runs for them too), not only the admin DSN. `alembic upgrade head` alone is
not enough: the laboratory import
looks every name up in the KPI catalog (ADR-0004 §18), and without a catalog it holds every
value for review and says so only in a log line. `seed_catalog` loads the catalog and nothing
else, is idempotent, prints row counts only, and **fails** (exit 1) if the catalog in the database
does not resolve names as this build's catalog does or does not confirm the names the import acts
on without a human. **It seeds; it does not upgrade:** where the database holds another catalog
release than the build ships it writes nothing and stops with exit 2 — replacing a release needs a
migration of its own, and none exists yet. The API does not check the catalog when it starts. It is safe for any environment —
unlike `hadp_api.scripts.seed`, the synthetic demo seeder, which refuses to run in production.

The application role `hadp_app` must exist **before** the first migration, with its own
password: migration 0002 creates the role only if it is missing, and then with the development
password. `postgres-init/10-app-role.sh` does this for the stack below; on a managed database
it is a provisioning step.

## The production-shaped stack

`compose.production.yml` runs the three images in production mode beside PostgreSQL, Redis
and an S3 endpoint, with a one-shot migrate service. `make stack-smoke` builds the images,
generates random secrets for the run, boots the stack, checks it, and tears it down:

- the migrate step exits 0, the schema is at one revision, the catalog tables are filled and
  confirm the import's automatic names; no clinic, staff member or patient exists, and the
  synthetic seeder refuses to run there;
- the API's database role is `hadp_app` — no superuser, no BYPASSRLS — and does not accept the
  development password; the API container holds no admin DSN;
- `/api/v1/health` answers in production mode with HSTS; `/api/v1/auth/dev-login` answers 404;
  an unknown session is refused after a database lookup; the API reaches Redis and its bucket;
- the web app's `/login` answers 200 with every security header of `next.config.mjs`, says
  that no sign-in is set up, and shows no form;
- api, worker and web run as non-root, carry no `.env` file, never restarted, and mount no
  volume.

### What it is not

- **Nobody can sign in to it.** The production identity provider is a stub that raises, and
  the development sign-in does not exist in production mode. The smoke proves boot and
  posture — not that the workflow works there.
- **It is not a database of record.** PostgreSQL and Redis keep their data on tmpfs; stopping
  the stack loses everything in it. There is no volume to back up.
- **Its object store is a test double** (moto): it keeps objects in memory and accepts any
  credentials. The MinIO images the development compose names can no longer be pulled, and
  which store a deployment uses is an open vendor decision.

## Still missing for a real deployment

TLS termination and public `https` origins (the `__Host-` cookies need them — and the web app
still keeps its own cookies under fixed names without `Secure`, which the production sign-in must
not inherit); managed
PostgreSQL with backups and a tested restore; a secret manager; an EU-region object store with
a bucket-scoped key; the production identity provider (OIDC + MFA); monitoring and alerting
with the redaction layer; a deploy job; runbooks. Go-live plan, workstreams B and C.
