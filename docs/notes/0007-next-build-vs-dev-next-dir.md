# Lesson: never `next build` against a running `next dev` (.next corruption)

Symptom: after running `pnpm --filter @hadp/web build` while the dev preview server was
running, `/login` started returning HTTP 500 with `Error: Cannot find module './544.js'`
(webpack-runtime require stack). Other routes (already compiled in memory) still served.

Cause: `next build` and `next dev` share the `apps/web/.next` directory. The production
build overwrote the dev server's chunk files, so the running dev process referenced chunk
ids that no longer existed.

Fix: stop the dev server, `rm -rf apps/web/.next`, restart the dev server (it recompiles
cleanly on first request). For verification builds, prefer building when the dev server is
stopped, or use a separate distDir.

Impact on this work: none to the deliverable — the design-vs-preview screenshots were
captured from the healthy dev server _before_ the build, so they remain valid; the build
itself succeeded (all routes compiled). Only the live preview needed a restart.
