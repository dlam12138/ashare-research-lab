# Goal: M4 dataset adapter design

## Objective and verified baseline
User explicitly approved squash merging PR #9 and designing the next dataset adapter.
PR #9 head 13a441ffc0deedc6cc49001d3009e8aaa5442628 had 42 successful checks;
merged with an exact-head guard as bab24f981fef9336b84280544ce709702b9df116.
The merge tree equals the approved head. New isolated worktree:
D:/量化分析-m4-adapter-design, branch codex/m4-dataset-adapter-design,
base origin/main bab24f981fef9336b84280544ce709702b9df116, initially clean.

## Allowed scope and required behavior
Design only: one normative adapter specification, synthetic acceptance scenarios,
this Goal, work record and acceptance. Explain contract/plan/input binding, immutable
role data, explicit date domain, PIT/identity provenance, coverage denominator,
missingness/duplicate policy, content identity, failure states and M3 reuse limits.
Freeze a bounded synthetic implementation proposal; distinguish design from implementation.

## Forbidden scope and protection
No adapter implementation, executor, real data reads, providers, statistics, holdout
execution, M4-B, dependencies, workflows, existing test changes, A.1/A.2 changes,
North-Star changes or protected hash updates. Do not merge PR #10 or this design.
Preserve all original worktrees and ignored artifacts. Original M2 HEAD 3679b1b;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; original DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Required tests and exact validation commands
From this design worktree use the existing interpreter with explicit source precedence:
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`.
`& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py`
`git diff --check` and `git diff --cached --check`.
Manual design audit against actual A.1/A.2/M3 source; validate local Markdown links
and synthetic expected coverage arithmetic; verify tracked changes are exactly the
five new documents. Inspect main CI at the merge commit, remote refs, stash and DB hash.
Full suite need not be repeated locally for five additive documents; inspect main CI.

## Acceptance, stop and delivery
Design must be implementable without hidden provider choices or silently changed
denominators. Every ambiguous or unsupported binding fails closed; eligibility never
authorizes execution. Local checks and main CI must pass; record actual evidence.
Create one scoped local commit after review. Do not push: user authorized merge and
design, not publication of the new design branch. Stop at design delivery; implementation
and any further merge require explicit authorization. Report PASS / CHANGES_REQUIRED / BLOCKED.
