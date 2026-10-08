# M4 paired synthetic input diagnostic comparison

## Objective
Root directly implements research prepare-compare for two caller-supplied
synthetic input files against one verified plan and one unchanged declared domain.
No DSH/delegation. User continuation authorizes this bounded engineering stage.

## Verified baseline
origin/live codex/m4-preparation-diagnostics:
748b782438ce25fbaab086eb2ddc48eb44a99958; PR73 OPEN/MERGEABLE,
38checksSUCCESS/2pending at last check, not claimed fully accepted.
Dependency chain73->71->70->69->68 remains unmerged; main8d0fb4d unchanged.
Fresh clean codex/m4-preparation-comparison at748b782. Before code snapshot
tmp/preparation-comparison/baseline.json captured40worktrees,27dirty file hashes
using NUL-delimited Git filename lists (including both formerly omitted paths),
427protected hashes, localmain966206f/stashcb568efd, databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Primary remains feat/m2-value-assessment-mvp@3679b1b with original user changes.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_compare,research_entry}.py,
tests/test_preparation_compare.py. Ignored validation artifacts allowed.

## Forbidden scope
Existing tests and all original preparation/diagnostic/verifier/adapter/compiler/
matrix/executor/registry/schema/method/gates, protected data/reports/CI; acquisition,
real research/holdout/statistics, source or digest repair, input writes, foreign
worktrees, user dirt/stash/databases, main/force push, merges and destructive cleanup.

## Required behavior
prepare-compare (--package DIR | --archive ZIP) --left-inputs JSON
--right-inputs JSON [--json]. Reuse unchanged complete build_report for each
distinct input path; same path reuses one loaded report. Each distinct side
verifies the plan independently before its once-read bound input. Fail closed
if original plan identity differs between reads or declared domain digests,
audit dates or role order differ; never compare a changed denominator as repair.
Use unchanged diagnostic projector with all roles/dates, no gaps filtering.
Retain both original quality reports, identities and truthful read/execution
boundaries. Deterministic date/role changes preserve complete original diagnostic
metadata, no raw observations/matrix cells. Validity transitions and changed
metadata are audit facts only, not effects, real provenance or research readiness.
Separate byte equality from adapter input-digest equality; formatting/reordering
equivalence is not a semantic edit. Metadata-only or outcome-evidence change does
not mean a gap repair. All counts are audit cell counts; unchanged cells explicit.
Markdown/JSON display both qualities/identities/boundaries, escape user data.
Invalid/corrupt/unsupported input/flags produce sanitized stderr/code2/no stdout.
No output option, writes, quality repair, ranking, execution or registry transition.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_compare.py tests/test_preparation_diagnostics.py
python -m ruff check src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_compare.py
git diff --check
Public directory/ZIP comparison CLI demo, captured source hash checks, final
protection verification and independently inspected committed diff/Goal/evidence.
Cases: missing/PIT/null diagnostics to valid and reversed; exact original sides,
global denominator and metadata-only changes, format/order/same path equivalence;
domain/date removal rejection, inter-read plan drift, stale digest/corrupt plan/
invalid flags failure; per-side once-read and immutable source/offline guards.

## Acceptance criteria
Seven-file scoped implementation, local targeted tests/Ruff/diff/demo pass.
All captured39foreign tree identities/statuses/27dirty hashes,427protected hashes,
stash/local-main/database unchanged; owned clean/local-origin-live synchronized.
No local full suite claim; hosted final-head checks reported separately.

## Stop conditions
Stop failed gates, dependency/main drift, unexpected concurrent changes,
scope/protection drift. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-preparation-diagnostics.
Explicit chain73->71->70->69->68, no merge/main push/force push.
Final PASS/CHANGES_REQUIRED/BLOCKED packet distinguishes local from hosted evidence.
