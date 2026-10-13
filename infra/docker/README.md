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
- a patient view sent through the web server with a forwarded address is counted by the API
  under the address a proxy would have named — not under the web server's, and not under what
  the client wrote into the header itself;
- api, worker and web run as non-root, carry no `.env` file, never restarted, and mount no
  volume.

### The client's address

The patient view and the two invitation redemptions are limited per client address — as is
the development sign-in, which does not exist in production (what limits the production
sign-in is decided with the identity provider).
A browser never reaches the API — the web server does — so the web server passes on the
`X-Forwarded-For` it received on those four calls, and the API decides what to believe
(`apps/api/src/hadp_api/security/client_address.py`):

| Setting (API)        | Meaning                                                                                                                                         |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `TRUSTED_PROXIES`    | The web server's address(es) or network(s), comma-separated. Only a peer named here is believed. Empty (the default): the header is never read. |
| `TRUSTED_PROXY_HOPS` | How many proxies stand in front of the web server; the client is that entry from the right (default 1: one TLS proxy).                          |

A deployment has to set both, or every client behind the web server shares one budget that
one of them can use up (the API says so when it starts — a warning in production). Four
things to hold when setting them:

- the proxy in front of the web server must **set or append** `X-Forwarded-For`. One that
  passes a client's own header through lets the client choose the address it is counted
  under (nginx does that unless the header is set from `$proxy_add_x_forwarded_for`);
- **count the proxies exactly.** `TRUSTED_PROXY_HOPS` set too high reads an entry the client
  wrote — the client then chooses its counter, and nothing looks wrong. Set too low it reads a
  proxy's address: a shared budget, the safe direction. A hop between the web server and the
  API that appends to the header (a sidecar, an internal load balancer) counts as well;
- name the web server narrowly. Any peer inside `TRUSTED_PROXIES` can say on whose behalf it
  calls; a range that holds every address is refused at start, and so is one address written
  with a mask (`10.20.0.5/24` would name the whole network around it);
- the API server runs with `--no-proxy-headers` (the image's command does): uvicorn would
  otherwise rewrite the peer from the same header, by its own rule, before the API reads it.

The compose file leaves `TRUSTED_PROXIES` empty — Docker assigns the stack's addresses — and
the smoke names the stack's own network for its run.

### What it is not

- **Nobody can sign in to it.** The production identity provider is a stub that raises, and
  the development sign-in does not exist in production mode. The smoke proves boot and
  posture — not that the workflow works there.
- **It is not a database of record.** PostgreSQL and Redis keep their data on tmpfs; stopping
  the stack loses everything in it. There is no volume to back up.
- **Its object store is a test double** (moto): it keeps objects in memory and accepts any
  credentials. The MinIO images the development compose names can no longer be pulled, and
  which store a deployment uses is an open vendor decision.

## The demo stack

`compose.demo.yml` puts HADP on one server so that people who are shown the product can open
it in a browser: partners, the team at home. **Synthetic data only — it is not a deployment,
and nothing real may ever be put into it.**

What runs: the API in **development mode**, the production build of the web app, PostgreSQL
(a named volume), Redis, the S3 test double — and in front of all of it a proxy (Caddy) that
terminates TLS with a certificate it obtains itself and asks every visitor for the **gate's**
user name and password. Only the proxy is published (80 and 443, TCP).

Why development mode: the development sign-in (an account's e-mail address, no password) is
the only sign-in that exists. That is also why the gate is not optional and why the data
must stay synthetic — **behind the gate, anyone can act as any account that exists there**,
in either seeded clinic. The stack shows the workflow; it is not a demonstration of who may
see what.

### On the server

A Linux server with Docker and a DNS name that points at it. Let the provider's firewall
pass 22, 80 and 443 and nothing else — a firewall on the server itself (ufw) does not filter
the ports Docker publishes. As root, on Ubuntu 26.04 (where this was run):

```bash
apt-get update && apt-get install -y docker.io docker-compose-v2 docker-buildx git openssl
# The web image is built here; on a 4 GB server that wants some swap.
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
git clone https://github.com/amshie/new_hadp.git /opt/hadp && cd /opt/hadp
scripts/demo_stack.sh init   # asks for the host name, the gate's user name and password
scripts/demo_stack.sh up     # builds the two images, starts, migrates, seeds
```

`init` generates the stack's secrets and writes them, with the host name, to
`/etc/hadp-demo/demo.env`; the gate's user name and the **hash** of its password go to
`/etc/hadp-demo/gate.env`. Both are readable by root only, neither is in the checkout, and
the password itself is kept nowhere. Keep `demo.env` as long as the database volume exists:
the volume was created with the passwords in it. `scripts/demo_stack.sh gate` sets a new gate
user and password — the way to end someone's access.

- **A newer state:** `git pull && scripts/demo_stack.sh up`.
- **Stop:** `scripts/demo_stack.sh down` — the database volume stays; the script never
  removes it.
- **After the server, or the object store's container, restarted:** run
  `scripts/demo_stack.sh up --no-build` once. The services come back by themselves, but the
  object store starts empty, and its bucket is created by `up`.
- **Start again from the seeded data only** (everything visitors entered is lost — a
  deliberate step, typed by hand):
  `scripts/demo_stack.sh down && docker volume rm hadp-demo_pgdata && scripts/demo_stack.sh up --no-build`.

Visitors open `https://<host name>/`, pass the gate, and sign in with one of the seeded
synthetic accounts: `owner@demo.synthetic`, `clinician@demo.synthetic`,
`assistant@demo.synthetic`, `medical.director@demo.synthetic` in the demo clinic, and
`clinician2@demo.synthetic` in a second one.

### What to tell every visitor

- Everything in it is made up. **Enter nothing real**: no real name, no real e-mail address,
  no real laboratory file — also not "just to try the import".
- All visitors share the same accounts. What one enters, every other holder of the gate
  password can read and change, and it stays until the data is reset.

### What is checked, and what is not

`make demo-smoke` (and CI, on every pull request) boots this stack with a throw-away
configuration and checks, from the API's container as a visitor: nothing is served without
the gate, on any path or method; nothing starts while the gate file holds no password hash;
behind the gate the sign-in page is offered and the workspace renders for a session of a
seeded account; a visitor is counted under the address the proxy saw — not the web server's,
and not an `X-Forwarded-For` the visitor sent; a new gate password replaces the old one; no
secret is in the logs.

Not checked by it: signing in through the proxy the way a browser does (the form's own
request), a public certificate, and what happens after a restart of the server. The first
two were done by hand on the first server — see `docs/notes/0006-review-followups.md`.

This is the first stack in the repository with a real proxy in front of the web server, so
it is also where `TRUSTED_PROXIES` is set as a deployment would set it (the web server's one
fixed address). It holds for visitors who arrive over IPv4: over IPv6 they reach the proxy
through Docker's own forwarder, and all of them are counted under one address.

### What the demo stack is not

- **Not for patients, not for a clinic's work.** Synthetic data only. Development mode is
  what makes it usable, and development mode is what must never meet real data.
- **One shared gate.** Every visitor uses the same user name and password; there is no
  per-person access, no record of who came, and no limit on wrong guesses beyond the cost of
  checking one. Give it only to people who may see the product, and change it (`gate`) when
  that group changes.
- **Open from the server itself.** Whoever has a shell on the server reaches the web app,
  the API's sign-in and the object store without the gate.
- **Uploaded files do not survive a restart.** The object store keeps them in memory; what
  was read from a laboratory file stays in the database, the file itself is gone.
- **No backup, no monitoring, no updates of its own.** The synthetic data can be seeded
  again; what a visitor created is lost with the volume. The server's own upkeep (system
  updates, SSH, the firewall) is its operator's.
- **Not the production path.** The images are built on the server from the checkout and the
  proxy's image is a tag that moves; a deployment pulls scanned, pinned images from a
  registry, runs in production mode behind the production sign-in, and has the list below
  behind it.

## Still missing for a real deployment

TLS termination and public `https` origins (the `__Host-` cookies need them — and the web app
still keeps its own cookies under fixed names without `Secure`, which the production sign-in must
not inherit); managed
PostgreSQL with backups and a tested restore; a secret manager; an EU-region object store with
a bucket-scoped key; the production identity provider (OIDC + MFA); monitoring and alerting
with the redaction layer; a deploy job; runbooks. Go-live plan, workstreams B and C.
