# M4/M2 open PR queue review and merge closeout

Date: 2026-10-08. Owner: single root agent, no DSH or delegated agents.

## Objective

Under the standing merge authorization recorded in AGENTS.md (2026-09-28),
independently review the 24 open task-scoped PRs (#68-#91), merge each one whose
exact head has a fully successful check set and verified mergeability, repair the
one real cross-platform test defect that blocks part of the queue, and publish a
complete evidence packet. No new research stage is started.

## Verified baseline

- Local main worktree D:/量化分析: branch feat/m2-value-assessment-mvp,
  HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, pre-existing dirty/untracked
  files preserved untouched.
- origin/main and live main ref: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
- Protected stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
- Protected database D:/量化分析/data/research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- 24 open PRs #68-#91, all single-purpose engineering/evidence branches stacked
  on main 8d0fb4d or on each other; each PR head, diff and check set to be
  re-verified at merge time.
- Known blocker: PRs #80-#87 fail the ubuntu clean-clone job because
  tests/test_preparation_comparison_summary.py shells out to `cmd` to create a
  junction, which does not exist on POSIX. The remaining checks in those runs are
  successful; windows clean-clone passes.

## Allowed scope

- Merging reviewed PRs #68-#91 via GitHub merge commits after per-PR
  verification, without branch deletion or history rewriting.
- Pushing ordinary commits to the affected PR branches when a genuine defect must
  be fixed (the #80 link-rejection test portability fix), then re-running CI.
- This branch: agent/goals/2026-10-08_m4_pr_queue_review_and_merge.md,
  agent/record/2026-10-08_01-m4-pr-queue-review-and-merge.md and the matching
  acceptance document.
- Constructing the fix in existing worktrees of the affected branches.

## Forbidden scope

- No force push, no direct main push, no branch deletion, no tag rewrite, no
  history rewriting, no rebase of published branches.
- No weakening, skipping, deleting or rewriting of tests to obtain green checks;
  the ubuntu failure is repaired by making the test portable, not by removing it.
- No data acquisition, provider/network calls for research, database queries,
  holdout use, statistics, or any new research stage.
- No edits to frozen artifacts, protected baselines, stashes, databases or
  foreign worktrees; no cleanup of unrelated dirty/untracked files.

## Required behavior

- For each PR: verify exact head SHA against the PR, inspect the actual diff and
  changed-file list, confirm the declared goal/acceptance evidence exists, and
  require all hosted checks to be completed with success before merging.
- Merge with GitHub merge commits, keeping branches; merge in dependency order
  (stacked branches oldest-first) so each merge keeps the next PR mergeable.
- On conflict or failing check that is not the known ubuntu test defect, stop
  merging that PR and report it; do not bypass.
- The portability fix must preserve the test's intent: a linked preparation
  package path is still rejected on both platforms (POSIX symlink / Windows
  junction), with the same exit code and error contract.

## Required tests / exact validation commands

From D:/量化分析-worktrees/量化分析-m4-pr-queue-closeout and the affected branch
worktree, interpreter D:/量化分析/.venv/Scripts/python.exe, PYTHONPATH=src:

```powershell
python -m pytest -q tests/test_preparation_comparison_summary.py
git diff --check
git status --short --branch
gh pr view <N> --json headRefOid,mergeStateStatus,statusCheckRollup
gh pr merge <N> --merge
git rev-parse origin/main
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git stash list
```

Each command is recorded with its own result; hosted check summaries are read
back after every merge. No claim of a passing run that was not executed.

## Acceptance criteria

- Every one of #68-#91 is either merged with an exact-head fully successful check
  set, or reported unmerged with concrete blocking evidence.
- The ubuntu clean-clone defect is fixed at its source by a real code change on
  the earliest affected branch and re-validated by hosted CI on new heads.
- Protected baseline values, stash, database hash and foreign worktree state are
  unchanged; local main worktree dirt preserved; no force push, no direct main
  push, no branch deletion.
- Final evidence packet: per-PR head, merge result, check summary; exact commands;
  residual risks; explicit statement of what was not done.

## Stop conditions

Baseline drift in main/stash/database, unexpected concurrent edits on a PR branch,
conflicts, failing checks other than the known defect, or any need to expand scope
(new stage, data access, destructive operation). Report with evidence instead of
proceeding.

## Commit / push requirements

Normal non-force pushes only. Local commits on the fix branch and on this closeout
branch; PRs for the fix and closeout are merged under the standing authorization
after green checks. No direct push to main, no force push, no branch deletion.
