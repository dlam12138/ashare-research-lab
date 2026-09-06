# PIT/TTM correctness and project entry

## Start
User authorized implementation, isolated main-based worktree, commits, push and PR;
no merge. Goal: `agent/goals/2026-09-06_pit_ttm_correctness_and_project_entry.md`.
Verified actual remote main at a0a7c13, original dirty M2 worktree and protected stash/DB.
Fetched origin and created the approved branch in D:/量化分析-pit-ttm.
Read agent agreement, record index, three latest Stage4P/4A1/4A1R records, date queries,
TTM implementation and existing tests. No nested AGENTS.md exists in the new tree.

## Decisions and sequence
Use a shared strict date validator outside repository/as_of to avoid circular imports.
Keep None as the existing repository audit default; reject other invalid explicit values.
Use synthetic dictionaries and in-memory DuckDB for regression tests. Install the declared
dependencies into this worktree's own venv; do not reuse another checkout's editable install.
First reproduce with failing tests; implement; then verify frozen gates and full tests.
README will own the current capability summary; history retains old stage detail.

## Validation and results
Implementation in progress. Actual commands and results will be appended as executed.

### Boundary regressions and repair
- Installed `.[dev]` in the isolated venv (Python 3.13); no dependency declarations changed.
- First new-test run found a test-fixture NOT NULL error (incomplete context insert).
  Corrected the fixture before collecting the baseline failure evidence.
- `.venv/Scripts/python.exe -m pytest -q tests/test_pit_date_boundaries.py tests/test_ttm_business_boundaries.py --tb=no`
  on unmodified product code: **62 failed, 46 passed**. This is the valid red baseline.
- Added shared strict cutoff validation to AsOfQuery and both repository query paths;
  kept None as the optional audit default. Empty string no longer silently removes PIT.
- TTM now resolves same-time candidates by visible ancestry, rejects cycles/conflicting
  identities/ambiguous chains, uses minimum period start and emits one annual state per time.
  All interim transitions use visible inputs, even when another dependency remains missing.
- Same boundary command after implementation: **108 passed**.
- Planned existing integration/financial-state/temporal-join/Stage4P command: **60 passed**.
- Compared baseline TTM module loaded from `git show a0a7c13:.../ttm.py` with new module
  on existing synthetic fixture bundles: PE and PS each have 25 states, all 25 unchanged
  including full payload, IDs and lineage (22 computed per metric).

### Entry documentation
- Moved repeated M2/M3 stage narrative into docs/project-history.md with source links.
  README now leads with current capabilities, supported inputs and explicit limitations;
  M4-A.2 design remains linked to its separate branch. Record index links back to README.
- Added capability and relative-evidence-link checks. First run found a nonexistent
  data/README.md link; replaced it with the actual data-service test evidence.
- Entry tests: **2 passed**; existing M2/M3/M4 status tests: **43 passed**.
- Ruff over src/tests and compileall passed. Full suite is running.
- An oversized shell documentation-edit command was rejected by execution policy;
  no files changed from that command. Applied the documentation through apply_patch.

### Full-suite findings and scoped amendment
- First full suite: **7 failed, 2412 passed, 4 skipped, 2 warnings**, 379.43 s.
  Six failures pin the old as_of.py source in historical tests; one was a malformed
  negative-earnings test fixture. No research-artifact or output baseline failed.
- Negative fixture previously kept two unrelated same-day versions and used a Q1
  lacking prior inputs. Replaced an actual annual input and strengthened assertions:
  require observations, nonpositive_earnings status and null ratio. All 8 series tests pass.
- Presented the conflict with the no-hash-update plan; user answered "继续".
  Applied the scoped PIT_DATE_GATE_V2 exception in the Goal: six as_of.py entries
  advance to its new exact blob, with old blob and rationale preserved. Equality
  assertions and all other expected hashes remain untouched. Full suite rerun required.
