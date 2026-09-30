# Capsule post-merge acceptance

Date: 2026-09-30. Module: reproducible value-assessment infrastructure.
Goal: agent/goals/2026-09-30_capsule_postmerge_acceptance.md.
User requested continuation. Baseline main 209b06c3507e9def970b43bcdc5ce03a61b223fc.
Working branch codex/capsule-postmerge-acceptance in a new isolated worktree.

Inspected actual primary branch/HEAD/status/diff, worktrees, remote, stash,
AGENTS.md and agent agreement, record README and latest three relevant records.
Fetched origin; live main matches fetched baseline. Protected DB hash matches
the prior recorded hash. Primary dirty/untracked files and runtime data retained.
Reviewed PR #36 actual hosted metadata: merged head 05b4a5597cce21425f244e5208cb7020427048b6,
merge 209b06c3507e9def970b43bcdc5ce03a61b223fc. Detailed checks inspected;
parent will retain compact check counts and independently validate merged code.

Plan: establish bounded Goal, delegate a read-only DSH audit of code/callers and
coverage, run focused parent tests and pinned lint once, inspect actual results
and protected-state equality, record acceptance in three evidence files, commit
locally. No product changes, new input acquisition or research authorization.

## Independent validation and observed defect

Parent ran the exact nine-module pytest command in the Goal once on merged main:
199 passed, 4 skipped in 68.82s. Two skips lack symlink account privilege;
two lack external real baostock snapshots. Pinned Ruff 0.13.2 check of src/tests
passed. `git diff --check` passed. Actual PR metadata: 42 checks, all SUCCESS.
`git diff 05b4a5597cce21425f244e5208cb7020427048b6 HEAD -- src tests reports
acceptance/fixtures docs .github` returned no changes. Existing PR full-suite
results inspected; no redundant full-suite execution or changed skip conditions.

Read actual runner at stage2g_reproducibility.py:118-139. It verifies portable
snapshot files but reuses an existing unhashed temporary_fact.duckdb. Formal
runner then declares portable snapshot hashes while consuming the cached DB.
Parent first attempted a synthetic probe using nonexistent concept basic_eps;
assertion failed before any mutation, exit 1. Corrected probe to committed
revenue facts, without changing project fixtures or tests.

Successful exact reproduction is preserved in the acceptance file: doubled
database revenue in owned temporary synthetic capsule, trusted portable files
untouched; manifest still valid; actual canonical loader read six doubled facts;
real runner and artifact verification both returned pass. Exit 0. Normal
TemporaryDirectory cleanup removed only probe-owned files. No real input used.

Parent verdict: CHANGES_REQUIRED for runtime input integrity, even though scoped
cleanup regression gates pass. This pre-existing defect triggers the stop
condition; no source fix is mixed into an evidence-only task. Acceptance document
defines repair cases and ownership requirements; do not claim whole-chain safety.

Protected primary status/binary diff/HEAD/stash exactly equal captured baseline.
Database SHA256 unchanged. No changes to source, tests, reports, fixtures,
contracts, events or workflows. Live remote main remains 209b06c. Local main
is 966206f (65 commits behind origin/main), checked out in a different user
worktree; preserved. Task branch starts at current origin/main.

## Delivery

Three evidence files: Goal, this record, acceptance document. Local commit after
final read-only DSH result and diff inspection; no push/PR/merge. Final commit
identity supplied in final handoff to avoid self-referential commit hashes.
Remote main unchanged; local task commit will be one evidence commit ahead.
DSH exited 0 after read-only audit, with PASS scoped to PR #36 regressions.
It independently identified the unbound cached database and missing regression
coverage, plus lower-priority partial-builder-output hygiene concerns. It ran no
tests and edited no files. Parent reproduced the cached database defect with the
real loader/runner and applies CHANGES_REQUIRED to end-to-end input integrity;
DSH's narrower PASS does not override that result. Low-priority concurrency and
builder concerns are inspection observations, not reproduced defects here.
No new research/data stage or automatic follow-on implementation allowed.
