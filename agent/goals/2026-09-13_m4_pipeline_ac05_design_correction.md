# Goal: correct M4 pipeline AC-05 minimum-domain outcome

Date: 2026-09-13. Executor and independent reviewer: Codex.

## Objective and verified baseline

Resolve the contradiction between frozen AC-05 and the existing S6 rank gate without changing pipeline capability. Start from clean `codex/m4-ac05-design-correction` at `291b733d710fcccae9436f4d93215988af06db5a` (local/origin/live `main`). The preserved implementation is `codex/m4-synthetic-pipeline-resume@f5f419e0377cf74925bd8bbff27f8a2f1c513ffd`, locally unpushed and clean; its independent acceptance verdict is `CHANGES_REQUIRED`. Its three-row AC-05 probe reaches the frozen estimator and raises `ExecutionError("SINGULAR_DESIGN")`. The design already lists that error as composed-reachable at S6 (§8.5.1); AC-05 currently allows only `AdapterError` or `MatrixError`. Original M2 HEAD, stash, database SHA256, and protected design blobs must be rechecked before acceptance.

## Allowed and forbidden scope

Allowed: this Goal, `docs/m4_synthetic_end_to_end_pipeline_design_v1.md`, `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md`, one new task record, and one new acceptance record. Edit only the AC-05 outcome and the directly related S6 error explanation/cross-reference. Preserve all other normative obligations. Forbidden: `src/**`, `tests/**`, README, other docs/records/acceptance, schemas, public APIs, error codes, execution gates, protected blobs, real-data/holdout authorization, database, stash, and other worktrees. Do not rewrite a test or weaken rank/quality rejection. No direct push to `main`, force push, or destructive cleanup.

## Required behavior and acceptance criteria

State the stage-specific result: malformed/empty domain fails in the adapter; matrix failure retains `MatrixError`; a successfully materialized matrix can fail the frozen S6 full-rank gate with the existing `ExecutionError("SINGULAR_DESIGN")`. Require stable first error and no partial envelope. Explain that three observations do not guarantee full rank or a valid estimate. Keep S0–S8, V1–V6, 20 public exports, 14 pipeline errors, and authorization boundaries unchanged. Accept only if the documentation is internally consistent, the correction follows actual upstream code and the preserved probe, exact changed paths stay within this whitelist, all validation succeeds, and protected state remains intact.

## Required tests and exact validation commands

From this worktree, set `PYTHONPATH` to its `src`, use `D:/量化分析-m4a2i/.venv/Scripts/python.exe`, and run separately:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$py = 'D:/量化分析-m4a2i/.venv/Scripts/python.exe'
& $py -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& $py -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py
& $py -m ruff check src tests
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/main
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
git diff --name-only origin/main -- src tests reports config data events .github pyproject.toml README.md
git hash-object docs/m4_bounded_execution_and_evidence_design_v1.md docs/m4b_hypothesis_registry_design_v1.md reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
```

Also inspect the exact changed-path whitelist; UTF-8, final newline, whitespace/conflict markers, links, and AC-05 cross-references. Record each command's exit code and do not treat a test setup error as a pass.

## Stop and delivery conditions

Stop if correction requires upstream code/test changes, weakens a protective gate, expands capability, or a protected baseline drifts. Create scoped local commit(s) on this branch only after validation. Do not merge or start implementation resumption automatically. Push/PR require a separate final review decision. Report the complete AGENTS.md evidence packet and exactly one verdict: `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.
