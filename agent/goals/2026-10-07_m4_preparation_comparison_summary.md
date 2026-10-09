# M4 preparation comparison role summary

## Objective
Root directly adds a focused comparison summary to prepare-compare and
prepare-delivery-compare: verify completely first, then show per-role transition
counts and role-filtered changes. User continuation authorizes this bounded
engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-preparation-delivery-diagnostics:
34572a8286c5eb2670879e4138e263983bc554db. PR79 OPEN/MERGEABLE;
19SUCCESS/16pending at initial query, not a complete hosted gate.
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-preparation-comparison-summary at34572a8.
Before code tmp/preparation-comparison-summary/baseline.json verified46worktrees/
27dirty hashes/427protected hashes against previous foreign states,
primary3679b1b/localmain966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Eight files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_compare,preparation_delivery_compare,research_entry}.py,
tests/test_preparation_comparison_summary.py. Ignored demo/validation artifacts allowed.
Only cli main may change in the two comparison modules; all existing comparison
calculations, verifiers, receipts and default renderers stay byte/AST unchanged.

## Forbidden scope
Existing tests, synthetic preparation, diagnostic projector, plan/preparation
package and archive verifiers, comparison calculations, schemas/compilers/
adapter/matrix/executor/registry/quality gates/CI/protected reports/data/foreign
worktrees/stash/DB/runtime. No acquisition, real research/statistics/holdout,
input/digest repair, extraction, writes, cleanup/overwrite, main/force push,
merges or automatic following stage.

## Required behavior
Both comparison commands accept --summary and repeatable --role ID.
Summary is a pure projection of the captured, fully verified comparison report:
raw-input compare reads plan/inputs through the original build once per side;
delivery compare verifies each distinct side through the original directory/ZIP
verifier once. No rereads, no extra IO, no extraction, no writes, no new
calculation of cell comparisons.
Role pattern validates before IO; --role without --summary rejects
INVALID_ARGUMENTS before IO; well-formed absent roles fail UNKNOWN_ROLE only
after the complete comparison/verification ran.
Summary preserves original classification, both sides' status/quality/identity,
global audit counts exactly, boundary and role counts over all dates; filters
affect only the selected role rows and displayed changes. Per-role transition
tallies derive from the captured changes and role diagnostics; any unreconciled
role set, transition, or totals versus global counts fails closed with
COMPARISON_SUMMARY_MISMATCH.
New schema m4_paired_synthetic_preparation_diagnostics_summary_v1; Markdown is a
compact Chinese table view; no raw observations, matrix cells, effects, repair,
provenance/sealing/readiness/execution claims. Without --summary original JSON
and default Markdown stay byte-identical. Sanitized errors/code2/no partial
stdout. Offline, no database/services/executor; sources immutable.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_comparison_summary.py tests/test_preparation_compare.py tests/test_preparation_delivery_compare.py tests/test_preparation_delivery_diagnostics.py tests/test_preparation_package.py tests/test_preparation_archive.py
python -m ruff check src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/preparation_delivery_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_comparison_summary.py
git diff --check
python tmp/preparation-comparison-summary/calculation_review.py
python tmp/preparation-comparison-summary/demo.py
python tmp/preparation-comparison-summary/verify_protections.py
Cases: raw and delivery summary exact projection (dir/zip/all transports),
repeated/reordered roles, no-change role NO_MATCHING_CHANGES, global counts/
quality/identity/boundary preserved, legacy outputs unchanged, once-read
snapshot handoff, unknown role after complete comparison, invalid flags and
bad patterns before IO, invariant guard and sanitized CLI failure, offline/
no-extraction/no-write guards, actual Windows junction rejection.

## Acceptance criteria
Eight-file scope; meaningful tests/Ruff/diff/demo/compatibility pass.
45foreign registrations/HEAD/branches/statuses,27dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; untouched modules byte-equal to base and
only cli main changed in touched comparison modules (AST review). Owned clean;
feature/dependency local/origin/live agree. No full local suite claim;
exact-head hosted pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-preparation-delivery-diagnostics.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted state.
