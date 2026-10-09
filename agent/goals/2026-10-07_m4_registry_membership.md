# M4-B registry membership check

## Objective
Root directly adds a read-only membership check between two explicit M4-B
registry artifacts of different kinds:
research registry-membership --record RECORD.json --snapshot SNAPSHOT.json
[--json]. Both files are read exactly once each through the frozen strict
decode and the frozen record/snapshot view entries; the tool then answers the
mechanical question whether the record's (hypothesis_id, hypothesis_version)
is registered in the snapshot and whether the snapshot's embedded entry has
the same canonical record bytes. A same-key entry with different canonical
bytes reports the mechanical changed-field list and equality map; an absent
key reports the versions of that hypothesis id present in the snapshot. The
tool produces, writes, repairs and promotes nothing and re-implements no
registry semantic check. User continuation authorizes this bounded
engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-registry-compare-summary:
fbe3898be871e0cb578e666f34666d39fb4fde49. PR86 OPEN/MERGEABLE; hosted
36SUCCESS/4pending at prior publication review (not a complete hosted gate).
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain86->85->84->83->82->81->80->79->78->77->76->75->74->73->71->70->69->68
unmerged. Fresh clean codex/m4-registry-membership at fbe3898.
Before code tmp/registry-membership/baseline.json must verify
53worktrees/52foreign states/28dirty hashes/427protected hashes against the
previous tmp/registry-compare-summary baseline; primary3679b1b/
localmain966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/research_entry.py (exactly one new
registry-membership COMMANDS entry inserted immediately after the registry
entry; every other entry and every pre-existing function/class stays AST
identical), new src/ashare_research/tools/research_registry_membership.py,
and new tests/test_research_registry_membership.py. Ignored demo/validation
artifacts allowed under tmp/registry-membership/. research_registry.py,
research_registry_compare.py, src/ashare_research/mechanism/registry/**, and
the previous view, preflight, compare and comparison-summary tests stay
byte-identical to base.

## Forbidden scope
registry package edits, existing test edits, research_registry.py and
research_registry_compare.py edits, all other src files, schemas/CI/protected
data/foreign worktrees/stash/DB/runtime. No registry writes, persistence,
migration or storage backend; no record production, transition application,
digest repair, promotion, default or real candidate dataset loading,
acquisition, real research/statistics/holdout, cleanup/overwrite, main/force
push, merges or automatic following stage.

## Required behavior
Arguments: --record and --snapshot are both required single paths plus
optional --json; missing or unknown options reject INVALID_ARGUMENTS
before any IO. Both explicit files are read exactly once each, capped at
1MiB: OSError is REGISTRY_READ_FAILED and oversize is REGISTRY_TOO_LARGE.
The record side is validated through the frozen build_record_view entry and
the snapshot side through the frozen build_snapshot_view entry, so every
single-side failure keeps exactly the stable codes already frozen by
research registry --record/--snapshot; no registry semantic check is
re-implemented and no new registry entry point is added.
Accepted checks emit schema m4_registry_snapshot_membership_v1, the record
identity block (file SHA256, hypothesis id/version, status, identity digest,
record digest, state count), the snapshot identity block (file SHA256,
registry schema/version/digest, record count, real demo candidate count),
and membership: found, the sorted versions of the same hypothesis id present
in the snapshot, canonical_equal, changed_field_count, the sorted
changed-field list with the snapshot-side and record-side values, and the
six-key equality map. status is registered_identical when the canonical
bytes equal, registered_different when the same key differs and
not_registered when the key is absent (then canonical_equal, changed count,
changed list and every equality flag are false/empty). The all-false
boundary and Chinese notes state that the check is a read-only mechanical
membership answer, does not decide which side is correct and is not
evidence, conclusion or authorization.
The check fails closed with REGISTRY_MEMBERSHIP_MISMATCH whenever the
captured views violate frozen invariants: record/snapshot view schema,
status, source SHA256 against the payload, exact side key sets (26 frozen
record fields; 8-key registry block; 9-key record projections; 7-key
snapshot document), all-true record verification, canonical recomputation,
embedded entries parsing and re-serializing through the frozen entries,
unique embedded keys, record count and real demo count recomputed through
the frozen counter, per-entry digest recomputation, membership arithmetic
(found iff the version is listed, status iff flags, canonical_equal iff
zero changed fields), changed-row shape/unicity against the frozen record
fields, equality and digest coverage consistency (identity_digest changed
iff an identity field changed; record_digest changed iff an identity or
mutable field changed), and the not_registered all-false rule.
All failures stay sanitized: exit code 2, empty stdout, error: CODE stderr
with REGISTRY_MEMBERSHIP_FAILED as the catch-all. Markdown is a compact
Chinese projection of the same check. The tool touches no database,
provider, network, clock or holdout and never writes to disk.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_registry_membership.py tests/test_research_registry_comparison_summary.py tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_membership.py src/ashare_research/tools/research_entry.py tests/test_research_registry_membership.py
git diff --check
python tmp/registry-membership/calculation_review.py
python tmp/registry-membership/demo.py
python tmp/registry-membership/verify_protections.py
Cases: registered-identical exact report and delegated entry/CLI/module
bytes; same-key different-state registered_different with the sorted
changed-field list and equality map; absent key with same-id version listing
and with no listing; delegated frozen failure codes from both sides
including the pinned REGISTRY_VIEW_MISMATCH for pretty-with-LF snapshot
bytes; doctored captured views failing closed as REGISTRY_MEMBERSHIP_MISMATCH
with sanitized CLI failure; argument shapes rejected before IO; two-file
single-read counting; offline/no-write/determinism guards; unchanged frozen
13-entry registry surface and unchanged previous view/preflight/compare/
summary outputs.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 52foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; registry package, research_registry.py,
research_registry_compare.py and the previous view/preflight/compare/summary
tests byte-equal to base; only the expected research_entry COMMANDS entry
added immediately after registry; owned clean; feature/dependency
local/origin/live agree. No full local suite claim; exact-head hosted
pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or
scope expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against
codex/m4-registry-compare-summary. No main/force push or merge. Final
PASS/CHANGES_REQUIRED/BLOCKED packet includes actual
Goal/base/head/files/tests/acceptance/protections/refs and hosted state.
