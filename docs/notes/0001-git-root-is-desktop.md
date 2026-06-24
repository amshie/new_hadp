# Lesson: the git repo root is `~/Desktop`, not `NEW_HADP`

`git rev-parse --show-toplevel` from inside `NEW_HADP` returns `/Users/amershieban/Desktop`.
The whole Desktop is one (commit-less) git repo; `NEW_HADP` is an untracked subdirectory.

Consequence for this build:

- I do **not** run `git init`, `git commit`, or any git mutation (commits are not requested,
  and a nested repo would be surprising). All work is plain files under `NEW_HADP/`.
- A project-local `.gitignore` and `.github/workflows/ci.yml` are delivered as files so they
  are correct whenever the user later makes `NEW_HADP` its own repo or moves it.
- The existing Docker container `hadp-alpha-postgres-1` on host port `55432` is the read-only
  reference; this project uses its own compose project (`newhadp`) on different ports.
