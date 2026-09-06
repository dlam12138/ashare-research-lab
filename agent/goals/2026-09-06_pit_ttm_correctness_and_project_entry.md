# PIT/TTM correctness and project entry

## Objective and verified baseline
Implement the user-approved plan: strict PIT cutoffs, deterministic TTM supersession,
missing-input transitions, and one current-capability entry on main.

- Base: origin/main `a0a7c13ee47057abf5e40a96a616baf78451774e`, fetched and live-remote verified.
- Worktree: `D:/量化分析-pit-ttm`; branch `codex/pit-ttm-correctness-and-project-entry`.
- Original worktree remains at `3679b1b`, including its existing tracked/untracked changes.
- Protected stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Original default DB SHA256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- New worktree has no default DB. Frozen report/acceptance and M3 source aggregates
  must pass the unchanged Stage4P governance gate.

## Allowed and forbidden scope
Allowed: facts query-date validation, PIT valuation TTM logic, focused regression tests,
README/history/index documentation, this Goal, one work record and dated acceptance.
Forbidden: default DB or existing worktree mutations, frozen research artifacts,
M3/M4 implementation changes, M4-A.2 design integration, real research, branch cleanup,
test weakening, baseline hash updates, direct main push, force push, merge.

## Required behavior
- YYYY-MM-DD only; PointInTimeError on other explicit cutoffs; omitted repository
  cutoff remains the existing audit path. Inclusive PIT boundary remains unchanged.
- Latest effective TTM candidates use unique supersession, never ID/list order;
  conflicts/cycles/ambiguity raise ValueError with candidate IDs. Annual and interim
  selections agree; period starts are minimum effective dates.
- Unavailable inputs produce missing_ttm_input with visible lineage only, transitioning
  when dependencies become visible without backfill or crossing the period window.
- README shows current main capabilities, supported entrypoints, evidence and limits;
  history links retain historical decisions and authorization boundaries.

## Tests and acceptance
First run added business tests against baseline and record failures. Then run:
```
python -m pytest -q tests/test_pit_date_boundaries.py tests/test_ttm_business_boundaries.py
python -m pytest -q tests/test_m2_integration.py tests/test_m2_stage2k1r4e_financial_state.py tests/test_m2_stage2k1r4e_temporal_join.py tests/test_m4_stage4p_governance.py
python -m pytest -q
python -m ruff check src/ tests/
python -m compileall -q src tests
git diff --check
```
Use this worktree's isolated .venv interpreter. Existing Windows/Linux CI remains
unchanged. Inspect actual diff, artifact protection, DB/stash, remote synchronization
and PR checks; report PASS/CHANGES_REQUIRED/BLOCKED based on actual evidence.

## Commit, push and stop
Commit scoped date fix, TTM fix, documentation and acceptance evidence; normal push
to the new branch and create one PR targeting main. Stop before merge or next stage.
