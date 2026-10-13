#!/usr/bin/env bash
# The demo stack (infra/docker/compose.demo.yml): HADP on one server, for people who are shown
# the product. SYNTHETIC DATA ONLY — see infra/docker/README.md ("The demo stack").
#
#   scripts/demo_stack.sh init      once: host name, gate user and password, generated secrets
#   scripts/demo_stack.sh up        build the images, start, migrate, seed the synthetic data
#   scripts/demo_stack.sh gate      set a new gate user and password
#   scripts/demo_stack.sh status    what is running
#   scripts/demo_stack.sh logs [service]
#   scripts/demo_stack.sh down      stop (the database volume is kept — there is no `-v` here)
#
# `init` writes two files into HADP_DEMO_HOME (default /etc/hadp-demo, so: as root), readable
# by their owner only: demo.env (generated secrets, the host name) and gate.env (the gate's
# user name and the HASH of its password). The password itself is typed at a hidden prompt,
# piped to the hashing command and kept nowhere. Nothing is printed, and nothing goes into
# the checkout.
#
# Without a terminal (the smoke) `init` and `gate` read DEMO_HOST, DEMO_GATE_USER and
# DEMO_GATE_PASSWORD from the environment instead of asking.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HADP_DEMO_HOME="${HADP_DEMO_HOME:-/etc/hadp-demo}"
ENV_FILE="$HADP_DEMO_HOME/demo.env"
GATE_FILE="$HADP_DEMO_HOME/gate.env"
PROXY_IMAGE="caddy:2-alpine"
# Named here, so that a COMPOSE_PROJECT_NAME left in a shell cannot point these commands at
# another project. The smoke runs under its own name.
PROJECT="${HADP_DEMO_PROJECT:-hadp-demo}"

die() {
  echo "demo_stack: $1" >&2
  exit 1
}

require_init() {
  [ -f "$ENV_FILE" ] && [ -f "$GATE_FILE" ] ||
    die "not initialised — run 'scripts/demo_stack.sh init' first ($HADP_DEMO_HOME)"
  # The gate is what stands between the internet and a sign-in without a password: nothing
  # is started with a gate file that holds no password hash.
  grep -q "^DEMO_GATE_HASH='\$2" "$GATE_FILE" ||
    die "$GATE_FILE holds no password hash — run 'scripts/demo_stack.sh gate'"
}

compose() {
  require_init
  local args=(-p "$PROJECT" --env-file "$ENV_FILE" --env-file "$GATE_FILE"
    -f "$ROOT/infra/docker/compose.demo.yml")
  # One more compose file (the smoke adds its own).
  if [ -n "${HADP_DEMO_COMPOSE_EXTRA:-}" ]; then args+=(-f "$HADP_DEMO_COMPOSE_EXTRA"); fi
  docker compose "${args[@]}" "$@"
}

# write_gate USER PASSWORD — the password reaches the hashing command on its standard input.
write_gate() {
  local user="$1" password="$2" hash
  case "$user" in
    "" | *[!A-Za-z0-9._-]*) die "the gate user may hold letters, digits, '.', '_' and '-' only" ;;
    import) die "'import' cannot be the gate user (it is a word of the proxy's configuration)" ;;
  esac
  [ "${#password}" -ge 12 ] || die "the gate password must have at least 12 characters"
  # bcrypt reads 72 bytes and no more.
  [ "$(printf '%s' "$password" | wc -c)" -le 72 ] ||
    die "the gate password must not be longer than 72 bytes"
  # The command reads one line, and needs no network for it. `|| true`: a failure reaches
  # the message below.
  hash="$(printf '%s\n' "$password" |
    docker run --rm -i --network none "$PROXY_IMAGE" caddy hash-password 2> /dev/null || true)"
  case "$hash" in
    '$2'*) ;;
    *) die "could not hash the gate password (is $PROXY_IMAGE on this machine? 'docker pull $PROXY_IMAGE')" ;;
  esac
  # Single quotes: the hash is full of "$", which an env file would otherwise read as variables.
  (
    umask 077
    printf "DEMO_GATE_USER=%s\nDEMO_GATE_HASH='%s'\n" "$user" "$hash" > "$GATE_FILE.new"
  )
  mv "$GATE_FILE.new" "$GATE_FILE"
}

ask_gate() {
  local user="${DEMO_GATE_USER:-}" password="${DEMO_GATE_PASSWORD:-}" again
  if [ -t 0 ]; then
    read -r -p "Gate user name (what visitors type first): " user
    IFS= read -r -s -p "Gate password (12 to 72 characters, not shown): " password
    echo
    IFS= read -r -s -p "Again: " again
    echo
    [ "$password" = "$again" ] || die "the two passwords differ"
  fi
  write_gate "$user" "$password"
}

cmd_init() {
  [ -e "$ENV_FILE" ] && die "$ENV_FILE exists — this stack is initialised (use 'gate' for a new password)"
  command -v docker > /dev/null || die "docker is not installed"
  command -v openssl > /dev/null || die "openssl is not installed"
  local host="${DEMO_HOST:-}" tls="${DEMO_TLS:-}"
  if [ -t 0 ]; then
    read -r -p "Host name visitors will open (a DNS name that points at this server): " host
  fi
  case "$host" in
    "" | *[!A-Za-z0-9.-]*) die "the host name may hold letters, digits, '.' and '-' only" ;;
  esac
  # This becomes a line of the proxy's configuration: nothing but the two values it knows.
  case "$tls" in
    "" | "tls internal") ;;
    *) die "DEMO_TLS is empty (a public certificate) or 'tls internal'" ;;
  esac
  mkdir -p "$HADP_DEMO_HOME" || die "cannot create $HADP_DEMO_HOME (run as root, or set HADP_DEMO_HOME)"
  chmod 700 "$HADP_DEMO_HOME"
  docker pull -q "$PROXY_IMAGE" > /dev/null || die "cannot pull $PROXY_IMAGE"
  ask_gate
  # Hex only: three of these are put into connection URLs by the compose file.
  (
    umask 077
    {
      echo "# Written by scripts/demo_stack.sh init. Secrets of the demo stack — keep this file:"
      echo "# the database volume was created with these passwords."
      echo "DEMO_HOST=$host"
      echo "DEMO_TLS=$tls"
      echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
      echo "HADP_APP_DB_PASSWORD=$(openssl rand -hex 24)"
      echo "REDIS_PASSWORD=$(openssl rand -hex 24)"
      echo "S3_ACCESS_KEY_ID=$(openssl rand -hex 10)"
      echo "S3_SECRET_ACCESS_KEY=$(openssl rand -hex 24)"
      echo "SESSION_SECRET=$(openssl rand -hex 32)"
    } > "$ENV_FILE"
  )
  echo "initialised: $HADP_DEMO_HOME (demo.env, gate.env). Next: scripts/demo_stack.sh up"
}

# The proxy answers only once it has read its configuration; one that cannot (a wrong host
# name, a damaged gate) stops and starts for ever while everything behind it looks healthy.
wait_for_proxy() {
  local id health
  for _ in $(seq 1 40); do
    id="$(compose ps -q proxy)"
    health="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2> /dev/null || true)"
    [ "$health" = "healthy" ] && return 0
    sleep 2
  done
  die "the proxy did not come up — see 'scripts/demo_stack.sh logs proxy'"
}

cmd_gate() {
  [ -f "$ENV_FILE" ] || die "not initialised — run 'scripts/demo_stack.sh init' first"
  ask_gate
  # The proxy takes the gate from its environment: it is created again, not just restarted.
  if [ -n "$(compose ps -q proxy 2> /dev/null)" ]; then
    compose up -d --no-deps proxy
    wait_for_proxy
  fi
  echo "the gate has a new user and password"
}

cmd_up() {
  require_init
  if [ "${1:-}" != "--no-build" ]; then
    docker build -f "$ROOT/apps/api/Dockerfile" -t "${HADP_API_IMAGE:-hadp-api:local}" "$ROOT"
    docker build -f "$ROOT/apps/web/Dockerfile" -t "${HADP_WEB_IMAGE:-hadp-web:local}" "$ROOT"
  fi
  # Returns once every dependency condition has held: the database healthy, the schema at
  # head and the synthetic data seeded, the API and the web server healthy, the proxy started.
  compose up -d
  # The proxy reads its configuration file once, when its container is created — and an
  # unchanged service is not created again. So that a changed file takes effect:
  compose up -d --no-deps --force-recreate proxy
  wait_for_proxy
  echo "the demo is up: https://$(sed -n 's/^DEMO_HOST=//p' "$ENV_FILE")/ (behind the gate; synthetic data only)"
}

# One command at a time. Two `up` runs side by side create the proxy twice and one of them
# fails on the name (seen on the first server: two people started it in the same minute).
# Where `flock` exists — on a server it does — the second run says so and stops.
lock() {
  command -v flock > /dev/null || return 0
  [ -d "$HADP_DEMO_HOME" ] || return 0
  exec 9> "$HADP_DEMO_HOME/.lock"
  flock -n 9 || die "another demo_stack command is running — wait for it to finish"
}

case "${1:-}" in
  init | gate | up | down) lock ;;
esac

case "${1:-}" in
  init) cmd_init ;;
  gate) cmd_gate ;;
  up) cmd_up "${2:-}" ;;
  status) compose ps ;;
  logs) shift; compose logs --tail 100 "$@" ;;
  down) compose down --timeout 20 ;;
  *) die "usage: demo_stack.sh init | up [--no-build] | gate | status | logs [service] | down" ;;
esac
