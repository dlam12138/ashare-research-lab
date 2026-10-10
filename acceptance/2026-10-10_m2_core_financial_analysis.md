<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# M2 Acceptance — Arbitrary-Symbol Multi-Year Core Financial Analysis

## Decision

`PASS — ONE_SCOPED_LOCAL_COMMIT_AUTHORIZED`

Acceptance authorizes only one scoped local commit of this task's files. It does not
authorize push, PR, merge, database writes, new data acquisition, scoring/ranking, or the
next stage.

## Task contract and verified baseline

- Goal/task-contract: `agent/goals/2026-10-09_core_financial_analysis.md`.
- Work record: `agent/record/2026-10-09_05-core-financial-analysis.md`.
- Owned worktree `D:\量化分析-worktrees\量化分析-core-financial-analysis`, branch
  `codex/core-financial-analysis`, verified base
  `ce7650267d4867d52b59e7c70e3d6bf4adb571e7` (= tip of `codex/m4-preparation-byte-diff`).
- Task-start protections (`tmp/core-financial-analysis/baseline_task_start.json`, captured
  and re-verified 2026-10-10): origin/live `main` =
  `47dbb6780933f8fb7abab922aa47027a1342de41`; local `main` unchanged at `966206f`;
  primary worktree dirty files and stash `cb568efd` preserved; 207 protected file hashes
  unchanged; primary database `data/research.duckdb` (SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`) never opened.
- Deviation: the earlier snapshot `baseline.json` predated a user-authorized PR-merge task
  (2026-10-08/10-09); protections were re-captured at task start and the verifier now reads
  `baseline_task_start.json` (comment documents why; old snapshot retained untouched).

## Gates

- [x] Core `build_report` accepts explicit database, symbol, as-of, bounded year window,
      optional compare-with and scope; every selector is validated before any database
      path is touched; missing database is `DATABASE_NOT_FOUND`, never created.
- [x] Facts are selected only through the public PIT gate `AsOfQuery.get_latest_available`
      (`available_at <= date`, verified/reconciled, eligible, latest version); future
      versions are never selected.
- [x] Only year-end annual flows (`period_end = YYYY-12-31`, `period_type = annual`) and
      year-end instant balances (`period_type = instant`) are bound; mismatched period
      contexts are visible `missing`/`excluded` states, never substituted.
- [x] All 12 metrics come from existing registries (4+2+4+2); no new formula, unit,
      scoring, ranking, qualification or advisory output exists; registry drift raises
      `METRIC_REGISTRY_INCOMPLETE`.
- [x] Precision boundary is explicit: only finite exact integers within 2^53−1, unit
      `万元`, `source_tier = reconciled_derived` are used; other inputs are excluded per
      fact with stable reason codes and are never rounded or coerced.
- [x] Role-level missingness, selected inputs, source references, lineage, parent
      resolution states and input availability bounds are reported; `available_at` is not
      presented as metric publication time (`created_at` is a fixed marker).
- [x] Same-year revisions (two PIT dates) are reported separately from adjacent-year
      descriptive deltas; exact Decimal equality drives
      `status_changed`/`value_changed`/`inputs_changed`/`unchanged`.
- [x] Read-only connection, one transaction for both PIT views, no schema
      initialization/migration, no default database path; database file hash and table
      set unchanged after analysis.
- [x] CLI `python -m ashare_research.tools.financial_analysis` (registered as
      `research financial`) succeeds with Markdown/JSON, exports a new directory with
      `report.md`, `report.json`, `manifest.json` (SHA256-bound), rejects an existing
      output path with `OUTPUT_PATH_EXISTS`, and sanitizes failures to exit code 2 with
      empty stdout.
- [x] Committed stage2g PetroChina fixture computes the existing seven metrics and
      honestly reports the five absent expanded inputs (`missing_input`); 12-metric ×
      3-year outputs match the public `MetricEngine` fed by an independent PIT selection
      over the same committed facts (0 differences).
- [x] No primary database, stash, foreign worktree, local/origin/live `main`, or frozen
      M2/M3/M4 disposition was touched.

## Exact validation commands and results

Run from the owned worktree with `$env:PYTHONPATH='src'` and
`D:/量化分析-m4a2i/.venv/Scripts/python.exe` (Python 3.13.9, DuckDB 1.5.5):

1. `pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py
   tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py
   tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py
   tests/test_research_entry.py`
   → `166 passed in 70.19s` (new suite: 30 tests, including a real CLI subprocess run).
2. `ruff check src/ashare_research/financial_analysis.py
   src/ashare_research/tools/financial_analysis.py
   src/ashare_research/tools/research_entry.py tests/test_financial_analysis.py`
   → `All checks passed!`
3. `git diff --check` → exit code 0.
4. `python tmp/core-financial-analysis/verify_protections.py`
   → `PASS: 64 foreign worktrees, 207 protected hashes, stash and main`
   (writes `tmp/core-financial-analysis/protection-review.json`; `tmp/` is gitignored).

Cross-check evidence (this session, before commit): temporary DB rebuilt from
`tests/fixtures/stage2g/canonical_fact_snapshot_v1` compared per metric/year against the
pre-existing replay and the independent public-engine expectation: statuses, values and
input fact ids identical.

## Implementation summary

- `src/ashare_research/financial_analysis.py` (new): read-only core with selector
  validation, PIT collection, role binding, precision classification, metric execution
  through `MetricEngine.compute`, missing/excluded reporting, lineage/parent resolution,
  adjacent-year deltas, two-date comparison, deterministic renderers, manifest and
  exclusive export.
- `src/ashare_research/tools/financial_analysis.py` (new): sanitized argparse CLI.
- `src/ashare_research/tools/research_entry.py` (modified): registers `research financial`.
- `tests/test_financial_analysis.py` (new): 30 acceptance tests.
- `docs/core_financial_analysis_guide_v1.md` (new): user guide.
- `agent/goals/2026-10-09_core_financial_analysis.md`,
  `agent/record/2026-10-09_05-core-financial-analysis.md`: contract and work record.
- `acceptance/2026-10-10_m2_core_financial_analysis.md`: this acceptance.

## Limitations and unresolved risks

- The caller-supplied database is taken as the fact input; the tool does not prove its
  provenance, availability or independence, and does not re-verify `available_at`.
- Parent evidence resolves only within facts retained in the selected database
  (`resolved_available_at_as_of` / `retained_not_available_at_as_of` /
  `absent_from_selected_database`).
- `context_missing` is mostly unreachable because the public PIT query inner-joins
  `fact_contexts`; the exclusion code is retained for completeness.
- Reports certify content consistency only; they are not a production, scoring,
  execution or research authorization.

## Explicit non-acceptance

No push, PR, merge, database write, default-database read, new data acquisition,
formula/definition change, scoring, ranking, target price, recommendation, holdout or
frozen-disposition change is authorized by this acceptance.

## Stop

`STOP_FOR_SCOPED_LOCAL_COMMIT`
