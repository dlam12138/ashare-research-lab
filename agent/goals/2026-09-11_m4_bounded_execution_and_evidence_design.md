# Goal: M4 bounded execution and evidence design

Date: 2026-09-11. Executor: DeepSeek Harness (`deepseek-flash`). Reviewer: Codex.

## Objective and verified baseline

Freeze an implementable, synthetic-only design for the remaining M4-A pipeline boundary:
`Bounded Execution -> Reproducible Artifacts -> Evidence Disposition`. Define the validated
matrix-to-estimator mapping, deterministic bootstrap and registered-robustness dispatch,
evidence disposition, artifact identity, and authorization state transitions. Correct the
project entry text that became stale after the adapter and matrix merges. This is a design and
documentation stage: do not implement or run statistical execution.

- Worktree: `D:/量化分析-m4-executor-design`.
- Branch: `codex/m4-bounded-execution-design`.
- Base: live `main` and `origin/main` at
  `f34adcb17c9995392690a1df6bb5a10ee102eb09` (PR #12 merge), verified through GitHub API at
  task start. PR #11 and PR #12 are merged; no PR is currently open.
- Existing capability chain on main: frozen contract -> deterministic plan -> validated
  synthetic dataset -> immutable design matrix. The matrix has
  `execution_authorized=False` and `statistics_computed=False`.
- Protected original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`;
  stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md` (this contract;
   Codex-owned and already committed before Harness execution)
2. `docs/m4_bounded_execution_and_evidence_design_v1.md`
3. `docs/m4_bounded_execution_acceptance_cases_v1.md`
4. `agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md`
5. `acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md`
6. `README.md`, limited to current-capability and roadmap statements made stale by merged
   PRs #9, #11, and #12
7. `tests/test_project_entry.py`, limited to synchronizing hard-coded current-capability text
   with the README while preserving all protective assertions
8. `tests/test_m4_stage4p_governance.py`, limited to synchronizing the canonical README-status
   assertion; do not alter protected aggregate, north-star, or production-surface gates

The design and acceptance-cases documents are normative. Every proposed interface must be
marked as proposed, not described as existing implementation.

## Forbidden scope

Do not modify `src/**`, dependencies, workflows, configuration, frozen reports, the north-star
documents, existing M4 design/acceptance documents, or any other test. Do not call regression,
bootstrap, robustness, or evidence code; do not compute coefficients, intervals, p-values, or
other outcomes even from synthetic data. Do not read database contents, call providers, obtain
real market inputs, access holdout data, or enter M4-B. Do not weaken or delete tests. Preserve
other worktrees, stash entries, ignored runtime data, and protected artifacts. Do not delegate.
Do not push, open a PR, merge, or start implementation.

## Required design behavior

The design must freeze, without leaving implementation-critical choices open:

1. A source-bound entry accepting matrix, preparation, contract, plan, and bound inputs and
   reusing `validate_design_matrix`; no matrix-only trust path.
2. Mechanical mapping from `plan.design_plan.ordered_terms` and `coefficient_role` to estimator
   inputs. Do not reuse M3-specific column names or fixed development dates.
3. Canonical-decimal-to-estimator conversion, finite/range checks, precision boundary, and
   fail-closed error order and stable error codes.
4. An allow-listed OLS method contract; unsupported method IDs fail rather than downgrade.
5. Bootstrap method, PCG64 seed/replications, block-length policy, complete-row sampling,
   confidence-level endpoint semantics, and the disabled path.
6. Registered robustness dispatch only: no automatic expansion, selection, or best-result use.
7. A complete disposition table for POSITIVE, NEGATIVE, and TWO_SIDED directions, confidence
   requirements, and data-quality failure disposition.
8. Immutable result/artifact schemas, canonical serialization and digest identity binding the
   full source chain, method configuration, code/schema version, outputs, and explicit
   `synthetic_test_only` provenance without host or absolute-path identity.
9. Exact meanings and transitions for execution authorization, statistics computed, and outcome
   read. The existing holdout boundary remains unauthorized and any holdout request fails closed.
10. Separation between synthetic execution readiness and real research authorization. No design
    result may imply estimability, significance, economic validity, tradability, or an A-share
    mechanism finding.

The acceptance cases must include base success plus: source or matrix tamper/re-hash, wrong
validation order, unsupported method, non-finite/conversion failure, singular/rank-deficient
input disposition, bootstrap disabled/enabled and exact endpoints, all evidence directions,
quality rejection, unregistered robustness, holdout refusal, input/key-order and CWD invariance,
artifact byte reproducibility, nested mutation, and explicit synthetic-only provenance.

## Required tests and exact validation commands

Run from the design worktree. Record each command and exit code independently. These commands
validate documents and existing behavior only; they do not authorize statistical execution.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'
gh pr list --state open --json number,title,headRefOid,baseRefName,url
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
```

Also verify all changed Markdown as UTF-8 with a final newline, no trailing whitespace or merge
markers, and resolve every repository-relative Markdown link. Review the existing source
interfaces directly; do not infer them from prior reports.

## Acceptance criteria

- The changed-path set is exactly within the whitelist; `src/**` and protected artifacts have
  no diff.
- The design freezes all ten required behavior areas and every acceptance case has an input
  change, expected output/error, validation stage, and authorization interpretation.
- README accurately states A.2I, adapter, and matrix are on main, while bounded execution and
  M4-B remain unimplemented/unauthorized. Protective project-entry statements remain intact.
- Existing targeted tests and ruff pass. Any genuine pre-existing/environmental failure is
  reported verbatim and independently reproduced or attributed by Codex; it is not hidden.
- Worktrees, stash, database hash, north-star and frozen M1-M3 evidence remain unchanged.
- The deliverables state that design completion is not implementation, statistical-execution,
  real-data, holdout, M4-B, push, PR, or merge authorization.

Codex independently reviews real branch/HEAD, commits/diff, all changed and untracked files,
test evidence, worktrees/stash, protected baselines, GitHub state, and Goal compliance. Final
verdict is exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop and report if the baseline or an allowed path changes concurrently; the design requires an
upstream schema or existing source change; a new dependency/workflow/test outside the whitelist
is needed; any statistical or outcome computation would be required; or any database, provider,
real-data, holdout, protected-artifact, or M4-B access would be required. Do not widen scope or
weaken a gate to continue.

## Commit and push requirements

Codex commits this Goal contract before Harness execution. DeepSeek Harness creates one scoped
local design-delivery commit containing only paths 2-8 after validation. Do not push, open a PR,
merge, or start implementation. After delivery, wait for Codex's independent verdict.
