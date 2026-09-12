# Goal: M4 synthetic end-to-end pipeline design correction

Date: 2026-09-12. Executor: DeepSeek Harness (`headless`, bounded sub-agents allowed). Reviewer:
Codex.

## Objective

Correct factual and internally contradictory requirements in the frozen M4 synthetic end-to-end
pipeline design and acceptance cases that were exposed by implementation and measured composition.
Keep the authorized capability unchanged: synthetic-only, in-memory orchestration of the five
already-frozen stages plus optional read-only registry metadata. This task is design correction
only; it must not add or change production source, tests, dependencies, workflows, real-data
capability, or research authorization.

## Verified baseline

- Worktree: `D:/量化分析-m4-synthetic-pipeline-design-correction`.
- Branch: `codex/m4-synthetic-pipeline-design-correction`.
- Base, `origin/main`, and live main: `d3fcb1967e9e7f6d3caac3e3f08ea874646f3098`
  (merge commit for PR #16); no open PR at task start.
- Design blob: `cce58d02bec0ee20c259f456188d3222b62ad602`.
- Acceptance-cases blob: `d4ba4fe4cc83c7be5a8b32aad0c9988a7545a216`.
- Protected bounded-execution design blob: `9617f64360b6c3d9a6148ec08c25fa0209a0f9f4`.
- Protected M4-B registry design blob: `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`.
- Protected Stage4P contract blob: `dfd41eaafc099e7748499f72de7ddd800bf97f69`.
- Original M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.
- Implementation evidence is preserved locally on branch
  `codex/m4-synthetic-pipeline-implementation` at
  `8a71fb9ba80701099be7c5df6e0c81ac13233ebb`; its measured host results are 40 new tests,
  328 upstream tests, and 15 governance tests passing, with Ruff clean.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md` (this
   Codex-owned contract, committed before DSH execution)
2. `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`
3. `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`
4. `agent/record/2026-09-12_02_m4-synthetic-end-to-end-pipeline-design-correction.md`
5. `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design_correction.md`

No README change is needed because main still truthfully describes the orchestrator as design-only.

## Required corrections

1. Replace the impossible successful-call bounds in design §11.3 with the measured bounds implied
   by the mandatory S0-S8 and V1-V6 topology: `build_analysis_plan <= 12`,
   `materialize_analysis_dataset <= 11`, and executor `_execute <= 3`. Explain why public producer
   counts include validation recomposition; preserve the absolute bootstrap replication ceiling.
2. Correct J4/R11: a concrete valid registry record always serializes to finite bytes, but the
   upstream schema does not impose a uniform finite upper bound over every valid record because
   tuple/history cardinalities and some strings are unbounded. Do not invent a size gate or fake
   total ceiling; retain deterministic lowercase hex round-trip requirements.
3. Correct G14/S0 timing: S0 may scan only request projections available at intake (including an
   optional registry projection). The full canonical result envelope, including contract and plan,
   is scanned at V5/S7. Specify the existing `FORBIDDEN_ARTIFACT_CONTENT` carrier without adding a
   fifteenth pipeline code.
4. Correct §5.5 D6: composed robustness parameters are present in the plan/envelope and are caught
   by pipeline V5 after composition; the separate registered-robustness dispatch path has its own
   existing scan but is not invoked by this orchestrator. Do not claim the bounded execution
   artifact contains robustness parameters when it does not.
5. Correct public reachability/classification of `PLAN_TERM_ROLE_MISMATCH`: public composed
   validation is preempted by `CONTRACT_PLAN_MISMATCH`; the downstream defense may only be shown by
   a clearly labeled internal/stage projection probe. Apply the same truthful composed-entry,
   stage-level, envelope-level, static, or structurally-unreachable classification to AC-10,
   AC-12, AC-14, AC-15, and AC-17 where needed.
6. Resolve G11 versus AC-28d explicitly: the replication ceiling applies only when bootstrap is
   enabled; a disabled bootstrap plan has no resampling work and is not rejected for its inert
   replication declaration.
7. Resolve remaining documented ambiguities without changing observable capability: define V4
   structural failures using an existing closed error, preserve RB4's hex-to-sha256 mapping,
   clarify G14's error type, and keep the public 20-symbol surface, 14-code pipeline table,
   constants, schemas, fields, signatures, L1-L14, S0-S8, V1-V6, authorization boundaries, and
   all upstream contracts unchanged except where the corrections above necessarily clarify them.

## Forbidden scope

Do not modify `src/**`, `tests/**`, README, any other docs/acceptance/record/Goal, reports, config,
data, events, fixtures, dependencies, workflows, or `pyproject.toml`. Do not weaken or rewrite an
acceptance obligation merely to fit an implementation. Do not add real data, provider, database,
filesystem, environment, network, market, literature, holdout, backtest, selection, ranking,
recommendation, trading, persistence, or registry-mutation authorization. Do not change any
upstream schema, digest, validator, public export, test, protected blob, north-star gate, stash,
database, or other worktree. Never force-push or push directly to main.

## DSH delegation authorization and limits

The user's explicit exception permits DSH to use bounded sub-agents for independent topology
measurement, schema/bounds audit, acceptance reachability audit, and adversarial final review.
Every sub-agent inherits this Goal and its exact whitelist/forbidden scope. DSH remains responsible
for integrating and independently checking their conclusions. Sub-agents are read-only, may not
edit any file, mutate Git, push, open/merge PRs, start another stage, or recursively delegate.

## Required validation

Run and record exact commands and exit codes:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'
& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& $py -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py
& $py -m ruff check src tests
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'
gh pr list --state open --json number,title,headRefOid,baseRefName,url
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
git diff --name-only origin/main...HEAD
git diff --name-only origin/main -- src tests reports config data events .github pyproject.toml README.md
git hash-object docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4b_hypothesis_registry_design_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
```

Also verify exact whitelist, changed Markdown link resolution, UTF-8/final newline/no CR/no conflict
markers/no trailing whitespace, internal cross-reference consistency, exact public surface/error-code
claims, and that each factual correction is supported by existing source behavior or measured
implementation evidence. Sandbox test failures must be reported as failures and rerun by Codex in
the host environment.

## Acceptance criteria

- All seven required corrections are explicit and mutually consistent in both normative files.
- No capability, API, error code, digest, stage, validation phase, upstream contract, protected
  baseline, or authorization boundary changes beyond those corrections.
- Acceptance cases truthfully distinguish composed entry, stage/internal probe, envelope layer,
  static proof, and structural unreachability; no fabricated public runtime path remains.
- All required tests, Ruff, hygiene, Markdown, protected-baseline, database/stash/worktree, and
  local/origin/live checks pass.
- Record and acceptance evidence enumerate exact changed lines/sections, commands/results,
  deviations and residual risks. Codex independently reviews actual Git and repository evidence.

## Stop conditions

Stop and report if a correction requires source/test/upstream contract changes, expands capability
or authorization, changes a non-whitelisted path, weakens a safety boundary, conflicts with actual
public behavior that cannot be resolved as a truthful clarification, moves a baseline, or Git
cannot create scoped commits. Do not work around Git permissions with alternate indexes, Git
directories, or repository recreation.

## Commit, push, PR, merge, and next stage

Codex commits this Goal before DSH starts. DSH may create scoped documentation/evidence commits by
explicit path staging only; never `git add -A`. DSH and sub-agents may not push, create/merge a PR,
or start implementation.

The user's standing authorization permits Codex to push, open a PR, wait for all required CI, and
merge normally only after an independent `PASS`. Never force-push or push to main. Implementation
may resume only after this correction PR is verified merged and main synchronized, on a new branch
with a newly committed Goal. The final evidence packet and verdict must meet `AGENTS.md` exactly.
