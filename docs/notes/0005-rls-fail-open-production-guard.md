# Lesson: RLS can silently fail open if the app connects as a superuser

The whole tenant-isolation guarantee depends on the application connecting as the
non-superuser role `hadp_app`. PostgreSQL **superusers and BYPASSRLS roles ignore RLS
unconditionally** — `FORCE ROW LEVEL SECURITY` only binds the table _owner_, not
superusers. So if the app ever connects as `postgres`, every `tenant_isolation` policy
is silently bypassed and all cross-tenant reads/writes succeed.

The original config made this one typo away: `effective_app_database_url` falls back to
the admin/superuser DSN when `APP_DATABASE_URL` is unset, and `database_url` defaults to
the `postgres` superuser. Nothing enforced the safe role. (Found by the adversarial
review as a P0.)

Guards added:

- `Settings._enforce_production_safety` (config.py) refuses to boot in production unless
  `APP_DATABASE_URL` is set and distinct from `DATABASE_URL`, the session secret is a
  strong non-default value, and S3 creds are not the dev default.
- `_assert_rls_enforceable` (db/engine.py) refuses a `current_user` that is a superuser or
  has `rolbypassrls`.

Tested in `tests/test_config_guard.py` (the configuration) and `tests/test_rls_role_guard.py`
(the role).

## Correction, 2026-10-12: the role guard did not hold

The role assertion ran in production only, when the engine was first created — and the
engine was stored **before** the assertion ran. With a misprovisioned application role (a
distinct DSN, so the configuration guard passes, but a superuser or BYPASSRLS role behind
it) the first request failed with the refusal and **every later request was served through
the stored engine, with RLS bypassed**. `/health` does not touch the database, so the
process also looked healthy. Nothing tested the assertion.

As it stands now:

- The assertion runs **before** the engine is kept; a refused engine is disposed and the
  next call is refused again.
- It runs in **every environment**. A development or test setup that runs the app as
  `postgres` (an unset `APP_DATABASE_URL` falls back to the admin DSN) is refused with the
  same message, instead of showing cross-tenant behaviour production never has.
- The API checks it at **startup** (`main.py`, lifespan): the process does not come up as
  such a role. Starting the API therefore needs a reachable database.
