# M4-B registry read-only view

User continues bounded engineering and explicitly requests root alone, no DSH.
Verified primary3679b1b/main8d0fb4d/base cb5fbedd, PR82 OPEN/MERGEABLE with
hosted checks pending at initial query. Fresh clean isolated
codex/m4-registry-view. Read the latest records, the frozen M4-B registry
package and its design/acceptance-case docs, the plan summary stage conventions
and the unified entry tests. Goal:
agent/goals/2026-10-07_m4_registry_view.md. Before implementation
captured49worktrees/48foreign states/28dirty hashes/427protected hashes
(previous27 plus the new Goal file) and checked database/stash/localmain
against the previous stage baseline; evidence at
tmp/registry-view/baseline.json.

Pre-code baseline PASS. Added research registry --record/--snapshot [--json]
as a read-only view in a new tools module. Record mode parses canonical bytes
through the frozen byte entry point and projects the canonical 26-key document
with recomputed digests and a verification block; when the frozen byte path
collapses a missing/extra-key failure into a bare TypeError, the view
re-enters the frozen mapping validation with the same JSON container
conversion so documented codes survive - no registry semantic check was
re-implemented and no registry file changed. Snapshot mode strictly decodes
the file, requires exactly the seven frozen top-level keys, revalidates each
record through canonical re-encode plus the frozen parse, rebuilds the
snapshot and then checks versions/boundary, canonical order, count, digest and
final byte equality in a frozen order, so duplicates, rewrites and over-scale
keep DUPLICATE_HYPOTHESIS_ID/PROVENANCE_REWRITE/SCALE_LIMIT_EXCEEDED while
non-canonical bytes stay NON_CANONICAL_SERIALIZATION. Both views carry the
all-false boundary and read-only/not-evidence notes; the JSON schemas are
m4_registry_record_view_v1 and m4_registry_snapshot_view_v1, and Markdown is a
compact Chinese projection of the same data.

Actual targeted45passed50.75s; Ruff and git diff --check PASS; no failed
test, existing test edit or full local-suite claim. Eight new cases cover
exact record/snapshot projections and delegated entry bytes, Markdown
renderer equality, canonical byte failures, digest/key/state/enum tampering,
all snapshot structural failures plus pretty-printed bytes, argument shapes
before IO, read failures, single-read counting, offline/no-write guards and
the frozen 13-entry registry surface. AST review
(tmp/registry-view/calculation-review.json): research_entry.py keeps every
pre-existing function/class unchanged and edits only the annotated COMMANDS
tuple, adding exactly one registry entry after plan; the registry package is
byte-equal to base.

Actual demo: two previous-stage plan invocations byte-equal to the previous
worktree; record and snapshot views reproduce recomputed digests, canonical
order, 3/2 counts, registry digest and interpretation boundary; thirteen
hash/V2/V7/V10/V11/V12 failure fixtures and three argument/IO fixtures return
exactly the documented sanitized codes with empty stdout; view runs created
no files and source hashes stayed unchanged. Evidence in
tmp/registry-view/demo/.

Protection review PASS:48foreign registrations/HEAD/branches/statuses,28dirty
hashes,427protected hashes and database/stash/localmain unchanged; the
untouched plan/prepare/comparison tools and the registry package are
byte-equal to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_registry_view.md.

Seven-file scoped normal feature commit/push and PR stacked on82. Final actual
head/scope/clean tree/refs/protections and hosted state retained in
tmp/registry-view/final-evidence.json.
No main/force push, automatic merge or following stage.
