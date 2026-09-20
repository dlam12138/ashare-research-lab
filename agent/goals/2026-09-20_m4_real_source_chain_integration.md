# Goal: M4 real-source gate, design and offline K1 integration

Date: 2026-09-20. Executor and Git operator: Codex. Independent reviewer: DSH.

## Objective and verified baseline

Replay the already completed, linear real-source chain onto post-PR21 main,
reconcile its historical PR #20 statements with current main, correct only
demonstrable K1 contract defects, and submit one bounded integration PR.

- Worktree: `D:/量化分析-m4-real-source-integration`.
- Branch: `codex/m4-real-source-integration`.
- Verified base: local tracking and live `origin/main` at
  `2bacfd7f7f5a51e168f1d386bfe8a93227fa78e7` (PR #21 merge).
- Replay order: `7888553`, `2910502`, `e4fbde5`, `c92dd66`, `228036c`.
- Protected state: original M2 HEAD
  `3679b1bac7a1634c6452784a4d8f6d139966f222`, stash
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, and default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed and forbidden scope

Allowed: replay the five listed commits; add this Goal, one integration record
and one integration acceptance file; add bounded post-PR21 reconciliation notes;
correct `real_daily_kernel.py` only where its behavior demonstrably contradicts
the accepted design; extend only `test_m4_real_daily_kernel.py`; validate,
commit, push this branch and open one PR to `main`.

Forbidden: provider/network acquisition, database reads or writes, real A-share
observations, holdout access, K2/provider adapters, hypothesis execution,
statistics, scoring, changes to frozen M3/M4 contracts, unrelated source/tests,
dependencies, CI, README, other worktrees, stash or ignored artifacts. Do not
merge the integration PR or start a later stage automatically.

## Required behavior

- Preserve the three separately authorized historical stages and their Goals;
  one integration PR may carry them in their original linear commit order.
- Historical PR #20 evidence remains intact, while a new reconciliation states
  that PR #20 and PR #21 are now merged and removes no historical audit text.
- K1 remains an in-memory offline proof kernel: no filesystem/provider/database
  access, no real-source validation claim, no execution authorization and no
  statistics or research outcome.
- Decimal handling must accept finite decimal strings used by the design,
  including zero and negative values such as `0.00` and `-0.002`, while still
  rejecting floats, exponent notation, non-numeric strings and unsafe shapes.
- All structurally present observation values are validated before PIT/coverage
  classification so an invalid late value cannot be silently downgraded to a
  gap.

## Required tests and exact validation commands

From this worktree, sequentially (never run Ruff concurrently with pytest):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_real_daily_kernel.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_project_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check --no-cache src/ashare_research/mechanism/datasets/real_daily_kernel.py tests/test_m4_real_daily_kernel.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff format --check --no-cache src/ashare_research/mechanism/datasets/real_daily_kernel.py tests/test_m4_real_daily_kernel.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
```

Validate every added Markdown file as strict UTF-8 with final newline, no
trailing whitespace or conflict markers, and resolvable relative links.

## Acceptance criteria

- Branch is based on exact post-PR21 main and contains only replayed artifacts,
  this integration evidence, and the bounded K1/test corrections.
- The replayed stage history is preserved; current repository/PR status is
  reconciled without presenting synthetic evidence as real-source evidence.
- Focused and regression tests, Ruff, formatting, whitespace, link, protected
  state, worktree/stash, and remote checks pass with actual results recorded.
- DSH independently reviews the final diff; final verdict is exactly `PASS`,
  `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop on main drift, replay conflict, protected-state mismatch, unexpected
source/test changes, provider/real-data need, failed regression that cannot be
fixed inside the two whitelisted Python files, or any requirement to weaken a
test or frozen contract.

## Commit, push and next-stage requirements

Local commits, push to `codex/m4-real-source-integration`, and one PR to `main`
are authorized after validation. Direct push to `main`, force-push, merge, K2,
provider access and real-data research are not authorized. The final evidence
packet must report base/final SHAs, files, commands/results, DSH findings,
protected state, worktree/stash state, synchronization, deviations and risks.
