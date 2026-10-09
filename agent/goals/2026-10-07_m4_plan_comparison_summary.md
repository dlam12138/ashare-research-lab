# M4 plan comparison section summary

## Objective
Root directly adds a focused section summary to research plan-compare: verify
both plans completely first, then project the captured comparison into
per-section change counts and section-filtered change rows. User continuation
authorizes this bounded engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-preparation-comparison-summary:
e427e5a1e3630063fc8abcdb4e7d2f47ff3aa8db. PR80 OPEN/MERGEABLE;
29SUCCESS/9pending at initial query, not a complete hosted gate.
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain80->79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-plan-comparison-summary at e427e5a.
Before code tmp/plan-comparison-summary/baseline.json verified47worktrees/
46foreign states/27dirty hashes/427protected hashes against the previous
baseline, primary3679b1b/localmain966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{research_plan_compare,research_entry}.py,
tests/test_research_plan_compare_summary.py. Ignored demo/validation artifacts
allowed. Only cli main may change in research_plan_compare.py; all existing
comparison loading, diffing, rendering and error handling stay AST unchanged.

## Forbidden scope
Existing tests, hypothesis config/contract compiler/analysis plan, plan
package/archive verifiers, synthetic preparation and all preparation tools,
schemas/adapter/matrix/executor/registry/quality gates/CI/protected reports/
data/foreign worktrees/stash/DB/runtime. No acquisition, real research/
statistics/holdout, digest repair, extraction, writes, cleanup/overwrite,
main/force push, merges or automatic following stage.

## Required behavior
plan-compare accepts --summary and repeatable --section ID where IDs are the
existing comparison sections config/contract/plan. The summary is a pure
projection of the captured, fully verified comparison report: both sides are
still loaded exactly once per side through the original directory/ZIP verifier
(identical paths remain two independent loads, as today); no rereads, no extra
IO, no extraction, no writes, no new diff computation.
--section without --summary rejects INVALID_ARGUMENTS before IO; an unknown or
malformed section rejects INVALID_SECTION before IO; repeated sections are
deduplicated in the canonical section order. The summary preserves both
identities, equality flags, canonical_content_equal, change_count, the global
section_change_counts, boundary and notes; filters affect only displayed change
rows, and a selected section with no change reports NO_MATCHING_CHANGES.
Every change row's section must be a known section and the recomputed per-section
counts and total must exactly equal the captured global counts or the projection
fails closed with COMPARISON_SUMMARY_MISMATCH.
New schema m4_verified_compile_only_plan_comparison_summary_v1; Markdown is a
compact Chinese view; no plan-superiority, provenance, sealing, readiness or
execution claim. Without --summary original JSON and default Markdown stay
byte-identical. Sanitized errors/code2/no partial stdout. Offline, no database/
services/executor; sources immutable.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan_compare_summary.py tests/test_research_plan_compare.py tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan_compare.py src/ashare_research/tools/research_entry.py tests/test_research_plan_compare_summary.py
git diff --check
python tmp/plan-comparison-summary/calculation_review.py
python tmp/plan-comparison-summary/demo.py
python tmp/plan-comparison-summary/verify_protections.py
Cases: summary exact projection across directory/ZIP transports, legacy JSON and
Markdown byte-equal, repeated/reordered sections, no-change section
NO_MATCHING_CHANGES, global counts/identity/boundary preserved, once-read
snapshot handoff, invalid flags/unknown section before IO, invariant guard and
sanitized CLI failure, offline/no-extraction/no-write guards, actual Windows
junction rejection.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 46foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary DB/stash/
localmain unchanged; untouched modules byte-equal to base and only cli main
changed in the touched comparison module (AST review). Owned clean; feature/
dependency local/origin/live agree. No full local suite claim; exact-head hosted
pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-preparation-comparison-summary.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted state.
