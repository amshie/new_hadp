#!/usr/bin/env bash
# Smoke for the production-shaped stack (infra/docker/compose.production.yml).
#
# Run it through `make stack-smoke`, which builds the three images first. It generates random
# secrets for this run (kept in this process's environment — never printed, never written to a
# file), boots the stack, asserts what is listed below, and tears its own stack down again
# (`docker compose down`, never `-v`: the stack has no volume to lose).
#
# What a pass means: the images boot in production mode and hold their posture. It does NOT
# mean the product works there — nobody can sign in to a production-mode stack yet (the
# identity provider is a stub that raises, the development sign-in answers 404), so no
# workflow is exercised. Nothing here uses or creates patient data, real or synthetic.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="hadp-prodshape"
COMPOSE_FILE="$ROOT/infra/docker/compose.production.yml"
CATALOG_TABLES="kpi_catalog_release kpi_catalog kpi_external_code kpi_alias kpi_secondary_domain"

compose() { docker compose -p "$PROJECT" -f "$COMPOSE_FILE" "$@"; }

for image in "${HADP_API_IMAGE:-hadp-api:local}" "${HADP_WORKER_IMAGE:-hadp-worker:local}" \
  "${HADP_WEB_IMAGE:-hadp-web:local}"; do
  docker image inspect "$image" > /dev/null 2>&1 ||
    { echo "image $image not found — run 'make images' (or 'make stack-smoke')" >&2; exit 1; }
done

# Hex only: three of these are put into connection URLs by the compose file.
export POSTGRES_PASSWORD HADP_APP_DB_PASSWORD REDIS_PASSWORD
export S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY SESSION_SECRET
POSTGRES_PASSWORD="$(openssl rand -hex 24)"
HADP_APP_DB_PASSWORD="$(openssl rand -hex 24)"
REDIS_PASSWORD="$(openssl rand -hex 24)"
S3_ACCESS_KEY_ID="$(openssl rand -hex 10)"
S3_SECRET_ACCESS_KEY="$(openssl rand -hex 24)"
SESSION_SECRET="$(openssl rand -hex 32)"

checks=0
ok() {
  checks=$((checks + 1))
  echo "  ok    $1"
}
fail() {
  echo "  FAIL  $1" >&2
  exit 1
}
# expect DESCRIPTION WANTED ACTUAL
expect() {
  [ "$3" = "$2" ] || fail "$1 — wanted '$2', got '$3'"
  ok "$1"
}

teardown() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ]; then
    echo "--- smoke failed; container state and the last log lines of each service ---" >&2
    compose ps -a >&2 || true
    compose logs --no-color --tail 60 >&2 || true
  fi
  echo "--- tearing the stack down ---"
  compose down --timeout 20 || status=1
  left="$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT")"
  if [ -n "$left" ]; then
    echo "containers of $PROJECT are still present after 'down'" >&2
    status=1
  fi
  if [ "$status" -eq 0 ]; then
    echo "stack smoke passed ($checks checks)"
  fi
  exit "$status"
}
trap teardown EXIT

container() { compose ps -aq "$1"; }
state() { docker inspect -f "$2" "$(container "$1")"; }
sql() { compose exec -T postgres psql -U postgres -d hadp -v ON_ERROR_STOP=1 -Atc "$1"; }

echo "--- starting $PROJECT ---"
# A stack left over from an interrupted run is this script's own (same project name).
compose down --timeout 20 > /dev/null 2>&1 || true
# The API takes a client's address from the web server only (TRUSTED_PROXIES). Docker assigns
# this stack's addresses, so the network is brought up first and its range is named: for this
# run "the web server" is any container of this stack.
compose up -d postgres
export TRUSTED_PROXIES
TRUSTED_PROXIES="$(docker network inspect "${PROJECT}_default" -f '{{range .IPAM.Config}}{{.Subnet}},{{end}}')"
[ -n "$TRUSTED_PROXIES" ] || fail "could not read the address range of the stack's network"
# Returns once every dependency condition has held: postgres/redis/s3 healthy, the migrate
# and bucket jobs completed successfully, the API healthy.
compose up -d

echo "--- waiting for the web server ---"
for _ in $(seq 1 60); do
  [ "$(state web '{{.State.Health.Status}}')" = "healthy" ] && break
  sleep 2
done
expect "web container is healthy" "healthy" "$(state web '{{.State.Health.Status}}')"

echo "--- migrate step ---"
expect "migrate exited with status 0" "exited 0" \
  "$(state migrate '{{.State.Status}} {{.State.ExitCode}}')"
# Captured first: `grep -q` closing a pipe early would fail it under `pipefail`.
migrate_log="$(compose logs --no-color migrate)"
case "$migrate_log" in
  *"the catalog confirms the import's"*)
    ok "migrate reported: the catalog confirms the import's automatic names" ;;
  *) fail "migrate did not report a catalog that confirms the import's automatic names" ;;
esac
expect "schema is at exactly one Alembic revision" "1" "$(sql 'SELECT count(*) FROM alembic_version')"
for table in $CATALOG_TABLES; do
  rows="$(sql "SELECT count(*) FROM $table")"
  [ "$rows" -gt 0 ] || fail "catalog table $table is empty"
  ok "catalog table $table has $rows rows"
done
identities="SELECT concat_ws(' ', (SELECT count(*) FROM tenants), (SELECT count(*) FROM users), (SELECT count(*) FROM patients))"
expect "no clinic, no staff, no patient was created" "0 0 0" "$(sql "$identities")"
# The migrate environment holds the admin DSN; the synthetic demo seeder must refuse there.
if refusal="$(compose run --rm --no-deps -T migrate python -m hadp_api.scripts.seed 2>&1)"; then
  fail "the synthetic demo seeder ran in the migrate environment"
fi
case "$refusal" in
  *"refusing to seed synthetic data"*) ;;
  *) fail "the synthetic demo seeder failed for another reason: $refusal" ;;
esac
expect "the synthetic demo seeder refuses to run in the migrate environment" "0 0 0" \
  "$(sql "$identities")"

echo "--- database role ---"
expect "role hadp_app: no superuser, no BYPASSRLS, no CREATEROLE, no CREATEDB" "f f f f" \
  "$(sql "SELECT concat_ws(' ', rolsuper, rolbypassrls, rolcreaterole, rolcreatedb) FROM pg_roles WHERE rolname = 'hadp_app'")"
expect "the API's own connection is that role" "hadp_app False False" "$(
  compose exec -T api python -c '
from sqlalchemy import text
from hadp_api.db.engine import get_engine

query = "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
with get_engine().connect() as conn:
    print(*conn.execute(text(query)).one())
'
)"
compose exec -T api python -c '
import sys

import psycopg

try:
    psycopg.connect("postgresql://hadp_app:hadp_app@postgres:5432/hadp", connect_timeout=5).close()
except psycopg.OperationalError as exc:
    sys.exit(0 if "password authentication failed" in str(exc) else f"unexpected error: {exc}")
sys.exit("accepted")
' || fail "role hadp_app accepts the development password"
ok "role hadp_app does not accept the development password"
expect "the API container holds no admin DSN" "unset" \
  "$(compose exec -T api sh -c 'if [ -n "${DATABASE_URL:-}" ]; then echo set; else echo unset; fi')"

echo "--- API (asked from the web container, as the web server reaches it) ---"
# api METHOD PATH [JSON-BODY] [COOKIE]  ->  "<status> <app_env or error detail> <hsts|no-hsts>"
api() {
  compose exec -T web node -e '
const [method, path, body, cookie] = process.argv.slice(1);
fetch("http://api:8000/api/v1" + path, {
  method,
  headers: { "content-type": "application/json", ...(cookie ? { cookie } : {}) },
  body: body || undefined,
}).then(
  async (res) => {
    const json = await res.json().catch(() => ({}));
    const hsts = res.headers.get("strict-transport-security") ? "hsts" : "no-hsts";
    console.log(res.status, json.app_env ?? json.error?.detail ?? "-", hsts);
  },
  (err) => {
    console.error(String(err));
    process.exit(1);
  },
);
' "$@"
}
expect "GET /api/v1/health: 200, production mode, HSTS" "200 production hsts" "$(api GET /health)"
expect "POST /api/v1/auth/dev-login: 404" "404 not found hsts" \
  "$(api POST /auth/dev-login '{"email":"owner@demo.synthetic"}')"
# A session cookie nobody was issued, under the production cookie name: the running API has
# to look it up (PostgreSQL, as hadp_app) before it can call it invalid.
expect "GET /api/v1/auth/me with an unknown session: 401 after a database lookup" \
  "401 invalid or expired session hsts" \
  "$(api GET /auth/me '' '__Host-hadp_session=smoke-not-a-session')"
expect "the API reaches Redis with its credentials" "True" "$(
  compose exec -T api python -c '
import redis

from hadp_api.config import get_settings

print(redis.Redis.from_url(get_settings().redis_url, socket_timeout=5).ping())
'
)"
# The stack's S3 endpoint is a test double that accepts any credentials: this proves the
# wiring (endpoint, bucket), not that access to the bucket is controlled.
expect "the API reaches the source-documents bucket on its S3 endpoint" "200" "$(
  compose exec -T api python -c '
import boto3

from hadp_api.config import get_settings

s = get_settings()
client = boto3.client(
    "s3",
    endpoint_url=s.s3_endpoint_url,
    region_name=s.s3_region,
    aws_access_key_id=s.s3_access_key_id,
    aws_secret_access_key=s.s3_secret_access_key,
)
response = client.head_bucket(Bucket=s.s3_bucket_source_documents)
print(response["ResponseMetadata"]["HTTPStatusCode"])
'
)"

echo "--- web ---"
compose exec -T web node -e '
(async () => {
  const config = (await import("/srv/hadp/apps/web/next.config.mjs")).default;
  const expected = (await config.headers())[0].headers;
  const res = await fetch("http://127.0.0.1:3000/login");
  const html = await res.text();
  const problems = [];
  if (res.status !== 200) problems.push(`/login answered ${res.status}`);
  for (const { key, value } of expected) {
    if (res.headers.get(key) !== value) problems.push(`${key} is ${res.headers.get(key)}`);
  }
  for (const key of [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
  ]) {
    if (!expected.some((header) => header.key === key)) problems.push(`${key} is not configured`);
  }
  const csp = res.headers.get("content-security-policy") ?? "";
  if (/unsafe-eval|ws:/.test(csp)) problems.push("the development content security policy");
  // Production mode has no sign-in: the page must say so and offer no form.
  if (!html.includes("Anmeldung nicht eingerichtet")) problems.push("no \"not set up\" notice");
  if (/<form|type="email"|type="password"/.test(html)) problems.push("a sign-in form is shown");
  if (problems.length) {
    console.error(problems.join("\n"));
    process.exit(1);
  }
})();
' || fail "web /login"
ok "GET /login: 200 with every security header of next.config.mjs (production policy)"
ok "the login page says that no sign-in is set up, and shows no form"

echo "--- client address (for the limits that count per address) ---"
# Sent the way a proxy in front of the web server would pass a request on: what the client
# wrote into the header itself on the left, the address the proxy saw on the right. The
# clinic does not exist, so the link is refused and nothing reaches a trail.
compose exec -T web node -e '
fetch("http://127.0.0.1:3000/patient-view", {
  headers: {
    cookie: "hadp_pv=00000000-0000-0000-0000-000000000000:smoke-not-a-token",
    "x-forwarded-for": "198.51.100.77, 203.0.113.77",
  },
}).then(
  async (res) => {
    const html = await res.text();
    if (res.status !== 200 || !html.includes("Dieser Bericht ist nicht verf")) {
      console.error(`/patient-view answered ${res.status} without the refusal`);
      process.exit(1);
    }
  },
  (err) => {
    console.error(String(err));
    process.exit(1);
  },
);
' || fail "a patient view through the web server, with a forwarded address"
expect "the API counted that patient view under the address the proxy named, not the client's claim" \
  "1 None" "$(
  compose exec -T api python -c '
import redis

from hadp_api.config import get_settings

store = redis.Redis.from_url(get_settings().redis_url, socket_timeout=5)
named, claimed = (store.get(f"rl:patient_view:{a}") for a in ("203.0.113.77", "198.51.100.77"))
print(named.decode() if named else None, claimed)
'
)"

echo "--- processes and images ---"
# Production mode is the API image's default: started with no configuration at all it must
# refuse — not come up in development mode with the password-less sign-in. An image that did
# start would hold the smoke for ever: where `timeout` exists (it does on the CI runner, not
# on every workstation) the run is cut off after a minute, and the check then fails.
api_image="${HADP_API_IMAGE:-hadp-api:local}"
limited() { if command -v timeout > /dev/null 2>&1; then timeout 60 "$@"; else "$@"; fi; }
unconfigured="$(limited docker run --rm "$api_image" 2>&1)" &&
  fail "the API image starts without any configuration"
case "$unconfigured" in
  *"unsafe production configuration"*)
    ok "the API image refuses to start without its configuration (production is its default)" ;;
  *) fail "the unconfigured API image did not refuse for the expected reason" ;;
esac
for service in api worker web; do
  uids="$(compose exec -T "$service" sh -c 'grep "^Uid:" /proc/1/status' | tr -s '[:space:]' ' ')"
  case "$uids" in
    "Uid: 0 "* | "Uid: "*" 0 "*) fail "$service runs as root ($uids)" ;;
    "Uid: "[1-9]*) ok "$service process is not root (${uids% })" ;;
    *) fail "could not read the uid of $service ($uids)" ;;
  esac
  # "searched" is printed after the search: an empty answer would also be what a failed
  # `exec` gives, and must not read as "nothing found".
  expect "$service image carries no .env file" "searched" \
    "$(compose exec -T "$service" sh -c 'find /srv -name ".env*" | head -n 3; echo searched')"
done
expect "the API's optional env file does not exist in the image" "False" "$(
  compose exec -T api python -c '
from pathlib import Path

from hadp_api.config import Settings

print(Path(str(Settings.model_config["env_file"])).exists())
'
)"
worker_log="$(compose logs --no-color worker)"
case "$worker_log" in
  *"worker started"*) ok "worker logged its start" ;;
  *) fail "worker did not log its start" ;;
esac
for service in postgres redis s3 api worker web; do
  expect "$service is running, never restarted, and mounts no volume" \
    "running restarts=0 volumes=" \
    "$(state "$service" '{{.State.Status}} restarts={{.RestartCount}} volumes={{range .Mounts}}{{if eq .Type "volume"}}{{.Destination}} {{end}}{{end}}')"
done
