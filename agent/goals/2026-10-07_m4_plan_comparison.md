# M4 compile-only hypothesis comparison

## Objective
Root agent alone, no DSH or delegation. Extend research plan with optional
--compare-with JSON to review canonical hypothesis changes before execution.

## Verified baseline
origin/main and live main: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Owned branch codex/m4-plan-comparison starts clean at that commit.
Primary feat/m2-value-assessment-mvp HEAD3679b1bac7a1634c6452784a4d8f6d139966f222,
existing dirty/untracked files, stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f,
database SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
protected by local snapshot. Frozen reports/config/fixtures hashed; foreign
worktree heads recorded. Snapshot is ignored tmp/plan-comparison/baseline.json.

## Allowed scope
This Goal, matching acceptance and work record, README.md,
src/ashare_research/tools/research_plan.py and research_entry.py,
new tests/test_research_plan_comparison.py. Ignored validation evidence.

## Forbidden scope
Existing tests, mechanism compilers/contracts/registry/executors, frozen data,
databases, acquisition, real research, holdout, user changes, foreign worktrees,
quality/method gates, direct main push, force push, cleanup or merging.

## Required behavior
Reuse build_report once per distinct input path and retain full original reports.
Compare canonical config, not compiler-derived duplicate fields. Sorted JSON
pointer paths; lists compared atomically to preserve order semantics; explicit
before/after presence distinguishes absent from null. Equal canonical input
classified separately from equal byte SHA; never describe an edit as an effect.
Original canonical contract/plan/source digests retained for both sides.
Fail closed with sanitized errors and no partial stdout. Existing single-plan
behavior unchanged. Markdown and JSON expose all changes and false boundaries.

## Required tests and exact validation commands
With PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan.py tests/test_research_plan_comparison.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_entry.py tests/test_research_plan_comparison.py
git diff --check
Public CLI example: python -m ashare_research.cli research plan --hypothesis
docs/examples/m4_hypothesis.json --compare-with docs/examples/m4_hypothesis.json --json

## Acceptance criteria
Semantic edits, reordered controls, optional holdout additions, same source and
formatting-only changes classified correctly; original reports/digests intact.
Invalid second input produces only error; no execution/network/database calls.
New and affected existing tests pass; protected hashes and primary state unchanged.

## Stop conditions
Stop on unexpected concurrent changes, failed validation, scope expansion or
protected-state drift. No next stage, real execution or automatic merge.

## Commit and push requirements
Scoped commit and normal feature-branch push/PR under prior delivery workflow.
Current user governance requires explicit merge authorization: leave PR unmerged.
Never push main. Report remote/CI state without treating pending checks as success.
