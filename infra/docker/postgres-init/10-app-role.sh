#!/bin/sh
# Runs once, when the postgres container initializes an empty data directory.
#
# Creates the application role BEFORE the first migration, with its own password from the
# environment. Migration 0002 creates `hadp_app` only if it is missing — and then with the
# development password, which must never exist outside a developer's machine. A deployment on
# a managed database does the same (by hand or by its provisioning tool) before it migrates.
#
# psql reads the password from the environment itself (the backquoted command below) and
# quotes it (:'app_password'), so it appears on no command line and in no shell-built SQL.
: "${HADP_APP_DB_PASSWORD:?HADP_APP_DB_PASSWORD must be set for the postgres service}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\set app_password `printf '%s' "$HADP_APP_DB_PASSWORD"`
CREATE ROLE hadp_app LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION;
SQL
