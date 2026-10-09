# M4-B registry comparison class summary

User continues bounded engineering and explicitly requests root alone, no
DSH. Verified primary3679b1b/main8d0fb4d/base ef9863e, PR85 OPEN/MERGEABLE
with hosted 12SUCCESS/20pending at the prior publication review. Fresh clean
isolated codex/m4-registry-compare-summary. Read the previous stage records,
the frozen registry package, the compare module and the plan-compare
summary precedent. Goal:
agent/goals/2026-10-07_m4_registry_compare_summary.md. Before implementation
captured 52worktrees/51foreign states/28dirty hashes/427protected hashes
against the previous tmp/registry-compare baseline and checked
database/stash/localmain against it; evidence at
tmp/registry-compare-summary/baseline.json.

Pre-code baseline PASS. Added research registry-compare --summary [--json]
as a pure class-level projection of the captured, fully verified comparison:
both explicit files are still read once each (max 1MiB) and validated
through the frozen decode/view entries, so every failure keeps the previous
stable codes; the projection rereads nothing, recomputes no diff, writes
nothing, repairs nothing and promotes nothing. Record pairs report the
frozen identity(22)/mutable(status, state_history)/digest(identity_digest,
record_digest) class counts and changed field names in frozen field order
plus the six-key equality map; snapshot pairs report registry equality,
added/removed/changed/unchanged counts and ID@VERSION rows in captured
order. Class partition is consumed from the frozen records exports and must
exactly cover the 26 frozen fields; captured-report invariant violations
fail closed as REGISTRY_COMPARISON_SUMMARY_MISMATCH. Without --summary both
JSON and Markdown stay byte-identical to the frozen compare output. The
module's public callable surface stays exactly
build_comparison/main/render_markdown; every new helper is underscore-private
with no **kwargs and no forbidden name fragment.

Actual targeted58passed42.39s (seven new cases plus the unchanged compare,
preflight, view, registry and entry suites); Ruff and git diff --check PASS;
no failed test, existing test edit or full local-suite claim. The seven new
cases cover exact record summary bytes with delegated entry/CLI/module
outputs, version/status class partitions, legacy byte-equality, snapshot
counts/rows/accounting with the identical pair, doctored-report guards with
sanitized CLI failure, argument shapes rejected before IO plus read/oversize
failures, single-read/offline/no-write/determinism guards and the unchanged
frozen 13-entry registry surface. AST review
(tmp/registry-compare-summary/calculation-review.json): research_entry.py
keeps every declaration and every other COMMANDS entry unchanged and only
documents --summary in the existing registry-compare usage text; the compare
module keeps every pre-existing definition AST-identical except cli main and
adds exactly the six declared private helpers; research_registry.py, the
registry package and the previous view/preflight/compare tests are
byte-equal to base.

Actual demo: four previous compare invocations byte-equal to the previous
worktree; version/status/identical record pairs and the
added/removed/changed/unchanged snapshot pair plus the identical snapshot
pair report exact class-level projections; eight fail-closed fixtures
return exactly the documented sanitized codes with empty stdout; summary
runs created no files, 463 source files and 12 case files stayed unchanged
and replay is byte-equal. Evidence in tmp/registry-compare-summary/demo/.

Protection review PASS:51foreign registrations/HEAD/branches/statuses,28dirty
hashes,427protected hashes and database/stash/localmain unchanged; the
untouched tools, research_registry.py, the registry package and the previous
tests are byte-equal to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_registry_compare_summary.md.

Seven-file scoped normal feature commit/push and PR stacked on85. Final
actual head/scope/clean tree/refs/protections and hosted state retained in
tmp/registry-compare-summary/final-evidence.json.
No main/force push, automatic merge or following stage. No record
production, transition application, promotion, default or real candidate
dataset loading, real research/statistics/holdout or literature acquisition.
