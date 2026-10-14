#!/usr/bin/env bash
# Restore one backup (scripts/backup.sh) into an EMPTY database, and say what came back
# (docs/security/BACKUP_RESTORE.md).
#
#   scripts/restore.sh latest                # the newest object under the prefix
#   scripts/restore.sh hadp/hadp-2026-10-14T03-17-00Z.dump.age
#
# Configuration, from the environment or $HADP_DEMO_HOME/backup.env (as backup.sh):
#   BACKUP_S3_ENDPOINT, BACKUP_S3_REGION, BACKUP_S3_BUCKET,
#   BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY, BACKUP_PREFIX
#   BACKUP_AGE_IDENTITY         the file holding the age identity (the private half) — on
#                               the machine that restores, for the time of the restore
#
# The target, one of — an EMPTY database, created for this restore (never the live one):
#   RESTORE_PG_DSN              a libpq URL, for a host that has pg_restore
#   RESTORE_PG_CONTAINER        a container with pg_restore in it, plus
#   RESTORE_PG_DATABASE         the empty database in it (RESTORE_PG_USER: postgres)
#
# The role hadp_app must exist in the target cluster before the restore (the dump's policies
# name it): postgres-init/10-app-role.sh does that for a new cluster.
#
# Output: the schema revision the restored database holds, and row counts of a few tables —
# counts, never a value or a name. Compare them with the source (docs: "The restore test").
set -euo pipefail

HADP_DEMO_HOME="${HADP_DEMO_HOME:-/etc/hadp-demo}"
if [ -f "$HADP_DEMO_HOME/backup.env" ]; then
  # shellcheck disable=SC1091
  set -a && . "$HADP_DEMO_HOME/backup.env" && set +a
fi

die() {
  echo "restore: $1" >&2
  exit 1
}

[ $# -eq 1 ] || die "usage: scripts/restore.sh <object name | latest>"
for name in BACKUP_S3_ENDPOINT BACKUP_S3_REGION BACKUP_S3_BUCKET BACKUP_S3_ACCESS_KEY_ID \
  BACKUP_S3_SECRET_ACCESS_KEY BACKUP_AGE_IDENTITY; do
  [ -n "${!name:-}" ] || die "$name is not set"
done
[ -f "$BACKUP_AGE_IDENTITY" ] || die "BACKUP_AGE_IDENTITY is not a file"
command -v age > /dev/null || die "age is not installed (apt-get install age)"

PREFIX="${BACKUP_PREFIX:-hadp}"
PG_USER="${RESTORE_PG_USER:-postgres}"

s3() {
  curl --silent --show-error --fail-with-body \
    --aws-sigv4 "aws:amz:$BACKUP_S3_REGION:s3" \
    --user "$BACKUP_S3_ACCESS_KEY_ID:$BACKUP_S3_SECRET_ACCESS_KEY" \
    "$@"
}
base="${BACKUP_S3_ENDPOINT%/}/$BACKUP_S3_BUCKET"

key="$1"
if [ "$key" = "latest" ]; then
  # The names carry their UTC time, so the last in order is the newest. One page (1000
  # objects) is far more than the retention keeps.
  key="$(s3 "$base?list-type=2&prefix=$PREFIX/" |
    grep -o '<Key>[^<]*</Key>' | sed 's/<Key>//; s#</Key>##' | sort | tail -n 1)"
  [ -n "$key" ] || die "no backup under $PREFIX/ in $BACKUP_S3_BUCKET"
fi

# The target, as a command that reads a custom-format dump on its standard input.
if [ -n "${RESTORE_PG_DSN:-}" ]; then
  command -v pg_restore > /dev/null || die "pg_restore is not installed on this host"
  dsn="${RESTORE_PG_DSN/postgresql+psycopg:/postgresql:}"
  restore() { pg_restore --no-owner --exit-on-error --dbname="$dsn"; }
  query() { psql --quiet --no-align --tuples-only --dbname="$dsn" -c "$1"; }
elif [ -n "${RESTORE_PG_CONTAINER:-}" ]; then
  [ -n "${RESTORE_PG_DATABASE:-}" ] || die "RESTORE_PG_DATABASE is not set"
  restore() { docker exec -i "$RESTORE_PG_CONTAINER" pg_restore --no-owner --exit-on-error -U "$PG_USER" -d "$RESTORE_PG_DATABASE"; }
  query() { docker exec -i "$RESTORE_PG_CONTAINER" psql --quiet --no-align --tuples-only -U "$PG_USER" -d "$RESTORE_PG_DATABASE" -c "$1"; }
else
  die "set RESTORE_PG_DSN, or RESTORE_PG_CONTAINER with RESTORE_PG_DATABASE"
fi

# Empty means empty: a restore never lands on data.
tables="$(query "select count(*) from pg_tables where schemaname = 'public'")"
[ "$tables" = "0" ] || die "the target database is not empty ($tables tables) — restore into a new one"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"

s3 --output "$work/dump.age" "$base/$key" || die "download of $key failed"
# age → pg_restore: the plain dump exists in a pipe only.
age --decrypt --identity "$BACKUP_AGE_IDENTITY" "$work/dump.age" | restore

echo "restored: $key"
echo "schema revision: $(query 'select version_num from alembic_version')"
for table in tenants users patients observations reports audit_events; do
  echo "$table: $(query "select count(*) from $table")"
done
