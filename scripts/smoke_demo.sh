#!/usr/bin/env bash
# Smoke for the demo stack (infra/docker/compose.demo.yml), through scripts/demo_stack.sh —
# the same commands a server runs. Run it through `make demo-smoke`, which builds the images
# first.
#
# It initialises a throw-away stack (its own project name and address range, a random gate
# password, the proxy's own certificate instead of a public one, no published port), and
# asks from the API's container, as a visitor would through the proxy:
#   - nothing is served without the gate's user name and password, on any path or method;
#   - behind the gate the sign-in page offers the development sign-in, and a session of a
#     seeded synthetic account renders the workspace;
#   - a visitor is counted under the address the PROXY saw — not under the web server's, and
#     not under an X-Forwarded-For the visitor sent;
#   - a new gate password replaces the old one.
# What it does NOT do: sign in through the proxy the way a browser does (the form's own
# request), and obtain a public certificate — neither can be had without a browser and a
# public name. Synthetic data only. Nothing is left behind: the stack is taken down, its
# files removed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO="$ROOT/scripts/demo_stack.sh"

for image in "${HADP_API_IMAGE:-hadp-api:local}" "${HADP_WEB_IMAGE:-hadp-web:local}"; do
  docker image inspect "$image" > /dev/null 2>&1 ||
    { echo "image $image not found — run 'make images' (or 'make demo-smoke')" >&2; exit 1; }
done

# Its own project and address range: it can run beside a demo on the same machine.
export HADP_DEMO_PROJECT="hadp-demo-smoke"
export HADP_DEMO_HOME
HADP_DEMO_HOME="$(mktemp -d)"
export HADP_DEMO_COMPOSE_EXTRA="$ROOT/infra/docker/compose.demo.smoke.yml"
export DEMO_SUBNET="172.30.251.0/27" DEMO_DYNAMIC_RANGE="172.30.251.0/28"
export DEMO_WEB_ADDRESS="172.30.251.20"
# "proxy" is the proxy's name inside the stack's network; no public name exists here.
export DEMO_HOST="proxy" DEMO_TLS="tls internal"
export DEMO_GATE_USER="smoke" DEMO_GATE_PASSWORD
DEMO_GATE_PASSWORD="$(openssl rand -hex 16)"

checks=0
ok() {
  checks=$((checks + 1))
  echo "  ok    $1"
}
fail() {
  echo "  FAIL  $1" >&2
  exit 1
}

compose() {
  docker compose -p "$HADP_DEMO_PROJECT" \
    --env-file "$HADP_DEMO_HOME/demo.env" --env-file "$HADP_DEMO_HOME/gate.env" \
    -f "$ROOT/infra/docker/compose.demo.yml" -f "$HADP_DEMO_COMPOSE_EXTRA" "$@"
}

teardown() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ] && [ -f "$HADP_DEMO_HOME/gate.env" ]; then
    echo "--- demo smoke failed; container state and the last log lines of each service ---" >&2
    compose ps -a >&2 || true
    compose logs --no-color --tail 40 >&2 || true
  fi
  echo "--- taking the demo stack down ---"
  # By project name: this works whatever became of the run's files.
  docker compose -p "$HADP_DEMO_PROJECT" down --timeout 20 || status=1
  rm -rf "$HADP_DEMO_HOME"
  if [ "$status" -eq 0 ]; then echo "demo smoke passed ($checks checks)"; fi
  exit "$status"
}
trap teardown EXIT

# A stack left over from an interrupted run is this script's own (same project name).
docker compose -p "$HADP_DEMO_PROJECT" down --timeout 20 > /dev/null 2>&1 || true

echo "--- what the stack exposes ---"
exposure="$(
  POSTGRES_PASSWORD=x HADP_APP_DB_PASSWORD=x REDIS_PASSWORD=x S3_ACCESS_KEY_ID=x \
    S3_SECRET_ACCESS_KEY=x SESSION_SECRET=x DEMO_GATE_USER=x DEMO_GATE_HASH=x \
    docker compose -f "$ROOT/infra/docker/compose.demo.yml" config --format json |
    python3 -c '
import json, sys

services = json.load(sys.stdin)["services"]
published = sorted(
    "%s:%s/%s" % (name, port.get("published"), port.get("protocol", "tcp"))
    for name, service in services.items()
    for port in service.get("ports") or []
)
on_the_host_network = sorted(name for name, service in services.items() if service.get("network_mode"))
print((" ".join(published) + " | " + " ".join(on_the_host_network)).strip())
'
)"
[ "$exposure" = "proxy:443/tcp proxy:80/tcp |" ] || fail "published ports and host networking: '$exposure'"
ok "the proxy publishes 80/tcp and 443/tcp; no other service publishes a port or shares the host's network"

echo "--- init and up, as on a server ---"
"$DEMO" init < /dev/null
for file in demo.env gate.env; do
  mode="$(python3 -c 'import os, sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777))' "$HADP_DEMO_HOME/$file")"
  [ "$mode" = "0o600" ] || fail "$file is readable by others ($mode)"
done
ok "demo.env and gate.env are readable by their owner only"
if grep -q "$DEMO_GATE_PASSWORD" "$HADP_DEMO_HOME/demo.env" "$HADP_DEMO_HOME/gate.env"; then
  fail "the gate password is stored in plain text"
fi
ok "the gate password is stored as a hash only"
# A gate file without a password hash must not start anything.
cp "$HADP_DEMO_HOME/gate.env" "$HADP_DEMO_HOME/gate.env.kept"
: > "$HADP_DEMO_HOME/gate.env"
if "$DEMO" up --no-build > /dev/null 2>&1; then fail "the stack started with an empty gate file"; fi
[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=$HADP_DEMO_PROJECT")" ] ||
  fail "containers were created with an empty gate file"
mv "$HADP_DEMO_HOME/gate.env.kept" "$HADP_DEMO_HOME/gate.env"
ok "nothing starts while the gate file holds no password hash"
"$DEMO" up --no-build

# visitor GATE_USER GATE_PASSWORD — the checks a visitor's side can make, from the API's container.
visitor() {
  compose exec -T -e GATE_USER="$1" -e GATE_PASSWORD="$2" -e WEB_ADDRESS="$DEMO_WEB_ADDRESS" \
    -e SMOKE_PART="$3" api python - <<'PY'
import base64
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request

import redis

from hadp_api.config import get_settings

USER, PASSWORD, PART = os.environ["GATE_USER"], os.environ["GATE_PASSWORD"], os.environ["SMOKE_PART"]
API = "http://127.0.0.1:8000/api/v1"

# The proxy signs its own certificate here; a public one exists only for a public name.
unverified = ssl.create_default_context()
unverified.check_hostname = False
unverified.verify_mode = ssl.CERT_NONE


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None


opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=unverified), NoRedirect)


def call(url, *, method="GET", body=None, headers=None, gate=None):  # type: ignore[no-untyped-def]
    request = urllib.request.Request(url, method=method, headers=dict(headers or {}))
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("content-type", "application/json")
    if gate is not None:
        token = base64.b64encode(f"{USER}:{gate}".encode()).decode()
        request.add_header("authorization", f"Basic {token}")
    try:
        with opener.open(request, timeout=60) as response:
            return response.status, response.headers, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode("utf-8", "replace")


def check(description, condition, detail=""):  # type: ignore[no-untyped-def]
    if not condition:
        sys.exit(f"  FAIL  {description} {detail}")
    print(f"  ok    {description}")


if PART == "status":
    # Used after the gate was changed: does this user name and password still open it?
    print(call("https://proxy/login", gate=PASSWORD)[0])
    sys.exit(0)

refused = {}
for method, path in [
    ("GET", "/"),
    ("GET", "/login"),
    ("GET", "/overview"),
    ("GET", "/patient-view"),
    ("GET", "/_next/static/chunks/main.js"),
    ("GET", "/api/v1/health"),
    ("POST", "/login"),
]:
    status, headers, _ = call(f"https://proxy{path}", method=method, body={} if method == "POST" else None)
    refused[f"{method} {path}"] = (status, headers.get("www-authenticate", "").lower()[:5])
check(
    "without the gate's credentials nothing is served, on any path or method (401, Basic)",
    all(answer == (401, "basic") for answer in refused.values()),
    f"— got {refused}",
)
status, _, _ = call("https://proxy/login", gate="not-the-password")
check("a wrong gate password is refused (401)", status == 401, f"— got {status}")
status, headers, _ = call("http://proxy/login")
check(
    "plain HTTP is sent to HTTPS, and serves nothing itself",
    status in (301, 308) and headers.get("location", "").startswith("https://proxy/"),
    f"— got {status} {headers.get('location')}",
)
status, _, page = call("https://proxy/login", headers={"host": "another.example"}, gate=PASSWORD)
check(
    "a request for another host name is not passed on to the application",
    'name="email"' not in page and "HADP" not in page,
    f"— got {status}",
)
status, headers, page = call("https://proxy/login", gate=PASSWORD)
check(
    "behind the gate the sign-in page offers the development sign-in, and says the data is synthetic",
    status == 200 and 'name="email"' in page and "synthetischen Beispieldaten" in page,
    f"— got {status}",
)
check("HTTP/3 is not offered (only TCP is published)", "h3" not in headers.get("alt-svc", ""))

status, _, health = call(f"{API}/health")
check("the API runs in development mode", json.loads(health).get("app_env") == "development")

# A seeded synthetic account, signed in at the API as the web server does it, then the
# workspace through the proxy with that session. (The form's own request — what a browser
# sends when a visitor signs in — is not made here.)
status, headers, _ = call(f"{API}/auth/dev-login", method="POST", body={"email": "owner@demo.synthetic"})
check("the seeded synthetic owner can sign in at the API", status == 200, f"— got {status}")
cookies = {}
for value in headers.get_all("set-cookie") or []:
    name, _, rest = value.partition("=")
    cookies[name] = rest.split(";", 1)[0]
session = "; ".join(f"{name}={value}" for name, value in cookies.items())
status, _, tenants = call(f"{API}/tenancy/my-tenants", headers={"cookie": session})
tenant = next(t for t in json.loads(tenants) if t["tenant_slug"] == "demo-clinic")
status, _, _ = call(
    f"{API}/tenancy/select-tenant",
    method="POST",
    body={"tenant_id": tenant["tenant_id"]},
    headers={"cookie": session, "x-csrf-token": cookies.get("hadp_csrf", "")},
)
check("the owner enters the synthetic demo clinic", status == 200, f"— got {status}")
status, _, page = call("https://proxy/overview", gate=PASSWORD, headers={"cookie": session})
check(
    "the workspace renders through the proxy for that session",
    status == 200 and "Synthetic Owner" in page and "Synthetische Beispieldaten" in page,
    f"— got {status}",
)

# Whose request it is. This container is the visitor; the proxy saw its address.
visitor = socket.gethostbyname(socket.gethostname())
claimed = "203.0.113.9"  # a documentation address the visitor writes into the header itself
store = redis.Redis.from_url(get_settings().redis_url, socket_timeout=5)
status, _, page = call(
    "https://proxy/patient-view",
    gate=PASSWORD,
    headers={
        "cookie": "hadp_pv=00000000-0000-0000-0000-000000000000:smoke-not-a-token",
        "x-forwarded-for": claimed,
    },
)
check("a wrong patient link is refused", status == 200 and "Dieser Bericht ist nicht verf" in page)
counted = sorted(key.decode() for key in store.scan_iter(match="rl:patient_view:*"))
check(
    "the visitor was counted under the address the proxy saw — not the web server's, "
    "and not the one the visitor claimed",
    counted == [f"rl:patient_view:{visitor}"]
    and visitor not in (os.environ["WEB_ADDRESS"], claimed),
    f"— counted under {counted}, visitor {visitor}",
)
PY
}

echo "--- as a visitor, from another container, through the proxy ---"
visitor "$DEMO_GATE_USER" "$DEMO_GATE_PASSWORD" all
checks=$((checks + 12))

echo "--- the proxy, and what the stack wrote ---"
proxy_state="$(docker inspect -f '{{.State.Status}} {{.State.Health.Status}} restarts={{.RestartCount}}' "$(compose ps -q proxy)")"
[ "$proxy_state" = "running healthy restarts=0" ] || fail "the proxy: $proxy_state"
ok "the proxy is running, reports itself ready, and never restarted"
logs="$(compose logs --no-color 2>&1)"
# shellcheck disable=SC2046  # one word per generated value
for secret in "$DEMO_GATE_PASSWORD" $(sed -nE 's/^[A-Z0-9_]*(PASSWORD|SECRET|KEY_ID|ACCESS_KEY)=//p' "$HADP_DEMO_HOME/demo.env"); do
  case "$logs" in
    *"$secret"*) fail "a secret of the stack is in its logs" ;;
  esac
done
ok "no generated secret and no gate password is in the stack's logs"

echo "--- a new gate password ---"
old_password="$DEMO_GATE_PASSWORD"
DEMO_GATE_PASSWORD="$(openssl rand -hex 16)"
"$DEMO" gate < /dev/null
[ "$(visitor "$DEMO_GATE_USER" "$old_password" status)" = "401" ] || fail "the old gate password still opens the gate"
[ "$(visitor "$DEMO_GATE_USER" "$DEMO_GATE_PASSWORD" status)" = "200" ] || fail "the new gate password does not open the gate"
ok "after 'gate' the old password is refused and the new one opens"

echo "--- the data is the synthetic set ---"
rows="$(compose exec -T postgres psql -U postgres -d hadp -v ON_ERROR_STOP=1 -Atc \
  "SELECT concat_ws(' ', (SELECT count(*) FROM tenants WHERE is_synthetic), (SELECT count(*) FROM tenants WHERE NOT is_synthetic), (SELECT count(*) FROM patients WHERE NOT is_synthetic))")"
case "$rows" in
  "0 "*) fail "no synthetic clinic was seeded ($rows)" ;;
  *" 0 0") ok "seeded clinics are synthetic, and no record is marked otherwise ($rows)" ;;
  *) fail "a record is not marked synthetic ($rows)" ;;
esac
