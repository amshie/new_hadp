# 0027 — A link navigation Next.js drops now and then

Status: observed, worked around in the browser tests; the product cause is open.

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
fresh browser contexts, the same on `main` (`b381d70`) as on the branch under test. The
development server did not show it. Clicking while the target's prefetch was held back did
not make it more likely (0 of 10), and waiting for the network to be idle did not make it
less (2 of 200). The app writes nothing to `history` itself.

## What the tests do

`e2e/support/staff.ts` `followLink`: click, and if the page has not arrived within five
seconds, click once more — what a person does. A link that does not lead where it should
fails both clicks. Used on the step where CI met it (`language.spec.ts`, the report page).

## Open

Whether a person meets it in use (about one click in a hundred, on any link); whether a
Next.js patch release or `prefetch={false}` on such links changes it. To be looked at on its
own, not by more retries in tests.
