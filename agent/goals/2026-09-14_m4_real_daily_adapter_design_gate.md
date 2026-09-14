# Goal: M4 real daily-data adapter design gate

Date: 2026-09-14. DSH performs a bounded read-only challenge; Codex owns the decision and independent review.

## Objective and verified baseline

Decide whether the next safe project stage may be a **design-only** contract for a real daily-data adapter. Identify the minimum source, calendar, universe membership, PIT, lineage and authorization evidence that design must specify. This decision neither supplies real inputs nor authorizes real hypothesis execution.

- Worktree `D:/量化分析-m4-real-data-adapter-preflight`, branch `codex/m4-real-data-adapter-preflight`, created clean from `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`; local/origin/live main matched at task start.
- Multi-hypothesis synthetic acceptance is on open PR #20, exact head `d593f40ee6cc17147164c67d31f84ce34da6785a`; 42/42 PR checks succeeded, including Ubuntu and Windows Stage 2G full suites. It is not merged into this base.
- The separate core-readiness review `codex/m4-core-readiness-review@65d8abd3b896750d0f8d40ed7bcb08cb91dd88ae` recommended this North-Star decision after two-hypothesis synthetic acceptance.
- Original M2 worktree HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`, protected stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed and forbidden scope

Only add this Goal, `docs/m4_real_daily_adapter_design_gate_v1.md` and `acceptance/2026-09-14_m4_real_daily_adapter_design_gate.md` in this new worktree. Read tracked North-Star, Stage4P, M3 source/timing/PIT contracts, M4 synthetic adapter and relevant tests. DSH may run read-only commands but must not edit, create temp directories, run tests or commit.

Do not modify source, tests, frozen contracts, README, reports, CI, dependencies, other worktrees, stash, data or ignored artifacts. Do not open/query the default database, acquire provider/market/literature data, build a real dataset, create a real candidate, inspect outcomes, use holdout, run a hypothesis, push, open a PR or merge. Do not silently extend the frozen synthetic schema to imply real provenance. PR #20 stays open.

## Required behavior and tests

Distinguish (1) synthetic portability demonstrated on PR #20, (2) the current real-data evidence gaps, and (3) the proposed design-only stage. The decision document must list exact evidence questions and fail-closed conditions for: provider/source identity and revisions; trading calendar/session/timezone; security/universe identity and membership as of the signal date; publication/ingestion/availability timestamps; return/adjustment conventions; role-level coverage and missingness; immutable input and code provenance; and pre-outcome registration/holdout separation. It must identify which existing M3 contracts can be reused as constraints without treating their specific data as automatically portable. State the stage that remains forbidden and the explicit gate before implementation and execution.

Run the existing targeted tests from this worktree to verify the current synthetic contracts, without changing them:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
git ls-remote origin refs/heads/main refs/heads/codex/m4-multi-hypothesis-acceptance
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
```

Check new Markdown as strict UTF-8, LF final newline, no trailing whitespace/conflict markers and valid relative links. Verify PR #20's exact head/status/checks through GitHub; do not infer merge from CI success. Inspect all changed/untracked files and all worktree/stash/protected states before accepting.

## Acceptance, stop and delivery

Acceptance requires a concrete, bounded design-only decision with no implication that real data or execution is authorized, only three whitelisted Markdown files, passing targeted tests and hygiene, unchanged protected states, and a clean local delivery commit. Final verdict exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

Stop if main/PR/protected baselines drift, actual code conflicts with the proposed boundary, a frozen contract would need modification, or real data/outcome access is necessary to decide. Commit the three documents locally after independent review; do not push, open PR, merge PR #20 or start the proposed design stage automatically. The next stage requires a separate user instruction and its own Goal.
