# Goal: M4 synthetic end-to-end pipeline design

Date: 2026-09-12

## Objective

Freeze an implementable design and executable acceptance-case specification for a single,
deterministic, in-memory entry point that composes the already-canonical M4-A synthetic-only
stages: typed hypothesis parsing and contract compilation, analysis-plan compilation, synthetic
dataset adaptation, immutable matrix materialization, and bounded execution/evidence output. The
design must close orchestration ambiguity without adding real-data capability or changing any
existing frozen component contract.

## Verified baseline

- Worktree: `D:/量化分析-m4-synthetic-pipeline-design`.
- Branch: `codex/m4-synthetic-pipeline-design`.
- Base and initial HEAD: `origin/main` at
  `fd1cc35ee824aa9449f7e7800c12d0d80c845e05` (merged PR #15).
- Worktree initially clean; branch initially identical to `origin/main`.
- Shared stash remains `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Original dirty M2 worktree remains
  `feat/m2-value-assessment-mvp@3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected database `D:/量化分析/data/research.duckdb` SHA256 is
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.
- Protected frozen blobs:
  - bounded-execution design: `9617f64360b6c3d9a6148ec08c25fa0209a0f9f4`
  - bounded-execution acceptance cases: `f857b9948c7f396a855a1e0f6506752f0065d667`
  - M4-B registry design: `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`
  - M4-B registry acceptance cases: `4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2`
  - Stage4P M4-B contract: `dfd41eaafc099e7748499f72de7ddd800bf97f69`

## Allowed scope

1. This Goal file (Codex-owned contract).
2. `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`.
3. `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`.
4. `README.md`, limited to accurate design/status and authorization wording.
5. `agent/record/2026-09-12_01_m4-synthetic-end-to-end-pipeline-design.md`.
6. `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md`.

No other tracked or untracked path may be created, changed, staged, or committed.

## Forbidden scope

- No source-code, test-code, workflow, dependency, configuration, report, fixture, database, cache,
  or existing frozen-document changes.
- No implementation of the proposed orchestrator and no modification of existing M4 APIs.
- No real candidate or registry dataset, literature acquisition, network/provider/database reads,
  market-data reads, holdout access, backtest, ranking, promotion, recommendation, or trading claim.
- No real hypothesis execution and no claim that synthetic pipeline readiness establishes an
  A-share mechanism.
- No direct push to `main`, force push, destructive cleanup, stash mutation, or original-worktree
  mutation.

## Required behavior to freeze

The design and acceptance cases must unambiguously specify:

1. One minimal public orchestration entry point and immutable result envelope, with exact names,
   inputs, outputs, version constants, canonical serialization, identity/digest rules, and public
   export surface.
2. Exact composition order across the five existing stages and validation before/after each stage;
   no duplicate statistical implementation or bypass of existing validators.
3. Synthetic-only provenance and authorization gates that reject real/unknown inputs before any
   computation and keep registry metadata logically separate from execution evidence.
4. Deterministic first-error ordering, stable error codes, exception mapping, and no partial result
   on failure.
5. Cross-artifact binding among source config, frozen contract, plan, prepared dataset, matrix, and
   execution artifact, including the exact digest chain and tamper detection responsibilities.
6. Immutability, canonical byte equality, repeated-run determinism, bounded resource behavior, and
   absence of filesystem/network/provider/database/holdout side effects.
7. How an optional synthetic/schema-only M4-B record may be bound as metadata without changing its
   state, treating it as evidence, or triggering execution; omission must have explicit semantics.
8. A complete acceptance matrix with positive, boundary, tamper, error-order, structural-ban,
   authorization, and regression cases, plus an implementation whitelist for a later Goal.
9. Explicit non-goals and residual risks, including why this is not a generic real-data research
   executor.

## DSH delegation authorization

DSH is explicitly allowed to use sub-agents for bounded analysis, design drafting, and independent
review during this stage. Every DSH sub-agent inherits this Goal's whitelist, forbidden scope,
protected baselines, and stop conditions. DSH remains responsible for integrating and checking all
delegated output. Sub-agents may not push, open or merge a PR, modify the Goal, expand scope, access
real data, or mutate protected state.

## Required validation commands

Run from the stage worktree and record exact exit codes/results:

```powershell
git status --short --branch
git diff --check
git diff --name-only origin/main...HEAD
git diff --name-only
git ls-files --others --exclude-standard
git hash-object docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4_bounded_execution_acceptance_cases_v1.md docs/m4b_hypothesis_registry_design_v1.md docs/m4b_hypothesis_registry_acceptance_cases_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/mechanism tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
git stash list
git fetch --prune origin
git rev-parse origin/main
git ls-remote origin refs/heads/main
```

Also run deterministic Markdown link/anchor validation over the two new design documents and the
README links using a temporary path outside the repository; no generated validator artifact may
remain in the worktree.

## Acceptance criteria

- The two design documents jointly cover every required behavior above with no implementation-
  critical ambiguity and with complete Goal-to-case traceability.
- Every proposed surface is demonstrably compositional over existing APIs; frozen APIs and blobs
  remain unchanged.
- The changed-path set is exactly the allowed scope, the database/stash/original worktree remain
  unchanged, all validation commands pass, and the final branch is clean after commit.
- README states design-only status accurately and preserves all real-data, registry-data,
  literature, holdout, and execution authorization boundaries.
- An independent DSH review finds no unresolved P0/P1 or implementation-blocking issue.

## Stop conditions

Stop and report `BLOCKED` if any required behavior cannot be specified without changing an existing
frozen contract, if protected state changes, if real data or external content is required, if the
whitelist must expand, or if an implementation-critical ambiguity remains after review.

## Commit, push, PR, merge, and next-stage requirements

- Commit the Goal alone before DSH design work.
- Commit the completed design/evidence packet separately after independent review and validation.
- The user's standing authorization permits pushing this branch, opening a PR, waiting for required
  CI, and merging with a normal merge commit if and only if the final verdict is `PASS` and all
  required checks succeed.
- Never push directly to `main` and never force-push.
- After merge, independently verify local/origin/live-main synchronization and protected state.
- A later implementation stage requires a new committed Goal. Do not begin implementation within
  this design Goal; user authorization to continue permits creating that later Goal only after this
  design is merged and its real-data prohibition is preserved.

