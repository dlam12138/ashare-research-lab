# M4 multi-hypothesis CI submission record

Date: 2026-09-14. Contract: [CI submission Goal](../goals/2026-09-14_m4_multi_hypothesis_ci_submission.md). Executor for bounded preflight: DSH. Reviewer and Git operator: Codex.

## Baseline and scope

Starting branch `codex/m4-multi-hypothesis-acceptance@7131d170dc49c7d0b5819d72155f147c1be9f792`, based on `main` and `origin/main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`. Live GitHub `main` was the same, with no open PR or remote branch for this work. Starting worktree was clean. Original M2 worktree HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222` and stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` were protected. Default database SHA256 was `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

This stage adds only the Goal, this record and the [acceptance file](../../acceptance/2026-09-14_m4_multi_hypothesis_ci_submission.md). It changes no product code, test, CI workflow, historical document, data or protected artifact. Earlier ignored `tmp/dsh-temp/tmpqb9tc2rv` remains untouched.

## DSH preflight

Codex invoked `dsh --profile headless` with the exact read-only scope in the Goal. DSH exited 0 and returned **PASS for preflight**, not for CI. It independently verified the branch/HEAD, local and live main, stash, M2 HEAD and database hash; the committed branch diff against `origin/main` consists of eight added files (seven documents and one new test), with no `src/**` or CI edits. It inspected the actual test, contract/plan/dataset/matrix identity functions and workflow. The workflow triggers on feature-branch push and PR, runs `pytest -q` on Ubuntu and Windows, and collects `tests/test_m4_multi_hypothesis_portability.py`. DSH ran read-only Ruff with `--no-cache` on that file: exit 0. It found no pre-submit blocker. DSH did not run pytest, write files, create temp directories, commit, push or open a PR.

DSH's direct `git ls-remote` failed with `SEC_E_NO_CREDENTIALS`, so it used authenticated `gh api`/`gh pr list` to verify live remote state. Main's prior Stage 2G run `34743804486` succeeded, but that run predates this branch and is not cross-OS evidence for the new test. The old ignored DSH temp directory was left alone.

## Codex local validation before submission

From this worktree with `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`:

| Command | Result |
| --- | --- |
| `D:/量化分析-m4a2i/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py` | Exit 0; `3 passed in 10.99s` |
| `D:/量化分析-m4a2i/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | Exit 0; `370 passed in 81.66s` |
| `D:/量化分析-m4a2i/.venv/Scripts/python.exe -m ruff check tests/test_m4_multi_hypothesis_portability.py` | Exit 0; `All checks passed!` |
| `git diff --check`; `git diff --cached --check` | Both exit 0; no output |

These are local Windows results. The earlier DSH sandbox interruption remains in its historical record. The pre-execution fingerprint has four contract/plan/dataset/matrix identities and excludes execution runtime fields; passing local tests does not prove Ubuntu execution or complete-envelope cross-OS identity.

## Submission evidence boundary

This record is committed before the remote CI run. The exact pushed SHA, PR URL, check run IDs, per-OS conclusions, final protection review and final verdict are recorded in the PR body and Codex's final evidence packet after CI finishes. No later documentation-only commit is made merely to embed the CI result in this branch, because that would change the SHA requiring CI verification again. No merge or next stage is authorized here.
