# M2 existing metric PIT replay acceptance

Verdict at commit: local PASS; required hosted delivery gate pending.
Goal: agent/goals/2026-10-01_m2_pit_metric_replay.md.
Base main: 682c8c127b6a500b4f69318af4d305b90a7867df.
Branch: codex/m2-pit-metric-replay. Actual final head/merge/hosted checks must be
independently verified in delivery, not guessed in this pre-delivery evidence.

Six paths changed: src/ashare_research/tools/pit_metric_replay.py;
tests/test_pit_metric_replay.py; README.md; this acceptance; Goal;
agent/record/2026-10-01_07_m2-pit-metric-replay.md.
No existing code/tests, definitions, fixtures or research reports changed.
One complete batch: seven existing annual metrics over two explicit PIT dates,
year/metric/scope selectors, status/value/input-version comparison, role-bound
facts/source/lineage/gaps, Chinese Markdown/exact JSON and fresh directory export.
Public fact read model gates each date separately; public MetricEngine computes
in memory from exact retained Decimals. Prior/opening FY-1, other roles FY;
annual flows/instant equity; max known input dates are bounds, not publication.
Result version1 is an unreviewed read-model convention, not historical admission.

## Actual local commands and results

Owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m pytest -q tests/test_pit_metric_replay.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/pit_metric_replay.py tests/test_pit_metric_replay.py
python -m ashare_research.tools.pit_metric_replay --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-pit-metric-replay
git diff --check
```

Initial same four-case run: 2 passed/2 failed in10.16s (Windows CRLF stderr).
Fixed output to explicit UTF8 bytes without changing assertions; final
4 passed in12.40s, no skips. Scoped Ruff All checks passed; diff check passed.
Parent's earlier scoped ruff check --fix and ruff format touched only the new
module; six SIM905 literals/long lines fixed, no lint exemptions or test bypass.
No full local suite duplicated; mandatory hosted regressions remain required.

Four meaningful cases: actual CLI seven FY2023 metrics match the public engine
fed independently gated committed fixture facts, exact FCF and ROE opening/
closing role/version/source assertions; missing history/empty scope/no future
inputs, real partial-role and null comparisons; selectors rejected before fact
read with sanitized errors; actual cross-cwd byte-identical exports/manifest
hashes, existing directory/file foreign sentinels unchanged, damaged pinned
snapshot rejected before output root creation. No custom temp fixtures or ACL
workaround. Existing engine arithmetic/formulas not copied into new code/tests.

Actual export exit0: report.md 21070 bytes SHA256
d639a892a56794432c8f880acdd3cfb80af77b95f953a6dae5662fbd9bd3d4e6;
report.json 200421 bytes SHA256
9fe7b9918e7e0941765c7f44c6b1ffcaa102ab4289f60d9529659ecf3e0c8dd0;
manifest SHA256 6a0f3497259e584f5d8155e0c7dccb84538fbdfa0d4761e705d4203c51de3fd2.
Three files, two managed, 221491 managed bytes. Actual 2023 replay has seven
computed values at each date and seven value changes. Cash FCF proxy
17407700.000000000000 ->17433900.000000000000 万元;
annual average-parent-equity ROE 0.114600416175 ->0.114591833946.
No implication that these replay artifacts were historically published.
FY2024/FY2025 comparison case: 7 status changes, 4 input-only changes,
3 unchanged missing values; missing stays null, never zero.

## Protection, deviations and remaining limits

Primary feat/m2-value-assessment-mvp remains
3679b1bac7a1634c6452784a4d8f6d139966f222 with identical captured porcelain/
full binary diff; stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f unchanged.
Protected tracked reports/config/events/evidence/mechanism/fixture SHA256 map
unchanged. Research DB SHA256 unchanged:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Other worktrees/runtime/ignored artifacts preserved; local main intentionally
stays966206f06262e43f40c1c7aadbfb8596839eac91. No main push/force/reset/clean.

Parent interrupted first uniquely identified owned DSH process tree after
repeated inefficient soft-size trimming; same-executor bounded completion retry
(tests/README only, module read-only) exited0/frozen. No fallback model or worker
tests/CLI/assertion helpers observed. Worker exceeded read/size-efficiency
guidance; actual final scope independently verified. Parent reviewed actual
files and validated rather than accepting worker claims.

Only existing five concepts/33 facts/601857.SH supported; 66 source parents
absent, original disclosures unavailable in this read model. Retained available_at
is not newly proved timing; period contexts can differ from restated fact dates.
Replay is unreviewed/nonproduction/non-scoring, no stored metric-version admission.
Cash FCF remains a proxy, ROE existing annual convention; no TTM/ROIC/valuation/
new methodology, acquisition, real backtest, holdout, Brent evidence resolution
or new research-stage conclusion. Late IO may retain owned partial output; no
destructive cleanup. Manifest aids file-byte checks, raw disclosures not attached.

Task branch commit/push/PR after independent scope review. Standing merge
authorization applies only after exact base/head, all mandatory hosted checks
and clean mergeability; final delivery verifies actual merge tree/parents, live
remote main, task local/origin sync, worktree/stash/protection. Continuing scoped
engineering allowed; a new research/data/holdout stage is not authorized.
