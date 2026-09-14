# Goal: M4 multi-hypothesis cross-OS CI submission

Date: 2026-09-14. Executor for bounded preflight: DSH (`dsh --profile headless`). Responsible reviewer and Git operator: Codex.

## Objective and verified baseline

Advance the locally accepted two-hypothesis synthetic portability check to an ordinary review PR so the existing Ubuntu/Windows CI can run on the exact branch head. Inspect the resulting checks and record what they actually prove. Do not merge or start real-data research.

- Worktree: `D:/量化分析-m4-multi-hypothesis-acceptance`, branch `codex/m4-multi-hypothesis-acceptance`, clean starting HEAD `7131d170dc49c7d0b5819d72155f147c1be9f792`.
- Local `main`, `origin/main`, and live remote `main`: `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`; no open PR and no remote branch for this work.
- Original M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; protected stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Local synthetic acceptance is `PASS`; the DSH resumed local audit is a limited `PASS`. Neither claims actual CI on this branch.

## Allowed and forbidden scope

Allowed: add this Goal, one execution record and one acceptance file; run DSH as a read-only preflight; run the focused and nine-file tests and Ruff on the host; commit only these three documents; push this branch; open one PR to `main`; inspect CI and record exact check evidence. Fix a concrete CI defect only through a new scoped contract, never by weakening tests.

Forbidden: changes to product code, existing tests, CI, dependencies, frozen contracts, real data, default database, other worktrees, stash or ignored artifacts. No real hypothesis, provider, holdout, claim of A-share effect, merge, force-push or direct push to `main`. DSH must not create temporary directories, modify files, commit, push or open the PR.

## Required behavior and tests

DSH independently inspects the existing branch diff and CI workflow to confirm the new test is collected by the Ubuntu/Windows full `pytest -q`, checks the fixed fingerprint projection, and reports blockers to submission without editing. Codex independently reviews DSH findings, runs the focused three-test command and nine-file regression, Ruff, Git hygiene, and protected-state checks. The PR description must distinguish local evidence from checks that have actually run on the pushed SHA. A green CI job establishes the test passed on that OS; it does not establish full-envelope byte identity or a real research result.

Exact local validation from this worktree, with `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`:

```powershell
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_m4_multi_hypothesis_portability.py
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD main origin/main refs/stash
git worktree list --porcelain
git stash list
git ls-remote origin refs/heads/main refs/heads/codex/m4-multi-hypothesis-acceptance
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
```

After push, inspect the PR's exact head SHA and per-OS check conclusions through `gh pr checks` and GitHub API. Pre-submit evidence goes in the committed record and acceptance file. The final CI evidence for the exact pushed SHA goes in the PR body and Codex's final evidence packet; do not append it to the branch and create an endless new-SHA CI cycle. Check new Markdown as strict UTF-8, final newline, whitespace, links and conflict markers; `git diff --check` alone does not cover untracked files.

## Acceptance, stop and delivery

Accept only if branch scope is clean, protected identities remain intact, local checks pass, the remote branch/PR points at the exact reviewed commit, and required Ubuntu and Windows CI jobs pass on it. If checks are still running, report `BLOCKED` for cross-OS closure and leave the PR open; if a check fails, report `CHANGES_REQUIRED` with its actual failure. Do not call a skipped test passed. Final verdict exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

Stop on baseline drift, out-of-scope changes, protection mismatch, DSH failure preventing meaningful preflight, failed local validation, or CI requiring a product/test/CI change. A commit and push to this feature branch plus one PR are required only after local review passes. Never merge or start the next stage automatically.
