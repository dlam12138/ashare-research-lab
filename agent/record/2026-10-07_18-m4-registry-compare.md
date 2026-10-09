# M4-B registry artifact comparison

User continues bounded engineering and explicitly requests root alone, no DSH.
Verified primary3679b1b/main8d0fb4d/base be03573, PR84 OPEN/MERGEABLE with
hosted 5SUCCESS/23pending at the prior publication review. Fresh clean
isolated codex/m4-registry-compare. Read the previous stage records, the
frozen registry package, the single-artifact view/preflight tools and the
plan/preparation comparison conventions. Goal:
agent/goals/2026-10-07_m4_registry_compare.md. Before implementation captured
51worktrees/50foreign states/28dirty hashes/427protected hashes against the
previous tmp/registry-transition-preflight baseline and checked
database/stash/localmain against it; evidence at
tmp/registry-compare/baseline.json.

Pre-code baseline PASS. Added research registry-compare --left ARTIFACT.json
--right ARTIFACT.json [--json] as a new read-only tool module plus one
unified-entry command inserted before registry. Both explicit files are read
once each (max 1MiB), strictly decoded with the same byte rules and, after
key-based record/snapshot classification, validated through the existing
build_record_view / build_snapshot_view entries so every single-side failure
keeps the frozen codes and no registry semantic check is re-implemented;
record vs snapshot rejects INCOMPARABLE_ARTIFACT_KINDS. Accepted comparisons
emit schema m4_registry_comparison_v1, status read_only_comparison, per-side
identity blocks, byte_identical, a record field-difference table with an
equality map, or snapshot registry equality plus
added/removed/changed/unchanged record lists; the all-false boundary and
Chinese notes keep the comparison mechanical, non-evidencing and
non-authorizing. Markdown is a compact Chinese projection.

Actual targeted51passed47.69s; Ruff and git diff --check PASS; no failed
test, existing test edit or full local-suite claim. Seven new cases cover
exact identical/version/status record reports, snapshot classification and
ordering, delegated entry bytes, mixed kinds, two-side frozen byte and
integrity failures including the pinned REGISTRY_VIEW_MISMATCH for
pretty-with-LF snapshot bytes and the stray-snapshot-key classification, read
failures, two-file single-read counting, offline/no-write/determinism guards
and the frozen 13-entry registry surface with previous outputs recomputed.
AST review (tmp/registry-compare/calculation-review.json): research_entry.py
keeps every pre-existing function/class unchanged and adds exactly one
registry-compare COMMANDS entry before registry; research_registry.py, the
registry package and the previous view/preflight tests are byte-equal to
base.

Actual demo: four previous record/snapshot view invocations byte-equal to the
previous worktree; identical/version/status record pairs and the
added/removed/changed/unchanged snapshot pair report exact mechanical
differences; six fail-closed fixtures and three argument/IO fixtures return
exactly the documented sanitized codes with empty stdout; comparison runs
created no files, source hashes stayed unchanged and replay is byte-equal.
Evidence in tmp/registry-compare/demo/.

Protection review PASS:50foreign registrations/HEAD/branches/statuses,28dirty
hashes,427protected hashes and database/stash/localmain unchanged; the
untouched tools, research_registry.py, the registry package and the previous
tests are byte-equal to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_registry_compare.md.

Seven-file scoped normal feature commit/push and PR stacked on84. Final
actual head/scope/clean tree/refs/protections and hosted state retained in
tmp/registry-compare/final-evidence.json.
No main/force push, automatic merge or following stage. No record
production, transition application, promotion, default or real candidate
dataset loading, real research/statistics/holdout or literature acquisition.
