# M4 Stage 4A.2 — Deterministic Analysis Plan Design Review

Status: COMPLETED — READY_FOR_M4A2_IMPLEMENTATION_REVIEW

## Objective

Freeze the design boundary from `FrozenMechanismContract` to a deterministic,
declarative, role-based `DeterministicAnalysisPlan` for the first
`DAILY_CONDITIONAL_CONTROLLED_OLS_V1` slice.

## Verified baseline

- Canonical base: `origin/main:a0a7c13ee47057abf5e40a96a616baf78451774e`
- Review branch: `docs/m4a2-deterministic-analysis-plan-design`
- Review worktree: `D:\量化分析-m4a2-design`
- Protected M2 worktree was not used.
- Starting worktree was clean on the review branch.

## Allowed scope

- Three design reports under `reports/`.
- This Goal contract, its Acceptance record, and its Work Record.
- Design-only decisions needed to establish A.1 sufficiency, plan identity,
  role-based requirements, M3 bounded reuse, and the A.2I slice.

## Forbidden scope

- Production implementation in `src/`.
- Changes to `tests/`, `README.md`, North-Star, `pyproject`, workflow, or M3
  artifacts.
- Dataset adapter, executor, regression adapter, bootstrap execution, real
  data, real outcome reads, or M4-B.
- A.1 schema changes unless the sufficiency review proves one is necessary.
- Merge or automatic progression to A.2I.

## Required behavior

- Keep `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- Decide contract sufficiency explicitly; do not silently add fields.
- Freeze an immutable, content-addressed, repository-independent,
  pre-execution plan envelope.
- Preserve frozen control order and method-owned OLS semantics.
- Keep universe and dataset acquisition outside the plan builder.
- Reuse M3 statistical semantics only where bounded; keep PetroChina bindings
  out of the generic core.
- Freeze dispatch specifications only for conditional summaries, bootstrap,
  robustness, evidence, and holdout.
- Define A.2I as compile-only with synthetic identity tests.

## Required tests and exact validation

- `python -m pytest tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py -q`
- JSON parse validation for the three new reports.
- `git diff --check`.
- No full 2309-test run is required for this documentation/design-only stage.

## Acceptance criteria

- `A1_CONTRACT_SUFFICIENT_FOR_FIRST_SLICE` is supported by the reviewed
  implementation and reports.
- `M4A2_PLAN_ARCHITECTURE = DECLARATIVE_PLAN_OVER_ROLE_BASED_SEMANTICS`.
- `M4_ARCHITECTURE = THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- Plan schema, digest policy, role mappings, bootstrap semantics, robustness
  dispatch, evidence inputs, and holdout boundary are frozen.
- No forbidden files are changed and no outcome is read.
- Final state is ready for explicit M4A2 implementation review.

## Stop conditions

- If `origin/main` differs from the required canonical base, stop for review.
- If A.1 is insufficient, emit `M4A2_A1_CONTRACT_INSUFFICIENT` and stop for
  `STOP_FOR_M4A1_SCHEMA_REVIEW`.
- If any design requires real data or production code, stop and request a new
  stage authorization.

## Commit and push requirements

- One commit: `docs: freeze M4A2 deterministic analysis plan design`.
- Push only `docs/m4a2-deterministic-analysis-plan-design`.
- A PR may be opened for review but must not be merged.
