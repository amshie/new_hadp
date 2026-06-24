# Lesson: `INSERT ... RETURNING` re-applies the SELECT RLS policy

Symptom: `new row violates row-level security policy for table "audit_events"` on a
tenant-less (login) audit insert — even though the INSERT `WITH CHECK` allowed
`tenant_id IS NULL`. A plain INSERT succeeded; only INSERT ... RETURNING failed.

Cause: SQLAlchemy fetches server-generated columns (id, created_at) via RETURNING.
RETURNING reads the new row back, which is subject to the table's **SELECT** policy. The
audit SELECT policy scoped strictly to the current tenant, so a NULL-tenant row was not
visible, and the statement failed.

Fix: the audit SELECT policy permits `tenant_id IS NULL OR <tenant matches>`. Tenant-less
rows are global security events (login/logout) carrying no health data; tenant-scoped
audit rows remain isolated.

General rule: any table whose rows are inserted with RETURNING under RLS must have a
SELECT policy that admits the just-inserted row. For tenant tables this is automatic
(we always insert under the matching tenant context); the audit table needed the
explicit NULL allowance.
