# Goal: accept the M4 synthetic pipeline after AC-05 correction

Date: 2026-09-13. Executor and independent reviewer: Codex.

## Objective and verified baseline

Deliver and independently accept the preserved synthetic-only, in-memory M4 pipeline candidate against the corrected frozen design and AC-01–AC-30 cases. Base is clean `main` / `origin/main` / live main `c9ff0c5a17b022ddbce0bd724e10a5ff6aaafb51`, the normal merge commit of PR #18 (42 successful checks). This worktree is `D:/量化分析-m4-synthetic-pipeline-acceptance` on `codex/m4-synthetic-pipeline-acceptance`. Preserved source candidate: clean `codex/m4-synthetic-pipeline-resume@f5f419e0377cf74925bd8bbff27f8a2f1c513ffd`; historical acceptance was `CHANGES_REQUIRED` solely for pre-correction AC-05 and is not reused as a PASS verdict. The corrected normative design and cases have blobs `6c2bd048f4f7e74bb4a8015b53c9a6e76fd483cd` and `2393b4723ef8ac4aa883a34386b7618fb2cd9025`.

Original protected M2 HEAD is `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default DB SHA256 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`. Protected bounded-execution design, M4-B registry design, and Stage4P contract blobs are `9617f64360b6c3d9a6148ec08c25fa0209a0f9f4`, `6d9c292001c09a4b1a8e895e54619dc1e8826f3d`, and `dfd41eaafc099e7748499f72de7ddd800bf97f69`.

## Allowed and forbidden scope

Allowed paths only: this Goal; `src/ashare_research/mechanism/pipeline/__init__.py`; `src/ashare_research/mechanism/pipeline/orchestrator.py`; `tests/test_m4_synthetic_pipeline_orchestrator.py`; `README.md` for truthful synthetic-only status; new `agent/record/2026-09-13_01_m4-synthetic-pipeline-post-ac05-acceptance.md`; new `acceptance/2026-09-13_m4_synthetic_pipeline_post_ac05_acceptance.md`. Import the three candidate code/test files and relevant README changes from `f5f419e` with explicit paths, then update only now-stale AC-05 comments and frozen normative blob expectations. Do not import old records or acceptance conclusions.

Evidence-driven contract addendum before AC-21 correction: the first required pipeline run gave 50 passed / 1 failed because AC-21 snapshots the shared platform temporary directory, which an unrelated process modified during the test; the unchanged test passed in isolation and the full rerun gave 51 passed. Within the already-allowed new test file, replace only AC-21's shared-directory snapshot target with pytest's dedicated `tmp_path`, keeping the external-to-repository assertion and all existing no-I/O monkeypatches, repository/package snapshots, module and stdout/stderr checks. This is a stricter isolation of the same no-side-effect obligation, not permission to weaken, skip, or broaden the test. Rerun the full pipeline suite and Ruff after the correction; stop if it still fails. The initial failure and reruns must remain in the evidence record.

Forbidden: modifying other source/test/docs/reports/config/data/events/fixtures/dependencies/workflows, existing protected blobs, public upstream APIs, schemas, errors, quality/rank gates, database, stash, ignored runtime data, or other worktrees. No provider, filesystem, network, real-data, holdout, literature, backtest, selection/ranking, recommendation, trading, registry mutation, persistence, or new execution authority. Do not weaken/delete/skip tests, force-push, or push to `main`.

## Required behavior, tests and acceptance

Preserve exact 20-symbol pipeline public surface, 14 pipeline errors, S0–S8/G1–G14/V1–V6/L1–L14 composition and digest chain, immutable canonical envelope, optional read-only registry binding, deterministic 12/11/3 successful call bounds, enabled-only bootstrap ceiling, fixed local decimal precision, and synthetic-only interpretation boundary. AC-05 must assert the existing `AdapterError("EMPTY_EXPECTED_DOMAIN")` and the composed three-row `ExecutionError("SINGULAR_DESIGN")`, with no partial envelope or bypass. AC-01–AC-30 must be non-skipped, and all upstream regressions and project/governance checks must pass. Independently review actual source/test diff, frozen normative behavior, static import/IO surface, README claims, acceptance evidence, worktree/stash/database, and live remote; do not accept the historical candidate report alone.

Run from this worktree, with `PYTHONPATH=<worktree>/src` and `D:/量化分析-m4a2i/.venv/Scripts/python.exe`, recording each exit code:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'
& $py -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py
& $py -m pytest -q -p no:cacheprovider tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_analysis_matrix.py tests/test_m4_bounded_execution.py tests/test_m4b_hypothesis_registry.py
& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& $py -m ruff check src tests
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
git ls-remote origin refs/heads/main
gh pr list --state open --json number,title,headRefOid,baseRefName,url
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
git diff --name-only origin/main -- docs reports config data events .github pyproject.toml
git hash-object docs/m4_synthetic_end_to_end_pipeline_design_v1.md docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4b_hypothesis_registry_design_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
```

Also verify exact changed-path whitelist, no skipped/xfail AC cases, public symbols and error codes, forbidden imports/IO, Markdown UTF-8/newlines/links/whitespace/conflict markers, and protected baselines. A sandbox `tmp_path` setup error is a failure until rerun with a writable basetemp.

## Stop, commit and release rules

Stop and report if conformance needs a non-whitelisted upstream change, any protected baseline drifts, any AC still conflicts with corrected norms, a safety test would need weakening, or a required test fails. Create scoped local commits after independent validation; never `git add -A`. A PASS permits push and PR. Because the user explicitly authorized continuation after the prior AC-05 gate, normal merge is permitted only after exact PR HEAD/base review and all required CI succeeds. Do not start another project stage after this implementation merge. Final evidence packet and one verdict (`PASS`, `CHANGES_REQUIRED`, or `BLOCKED`) follow AGENTS.md.
