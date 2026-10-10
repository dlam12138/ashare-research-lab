<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Core financial analysis: mainline integration

## Objective and verified baseline

Port the verified read-only `research financial` feature (commit 4155359,
"feat(m2): analyze any eligible symbol with the existing metric definitions")
onto the current mainline as a minimal, reviewable branch, resolving the single
expected conflict in `src/ashare_research/tools/research_entry.py`, without
touching any formula, test or governance boundary. Root works directly; no DSH
and no delegation.

Verified before any edit (2026-10-10, this session):

- Owned worktree `D:\量化分析-worktrees\量化分析-core-financial-analysis` clean on
  `codex/core-financial-analysis` @ 4155359518aba84d64524fef17c1a3e3138f0c37;
  feature chain `9f7bebc → 3b925c6 → f8d89cb → ce76502 → 4155359`, none of it
  on origin/main; 4155359 adds 7 new files plus a 12-line edit to
  `research_entry.py`.
- origin/main local ref = live `ls-remote` =
  47dbb6780933f8fb7abab922aa47027a1342de41; merge-base(4155359, origin/main) =
  0818edff8a2aae454c41145f5ef55184cf0d3a46.
- `git merge-tree --write-tree origin/main 4155359` conflicts only in
  `src/ashare_research/tools/research_entry.py`; README.md and
  `research_plan_compare.py` auto-merge. The seven added files do not exist on
  origin/main.
- Foundation modules (`metrics`, `facts`, `storage`, `reproducibility`,
  `exceptions.py`, `tests/fact_test_helpers.py`, `tests/test_research_entry.py`)
  unchanged between feature base ce76502 and origin/main. Mainline advances are
  registry / hypothesis / plan / preparation tooling and the expanded entry
  command set; mainline's `ResearchCommand` still has the same four fields.
- Protection baseline `tmp/core-financial-analysis-mainline/baseline_task_start.json`:
  64 foreign worktrees, 207 protected file hashes, stash
  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, local main unchanged at 966206f;
  verifier `tmp/core-financial-analysis-mainline/verify_protections.py` dry-run
  PASS (owns-only change; live checked via the repository's configured proxy).
- Primary database `D:/量化分析/data/research.duckdb` never opened.

## Allowed scope

- Create branch `codex/core-financial-analysis-mainline` from origin/main.
- Apply 4155359 with `git cherry-pick` (author and message preserved); resolve
  the expected `research_entry.py` conflict by keeping mainline's content and
  re-adding exactly the financial additions: one docstring line after
  `metrics`, one provenance entry after the module docstring, and the
  `ResearchCommand` block inserted before the `facts` command.
- Add this task's goal, work record and acceptance files; one scoped local docs
  commit.

## Forbidden scope

No push, PR, merge to main, force-push or branch deletion. No change to
metrics, facts, storage, reproducibility, formulas, schemas, existing tests,
README, other entry commands, or M2/M3/M4 dispositions. Do not open or write
the primary database; do not touch foreign worktrees, stash or local main; do
not weaken, skip or rewrite any test; no new dependencies; no data
acquisition; no scoring, ranking or advice; no DSH.

## Required behavior

- New branch starts exactly at 47dbb678 and contains the cherry-picked feature
  commit (message and author preserved) plus one docs commit.
- The seven files added by 4155359 are byte-identical to 4155359's content on
  the new branch.
- Resolved `research_entry.py` equals mainline's version plus exactly the
  three financial additions, verified by direct diff against origin/main.
- All mainline entry commands keep working; `research financial` dispatches the
  ported CLI; the ported never-implicit rules (read-only, explicit database,
  missing stays missing) are unchanged.

## Required tests and exact commands

From the owned worktree with `D:/量化分析-m4a2i/.venv/Scripts/python.exe` and
`$env:PYTHONPATH='src'`:

1. Feature and foundation behavior (same selection as the feature task; rerun
   required because `research_entry.py` and the branch base change):

   ```powershell
   & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py
   ```

2. Mainline entry contract on the new base (the entry now carries mainline's
   command set):

   ```powershell
   & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_research_hypothesis_batch.py tests/test_m4b_hypothesis_registry.py
   ```

3. `& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/research_entry.py src/ashare_research/financial_analysis.py src/ashare_research/tools/financial_analysis.py tests/test_financial_analysis.py`
4. `git diff --check`
5. `& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' tmp/core-financial-analysis-mainline/verify_protections.py`
   (64 foreign worktrees, 207 protected hashes, stash, local main, origin/live
   main; live check uses the repository's configured proxy with bounded
   timeouts).
6. Real CLI smoke on a temporary DB rebuilt from the committed stage2g
   snapshot (`tests/fixtures/stage2g/canonical_fact_snapshot_v1` via
   `ashare_research.reproducibility.capsule.build_temp_fact_db`):
   `python -m ashare_research.cli research financial --database <db> --symbol 601857.SH --as-of 2024-03-31 --year 2023 --json`
   returns the report schema; `python -m ashare_research.cli research --help`
   lists mainline commands plus `financial`; one mainline command's help (e.g.
   `research plan-batch --help`) still works.
7. Integration identity checks: `git merge-base --is-ancestor 47dbb678 HEAD`;
   `git diff --stat 47dbb678 <tip>` shows exactly the feature files plus this
   task's docs; `git diff 4155359 <tip> -- <seven added files>` is empty.

## Acceptance criteria

- Branch off 47dbb678; cherry-pick commit message/author preserved; exactly one
  additional docs commit; clean worktree afterwards.
- All checks in "Required tests" pass with output recorded; protections PASS
  with no drift; primary database untouched; no push/PR/merge performed.
- Feature files identical to 4155359; entry file = mainline + financial
  additions; report lists deviations, reused evidence and anything not run.

## Stop conditions

Stop and report without workaround if: foreign worktree, stash or main drift
appears; live main ≠ 47dbb678; cherry-pick conflicts extend beyond
`research_entry.py`; any test fails in a way that would require changing
feature code, mainline code or tests beyond the allowed scope; any command
would touch the primary database or foreign worktrees.

## Commit and push requirements

Exactly two local commits on `codex/core-financial-analysis-mainline`:
(1) the cherry-picked feature commit 4155359 (author/message preserved);
(2) one scoped docs commit containing this goal, the work record and the
acceptance file. No push, no PR, no merge, no DSH. Merging to main and starting
any next stage require explicit user authorization.
