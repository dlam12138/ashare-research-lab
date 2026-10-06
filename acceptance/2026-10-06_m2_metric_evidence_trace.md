# Metric evidence trace — local acceptance

Goal agent/goals/2026-10-06_m2_metric_evidence_trace.md; base origin/live main
4bfea9d684c5d8be0e61a28b79d9fa59328ac886; branch codex/m2-metric-evidence-trace.
Root executes without DSH/subagents. Seven files: Goal, this checkpoint, dated
record, README, metric_evidence_trace.py, research_entry.py and new test file.

research trace explicitly selects metric/year from a fully verified session or
workflow directory/ZIP. It retains original rows in requested views and original
comparison entry, request, boundary/limitations/full verification/archive receipt.
Markdown displays original values, input roles/values/fact IDs, source references,
missing source fields and full parent IDs/statuses. JSON preserves all original
context/lineage/input fields. No arithmetic, reclassification, imputation, new
data, caller restoration, arbitrary paths or retained-file reread/cache.

Exact validation in owned worktree, PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_metric_evidence_trace.py
python -m pytest -q tests/test_metric_evidence_trace.py::test_exact_metric_rows_input_evidence_missing_values_and_public_formats
python -m ruff check src/ashare_research/tools/metric_evidence_trace.py src/ashare_research/tools/research_entry.py tests/test_metric_evidence_trace.py
git diff --check
git diff --exit-code 4bfea9d -- reports config events evidence tests/fixtures .github src/ashare_research/mechanism
```
Initial2case run:1failed/1passed109.82s. Failure revealed actual missing_roles
are structured role/concept/year records; new Markdown renderer incorrectly
joined them as strings. Fixed product display to show all three fields, without
changing tests or original records. Only affected case rerun:1passed60.69s.
Two E501 lines wrapped before first tests; final scoped Ruff PASS. No test
weakening/new skips/full local suite/repeated whole target suite.

Actual fixed workflow/session/ZIP cases compare entire original records and
comparison entries, all nested input/source/context/lineage fields, selected
dates and metadata. ZIP/directory/CLI outputs agree. Both computed and missing
records covered; missing remainsnull, one-view archive has no comparison.
Source files unchanged. Invalid metric/year/kind/argument/output-path requests
fail2 with no partial stdout or output path. Forged outer index with valid ZIP
CRC rejected even when selected metrics intact. Canonical byte handoff consumes
verified map once after source mutation; later fresh verification rejects it.

Actual retained ZIP demo (each format once, exit0):
```powershell
python -m ashare_research.cli research trace --archive tmp/m2-handoff-walkthrough/delivery.zip --metric cash_based_free_cash_flow_proxy --year 2023
python -m ashare_research.cli research trace --archive tmp/m2-handoff-walkthrough/delivery.zip --metric cash_based_free_cash_flow_proxy --year 2023 --json
```
Saved tmp/m2-metric-evidence-trace-demo/trace.md and trace.json. Two original
views2024-03-31/2025-03-31, values17407700.000000000000 and17433900.000000000000,
unit retained; original comparisonvalue_changed. All source/parent gaps retained.
Original ZIP SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Original primary snapshot/427protected hashes compared at baseline; primary
HEAD3679b1b/localmain966206f/stashcb568efd; databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Independent final review rechecks exact commit/diff/Goal/refs/protection.
This is local precommit evidence; hosted checks and merge results are separately
retained in tmp/m2-metric-evidence-trace-final-review.md. Normal scoped push/PR,
all hosted gates and exact base/head/CLEAN gate before standing-authorized merge.
No scope deviation/local blocker. Compatible installed fixed baseline required;
history/source gaps unchanged. No automatic next stage/research admission.
