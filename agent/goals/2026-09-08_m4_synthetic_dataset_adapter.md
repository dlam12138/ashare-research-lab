# Goal: M4 synthetic dataset adapter

## Objective and baseline
User said continue after explicitly reaffirming Astra planning, Luna implementation,
Astra independent acceptance. Implement the previously delivered bounded synthetic
adapter design. Base codex/m4-dataset-adapter-design at
40d10b46c2e7e4a7e0cac0f28ccea07ef50d784d; main/origin/live main bab24f981fef9336b84280544ce709702b9df116.
Isolated branch codex/m4-synthetic-dataset-adapter in D:/量化分析-m4-adapter.

## Required behavior and scope
Implement docs/m4_dataset_adapter_design_v1.md and its acceptance cases. Frozen
synthetic inputs and output, original contract/plan exact binding, explicit date-domain
denominator, evidence verification, PIT gaps, fail-closed quality, deterministic
serialization, validation and four public dataset APIs. Execution authorization false.
Worker writes only src/ashare_research/mechanism/datasets/** and
tests/test_m4_synthetic_dataset_adapter.py. Parent owns this Goal, record and acceptance.
Keep design documents historical; document any necessary bounded clarification here.

### Review clarification
The one-argument serializer cannot rederive the condition predicate because the frozen
output does not contain the original threshold/operator. It validates strict integer
0/1 indicators plus structure/digest/audit-to-quality/complete-row consistency. The
four-argument validator recomputes from original contract/plan/inputs to prove the
predicate and source binding. No new output fields or weaker four-argument validation.
Exact coverage comparison must not depend on ambient Decimal context rounding;
integer comparison of the canonical gate's ratio is acceptable.
Synthetic domain/source identifiers use the existing A.1-style stable ASCII identifier
alphabet (letters/digits followed by letters/digits/underscore/dot/hyphen), rejecting
paths as identity. Intermediate BoundDatasetInputsV1 values may hold a blank digest
while callers calculate it; every materialization verifies the full canonical digest.

### Explicit escalation after failed deliveries
After two incomplete Luna deliveries, parent independently reproduced remaining
immutability and validation failures and split the work. The input followup still
left invariants incomplete. Parent explicitly announced taking responsibility for
core source repair under the routing escalation rule; Luna now writes only the new
test file. No silent model substitution; provenance is recorded in the work log.
Parent also owns tests/test_m4_dataset_adapter_review.py: independent executable
regressions for source/immutability/rehash/domain boundaries. Run this together with
the worker suite before full acceptance; no existing tests are replaced.

## Forbidden scope
No existing src/tests modifications, research artifacts, protected hashes, dependencies,
workflows, providers, default database, real data, statistics/executor, holdout execution,
M4-B, PR #10 merge, or changes to original dirty worktrees. No recursive delegation.
Original M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Tests and exact commands
Use existing declared-dependency interpreter without changing its installation:
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_synthetic_dataset_adapter.py`
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py`
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q`
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ tests/`
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m compileall -q src tests`
`git diff --check` and staged diff check.
If the full-run session cannot be recovered, persist its repeat with
`-m pytest -q --junitxml=tmp/adapter-validation/full-pytest.xml` and redirect output to
tmp/adapter-validation/full-pytest.log, saving its exit code in full-pytest.exit.
New tests cover design matrix, rehashed invalid input/output, immutable defensive copies,
exact coverage and condition boundaries, source conflicts, no IO/statistics, golden identity.
Worker runs focused tests and Ruff; parent independently reviews actual code and evidence,
then full suite once stable. Do not repeat full suite absent new failures/changes.

## Acceptance, delegation and stop
One explicit gpt-5.6-luna / medium worker, fork_turns=none, no fallback. Two failed
repair attempts or a semantic/protection conflict escalates to parent. Parent audits
diff, tests, HEAD, untracked files, protections and live remote. Scoped local commit(s)
after acceptance; no push or merge authorized. Stop after local implementation delivery,
before real data/executor or next stage. Verdict PASS / CHANGES_REQUIRED / BLOCKED.
