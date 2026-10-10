<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# M2 Acceptance — Core Financial Analysis Mainline Integration

## Decision

`PASS — INTEGRATION VERIFIED; ONE_SCOPED_LOCAL_DOCS_COMMIT`

This acceptance covers the cherry-picked feature commit `ceb953b` on
`codex/core-financial-analysis-mainline` and authorizes only the one scoped
local docs commit (goal, work record, this file). It does not authorize push,
PR, merge to main, force-push, database writes, or any next stage.

## Task contract and verified baseline

- Goal/task-contract: `agent/goals/2026-10-10_core_financial_analysis_mainline_integration.md`.
- Work record: `agent/record/2026-10-10_01-core-financial-analysis-mainline-integration.md`.
- Branch `codex/core-financial-analysis-mainline` created from origin/main
  `47dbb6780933f8fb7abab922aa47027a1342de41` (= live `ls-remote` main verified
  this date via the repository's configured proxy).
- Task-start protections (`tmp/core-financial-analysis-mainline/baseline_task_start.json`):
  64 foreign worktrees, 207 protected file hashes (including the primary
  database), stash `cb568efd`, local main unchanged at `966206f`.
- Predicted conflict scope from `git merge-tree` was `research_entry.py`; on
  the cherry-pick path the three feature hunks merged cleanly and the result
  equals mainline + exactly those hunks (verified by diff).

## Gates

- [x] Branch base is exactly `47dbb678`; `git merge-base --is-ancestor` holds.
- [x] `ceb953b` preserves the feature author/message; diff vs base = 8 files,
      +2644 lines; the seven added files are byte-identical to `4155359`.
- [x] `research_entry.py` = mainline content + 3 hunks: docstring line,
      one provenance entry, `financial` ResearchCommand before `facts`.
- [x] Feature and foundation suites: 166 passed in 76.52s; mainline entry
      tests: 32 passed in 2.69s; ruff clean; `git diff --check` clean.
- [x] Real CLI smoke on the committed stage2g snapshot rebuilt as a temp DB:
      schema `m2_core_financial_analysis_report_v1`, 12 records, 7 computed /
      5 missing_input; mainline commands (`plan-batch`) still dispatch.
- [x] Protection review PASS: foreign worktrees, 207 hashes (primary DB SHA256
      unchanged), stash, local main, origin/live main all unchanged.
- [x] No push, PR, merge, force-push, or DSH; primary database never opened by
      this task.

## Not applicable / not run

- Broad business regression beyond the entry contract: not required here
  because the ported diff touches only new feature files plus 12 additive entry
  lines; mainline code paths are unchanged, and the entry contract itself plus
  its two registry/hypothesis test modules were executed.
- Primary-database content checks: not applicable; the database was never
  opened, and its protected hash is unchanged.

## Deviations

- The merge-tree-predicted conflict did not occur on the cherry-pick path (the
  feature hunks' contexts all exist in mainline); no manual resolution was
  needed or performed. Recorded rather than forced.
- Temp smoke artifacts remain under `%TEMP%` because recursive deletion was
  blocked by command policy; nothing in the repository or protected paths is
  affected.
