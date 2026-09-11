# Work record: M4 dataset adapter design

Date: 2026-09-07. Agent: Codex. Module: mechanism validation.
Goal: [task contract](../goals/2026-09-07_m4_dataset_adapter_design.md).

## Start and actual actions
Rechecked original dirty M2 branch/HEAD, worktrees, remote refs, stash and default DB.
Read AGENTS.md, agent agreement, record index, recent records, A.2 design/sufficiency/
reuse reports, A.1 types and M3 dataset/gates. PR #9 was OPEN/CLEAN with the approved
head and 42 successful checks. Squash merged using --match-head-commit, fetched origin,
verified exact tree equality, then created the isolated design branch from bab24f9.
No original worktree, stash or database was changed. PR #10 remains outside scope.

## Plan and decisions
Write the contract before design. Use an explicit frozen source contract alongside the
plan because the plan does not project all target/outcome identity fields. Inputs must
carry an independent expected-date domain so omitted rows cannot improve coverage.
First implementation proposal will accept synthetic in-memory bundles only. Reuse M3
validation semantics, not its case-specific dates, columns or execution gates.
No real dataset, return computation, hypothesis threshold or statistical outcome is used.
Finish with source/protection tests, document checks, main CI review and a local commit.

## Verification and delivery
Completed the specification and future synthetic acceptance matrix, then reviewed against
the actual A.1 enums and A.2 source. Corrected draft policy names to
SYNTHETIC_FIXED_UNIVERSE and EXPLICIT_PIT before validation. Added explicit treatment
of unsupported transforms, independent date domain, source conflicts and rehashed plans.
One patch-context mismatch made no changes; reapplied with exact context successfully.

Ran the Goal's focused pytest command with this checkout's src first on PYTHONPATH:
132 passed in 0.82s. Printed imported compiler path to verify checkout isolation.
Inline Python validated five UTF-8 documents, seven local links, code fences, actual
policy spellings and exact 2/3 coverage comparisons. Staged/unstaged diff checks pass.
Only the five new Markdown files are staged; all previous tracked bytes equal base.

Main merge CI completed with seven successful workflows and 21/21 successful checks.
Read run 34134084010 logs: Linux 2487 passed/3 skipped/3 warnings; Windows
2487 passed/3 skipped/2 warnings. Cross-platform identity comparison succeeded.
This differs from prior PR counts; recorded actual main results without modifying tests.

Rechecked original M2 status/HEAD, all worktrees, stash and default DB SHA256: unchanged.
origin/main and live main remain bab24f9; original local main remains 9e016e7.
Final delivery: one local design commit, no push, no new PR or implementation. Final
commit SHA is reported outside its own content. See linked Goal and
[acceptance](../../acceptance/2026-09-07_m4_dataset_adapter_design.md) for exact commands,
scope, file list, limits and CI link. Status: completed; verdict PASS for design only.
