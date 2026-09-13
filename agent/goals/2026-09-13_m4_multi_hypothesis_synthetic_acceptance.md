# Goal: M4 multi-hypothesis synthetic portability acceptance

Date: 2026-09-13. Planner and independent reviewer: Codex. Bounded implementation worker: one Luna (`gpt-5.6-luna`, medium); no recursive delegation.

## Objective and verified baseline

Prove that the merged M4 synthetic pipeline handles two structurally different, valid frozen hypotheses through its existing public entry without changing core code. Add a stable pre-execution identity fingerprint check that will run on the existing Ubuntu/Windows CI matrix when this local branch is later reviewed remotely. Do not claim cross-OS equivalence until that CI actually runs.

- Worktree: `D:/量化分析-m4-multi-hypothesis-acceptance`; branch `codex/m4-multi-hypothesis-acceptance`; clean base `origin/main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05` (merged PR #19).
- At task start local `main`, `origin/main`, and live GitHub `main` match; no open PRs. The preceding review is local `codex/m4-core-readiness-review@65d8abd3b896750d0f8d40ed7bcb08cb91dd88ae`, not merged into this branch.
- Protected original M2 worktree: `feat/m2-value-assessment-mvp@3679b1bac7a1634c6452784a4d8f6d139966f222` with pre-existing modified/untracked files; stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Existing synthetic pipeline design, acceptance cases, implementation, Stage4P contracts and North-Star remain frozen. The public entry is `run_synthetic_pipeline(request=...)`.

## Allowed scope

Only these paths may be added or changed:

1. `agent/goals/2026-09-13_m4_multi_hypothesis_synthetic_acceptance.md` (Codex-owned contract, committed before worker execution)
2. `agent/record/2026-09-13_01_m4-multi-hypothesis-synthetic-acceptance.md` (created before code changes, then updated with actual evidence)
3. `tests/test_m4_multi_hypothesis_portability.py` (new focused acceptance test)
4. `acceptance/2026-09-13_m4_multi_hypothesis_synthetic_acceptance.md` (actual evidence and limited verdict)

The new test may import existing test fixture helpers and the established public M4 APIs. It must not edit those helper files or weaken existing assertions.

## Forbidden scope

No changes to `src/**`, existing `tests/**`, `docs/**`, `reports/**`, `README.md`, `config/**`, `data/**`, `events/**`, `.github/**`, dependencies, North-Star, other worktrees, stash or ignored runtime. No real candidate, provider, database connection, market data, literature, holdout, real outcome execution, optimizer, ranking or research claim. Do not push, open PR, merge, or begin another stage. Do not assume that `SYNTHETIC` proves real provenance.

## Required behavior and acceptance cases

1. Construct two valid caller-supplied synthetic requests through the existing public types. They must differ in hypothesis ID, condition semantics, ordered controls and bootstrap policy (enabled versus disabled); each request's bound-input digest must be recomputed from its own compiled contract/plan and observations, never borrowed from the other request.
2. Run both through `run_synthetic_pipeline(request=...)`, validate each envelope against its own request, and assert that contract, plan, dataset and matrix identities are distinct and correctly bound. Assert the expected control columns/condition and bootstrap state, without asserting statistical significance or an A-share effect.
3. Define a documented pre-execution fingerprint from canonical contract, plan, dataset and matrix identities only. Exclude execution bytes, pipeline digest, numeric runtime/version and wall-clock/environment fields. Assert fixed expected fingerprints and reproduce them in a fresh Python process from another CWD; different hypotheses must not collapse to one fingerprint.
4. Use explicit synthetic provenance and preserve existing no-I/O, quality, rank, PIT, identity and no-holdout gates. A negative binding test must show that swapping the two hypotheses' bound inputs fails, without any partial accepted envelope.
5. Keep the new test focused; do not duplicate the existing AC-01–AC-30 implementation tests. The acceptance file must distinguish local Windows proof, cross-process/CWD proof and future Ubuntu CI proof. No claim of complete-envelope cross-OS byte identity.

## Required tests and exact validation commands

Run from this worktree with the shared interpreter, `PYTHONPATH=<worktree>/src`, and no pytest cache:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_m4_multi_hypothesis_portability.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
```

Check new Markdown as strict UTF-8 with LF final newline, no trailing spaces/conflict markers, and valid relative links. Independently inspect all changed/untracked files, commit/diff, test evidence, protected hashes, worktrees/stash, and local/origin/live synchronization. The previous full 2748-test run on `dec8a29` is historical baseline evidence, not a substitute for the focused commands above.

## Stop conditions and commit/push requirements

Stop if a valid second request requires changing a frozen schema or product code; if expected portable identity includes environment/numeric output fields; if a fixed fingerprint differs in the local child process; if protected identities or remote main drift; or if an existing protective test must be weakened. Record an observed failure honestly. Codex commits this Goal and initial record before delegation. The worker may create one scoped local delivery commit for paths 2–4 after tests; Codex independently reviews the final commit and may correct the branch only within this scope. Do not push, open PR, merge or start a next stage. Final verdict is exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`; `PASS` covers local synthetic acceptance only, with remote cross-OS CI explicitly pending.
