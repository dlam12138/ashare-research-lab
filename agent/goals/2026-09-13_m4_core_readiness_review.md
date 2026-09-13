# Goal: M4 core readiness review

Date: 2026-09-13. Reviewer: Codex.

## Objective and verified baseline

Independently assess what M4-A and M4-B can do on the current main branch, what the North-Star v2 acceptance criteria still require, and the smallest safe next decision. This is a read-only technical review with a committed evidence report, not authorization to execute a real hypothesis.

- Base: `origin/main` at `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`, merged PR #19; `main` and `origin/main` matched after fetch.
- Review worktree: `D:/量化分析-m4-core-readiness-review`, branch `codex/m4-core-readiness-review`, created directly from that base.
- Open PRs: none at review start (`gh pr list --state open`).
- Protected original M2 worktree HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash ref: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed and forbidden scope

Allowed: read tracked source, tests, North-Star, contracts, goals and acceptance files; run offline tests and static checks; add this Goal and `acceptance/2026-09-13_m4_core_readiness_review.md`; commit only those two files locally.

Forbidden: change source, tests, README, dependencies, reports, frozen research artifacts, data, runtime or other worktrees; connect to the database, acquire real data or literature, access holdout, run real hypotheses, create candidates, push, open a PR or merge. Preserve pre-existing M2 changes, ignored artifacts and stash.

## Required behavior and tests

The report must distinguish merged capability from historical preflight status, check the M4-A and M4-B North-Star acceptance criteria against actual code/tests, document missing evidence and authorization gates, and recommend one bounded next task without silently starting it. A PASS verdict means this *review* is sound, not that M4 is complete.

Run the full offline pytest suite from the clean main-equivalent worktree, plus Ruff on the relevant M4 modules and tests. Inspect representative source/test entry points and report exact commands and observed results. Check Markdown hygiene and relative links. Do not change tests to obtain a pass.

## Exact validation commands

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/mechanism/registry src/ashare_research/mechanism/pipeline tests/test_m4b_hypothesis_registry.py tests/test_m4_synthetic_pipeline_orchestrator.py
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
```

## Acceptance criteria, stop conditions, and delivery

Only the two whitelisted Markdown files differ from the base. The report cites tracked evidence, gives a precise readiness verdict and remaining gates, records test failures honestly, and proves that protected branch, stash and database identities are unchanged. Stop if the base or protected identities drift, if review needs real outcome access, or if a required claim cannot be supported without changing code or frozen contracts.

Commit the two reviewed files locally on this branch after validation. Do not push, open a PR, merge, or start the recommended next task. Final task verdict must be exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.
