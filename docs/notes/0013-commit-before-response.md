# Lesson: FastAPI commits a `yield` dependency AFTER the response unless told otherwise

Date: 2026-10-12.

Symptom: the web route smoke failed once in CI with `TypeError: string indices must be integers`.
The API log showed `POST /auth/dev-login` → 200 followed, on the same connection, by
`GET /tenancy/my-tenants` → 401 "invalid or expired session". The job had passed on every earlier
run and passed locally.

Cause: the request session (`db/session.py:get_db`) commits in the code after its `yield`. Since
FastAPI 0.106 a `yield` dependency ends **after the response has been sent** (scope `"request"`,
the default). So every write endpoint answered before its transaction was committed:

- a request sent right after a write could miss it — the login above, or the web login action
  (log in, then select the clinic);
- a commit that failed was reported to the client as success, with the row **and its audit
  event** silently dropped.

Proof: with the real app and every commit delayed by 300 ms, the login answered in 121 ms and the
immediate read got 401; the same read 0.6 s later got 200. A test that makes the commit fail
received `201` for a patient that was never stored.

Fix: the dependency is declared once, as `RequestSession = Depends(get_db, scope="function")`
(FastAPI ≥ 0.121). The function scope ends the dependency — the commit — when the path operation
returns, before the response is sent. Routes use `db: Session = RequestSession`; nothing else may
declare `Depends(get_db)`, because two declarations with different scopes would be two sessions in
one request. After the fix the same experiment answers the login in 515 ms and the immediate read
gets 200.

Guards (`apps/api/tests/test_commit_before_response.py`): at the ASGI boundary, the row and its
audit event are visible to an independent connection when the response starts; a session is usable
the moment login answers; a failed commit returns 500 and stores nothing; no file but
`db/session.py` declares the dependency.

What this does not change: `expire_on_commit=False` keeps returned objects readable after the
commit; the erasure route's explicit mid-request commit and `record_security_event`'s own
connection are untouched.
