# Capsule runtime database repair: delivery acceptance

Local independent review gate: PASS. Hosted delivery gate: not started.
Final remote verdict, PR/head/merge identities and check results will be supplied
from actual hosted metadata in the final handoff; this document does not claim
unexecuted remote checks or a merge that has not happened.

Goal: agent/goals/2026-09-30_capsule_runtime_db_delivery.md.
Verified base remote main/origin/main:
209b06c3507e9def970b43bcdc5ce03a61b223fc.
Accepted repair: 57e710c818774c0e7c31c36bfc2d995e62e397fc.
Delivery branch: codex/capsule-runtime-db-delivery; audit 217c45f retained.
Standing merge authority independently verified against AGENTS.md, its Goal
and actual merged PR #34 (head 02a4518, merge 5b899cc).

## Behavior and scope

Every run consumes a fresh snapshot-derived database in an owned temporary
directory; existing capsule caches are untouched. Runtime remains alive through
formal processing and artifact verification; cleanup OSError warns and preserves
the result/primary error. Historical audit and repair evidence remain intact.
No algorithm, provider, schema, fixture, research contract or builder changes.

Delivery changes only three new documents: Goal, corresponding record and this
acceptance file. Cumulative PR contains those three plus the nine prior scoped
audit/repair files; only product changes are the runner and two test modules.
Parent inspected actual cumulative implementation/test diff and existing
input/output contracts. No new data acquisition, real research or holdout use.

## Parent local validation

PowerShell in the isolated worktree:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/test_capsule_runtime_db_isolation.py -q -rs
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
git diff --check
git diff --cached --check
git diff origin/main...HEAD -- src tests
Get-FileHash -Algorithm SHA256 -LiteralPath @('src/ashare_research/tools/stage2g_reproducibility.py','tests/test_capsule_runtime_db_isolation.py','tests/test_capsule_input_bindings.py','D:/量化分析/data/research.duckdb')
```

Observed: pytest 14 passed in 16.97s, exit 0; pinned Ruff all checks passed;
unstaged and cached whitespace checks passed.
Prior focused compatibility acceptance: 213 passed / 4 existing skips in 102.78s
at the exact current product/test hashes, verified directly. Two skips lack
symlink privilege and two lack external real-baostock snapshots. Full local
offline suite not redundantly rerun for this documents-only delivery; hosted
workflows must run successfully on the exact published head before merge.

Verified product/test SHA256:
- runner 5dbcfe4b722354b39e3db95bbe58b5cde4673ddb62a12291d98be2e9d10d1c5e
- runtime tests 903114667a8490d27fed1f436d2a27d7b5ce66fb788916ecb01dfe935993dcee
- binding tests e2db6f7f1c6afe519acde051ef8db55b2b7b3cf553794cb3d2d6a5ecd3706abc

Original defect reproduction, before/after consumed facts, baseline regression
failure and repaired formal-run comparisons are in the committed repair
acceptance document; they were not replaced by a summary-only inference.

DSH bounded read-only review exited 0 with PASS and no actionable blockers.
Parent inspected actual cumulative diff, hashes and command results independently.
DSH disclosed one out-of-scope read-only remote metadata attempt that failed
because its network was unavailable, plus a denied cache read; it edited no
files, ran no tests and acquired no provider data. Parent performed required
live remote/authorization checks. This deviation did not expand delivery scope.

## Hosted delivery gates

Publish only the task branch. PR must target main and contain exactly the Goal
scope. Parent verifies published head/base, cumulative files, all hosted check
conclusions and mergeability. Merge only with --match-head-commit and unchanged
base; stop on failed checks, conflicts or drift. Verify actual merged state,
merge commit containment and live remote refs afterward. Preserve published
branch, local user worktrees, stash and runtime databases.

After scoped delivery commit, final head/merge/check identities are recorded by
Git/GitHub itself and in final handoff; no self-referential documentation commit
is added after CI. No direct main push, force push or branch deletion.

## Protection and limits

Protected primary HEAD: 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash: cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f;
research.duckdb SHA256:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Parent compares primary status/diff/HEAD/stash to captured start state and hashes
the protected DB before publication and at final acceptance. Local main in a
different worktree remains untouched; task worktree must finish clean.
Prepublication comparison: primary status/binary diff/HEAD/stash exactly equal
start state, protected DB hash matches, live main still 209b06c. All scoped
source/test hashes match prior validation; only three new delivery docs staged.

Cleanup warning can accompany retained owned staging; non-OSError/logging errors
still propagate. No source-provenance authentication or concurrent portable
input mutation guarantees are added. Rebuild cost per bounded test run remains.
No next implementation/research stage is started by this delivery.
