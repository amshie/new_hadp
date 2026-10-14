#!/usr/bin/env bash
# One encrypted dump of the database, uploaded to an S3 bucket (docs/security/BACKUP_RESTORE.md).
#
#   scripts/backup.sh            # dump, encrypt, upload, verify — one line of output
#
# Configuration comes from the environment, or from $HADP_DEMO_HOME/backup.env (default
# /etc/hadp-demo/backup.env, read if it exists — the demo server's way):
#
#   BACKUP_S3_ENDPOINT          https://nbg1.your-objectstorage.com  (an EU endpoint)
#   BACKUP_S3_REGION            nbg1                                  (the endpoint's region)
#   BACKUP_S3_BUCKET            hadp-backups
#   BACKUP_S3_ACCESS_KEY_ID     a key that may write this bucket and nothing else
#   BACKUP_S3_SECRET_ACCESS_KEY
#   BACKUP_AGE_RECIPIENT        age1…  — the PUBLIC half of the backup key. The private half
#                               (the identity) is never on the server; whoever restores holds
#                               it (docs/security/BACKUP_RESTORE.md, "The key").
#   BACKUP_PREFIX               hadp (default) — the object name is <prefix>/<prefix>-<UTC time>.dump.age
#
# The source, one of:
#   BACKUP_PG_CONTAINER         a container with pg_dump in it (the stack's own postgres)
#   BACKUP_PG_DSN               a libpq URL, for a host that has pg_dump
#   neither                     the demo stack's postgres container, found by its compose labels
#   BACKUP_PG_DATABASE / BACKUP_PG_USER   hadp / postgres (the container modes)
#
# The dump leaves this process encrypted: pg_dump's output goes through age before it
# touches the disk, into a directory of this run that is removed on exit. Nothing here
# prints a secret, a value, or a name — the one line of output is the object's name, its
# size and the first bytes of its checksum. The exit status is what cron reports.
set -euo pipefail

HADP_DEMO_HOME="${HADP_DEMO_HOME:-/etc/hadp-demo}"
if [ -f "$HADP_DEMO_HOME/backup.env" ]; then
  # shellcheck disable=SC1091
  set -a && . "$HADP_DEMO_HOME/backup.env" && set +a
fi

die() {
  echo "backup: $1" >&2
  exit 1
}

for name in BACKUP_S3_ENDPOINT BACKUP_S3_REGION BACKUP_S3_BUCKET BACKUP_S3_ACCESS_KEY_ID \
  BACKUP_S3_SECRET_ACCESS_KEY BACKUP_AGE_RECIPIENT; do
  [ -n "${!name:-}" ] || die "$name is not set"
done
case "$BACKUP_AGE_RECIPIENT" in
  age1*) ;;
  *) die "BACKUP_AGE_RECIPIENT is not an age recipient (age1…)" ;;
esac
command -v age > /dev/null || die "age is not installed (apt-get install age)"
command -v curl > /dev/null || die "curl is not installed"

PREFIX="${BACKUP_PREFIX:-hadp}"
DATABASE="${BACKUP_PG_DATABASE:-hadp}"
PG_USER="${BACKUP_PG_USER:-postgres}"

# The dump, as a command that writes pg_dump's custom format to its standard output.
if [ -n "${BACKUP_PG_DSN:-}" ]; then
  command -v pg_dump > /dev/null || die "pg_dump is not installed on this host (set BACKUP_PG_CONTAINER instead)"
  # SQLAlchemy's URL, as the application writes it, is a libpq URL once the driver is dropped.
  dsn="${BACKUP_PG_DSN/postgresql+psycopg:/postgresql:}"
  dump() { pg_dump --format=custom --no-owner --dbname="$dsn"; }
else
  container="${BACKUP_PG_CONTAINER:-}"
  if [ -z "$container" ]; then
    container="$(docker ps -q \
      --filter "label=com.docker.compose.project=${HADP_DEMO_PROJECT:-hadp-demo}" \
      --filter "label=com.docker.compose.service=postgres" | head -n 1)"
    [ -n "$container" ] || die "no running postgres container of the demo stack (is it up?)"
  fi
  dump() { docker exec -i "$container" pg_dump --format=custom --no-owner -U "$PG_USER" "$DATABASE"; }
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"

stamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
key="$PREFIX/$PREFIX-$stamp.dump.age"
file="$work/dump.age"

# pg_dump → age: the plain dump exists in a pipe only. pipefail: a failed dump fails the run,
# whatever age wrote.
dump | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" --output "$file"
size="$(stat -c %s "$file")"
[ "$size" -gt 0 ] || die "the dump is empty"
sum="$(sha256sum "$file" | cut -c1-16)"

s3() {
  curl --silent --show-error --fail-with-body \
    --aws-sigv4 "aws:amz:$BACKUP_S3_REGION:s3" \
    --user "$BACKUP_S3_ACCESS_KEY_ID:$BACKUP_S3_SECRET_ACCESS_KEY" \
    "$@"
}
url="${BACKUP_S3_ENDPOINT%/}/$BACKUP_S3_BUCKET/$key"

s3 --upload-file "$file" --output /dev/null "$url" || die "upload failed"
# Verify: the object is there with the size that was sent.
stored="$(s3 --head --output /dev/null --write-out '%header{content-length}' "$url" || true)"
[ "$stored" = "$size" ] || die "the stored object has size '${stored:-none}', expected $size"

echo "backup: $key $size bytes sha256:$sum…"
