<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial analysis: finite JSON evidence

## Objective and verified baseline

Advance the north-star value-assessment path by verifying and correcting the
pending arbitrary-symbol PIT financial report's handling of non-finite facts.
Current main is locally and remotely 47dbb6780933f8fb7abab922aa47027a1342de41.
The delivered financial feature is on codex/core-financial-analysis-mainline
at 4446fb84c9b496d0654780c4ff4f0447f2ee07e7, two commits above main, clean.
Work in isolated codex/financial-json-review at that exact delivered revision.
Root remains feat/m2-value-assessment-mvp at 3679b1b with protected user edits.
Snapshot: C:/Users/111/AppData/Local/Temp/codex-financial-json-20261010-before.json.

## Allowed scope

Financial report value projection and JSON serialization, regression tests,
the existing financial guide, this Goal and one work record.
Reuse all PIT selectors, metric definitions, missingness and precision gates.
Required behavior: non-finite facts remain excluded with their existing reason,
never produce numeric NaN/Infinity in reports, and never become zero or valid
metric inputs. Finite values and existing results retain their meanings.

## Forbidden scope

No formulas, fact schema, dependencies, source acquisition, primary database
connection, scoring, ranking, recommendations, M3/M4 dispositions, provider
access, holdout, DSH, unrelated files or other worktree edits.
No push, merge, PR, automatic next stage or modification of previous acceptance.

## Required tests and exact validation commands

Run in the isolated worktree with PYTHONPATH=src and the existing interpreter:

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py -k non_finite
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/financial_analysis.py tests/test_financial_analysis.py
git diff --check
git diff --stat
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git ls-remote origin refs/heads/main refs/heads/feat/m2-value-assessment-mvp
```

The new tests must fail before the fix, using real temporary DuckDB facts.
Exercise NaN and both infinities, strict JSON decoding, exclusion state,
unaffected finite facts, export byte hashes and database hash preservation.
The focused regression set covers report/CLI, reused calculations, PIT/TTM and
entry integration; no full suite is required for this bounded projection fix.
Inspect final diff and headers; separately check untracked Markdown whitespace.
Compare root dirty/untracked hashes, primary database, north star, stash and all
pre-existing worktree HEAD/status to the snapshot. Only the new worktree may
change. No historical test evidence is reused as a fresh run.

## Acceptance criteria and stop conditions

All selected tests and lint pass; strict JSON preserves excluded facts and
finite results; protection comparisons pass; actual results are recorded.
Stop for foreign concurrent changes, protected hash differences, required-check
failure or any need to weaken metric/PIT rules. A failed pre-fix regression is
expected evidence and must remain documented.

## Commit and push requirements

Leave the scoped correction and evidence uncommitted for review. No push,
merge or next-stage authorization is inferred from the general continuation.
