# M2 existing metric PIT replay

Objective: deliver a complete dated annual metric read model using existing
approved definitions/engine and existing pinned canonical facts: seven metrics,
annual selection, before/after comparison, input-role trace and portable export.
This is scoped M2 engineering replay, not new methodology or research-stage work.

Verified base: live remote/origin main 682c8c127b6a500b4f69318af4d305b90a7867df;
owned clean worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance;
branch codex/m2-pit-metric-replay. Primary feat/m2-value-assessment-mvp stays at
3679b1bac7a1634c6452784a4d8f6d139966f222 with pre-existing dirty changes; stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; protected research.duckdb SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
local main 966206f06262e43f40c1c7aadbfb8596839eac91 stays untouched.

Allowed files: new src/ashare_research/tools/pit_metric_replay.py;
tests/test_pit_metric_replay.py; README.md; this Goal;
agent/record/2026-10-01_07_m2-pit-metric-replay.md;
acceptance/2026-10-01_m2_pit_metric_replay.md. One bounded DSH implementation
writes the first three only; parent owns records/Git/independent validation.
Forbidden: existing engines/definitions/fact explorer/tests, snapshots/reports/
configs/events/evidence/DB/runtime modifications; acquisition/network/messages;
new formulas, scores/ranks/recommendations, valuation/TTM/ROIC/holdout/backtests/
registries/Brent evidence changes; recursive delegation or model fallback;
overwriting existing output paths; arbitrary source or database selection.

Required: reuse public pit_fact_explorer.build_report with validated selectors
to obtain both dates' gated exact-decimal facts and source traces; use existing
MetricDefinitionRegistry (4), CashFlowMetricDefinitionRegistry (2), and existing
ROE definition in CapitalReturnMetricDefinitionRegistry (1). Never copy formulas
into new arithmetic. Bind roles by concept, fiscal year, December period-end and
annual flow/instant equity context. Restore value as Decimal from value_decimal
and retain original eligibility/source-tier fields for MetricEngine validation.
Explicit --as-of required, --compare-with >= as-of optional, repeatable --year
2021..2025 and --metric accepted seven only; --scope consolidated/parent_company.
Markdown default, --json or --output NEW_DIR. Default years/metrics all retained
five/seven, deterministic sorted results, no implicit today or runtime timestamp.
MetricEngine.compute in memory only, no MetricRepository/schema writes. Pass an
explicit non-clock replay metadata marker for created_at; do not publish it as a
historical timestamp. revision_review_status explicitly offline replay/unreviewed;
result_version 1 denotes this read model, not stored historical metric version.
Missing values retain engine status plus complete wrapper missing-role/year
diagnostics; 2021 growth prior missing is insufficient_history. Never claim a
missing result was published at engine's as_of fallback availability; expose max
known input availability as a bound only, null for no inputs. Canonical metric ID
is engine identity, not new version admission; all input roles/IDs/dates/values
trace to selected facts, future facts excluded separately at each query date.
Two-date comparison distinguishes status/value/input revision/unchanged, keeps
null values missing and explicit before/after lineage. Preserve snapshot/source
limitations (33 facts, 66 absent parents, retained availability dates not reproved,
period context dates may differ from restated facts). FCF is a cash proxy; ROE is
existing annual average-equity convention; these are not cash valuation/TTM/ROIC.
Portable report.md/report.json/manifest.json: finish validation/rendering before
exclusive new root mkdir, reject existing file/dir/symlink without mutation.
Late IO may retain owned partial output; sanitized exit2, no partial stdout.

Minimal required local checks (owned worktree; PYTHONPATH=src):
python -m pytest -q tests/test_pit_metric_replay.py
D:/量化分析/.venv/Scripts/python.exe -m ruff check src/ashare_research/tools/pit_metric_replay.py tests/test_pit_metric_replay.py
python -m ashare_research.tools.pit_metric_replay --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-pit-metric-replay
git diff --check
Four meaningful cases only: real existing-engine outputs/roles/precision at both
dates and restatement effects; missing history/empty scope and no future inputs;
selectors sanitized; actual deterministic portable export/hash/foreign path safety
and pinned-source failure before output. No broad local regression duplication;
full mandatory hosted suite and contract/identity gates remain required.

Acceptance: usable actual replay artifact, independent actual diff/scope review,
four checks pass, unchanged protected hashes/primary dirty snapshot/stash/DB/local
main, clean worktree and exact task branch push sync. Task branch commit/push/PR
only; independently verify exact base/head, required hosted checks and clean
mergeability, then merge under standing AGENTS authorization. Never push main.
Stop on unclear source/methodology expansion, DSH unavailability/failure or two
unsuccessful repairs (report to parent, no silent fallback), failed CI/conflicts/
protection changes. Final verdict PASS/CHANGES_REQUIRED/BLOCKED with Goal/ref/
files/commands/results/acceptance/protection/sync/deviations/risks packet. Scope
allows further already authorized engineering, not a new research/data stage.
