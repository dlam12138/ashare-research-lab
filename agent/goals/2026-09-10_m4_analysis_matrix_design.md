# Goal: M4 synthetic analysis matrix design

## Objective and verified baseline
User authorized starting the next stage after PR #11 final acceptance. Deliver a
bounded design for the next dependency: exact synthetic analysis matrix preparation
and the boundary before statistical execution. This is a design stage, not a full
executor implementation. PR #11 is OPEN; do not infer merge authorization.
Base codex/m4-synthetic-dataset-adapter at
b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef, matching origin and live remote.
Main/origin/live main: bab24f981fef9336b84280544ce709702b9df116.
New isolated branch codex/m4-analysis-matrix-design, D:/量化分析-m4-matrix-design.

## Allowed scope and required behavior
Five new Markdown files: this Goal, a normative matrix design, its acceptance cases,
one work record and one acceptance document. Specify original-input verification,
plan-defined term order, exact decimal values, immutable output, deterministic identity,
quality rejection and separation of matrix preparation from estimability/execution.
Audit against actual planning/compiler.py and datasets/synthetic.py interfaces.

## Forbidden scope and protections
No source/tests changes, statistics, providers, real inputs, database reads/writes,
holdout execution, M4-B, dependencies, workflows, protected artifacts, README or old
design edits. No PR merge or push. Preserve all existing worktrees and ignored data.
Original M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f;
DB SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Tests and exact validation commands
From the new worktree:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
git diff --check
git diff --cached --check
```
Manually audit schema, ordering, examples, negative cases and local Markdown links.
Check that the commit adds exactly the five allowed documents; no full suite rerun
for additive design documents. Inspect actual PR #11 CI and live refs at final audit.

## Acceptance, stop and delivery
Design is implementable using current four-argument dataset validation without
altering A.1/A.2/dataset schemas. Every readiness claim excludes statistical validity
and execution authorization. Local checks pass and protected state remains unchanged.
Create one scoped local commit after review; no push or merge. Stop at design delivery.
Any subsequent implementation is a separate stage. Verdict PASS / CHANGES_REQUIRED / BLOCKED.
