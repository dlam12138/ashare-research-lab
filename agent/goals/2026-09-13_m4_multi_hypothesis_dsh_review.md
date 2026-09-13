# Goal: DSH audit of M4 multi-hypothesis synthetic acceptance

Date: 2026-09-13. Executor: DeepSeek Harness (`dsh --profile headless`). Independent reviewer: Codex. The user explicitly selected DSH after the local Luna delivery; this overrides the repository's default Luna routing for this follow-up.

## Objective and verified baseline

Use DSH to independently challenge the local multi-hypothesis acceptance before any remote CI. Check that both requests are genuinely legal and structurally distinct, the fingerprints bind only intended pre-execution identities, the negative case fails at the public entry, and the new test is portable to Ubuntu/Windows. Correct an actual in-scope defect if found; otherwise deliver a documented DSH audit. This is not a rerun of the completed implementation stage and does not authorize real research.

- Worktree: `D:/量化分析-m4-multi-hypothesis-acceptance`, branch `codex/m4-multi-hypothesis-acceptance`, clean HEAD `1e3a514b61ece0f134011c4b84a60ca1931e31cc`.
- Base main: local `main`, `origin/main` and live GitHub `main` all `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`; no open PR. The branch is local only, ahead of main by two commits and not pushed.
- Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Prior task contract: [local synthetic acceptance Goal](2026-09-13_m4_multi_hypothesis_synthetic_acceptance.md). Its local `PASS` does not claim actual Ubuntu CI execution.

## Allowed scope and forbidden scope

Allowed: DSH reads current code/test/contracts and runs offline checks. It may update only `tests/test_m4_multi_hypothesis_portability.py` when it finds a concrete defect, plus `agent/record/2026-09-13_02_m4-multi-hypothesis-dsh-review.md` and `acceptance/2026-09-13_m4_multi_hypothesis_dsh_review.md`. This Goal is Codex-owned and committed before DSH runs. The record is created before DSH runs.

Forbidden: `src/**`, existing other tests, `docs/**`, `reports/**`, `config/**`, `data/**`, `events/**`, `.github/**`, `README.md`, dependencies, North-Star, default database contents, real inputs, provider/literature/holdout, other worktrees, stash or ignored artifacts. Do not weaken a test, rewrite an earlier commit, push, open a PR, merge or delegate recursively. Do not represent a DSH sandbox failure as a product failure or a skipped test as a pass.

## Required behavior, tests and acceptance criteria

DSH must inspect the actual test and public pipeline/adapter/compiler interfaces, not merely repeat the prior summary. Audit at least: two distinct legal configurations; exact identity rebinding; condition/control/bootstrap projections; negative swap error code; fixed fingerprint projection and its lack of numeric/runtime fields; child interpreter using `sys.executable`; CWD/process behavior; no real inputs or authorization claims. Examine the existing Ubuntu/Windows CI workflow to confirm the test will be discovered when a branch is pushed, but do not claim it has run on this branch.

If there is an actual defect, make the smallest whitelist test correction and rerun focused and upstream regression. If there is no defect, do not change the test merely for style or mirror its implementation. Record each command, exit code and any first failure. Report limits honestly: local Windows and child-process evidence cannot close actual cross-OS CI. Acceptance is a sound DSH audit with only whitelisted diffs, test evidence, clean final worktree, unchanged protected identities and clear remote-state boundary.

Exact commands from this worktree:

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

The nine-file regression need run in DSH only if the test changes; otherwise the focused test, Ruff and direct audit suffice, using the previous 370-pass run as historical evidence. Codex independently reruns the focused test after any correction, checks diff/commit/worktrees/stash/remote/database and returns exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop and delivery rules

Stop on main drift, protected hash change, an out-of-scope fix, frozen-contract conflict, real-data need, inaccessible DSH profile, or repeated sandbox failures that prevent meaningful verification. DSH may commit one scoped local delivery if Git metadata is writable; if not, leave changes uncommitted for Codex and report the precise error. No push, PR or merge. This follow-up does not start real-data adapter design or declare M4 complete.
