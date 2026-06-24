# Lesson: RLS predicate must `NULLIF(current_setting('app.current_tenant', true), '')`

Symptom: `invalid input syntax for type uuid: ""` on tenant-scoped queries, but only
after the first request on a pooled connection.

Cause: we scope each transaction with `set_config('app.current_tenant', <uuid>, true)`
(transaction-local). At transaction end the GUC reverts — but once a custom GUC has been
set in a session, its reset value is the empty string `''`, **not** NULL. So the next
transaction's `current_setting('app.current_tenant', true)` returns `''`, and the RLS
policy's `''::uuid` cast raises.

Fix: policies compare against
`NULLIF(current_setting('app.current_tenant', true), '')::uuid`, so an unset/empty
context becomes NULL and the predicate cleanly denies all rows (deny-by-default).

Tested by `tests/test_tenant_isolation.py::test_rls_blocks_direct_cross_tenant_reads`,
which runs a query with no tenant context and asserts zero rows.
