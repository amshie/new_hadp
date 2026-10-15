# 0027 — A link navigation Next.js drops now and then

Status: cause found in React; fixed by a patch to the React that Next.js 15.5 bundles
(2026-10-15). Remove the patch with the upgrade to Next.js 16 (below).

## What happens

On a production build (`next build` + `next start`, Next.js 15.5.27), a click on a `<Link>`
now and then leads nowhere. Seen on the patient page's "Open report":

- the page is hydrated and idle (no request in flight for 500 ms);
- the click is taken: the router fetches the report page's payload, and it arrives — 200,
  `text/x-component`, no redirect;
- nothing is written to the console and no error is thrown;
- the address and the page stay the patient's;
- a second click on the same link goes through.

Measured on 2026-10-14 against the synthetic seed: 2 of 80, 0 of 120, 2 of 200 and 1 of 79
fresh browser contexts, the same on `main` (`b381d70`) as on the branch under test; on
2026-10-15, 10 of 800 on `main` (`a812ee4`). The development server did not show it.

## What it is

Traced on 2026-10-15 in the browser, with nothing on disk changed: the router's chunk and
React's were rewritten in flight by the test to log each router action and each of React's
ping listeners, and React's root was read through the hook React's developer tools use.

1. The click dispatches the navigation; the router applies it, fetches the page's missing
   data and applies that too. Its state holds the report page and its address — in a lost
   click exactly as in a good one.
2. React renders that state inside a transition and suspends on data the server sent but
   React Flight has not decoded yet (a chunk in status `resolved_model`). To be woken when it
   is ready, React calls the chunk's `then` — and such a chunk decodes at once and calls back
   **synchronously, while React is still rendering**.
3. If that render has already been marked "suspended with delay" (a transition that keeps the
   old page on screen), React ignores a ping that arrives during the render phase
   (`pingSuspendedRoot`: "Unless this is being called from the render phase, because that
   would cause a crash … TODO"). The render then ends, the root is marked suspended, and the
   ping is gone: `pendingLanes = suspendedLanes`, `pingedLanes = 0`, no callback scheduled.
   Nothing wakes it again — the page stays for 70 s and longer; only a new update (the second
   click) gets past it.

React has fixed this upstream: in the render phase it now records the ping
(`workInProgressRootPingedLanes`) so that marking the root suspended leaves those lanes
retryable. The React Next.js 15.5 ships (`19.2.0-canary-0bdb9206-20250818`) does not have the
fix — Next.js 15.5.28 changes nothing in the client either. The React Next.js 16.4.1 ships
(`19.3.0-canary-278794d7-20261002`) has it.

## The fix

`patches/next@15.5.27.patch` (`pnpm patch`, named in `package.json` →
`pnpm.patchedDependencies`) makes the same change in every build of `react-dom` Next.js 15.5
bundles (`dist/compiled/react-dom*/cjs/*`): a ping during the render phase is recorded instead
of dropped. Ten files, one condition each; nothing else. The web image copies `patches/`
before it installs (`apps/web/Dockerfile`, `.dockerignore`).

pnpm refuses to install when the patched version is no longer the one installed, so a bump
of `next` has to decide about the patch: port it to the new 15.5 release, or drop it with the
upgrade to a Next.js whose React has the fix (16.4.1 has; the major upgrade is a go-live-plan
decision). `e2e/react-ping.spec.ts` fails if the React the app is built with drops the ping
again.

Measured after the fix on the same seed, a click counted as arrived only when the address
and the page's own content were there within five seconds:

| Navigation                                   | Before (`a812ee4`) | After    |
| -------------------------------------------- | ------------------ | -------- |
| Record → its report ("Open report")          | 10 of 800          | 0 of 800 |
| Report → its record (the crumb)              | —                  | 0 of 200 |
| Record → overview (the sidebar)              | —                  | 0 of 200 |
| Patient list → record (a row, `router.push`) | —                  | 0 of 200 |
| Settings → "Team & roles" (a section)        | —                  | 0 of 200 |

## What was tried and not kept

**Loading states** (`loading.tsx` for every segment a navigation enters) removed the lost
clicks too (0 of 2,000): a navigation into a new segment then commits at once with its
fallback, so its render is never "suspended with delay". But an update that stays on the same
page — a server action that redirects to the page it came from (the interface language, the
preparation-time statement), a link that changes only the search parameters (the audit
trail's filter), a refresh — then suspends inside a boundary that is already on screen, and
lost its ping every time: four browser tests failed deterministically. A loading state at the
root also turned the pages' redirects to the sign-in into 200 answers with a client redirect.
The cause is the ping, not the missing boundaries.

**Next.js 15.5.28**: no change in the client. **`prefetch={false}`**: not measured once the
cause was known — the ping is lost after the page's data has arrived, whatever fetched it.

With the patch the browser suite passes as on `main`, now with one click per link (below).

## What the tests do

`followLink` (`e2e/support/staff.ts`) clicks once again: a link that leads nowhere fails the
step instead of being clicked a second time.

## Open — found on the way, not caused by it

Loading `/einstellungen` (as the owner, in English) fails React's hydration now and then:
"Minified React error #418" (the server's markup and the client's first render differ in an
element), which React recovers from by rendering that part again in the browser. 3 of 1,600
loads on `main`, 2 of 1,600 with the patch — the same before and after. The browser suite
counts any page error as a failure (`watchPageErrors`), so it can meet it about once in a
thousand page loads. Not looked at further here.
