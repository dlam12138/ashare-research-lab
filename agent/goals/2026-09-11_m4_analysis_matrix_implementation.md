# Goal: M4 synthetic analysis matrix implementation

Date: 2026-09-11. Executor: DeepSeek Harness (`deepseek-flash`). Reviewer: Codex.

## Objective

Implement the accepted synthetic analysis matrix preparation design as a pure, deterministic
module. Produce a validated immutable matrix from an existing `DatasetPreparationV1`, frozen
contract, deterministic plan and original bound inputs. Stop after implementation, tests,
local commit and independent review; do not execute statistics or merge any PR.

## Verified baseline

- Worktree: `D:/量化分析-m4-matrix-implementation`.
- Branch: `codex/m4-analysis-matrix-implementation`.
- Base: design closeout commit `8a3b6a5d83d13aa9db71a0191f18b60af195b628`, whose parent is adapter commit
  `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`.
- Normative inputs: `docs/m4_analysis_matrix_design_v1.md` and
  `docs/m4_analysis_matrix_acceptance_cases_v1.md`; design acceptance is PASS.
- Live `main` is `bab24f981fef9336b84280544ce709702b9df116`; PR #11 remains open at adapter
  commit `b0c8fafb...`, with 42 successful checks at task start.
- Protected original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Allowed scope

Only these implementation-stage paths may be added or changed:

1. `agent/goals/2026-09-11_m4_analysis_matrix_implementation.md` (this contract)
2. `src/ashare_research/mechanism/planning/matrix.py`
3. `tests/test_m4_analysis_matrix.py`
4. `agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md`
5. `acceptance/2026-09-11_m4_analysis_matrix_implementation.md`

Do not modify either accepted design document. Do not modify package `__init__.py` files; tests
and callers import the new module directly, preserving the existing public package surface.

## Forbidden scope

No database connection or business-data read, provider call, real market input, regression,
rank/estimability calculation, bootstrap, evidence decision, holdout access, M4-B work, README,
dependency, workflow, historical document, schema or existing test change. Do not weaken or
delete tests. Do not touch other worktrees, stash entries, ignored runtime data or protected
artifacts. Do not recursively delegate. Do not merge PR #11 or any branch.

## Required behavior

- Implement exactly the four public functions and immutable types frozen by the design:
  `materialize_design_matrix(preparation, contract, plan, bound_inputs)`,
  `matrix_to_canonical_dict(matrix)`, `serialize_matrix(matrix)` and
  `validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)`.
- Keep `_project_validated_matrix(preparation, plan)` private. The public materializer must call
  existing four-argument `validate_dataset` before the quality gate and projection. Upstream
  `AdapterError` values propagate unchanged.
- Reject `REJECTED_QUALITY` and empty complete rows with
  `MatrixError("DATASET_NOT_READY")`; never return a partial or empty matrix object.
- Derive ordered columns exclusively from `plan.design_plan.ordered_terms`. Dispatch values by
  `term_role`: intercept `"1"`, factor and controls from their `role_order` values, condition
  indicator from the row's strict integer indicator. Preserve canonical decimal strings without
  float conversion.
- Copy the preparation identity chain and quality facts exactly. `MatrixQualityV1.status` comes
  from `preparation.status`; its other seven fields come from `preparation.quality` without
  re-judgment. `source_role` is identity-bearing audit/provenance metadata and must match the plan.
- Produce frozen tuple-backed objects, independent canonical dictionaries, one-LF canonical UTF-8
  serialization and `canonical_digest` identity over the exact frozen payload excluding only
  `matrix_digest` itself.
- `validate_design_matrix` must validate the matrix object, re-run source validation, re-project,
  and compare canonical bytes. Preserve the design's deterministic validation order and stable
  error types/codes.
- No success state authorizes statistical execution. Both `execution_authorized` and
  `statistics_computed` remain strict `False`.

## Required tests

Implement meaningful product tests covering the accepted AC-01 through AC-15 and AC-08b,
including: base exact matrix and digest, no/multiple/reordered controls, all exact condition
boundaries, missing/PIT quality behavior, fail-closed rejection, self-consistent source tampering,
forged matrix and rehashed matrix rejection, nested semantic change, input/key-order invariance,
cross-directory identity, immutability/defensive copies, error type/code/order, canonical decimal
behavior and serializer/digest consistency. Reuse existing fixtures where helpful; do not replace
real calls with a mirror implementation of the production algorithm.

## Exact validation commands

Run from the implementation worktree and record every exit code separately:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_analysis_matrix.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
git -c http.proxy= -c https.proxy= ls-remote origin
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
```

Refresh PR #11 and all check-runs at its exact HEAD. New failures or unexplained regressions require
focused diagnosis; do not edit unrelated code or tests to make the suite pass.

## Acceptance criteria

Exactly the five allowed paths differ from the base contract commit; the implementation matches
the frozen APIs, payload and measured example digests; all targeted and regression tests and ruff
pass; no source-verification bypass exists; rejected quality returns no object; protected state is
unchanged. Codex independently inspects the actual commit/diff and repeats the relevant validation.
Final verdict is exactly PASS, CHANGES_REQUIRED or BLOCKED.

## Stop conditions

Stop and report if implementing the accepted design requires changing an upstream schema, existing
adapter/compiler behavior, package exports, dependencies, protected data, or another worktree; if
the baseline drifts; if a concurrent change appears in an allowed path; or if real data/statistical
execution is required. Do not work around these conditions by widening scope.

## Commit and push requirements

Commit this Goal separately before implementation. DeepSeek must create one scoped local
implementation commit containing only paths 2–5. Do not push, open a PR or merge. Codex reviews the
commit and may return precise findings to DeepSeek for at most three implementation/fix rounds.
After PASS, stop; any push, PR, merge or statistical-execution stage needs separate authorization.
