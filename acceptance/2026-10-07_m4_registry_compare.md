# M4-B registry artifact comparison acceptance

Goal: agent/goals/2026-10-07_m4_registry_compare.md.
Verified base codex/m4-registry-transition-preflight:
be03573ff9c89163bc7a7cde29bbf8823bcf804d. PR84 OPEN/MERGEABLE; hosted
5SUCCESS/23pending at the prior publication review, not a complete hosted
gate. Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered research registry-compare --left ARTIFACT.json --right
ARTIFACT.json [--json]: a read-only comparison of two explicit canonical
M4-B registry artifacts. Both files are read exactly once each (max 1MiB),
strictly decoded with the same byte rules as the single-artifact view, then
each side is classified as a record or a snapshot (a decoded document
containing any of the seven frozen snapshot top-level keys is a snapshot;
otherwise a record) and validated through the existing build_record_view /
build_snapshot_view entry points, so every single-side failure keeps exactly
the codes already frozen by research registry --record/--snapshot and no
registry semantic check is re-implemented. A record on one side and a
snapshot on the other rejects INCOMPARABLE_ARTIFACT_KINDS. The tool writes
only to stdout: it produces, writes, repairs and promotes nothing; the frozen
mechanism/registry package, research_registry.py and the previous view and
preflight tests stay byte-identical to base.

Accepted comparisons emit schema m4_registry_comparison_v1, status
read_only_comparison, the detected kind, byte_identical, per-side SHA256 and
frozen identity blocks. Record pairs report record_equal, the sorted
per-top-level-field difference list with left/right values and the
hypothesis id/version/status/identity digest/record digest/state-count
equality map. Snapshot pairs report registry schema/version/digest and count
equality plus added/removed/changed record lists keyed and sorted by
(hypothesis_id, hypothesis_version) and an unchanged count. The all-false
boundary and Chinese notes state that the comparison is a read-only
mechanical difference, does not decide which side is correct and is not
evidence, conclusion or authorization; Markdown is a compact Chinese
projection of the same comparison.

All failures stay sanitized: exit code 2, empty stdout, error: CODE stderr
with REGISTRY_COMPARISON_FAILED as the catch-all; argument shapes
(missing/unknown options) reject INVALID_ARGUMENTS before any IO; missing or
unreadable paths are REGISTRY_READ_FAILED and oversize input is
REGISTRY_TOO_LARGE. The tool touches no database, provider, network, clock or
holdout and never writes to disk.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_compare.py src/ashare_research/tools/research_entry.py tests/test_research_registry_compare.py
git diff --check
python tmp/registry-compare/calculation_review.py
python tmp/registry-compare/demo.py
python tmp/registry-compare/verify_protections.py
```

Targeted51passed47.69s (seven new cases plus the unchanged preflight, view,
registry and entry suites). Final Ruff/diff PASS; no pytest failure, existing
test edit or full local-suite claim. Cases cover the identical pair exact
report and delegated entry/CLI/module bytes, version/status/provenance
record differences with sorted changed fields, snapshot
added/removed/changed/unchanged classification with same-id version pairs,
two-side frozen byte failures (BOM/CR/LF/duplicate key/float/pretty), record
missing/extra/digest tampering, snapshot
order/count/digest/extra/missing/pretty failures including the pinned
REGISTRY_VIEW_MISMATCH for pretty-with-LF snapshot bytes, the
stray-snapshot-key classification rule, mixed kinds, argument shapes rejected
before IO, read failures, two-file single-read counting,
offline/no-write/determinism guards, and the unchanged frozen 13-entry
registry surface with previous view/preflight outputs recomputed.

Actual subprocess demo (tmp/registry-compare/demo/): four previous
record/snapshot view invocations (JSON and Markdown) are byte-equal to the
previous worktree; the identical record pair reports byte_identical true with
zero changed fields; the version pair reports exactly
hypothesis_version/identity_digest/record_digest/theory and the status pair
exactly record_digest/state_history/status; the snapshot pair reports
SYNTH_EXAMPLE_0004 added, SYNTH_EXAMPLE_0003 removed, SYNTH_EXAMPLE_0002
changed and one unchanged record with registry_digest inequality; six
fail-closed fixtures return exactly INCOMPARABLE_ARTIFACT_KINDS,
NON_CANONICAL_SERIALIZATION, INVALID_RECORD_STRUCTURE, INVALID_FIELD_TYPE,
REGISTRY_VIEW_MISMATCH and IDENTITY_DIGEST_MISMATCH with empty stdout;
INVALID_ARGUMENTS, REGISTRY_READ_FAILED and REGISTRY_TOO_LARGE match;
comparison runs created no files, source hashes stayed unchanged and replay
is byte-equal.

Independent AST review (tmp/registry-compare/calculation-review.json):
research_entry.py keeps every pre-existing function/class AST-identical and
adds exactly one registry-compare COMMANDS entry immediately before registry,
with every other COMMANDS entry unchanged; the module exposes exactly
build_comparison/main/render_markdown with no **kwargs and no forbidden
names; research_registry.py, the registry package and the previous view and
preflight tests are byte-equal to base.

Before implementation captured51worktrees/50foreign states/28dirty
hashes/427protected hashes against the previous
tmp/registry-transition-preflight baseline; protection review PASS:50foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary database/stash/localmain unchanged and the untouched tools,
research_registry.py, the registry package and the previous tests byte-equal
to base. No comprehensive ignored-runtime hash claim.

Seven-file scoped normal feature commit/push and stacked PR against84. Final
exact committed scope/head, clean owned tree, local/origin/live
feature/dependency/main refs, protections and exact-head hosted state
independently reviewed after publication, retained in
tmp/registry-compare/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain84->83->82->81->80->79->78->77->76->75->74->73->
71->70->69->68 is unmerged. No automatic merge or following stage. Real
research/statistics/holdout sealed; no real registry dataset, record
production, transition application or promotion.
