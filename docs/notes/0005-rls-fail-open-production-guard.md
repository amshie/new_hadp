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
  next call is refused again. One initialisation at a time (the first requests after a start
  arrive on several threads), and a connect that does not answer fails after ten seconds.
- It runs in **every environment**. A development or test setup that runs the app as
  `postgres` (an unset `APP_DATABASE_URL` falls back to the admin DSN) is refused with the
  same message, instead of showing cross-tenant behaviour production never has.
- The API checks it at **startup** (`main.py`, lifespan): the process does not come up as
  such a role. Starting the API therefore needs a reachable database.

What the guard does **not** establish (independent review, 2026-10-12; open):

- It reads two attributes of the connecting role, once, at start. A role that is neither a
  superuser nor BYPASSRLS but **owns the tables** passes — on a managed database the admin user
  can be exactly that. Tenant isolation still holds for an owner (every tenant table has
  ENABLE **and** FORCE; `tests/test_rls_tables.py` now asserts it), but the `REVOKE`s that make
  the audit and consent tables append-only do not bind an owner. `APP_DATABASE_URL` unset still
  falls back to the admin DSN, and the production check compares the two DSNs as strings.
  Closing this: make an unset `APP_DATABASE_URL` an error everywhere and refuse a role that
  owns a table.
- A later `ALTER ROLE … BYPASSRLS`, or membership in a bypassing role used through `SET ROLE`,
  is not noticed (no code issues `SET ROLE`).
