# M4-B registry comparison class summary

## Objective
Root directly adds a focused class-level summary projection to
research registry-compare: --summary [--json]. Both explicit artifacts are
still loaded exactly once each through the frozen strict byte decode and the
frozen view entry points; the already-captured comparison report is then
projected into a compact per-class summary. The projection rereads nothing,
recomputes no diff, writes nothing, repairs nothing and promotes nothing.
User continuation authorizes this bounded engineering stage; no
DSH/delegation.

## Verified baseline
Origin/live codex/m4-registry-compare:
ef9863e8926b1abe3ec67f980631194aec624d99. PR85 OPEN/MERGEABLE; hosted
12SUCCESS/20pending at prior publication review (not a complete hosted gate).
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain85->84->83->82->81->80->79->78->77->76->75->74->73->71->70->69->68
unmerged. Fresh clean codex/m4-registry-compare-summary at ef9863e.
Before code tmp/registry-compare-summary/baseline.json must verify
52worktrees/51foreign states/28dirty hashes/427protected hashes against the
previous tmp/registry-compare baseline; primary3679b1b/localmain966206f/
stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/research_entry.py (only the existing registry-compare
COMMANDS usage text may change to document --summary),
src/ashare_research/tools/research_registry_compare.py (new private
projection helpers plus the existing cli main), and new
tests/test_research_registry_comparison_summary.py. Ignored demo/validation
artifacts allowed under tmp/registry-compare-summary/. research_registry.py,
src/ashare_research/mechanism/registry/**, and the previous view, preflight and
compare tests stay byte-identical to base. The module's public callable
surface stays exactly build_comparison/main/render_markdown: every new helper
is underscore-private, has no **kwargs, and avoids every forbidden name
fragment already frozen by the compare test (scan/rank/sort/promote/advance/
select/optimize/search/auto_).

## Forbidden scope
registry package edits, existing test edits, all other src files, schemas/CI/
protected data/foreign worktrees/stash/DB/runtime. No registry writes,
persistence, migration or storage backend; no record production, transition
application, digest repair, promotion, default or real candidate dataset
loading, acquisition, real research/statistics/holdout, cleanup/overwrite,
main/force push, merges or automatic following stage.

## Required behavior
Arguments: --left and --right are both required single paths plus optional
--summary and --json; missing/unknown/duplicate options reject
INVALID_ARGUMENTS before any IO. Both explicit files are read exactly once
each, capped at 1MiB, with the frozen read/decode/validation codes unchanged
(REGISTRY_READ_FAILED, REGISTRY_TOO_LARGE, NON_CANONICAL_SERIALIZATION,
INVALID_RECORD_STRUCTURE, the delegated frozen view codes and
INCOMPARABLE_ARTIFACT_KINDS). Without --summary both JSON and Markdown stay
byte-identical to the frozen compare output.
--summary is a pure projection of the captured, fully verified comparison:
no rereads, no new diff computation, no new IO, no writes. Accepted summaries
emit schema m4_registry_comparison_summary_v1, status
read_only_comparison_summary, the detected kind, byte_identical, both frozen
identity blocks, the all-false boundary and summary notes.
For record pairs the summary reports record_equal, changed_field_count,
unchanged_field_count (26 minus changed), field_count 26, the per-class
changed counts and the per-class changed field names for the frozen partition
identity/mutable/digest, in frozen RECORD_FIELDS order, plus the unchanged
six-key equality map (hypothesis id/version/status/identity digest/record
digest/state count). The partition is consumed from the frozen records
exports (IDENTITY_FIELDS = RECORD_FIELDS[:22]; mutable = status, state_history;
digest = identity_digest, record_digest) and must exactly cover the 26 frozen
fields or the projection fails closed.
For snapshot pairs the summary reports registry_equal, the unchanged five-key
registry equality map, added/removed/changed/unchanged counts and the compact
added/removed/changed rows as ID@VERSION strings in the captured
(hypothesis_id, hypothesis_version) order.
The projection fails closed with REGISTRY_COMPARISON_SUMMARY_MISMATCH whenever
the captured report violates frozen invariants: comparison schema/status/kind;
exact side identity key sets; byte_identical equal to side SHA equality;
exact all-false boundary; record changed rows with exactly field/left/right
and unique known field names, changed_field_count equal to the row count,
record_equal iff zero rows, class counts equal to the class name lists and
summing to the changed count, equality booleans recomputed from both identity
blocks, status/identity-digest/record-digest equality consistent with the
changed rows, and digest coverage consistency (identity_digest changed iff
some identity-class field changed; record_digest changed iff some
identity/mutable-class field changed); snapshot rows carrying the exact frozen
projections, counts equal to list lengths, per-list keys unique and
non-decreasing, changed rows differing on both sides, added/removed/changed
disjoint, registry_equal implying the five-key equality map, equality
booleans recomputed from both identity blocks, and record-count accounting
left = removed + changed + unchanged and right = added + changed + unchanged.
Markdown is a compact Chinese projection of the same summary. All failures
stay sanitized: exit code 2, empty stdout, error: CODE stderr with
REGISTRY_COMPARISON_FAILED as the catch-all. The tool touches no database,
provider, network, clock or holdout and never writes to disk.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_registry_comparison_summary.py tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_compare.py src/ashare_research/tools/research_entry.py tests/test_research_registry_comparison_summary.py
git diff --check
python tmp/registry-compare-summary/calculation_review.py
python tmp/registry-compare-summary/demo.py
python tmp/registry-compare-summary/verify_protections.py
Cases: record summary exact projection and delegated entry/CLI bytes with
class counts and frozen-order name lists; version pair and status pair class
partitions; legacy JSON and Markdown byte-equal without --summary; snapshot
summary counts, compact rows, order and count accounting; doctored-report
invariant guards with sanitized CLI failure; argument shapes rejected before
IO; single-read counting, offline/no-write and determinism guards with
--summary; delegated frozen failure codes preserved; unchanged frozen
13-entry registry surface and unchanged previous view/preflight/compare
outputs.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 51foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; registry package, research_registry.py
and the previous view/preflight/compare tests byte-equal to base; only the
registry-compare COMMANDS usage text changed in research_entry.py; the
compare module keeps every pre-existing function/class AST-identical except
cli main and only adds declared private helpers; owned clean;
feature/dependency local/origin/live agree. No full local suite claim;
exact-head hosted pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or
scope expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-registry-compare. No
main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted
state.
