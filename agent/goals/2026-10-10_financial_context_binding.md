<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial fact/context binding

## Objective and verified baseline

Advance explainable company financial analysis by enforcing the already
required year-end annual-flow and instant-balance context before metric binding.
User asked to continue and inspect other agents' recent work.
Work in codex/financial-json-review at
4446fb84c9b496d0654780c4ff4f0447f2ee07e7, based on the delivered core financial
feature. Its preceding finite-JSON correction remains uncommitted and must
be preserved. origin/main and live main are 47dbb6780933f8fb7abab922aa47027a1342de41.
Root remains feat/m2-value-assessment-mvp at 3679b1b with existing user changes.

## Allowed scope and required behavior

Modify financial_analysis.py, its tests and existing guide; add this Goal and
one record. Check context symbol, fiscal year, year-end identity, scope,
instant/duration semantics and full annual duration before any metric binding.
Annual flows require January 1 through December 31 of the requested year.
Instant balances allow absent period_start or period_start equal to period_end.
Malformed selected contexts remain excluded under period_context_mismatch.
Do not fall back to older fact versions when the latest PIT-selected input is
incompatible. Keep finite-JSON behavior and all previous tests intact.

## Forbidden scope

No formulas, shared fact repository/schema, dependencies, source fetches,
primary DB connections, statistics, scores, ranking, investment advice,
DSH, M3/M4/holdout dispositions, other agent worktree edits, old task-record
edits, pushing or merging. This is not K2 admission or milestone acceptance.

## Required tests and exact validation commands

Owned worktree, PYTHONPATH=src, Python 3.13.9/DuckDB 1.5.5:

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py -k context_binding --tb=short
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/financial_analysis.py tests/test_financial_analysis.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git ls-remote origin refs/heads/main refs/heads/feat/m2-value-assessment-mvp
```

Reproduce malformed annual and instant contexts in temporary DuckDB databases
before implementation. Verify missing metrics, excluded roles, no older-version
fallback, valid instant conventions, and DB hash preservation.
The selected regressions cover affected report/CLI and calculation/PIT/TTM
integration. Full unrelated business tests are not required.
Final diff/header/document checks and protection comparisons are required.
Do not claim historical agent test counts as this task's execution.

## Acceptance, stop conditions and delivery

Required tests/lint pass; committed fixtures and valid contexts retain values;
wrong contexts cannot produce a computed metric; no silent repair or fallback.
Review actual branch/diff/status, prior correction preservation and other-agent
evidence boundaries. Protection snapshot:
C:/Users/111/AppData/Local/Temp/codex-financial-context-20261010-before.json.
All foreign worktree HEAD/status, foreign dirty/untracked file hashes, prior
task documents, frozen owned reports/config/evidence, root north stars, primary
DB hash and stash must match. Three explicitly allowed files may change.
Stop for unexpected concurrent changes, protected mismatches or expanded scope.
Record any reproduction/checker/lint failures honestly.
Leave uncommitted; no push, merge, PR or automatic subsequent stage.
