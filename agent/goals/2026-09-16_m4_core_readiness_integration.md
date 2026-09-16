# Goal: M4 core-readiness review integration on post-PR20 main

Date: 2026-09-16. Executor and Git operator: Codex. Independent read-only reviewer: DSH.

## Objective and verified baseline

Replay the already completed M4 core-readiness review from local commit
`65d8abd3b896750d0f8d40ed7bcb08cb91dd88ae` onto the post-PR20 main,
independently verify that its conclusions still match the merged repository, and
submit the bounded documentation-only result for review. Do not begin the real
daily adapter design, K1/K2 implementation, or real-data research.

- Worktree: `D:/量化分析-m4-core-readiness-integration`.
- Branch: `codex/m4-core-readiness-integration`.
- Verified base: local `main`, `origin/main`, and live main
  `966206f06262e43f40c1c7aadbfb8596839eac91` (PR #20 merge commit).
- Source deliverable: clean local branch `codex/m4-core-readiness-review` at
  `65d8abd3b896750d0f8d40ed7bcb08cb91dd88ae`, based on pre-PR20 main
  `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`.
- Protected state: original M2 HEAD
  `3679b1bac7a1634c6452784a4d8f6d139966f222`, stash
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, and default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed and forbidden scope

Allowed:

1. replay the two files introduced by `65d8abd`:
   `agent/goals/2026-09-13_m4_core_readiness_review.md` and
   `acceptance/2026-09-13_m4_core_readiness_review.md`;
2. add this integration Goal, one integration record, and one integration
   acceptance file;
3. correct only demonstrably stale post-PR20 facts in the replayed review;
4. run read-only validation, commit this bounded scope, push this feature
   branch, and open one PR to `main`.

Forbidden: product code, tests, CI, dependencies, configuration, frozen
contracts, reports, data, databases, other worktrees, stash, ignored artifacts,
real provider access, real-data execution, K1/K2 work, merging this PR, or
starting the next stage. Do not rewrite or delete historical PR #20 evidence.

## Required behavior

- Preserve the original review's distinction between synthetic readiness and
  real-data readiness.
- Re-evaluate its conclusions against post-PR20 main rather than copying the old
  verdict blindly. PR #20 may close only the bounded multi-hypothesis synthetic
  portability gap it actually tested.
- Record any superseded statements explicitly. Do not claim full-envelope
  cross-OS identity, real source validation, holdout evidence, or a completed
  M4 milestone.
- DSH performs a read-only independent review and must not edit, commit, push,
  open a PR, create temporary directories, or run real-data workflows.

## Required tests and exact validation commands

From this worktree:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_m4_multi_hypothesis_portability.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
```

Validate every new or replayed Markdown file as strict UTF-8 with final newline,
no trailing whitespace or conflict markers, and valid relative links. Refresh
live `main` and PR state through authenticated GitHub CLI/API before submission.

## Acceptance criteria

- The branch is based on exact post-PR20 main and contains only the five allowed
  Markdown files relative to it.
- The replayed review accurately reflects PR #20's merged evidence and does not
  overstate synthetic or real-data readiness.
- Required regression, Ruff, whitespace, link, protected-state, worktree, stash,
  and remote checks pass with actual results recorded.
- Local, tracking, live remote branch, PR head, and reviewed commit agree after
  push; CI status is reported truthfully.
- Final verdict is exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop on baseline drift, file overlap, unexpected source/test/CI changes,
protected-state mismatch, failed regression, disagreement between the replayed
review and current code, or any need to enter real-data/K1/K2 scope. Do not
weaken or skip tests to obtain a pass.

## Commit, push, and next-stage requirements

Local commits, push to `codex/m4-core-readiness-integration`, and one PR to
`main` are authorized after validation. Direct push to `main`, force-push,
merge, and any later stage are not authorized. The final evidence packet must
include base/final SHAs, files, commands/results, DSH findings, protected state,
worktree/stash state, synchronization, deviations, risks, and whether further
progress is allowed.
