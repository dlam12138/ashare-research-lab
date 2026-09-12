# Goal: M4 synthetic-only bounded execution implementation

Date: 2026-09-12. Executor: DeepSeek Harness (`headless`). Reviewer: Codex.

## Objective and verified baseline

Implement the frozen M4 bounded-execution and evidence design for synthetic fixtures only. Add
an allow-listed execution package that consumes the fully source-bound five-object chain
`(matrix, preparation, contract, plan, bound_inputs)`, computes the specified OLS/bootstrap result,
emits deterministic immutable execution and registered-robustness-dispatch artifacts, and realizes
the frozen acceptance cases without weakening any upstream or governance boundary.

- Worktree: `D:/量化分析-m4-executor-implementation`.
- Branch: `codex/m4-bounded-execution-implementation`.
- Base: `2ee110cddec4bd66e51a3913a4515a8dbe0af823`, whose parent chain contains the accepted design and
  whose main ancestor is `f34adcb17c9995392690a1df6bb5a10ee102eb09`.
- At task start, local `main`, `origin/main`, and live main are `f34adcb`; no PR is open. The design
  branch remains local-only and is not merged. Its two commits intentionally travel as ancestors of
  this implementation branch; no separate design merge is performed.
- Protected original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

This Goal explicitly authorizes coefficient, interval, and evidence-disposition computation on
bounded synthetic test fixtures only. It does not authorize real data, providers, database access,
holdout, production execution, M4-B, trading conclusions, or an A-share mechanism finding.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-12_m4_bounded_execution_implementation.md` (this Codex-owned contract)
2. `src/ashare_research/mechanism/execution/__init__.py`
3. `src/ashare_research/mechanism/execution/bounded.py`
4. `tests/test_m4_bounded_execution.py`
5. `README.md`, limited to current capability, roadmap, and authorization wording made stale by
   this implementation
6. `tests/test_project_entry.py`, limited to synchronizing stale capability text while preserving
   all protective assertions
7. `tests/test_m4_stage4p_governance.py`, limited to synchronizing stale README-status assertions
   while preserving all frozen aggregate and north-star gates
8. `agent/record/2026-09-12_01_m4-bounded-execution-implementation.md`
9. `acceptance/2026-09-12_m4_bounded_execution_implementation.md`

The normative sources are `docs/m4_bounded_execution_and_evidence_design_v1.md` and
`docs/m4_bounded_execution_acceptance_cases_v1.md`. Existing planning, dataset, matrix, digest,
and frozen-JSON modules may be imported and read but not modified.

## Forbidden scope and protections

Do not add or modify a top-level `src/ashare_research/mechanism/*.py` file: that surface is covered
by the frozen M1-M3 aggregate. Do not modify `planning/**`, `datasets/**`, existing schemas or digest
algorithms, dependencies, workflows, configuration, reports, north-star documents, data, databases,
or any unlisted test. Do not import or reuse the M3 regression/bootstrap/robustness/evidence modules,
`statsmodels`, or `pandas`. Do not weaken, delete, skip, or rewrite a gate to pass.

Do not access real inputs, providers, database contents, holdout, or M4-B. Do not invent robustness
statistics: registered parameters are validated, bound, and forwarded only. Do not touch other
worktrees or the stash. Do not recursively delegate. Do not push, open a PR, merge, force-push, use
destructive Git cleanup, or start a later stage.

## Required behavior

- Expose exactly the eight frozen public functions from the design. Public execution must accept
  the five source-bound objects and call `validate_design_matrix` before trusting values; there is no
  matrix-only path or `**kwargs` escape hatch.
- Preserve the frozen X1-X16, R0-R9, and V1-V4 validation orders and stable errors. Propagate
  upstream `AdapterError`/`MatrixError`; failures produce no partial artifact.
- Map estimator inputs mechanically from ordered matrix metadata; align response rows to
  `preparation.complete_rows`; enforce decimal conversion, finite/range gates, and `n >= k` plus
  exact full-column-rank checks before and after fitting. Do not downgrade or use a pseudoinverse.
- Implement the allow-listed OLS and moving-block bootstrap exactly as frozen, including PCG64,
  block-length and endpoint rules, disabled behavior, direction/disposition tables, and zero-strict
  comparisons.
- Produce immutable, canonically serialized and digest-bound `ExecutionArtifactV1` and
  `RobustnessArtifactV1`. Preserve source-chain identity, float identity, interpretation boundaries,
  synthetic-only provenance, and active forbidden-key/path rejection.
- Registered robustness is dispatch-only: no statistic, selection, ranking, best result, aggregate,
  or outcome read. Holdout and real-data-shaped requests fail closed.
- Implement AC-01 through AC-19 against real code. Build a valid positive fixture with `n >= k` and
  full rank while retaining the existing 3x5 fixture as a singular negative. Defense-in-depth cases
  that are unreachable by construction use structural/order assertions rather than invented hits.
- Update project-entry wording accurately: bounded execution is implemented for synthetic tests,
  but there is still no generic research executor; real execution, holdout, and M4-B remain
  unauthorized/not started.

## Required tests and exact validation commands

Run from the implementation worktree and record every command and exit code independently:

```powershell
$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& $py -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py
& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& $py -m pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py
& $py -m ruff check src/ashare_research/mechanism/execution tests/test_m4_bounded_execution.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'
gh pr list --state open --json number,title,headRefOid,baseRefName,url
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C D:/量化分析 rev-parse HEAD
```

If the known `tmp_path` `WinError 5` appears, reproduce the affected group with an explicit writable
`--basetemp` and report both outcomes; do not hide it or modify tests. Also check the changed-path
whitelist, forbidden imports, UTF-8/final-newline/whitespace/merge markers, and all Markdown links.

## Acceptance criteria

- Changed paths are exactly within the whitelist; source changes are only the two new files beneath
  `mechanism/execution/`; frozen top-level mechanism aggregate, M1-M3 evidence, schemas, north-star,
  database, stash, and other worktrees remain unchanged.
- All eight public signatures, artifact fields, constants, validation orders, deterministic identity,
  OLS/bootstrap/disposition semantics, dispatch-only semantics, and authorization flags match the
  frozen design without implementation-critical deviation.
- AC-01 through AC-19 are covered by non-skipped tests, including success, tamper, validation-order,
  rank, conversion, bootstrap, all directions, provenance, forbidden content, holdout refusal,
  nested mutation, order/CWD invariance, and byte reproducibility cases.
- New tests, entry/governance tests, upstream M4 regressions, ruff, and diff checks pass. Any genuine
  environment failure is reproduced and reported rather than concealed.
- README remains explicit that synthetic readiness is not real research authorization, statistical
  significance, economic validity, tradability, or a mechanism finding.

Codex independently inspects the actual branch/HEAD, commits/diff, changed and untracked files, test
evidence, worktrees/stash, protected baselines, live remote state, Goal compliance, and acceptance
evidence. Final verdict is exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop and report if the baseline moves; any non-whitelisted file is changed; implementation requires
an upstream schema/digest/dependency/workflow change; a frozen or protective test would need to be
weakened; a valid full-rank synthetic fixture cannot be built without changing frozen modules; real
data/provider/database/holdout/M4-B access is required; registered robustness would require computing
statistics; design and actual upstream interfaces conflict; or Git cannot create the required local
commit. Do not work around Git permissions with alternate indexes/git-dirs or repository recreation.

## Commit and push requirements

This Goal contract is committed by Codex before Harness execution. The Harness creates scoped local
implementation and evidence commit(s) using explicit path staging only; never use `git add -A`.
Do not push, open a PR, merge, or start the next stage. The final report must include this Goal path,
verified base, final branch/full commit hashes, files changed, implementation summary, every actual
validation command and result, acceptance evidence, worktree/stash/protected state, local/origin/live
synchronization, deviations and residual risks, and whether any next stage is authorized.
