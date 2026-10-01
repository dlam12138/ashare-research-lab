# M2 PIT fact explorer acceptance

Verdict at commit: local PASS; required hosted delivery gate pending.
Goal: agent/goals/2026-10-01_m2_pit_fact_explorer.md.
Base: main 9db39e8520f733966c0357b4367c696145d4c7e4.
Branch: codex/m2-pit-fact-explorer. Final exact head/merge/check evidence belongs
to the independently verified PR delivery packet, not a guessed future commit.

Changed paths: README.md; src/ashare_research/tools/pit_fact_explorer.py;
tests/test_pit_fact_explorer.py; this acceptance; Goal; record
agent/record/2026-10-01_06_m2-pit-fact-explorer.md. No existing tests modified.
One functional batch: explicit-date latest fact query, two-date version changes,
both dates' source/context/lineage/parent tracing, stable Chinese Markdown/JSON,
fresh directory export and SHA256 manifest. Five fixed existing concepts,
33 canonical retained facts, 601857.SH; public PIT and eligibility gates reused.
Exact source value_decimal restored by selected ID; comparison uses Decimal.
Owned temporary DB is closed before directory cleanup; caller DB untouched.

## Actual local commands and results

Owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance;
PowerShell PYTHONPATH set to its src directory.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m pytest -q tests/test_pit_fact_explorer.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/pit_fact_explorer.py tests/test_pit_fact_explorer.py
python -m ashare_research.tools.pit_fact_explorer --as-of 2024-03-31 --compare-with 2025-03-31 --concept net_profit_attributable_to_parent --period-end 2023-12-31 --output tmp/m2-pit-fact-comparison
git diff --check
```

Same five tests: initial 4 failed/1 passed in 14.29s (scope column adapter),
second 2 failed/3 passed in 22.24s (incorrect fixture change-count expectation),
final 5 passed in 25.55s, no skips. Ruff initially three E501s, final
All checks passed. Diff check passed. Failed cases were fixed, never skipped.
Parent debugging used inline build_report calls to expose KeyError and inspect
actual PIT selections, not separate helper files or broad tests.

Five meaningful cases cover real before/on restatement boundary, exact amounts/
units/date gates and two-date traces; truthful empty/missing scope; sanitized
invalid selectors; original lineage/context plus unresolved parents; genuine
cross-cwd exports byte-identical, manifest hashes, existing file/directory foreign
sentinels unchanged and corrupted pinned source failure before output creation.
No static implementation-mirroring timestamp word-ban retained; stable bytes and
explicit report boundaries checked. Full suite reserved for mandatory hosted CI.

Actual export exit0: 3 files, 2 managed, 19844 managed bytes.
report.md 7891 bytes SHA256
eca96bb3e1f8e525ef0df00b447f0cab3c32e367ce127b4fe19ad7c68819519e;
report.json 11953 bytes SHA256
14b3dbee2dee9d81bca04461014c13a3e8491cf92a3f08b85a27cb44e38b7eb8;
manifest SHA256 20c64abe1f054d5bb18130f9d39d6048fb23a6ea655f7047ffb1783102213af3.
One 2023 profit key: 16114400.000000000000 -> 16141400.000000000000 万元.
Broader two-date view tested: 16 before/21 after, 5 added, 5 value changes,
11 unchanged; 2022 restatement already in first view and not double-counted.

## Protection, deviations and limits

Primary feat/m2-value-assessment-mvp remains
3679b1bac7a1634c6452784a4d8f6d139966f222 with byte-identical captured dirty
status/full binary diff; stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Protected tracked reports/config/events/evidence/mechanism/fixtures SHA256 map
unchanged. D:/量化分析/data/research.duckdb SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Other worktrees/runtime/ignored artifacts preserved; local main deliberately
remains 966206f06262e43f40c1c7aadbfb8596839eac91. No main push/force/reset/clean.

DSH initial run exit1 with unknown cause after writing three allowed files;
one read-only completion audit retry exit0/frozen, no fallback. Parent review
and actual validations establish acceptance, not the worker's incomplete audit.
No unapproved worker helper/test execution observed this batch.

All 66 source parent IDs absent from retained snapshot. Explicit unresolved
references and missing URL/hash/page/table remain; context dates are period-level
metadata and may not match restated fact filing dates. available_at dates are
retained source assertions used by query, not newly verified timing evidence.
Snapshot is a canonical export/read model, not a new source of truth. No new
metrics, scoring, ranking, acquisition, real backtest, holdout, Brent resolution
or research-stage conclusion. Manifest aids byte checks; raw disclosure documents
not attached. Late disk failure can leave an owned partial directory, retained
without deleting caller artifacts.

Task branch commit/push/PR only after independent scope/protection review;
standing AGENTS merge authorization applies only after exact head/base,
successful mandatory checks and clean mergeability. Final handoff must verify
local/origin task sync and actual remote main merge identity. Continuing scoped
engineering is authorized; a new research/data/holdout stage is not.
