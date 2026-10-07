# M4 synthetic preparation diagnostics by role

## Objective
Root directly implements --summary [--role ID ...] [--gaps-only] for research
prepare so users can locate supplied synthetic input defects before statistics.
No DSH or delegation. User continuation authorizes this bounded engineering stage.

## Verified baseline
Dependency origin/live codex/m4-synthetic-prepare:
045d6b3cb272dc239368ec54cec5ef95579e91b1. PR71 OPEN/MERGEABLE, 42 checks SUCCESS.
It depends on PR70/69/68; main is 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Fresh codex/m4-preparation-diagnostics starts clean at dependency045d6b3.
Primary HEAD3679b1bac7a1634c6452784a4d8f6d139966f222, original dirty files,
stashcb568efd7eaa6f0fca4b3bb5a1e2200b9341985f and DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 captured.
Ignored baseline snapshot records 39 worktrees including statuses and 25 dirty
file hashes, local main and 427 protected reports/config/evidence/events/fixtures.

## Allowed scope
Eight files: this Goal, matching acceptance and record, README.md,
src/ashare_research/tools/{synthetic_prepare,preparation_diagnostics,research_entry}.py,
tests/test_preparation_diagnostics.py. Ignored evidence allowed.

## Forbidden scope
Existing tests; original build_report/read-input function, verifiers, compilers,
adapter/matrix/executor/registry/policy/schema, fixtures/config/reports/evidence/
events/CI; source acquisition, real data/holdout, statistics, quality repair,
user changes, foreign worktrees/stash/databases, main/force push/merge/cleanup.

## Required behavior
Use unchanged complete plan verification and synthetic preparation exactly once
before projection; never bypass quality/integrity gates or reread sources.
Retain original global quality, source/input/contract/plan/dataset/matrix identities
and truthful read/execution boundaries. Display roles in original adapter order;
repeat role selectors deduplicate, unknown roles reject. Only --summary permits
--role/--gaps-only; malformed role and invalid combinations reject before reads.
Role diagnostic counts cover all original audit dates; gap filtering affects
detail cells only, never global denominator/rejected dates or preparation status.
No-match gaps explicitly distinguished from invalid selection. Detail rows retain
date, role, valid, reasons, original available_on/source_record_id/evidence_digest;
no observation values or matrix cells in summary. Counters count audit diagnostics,
not statistical estimates. Markdown escapes user text; JSON deterministic, no
host paths/timestamps. No flags preserves original report and renderer unchanged.
Fail closed with sanitized errors and empty stdout; all legacy commands preserved.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_diagnostics.py tests/test_synthetic_prepare.py
python -m ruff check src/ashare_research/tools/preparation_diagnostics.py src/ashare_research/tools/synthetic_prepare.py src/ashare_research/tools/research_entry.py tests/test_preparation_diagnostics.py
git diff --check
Public CLI directory/ZIP --summary --json and role/gap Markdown demos retained.
Cases: exact identities/global quality/role counts and original diagnostic fields;
ready/quality-rejected/empty/known-no-gaps; role dedup/order, malformed/unknown,
invalid flags before IO; corrupt plan/input failure with no stdout; once-read
preparation, immutable sources, no network/database/pipeline/execution.

## Acceptance criteria
Eight-file scoped diff, meaningful targeted tests/Ruff/diff/demo pass.
All captured foreign worktree heads/status/dirty hashes, stash, primary database
and427protected hashes unchanged; owned clean and local/origin/live tip equal.
No full local suite claim; actual hosted final-head checks reported separately.

## Stop conditions
Stop failed gates, unexpected concurrent edits, dependency/base/protection drift
or scope expansion. No automatic merge, following stage or research execution.

## Commit and push requirements
Normal scoped commit/push and stacked PR against codex/m4-synthetic-prepare.
Explicit dependency PR71 ->70 ->69 ->68; no main push or automatic merge.
Final verdict PASS/CHANGES_REQUIRED/BLOCKED with exact evidence and pending CI limits.
