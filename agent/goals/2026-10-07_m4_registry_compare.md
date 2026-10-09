# M4-B registry artifact comparison

## Objective
Root directly adds a read-only comparison of two explicit canonical M4-B
registry artifacts: `research registry-compare --left ARTIFACT.json --right
ARTIFACT.json [--json]`. After the shared strict byte decode, each side is
classified as a record or a snapshot (a document containing any of the seven
frozen snapshot top-level keys is a snapshot; otherwise a record) and is
validated through the existing frozen-entry view builders, so every failure
keeps the codes already frozen by `research registry --record/--snapshot`.
The comparison reports mechanical structural differences only: it produces,
writes, repairs and promotes nothing. User continuation authorizes this
bounded engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-registry-transition-preflight:
be03573ff9c89163bc7a7cde29bbf8823bcf804d. PR84 OPEN/MERGEABLE; hosted
5SUCCESS/23pending at prior publication review (not a complete hosted gate).
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain84->83->82->81->80->79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-registry-compare at be03573.
Before code tmp/registry-compare/baseline.json must verify 51worktrees/50
foreign states/28dirty hashes/427protected hashes against the previous
tmp/registry-transition-preflight baseline; primary3679b1b/localmain966206f/
stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/research_entry.py (only one new registry-compare
COMMANDS entry inserted before the registry entry),
src/ashare_research/tools/research_registry_compare.py (new module), and new
tests/test_research_registry_compare.py. research_registry.py,
src/ashare_research/mechanism/registry/**, the previous view and preflight
tests, and every other src/test file stay byte-identical to base.

## Forbidden scope
registry package edits, existing test edits, all other src files, schemas/CI/
protected data/foreign worktrees/stash/DB/runtime. No registry writes,
persistence, migration or storage backend; no record production, transition
application, digest repair, promotion, default or real candidate dataset
loading, acquisition, real research/statistics/holdout, cleanup/overwrite,
main/force push, merges or automatic following stage.

## Required behavior
Arguments: --left and --right are both required single paths plus optional
--json; missing/unknown/duplicate options reject INVALID_ARGUMENTS before any
IO. Both explicit files are read exactly once each, capped at 1MiB: OSError is
REGISTRY_READ_FAILED and oversize is REGISTRY_TOO_LARGE.
Both sides go through the same strict decode as the view (BOM, CR,
missing/extra trailing LF, float token, non-finite constant or duplicate key
are NON_CANONICAL_SERIALIZATION; a non-mapping root is
INVALID_RECORD_STRUCTURE). Inside the tool package, validation reuses the
existing `build_record_view`/`build_snapshot_view` entry points so record and
snapshot failures keep exactly the frozen stable codes of the single-artifact
view; no registry semantic check is re-implemented and no new registry entry
point is added. A record on one side and a snapshot on the other rejects
INCOMPARABLE_ARTIFACT_KINDS.
Accepted comparisons emit schema m4_registry_comparison_v1, status
read_only_comparison, the detected kind, per-side SHA256 and frozen identity
blocks: for records, hypothesis id/version, current status, identity digest,
record digest and state count per side, byte_identical, record_equal, the
sorted list of differing canonical top-level fields with the per-field
left/right values, and status/state-count/identity-digest/record-digest
equality booleans; for snapshots, registry digest, record count and
real_demo_candidate_count per side plus added/removed/changed record lists
keyed and sorted by (hypothesis_id, hypothesis_version) with the per-record
status/identity-digest/record-digest projections and an unchanged count. The
all-false boundary and Chinese notes state that the comparison is a read-only
mechanical difference, does not decide which side is correct, and is not
evidence, conclusion or authorization. Markdown is a compact Chinese
projection of the same comparison.
All failures stay sanitized: exit code 2, empty stdout, error: CODE stderr
with REGISTRY_COMPARISON_FAILED as the catch-all. The tool touches no
database, provider, network, clock or holdout and never writes to disk.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_compare.py src/ashare_research/tools/research_entry.py tests/test_research_registry_compare.py
git diff --check
python tmp/registry-compare/calculation_review.py
python tmp/registry-compare/demo.py
python tmp/registry-compare/verify_protections.py
Cases: identical record pair; record pair with status/provenance/version
differences with sorted changed fields and equality booleans; identical and
changed snapshot pairs with added/removed/changed/unchanged record
classification and sorted order; delegated entry bytes and Markdown
equality; mixed kinds INCOMPARABLE_ARTIFACT_KINDS; per-side frozen byte and
integrity failures (BOM/CR/LF/float/duplicate key, digest tamper,
missing/extra key, order/count/digest snapshot failures); argument shapes
rejected before IO; read failures and oversize; two-file single-read
counting; offline/no-write/determinism; unchanged frozen 13-entry registry
surface and unchanged previous view/preflight outputs.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 50foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; registry package, research_registry.py
and the previous view/preflight tests byte-equal to base; only the expected
research_entry COMMANDS entry added; owned clean; feature/dependency
local/origin/live agree. No full local suite claim; exact-head hosted pending
state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or
scope expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against
codex/m4-registry-transition-preflight. No main/force push or merge. Final
PASS/CHANGES_REQUIRED/BLOCKED packet includes actual Goal/base/head/files/
tests/acceptance/protections/refs and hosted state.
