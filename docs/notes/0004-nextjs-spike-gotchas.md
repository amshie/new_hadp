# Lesson: Next.js 15 web spike gotchas

Building the thin clinic/patient UI (apps/web) surfaced a few Next 15 specifics:

- `cookies()` is **async** in Next 15 — `const jar = await cookies()`. The server-side API
  client (`apps/web/src/lib/api.ts`) reads the session cookie this way and forwards it to the
  API as a `Cookie` header (browser↔web is same-origin; web↔API is server-to-server).
- `redirect()` throws a control-flow error, so it must be **outside** any `try/catch` that
  would otherwise swallow it (see `src/app/page.tsx`).
- Cross-origin auth: the API's `Set-Cookie` never reaches the browser (different origin), so
  the dev-login action reads `res.headers.getSetCookie()` and re-sets the session cookie on the
  web app's own domain.
- tsconfig `paths` require `baseUrl` to be set, or tsc errors `TS5090`.
- Pages that call `cookies()`/use `searchParams` render dynamically, so `next build` does not
  call the API at build time (no running backend needed to build).

Verification is via `make web-build` (production build) + the live `make smoke` happy path,
rather than Playwright (deferred). Playwright e2e is the documented follow-up.
