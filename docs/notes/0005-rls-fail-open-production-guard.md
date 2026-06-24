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
- `_assert_rls_enforceable` (db/engine.py) runs at engine init in production and refuses
  to start if `current_user` is a superuser or has `rolbypassrls`.

Tested in `tests/test_config_guard.py`. Dev/test are unaffected (the guard is
production-only); the test suite still exercises real RLS by connecting as `hadp_app`.
