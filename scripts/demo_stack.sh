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
# `init` writes two files into HADP_DEMO_HOME (default /etc/hadp-demo), readable by their
# owner only: demo.env (generated secrets, the host name) and gate.caddy (the gate's user name
# and the HASH of its password). The password itself is typed at a hidden prompt, piped to
# the hashing command and kept nowhere. Nothing is printed, and nothing goes into the checkout.
#
# Without a terminal (the smoke) `init` reads DEMO_HOST, DEMO_GATE_USER and DEMO_GATE_PASSWORD
# from the environment instead of asking.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HADP_DEMO_HOME="${HADP_DEMO_HOME:-/etc/hadp-demo}"
ENV_FILE="$HADP_DEMO_HOME/demo.env"
GATE_FILE="$HADP_DEMO_HOME/gate.caddy"
PROXY_IMAGE="caddy:2-alpine"
# More compose files (the smoke adds its own), separated by spaces.
COMPOSE_FILES="$ROOT/infra/docker/compose.demo.yml ${HADP_DEMO_COMPOSE_EXTRA:-}"

die() {
  echo "demo_stack: $1" >&2
  exit 1
}

compose() {
  [ -f "$ENV_FILE" ] && [ -f "$GATE_FILE" ] ||
    die "not initialised — run 'scripts/demo_stack.sh init' first ($HADP_DEMO_HOME)"
  local args=()
  local file
  for file in $COMPOSE_FILES; do args+=(-f "$file"); done
  docker compose --env-file "$ENV_FILE" "${args[@]}" "$@"
}

# write_gate USER PASSWORD — the password reaches the hashing command on its standard input.
write_gate() {
  local user="$1" password="$2" hash
  case "$user" in
    "" | *[!A-Za-z0-9._-]*) die "the gate user may hold letters, digits, '.', '_' and '-' only" ;;
  esac
  [ "${#password}" -ge 12 ] || die "the gate password must have at least 12 characters"
  # The command reads one line; `|| true` so that a failure reaches the message below.
  hash="$(printf '%s\n' "$password" | docker run --rm -i "$PROXY_IMAGE" caddy hash-password 2> /dev/null || true)"
  case "$hash" in
    '$2'*) ;;
    *) die "could not hash the gate password (is the image $PROXY_IMAGE available?)" ;;
  esac
  (
    umask 077
    printf 'basic_auth {\n\t%s %s\n}\n' "$user" "$hash" > "$GATE_FILE.new"
  )
  mv "$GATE_FILE.new" "$GATE_FILE"
}

ask_gate() {
  local user="${DEMO_GATE_USER:-}" password="${DEMO_GATE_PASSWORD:-}" again
  if [ -t 0 ]; then
    read -r -p "Gate user name (what visitors type first): " user
    read -r -s -p "Gate password (at least 12 characters, not shown): " password
    echo
    read -r -s -p "Again: " again
    echo
    [ "$password" = "$again" ] || die "the two passwords differ"
  fi
  write_gate "$user" "$password"
}

cmd_init() {
  [ -e "$ENV_FILE" ] && die "$ENV_FILE exists — this stack is initialised (use 'gate' for a new password)"
  command -v docker > /dev/null || die "docker is not installed"
  command -v openssl > /dev/null || die "openssl is not installed"
  local host="${DEMO_HOST:-}"
  if [ -t 0 ]; then
    read -r -p "Host name visitors will open (a DNS name that points at this server): " host
  fi
  case "$host" in
    "" | *[!A-Za-z0-9.-]*) die "the host name may hold letters, digits, '.' and '-' only" ;;
  esac
  mkdir -p "$HADP_DEMO_HOME"
  chmod 700 "$HADP_DEMO_HOME"
  ask_gate
  # Hex only: three of these are put into connection URLs by the compose file.
  (
    umask 077
    {
      echo "# Written by scripts/demo_stack.sh init. Secrets of the demo stack — keep this file here."
      echo "DEMO_HOST=$host"
      echo "DEMO_TLS=${DEMO_TLS:-}"
      echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
      echo "HADP_APP_DB_PASSWORD=$(openssl rand -hex 24)"
      echo "REDIS_PASSWORD=$(openssl rand -hex 24)"
      echo "S3_ACCESS_KEY_ID=$(openssl rand -hex 10)"
      echo "S3_SECRET_ACCESS_KEY=$(openssl rand -hex 24)"
      echo "SESSION_SECRET=$(openssl rand -hex 32)"
    } > "$ENV_FILE"
  )
  echo "initialised: $HADP_DEMO_HOME (demo.env, gate.caddy). Next: scripts/demo_stack.sh up"
}

cmd_gate() {
  [ -f "$ENV_FILE" ] || die "not initialised — run 'scripts/demo_stack.sh init' first"
  ask_gate
  # The proxy reads its configuration at start.
  if [ -n "$(compose ps -q proxy 2> /dev/null)" ]; then compose restart proxy; fi
  echo "the gate has a new user and password"
}

cmd_up() {
  if [ "${1:-}" != "--no-build" ]; then
    docker build -f "$ROOT/apps/api/Dockerfile" -t "${HADP_API_IMAGE:-hadp-api:local}" "$ROOT"
    docker build -f "$ROOT/apps/web/Dockerfile" -t "${HADP_WEB_IMAGE:-hadp-web:local}" "$ROOT"
  fi
  # Returns once every dependency condition has held: the database healthy, the schema at
  # head and the synthetic data seeded, the API and the web server healthy, the proxy started.
  compose up -d
  echo "the demo is up: https://$(sed -n 's/^DEMO_HOST=//p' "$ENV_FILE")/ (behind the gate; synthetic data only)"
}

case "${1:-}" in
  init) cmd_init ;;
  gate) cmd_gate ;;
  up) cmd_up "${2:-}" ;;
  status) compose ps ;;
  logs) shift; compose logs --tail 100 "$@" ;;
  down) compose down --timeout 20 ;;
  *) die "usage: demo_stack.sh init | up [--no-build] | gate | status | logs [service] | down" ;;
esac
