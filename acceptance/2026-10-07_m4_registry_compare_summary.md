# M4-B registry comparison class summary acceptance

Goal: agent/goals/2026-10-07_m4_registry_compare_summary.md.
Verified base codex/m4-registry-compare:
ef9863e8926b1abe3ec67f980631194aec624d99. PR85 OPEN/MERGEABLE; hosted
12SUCCESS/20pending at the prior publication review, not a complete hosted
gate. Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered research registry-compare --left ARTIFACT.json --right
ARTIFACT.json [--summary] [--json]: a focused class-level projection of the
already-captured read-only comparison. Both explicit files are still read
exactly once each (max 1MiB) and validated through the frozen strict decode
and view entry points, so every failure keeps the codes frozen by the
previous view/preflight/compare stages; the projection rereads nothing,
recomputes no diff, writes nothing, repairs nothing and promotes nothing.
Without --summary both JSON and Markdown stay byte-identical to the frozen
compare output (proven subscript- and subprocess-level against the previous
worktree). Accepted summaries emit schema
m4_registry_comparison_summary_v1 and status read_only_comparison_summary.
Record pairs report record_equal, changed/unchanged/field counts, the frozen
class counts and changed field names for identity (22 identity-bearing
fields)/mutable (status, state_history)/digest (identity_digest,
record_digest) in frozen field order, and the six-key equality map;
snapshot pairs report registry_equal, the five-key equality map,
added/removed/changed/unchanged counts and ID@VERSION compact rows in
captured order. Class partition is consumed from the frozen records exports
(IDENTITY_FIELDS = RECORD_FIELDS[:22]) and must exactly cover the 26 frozen
fields.

The projection fails closed with REGISTRY_COMPARISON_SUMMARY_MISMATCH on any
captured-report invariant violation: comparison schema/status/kind, exact
side key sets, byte_identical against side SHA equality, the all-false
boundary, record changed-row shape/unicity/counts, record_equal iff zero
changes, equality recomputation from both identity blocks, status/identity
digest/record digest equality consistency, digest coverage consistency
(identity_digest changed iff an identity field changed; record_digest changed
iff an identity or mutable field changed), snapshot row shapes, per-list
uniqueness and captured order, changed rows differing on both projections,
added/removed/changed disjointness, registry_equal implying the equality
map, and record-count accounting left = removed + changed + unchanged and
right = added + changed + unchanged. All failures stay sanitized: exit code
2, empty stdout, error: CODE stderr with REGISTRY_COMPARISON_FAILED as the
catch-all. Markdown is a compact Chinese projection; report content carries
no superiority, provenance, sealing or execution claim.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_registry_comparison_summary.py tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_compare.py src/ashare_research/tools/research_entry.py tests/test_research_registry_comparison_summary.py
git diff --check
python tmp/registry-compare-summary/calculation_review.py
python tmp/registry-compare-summary/demo.py
python tmp/registry-compare-summary/verify_protections.py
```

Targeted58passed42.39s (seven new cases in 1.30s plus the unchanged compare,
preflight, view, registry and entry suites). Final Ruff/diff PASS; no pytest
failure, existing test edit or full local-suite claim. Cases cover the exact
record version-pair summary with frozen class counts/order and delegated
entry/CLI/module bytes, the status pair partition with legacy JSON/Markdown
byte-equality, snapshot counts/rows/accounting plus the identical pair,
doctored-report invariant guards (count, coverage, boundary, accounting,
changed-row identity) with sanitized CLI failure, argument shapes rejected
before any IO plus read/oversize failures with --summary, two-file
single-read counting with offline/no-write/determinism guards, and the
unchanged frozen 13-entry registry surface with the previous compare output
recomputed.

Independent AST review (tmp/registry-compare-summary/calculation-review.json):
research_entry.py keeps every pre-existing function/class and every COMMANDS
entry except registry-compare AST-identical, changing only that entry's
usage text to document --summary; research_registry_compare.py keeps every
pre-existing function/class AST-identical except cli main and adds exactly
the declared private helpers (_build_summary, _record_summary,
_snapshot_summary, _render_summary_markdown, _record_field_classes,
_summary_fail), with SCHEMA/STATUS/NOTES/IDENTITY_KEYS/
REGISTRY_EQUALITY_KEYS unchanged and exactly one --summary store_true flag;
research_registry.py, the registry package and the previous view, preflight
and compare tests are byte-equal to base.

Actual subprocess demo (tmp/registry-compare-summary/demo/): four previous
compare invocations (record JSON/Markdown, status JSON, snapshot JSON) are
byte-equal to the previous worktree; the version pair reports identity
hypothesis_version/theory plus both digests (2/0/2), the status pair mutable
status/state_history plus record_digest (0/2/1), the identical record pair
reports byte_identical/one zero-change class map and unchanged 26, the
snapshot pair reports added 0004, removed 0003, changed 0002 (LITERATURE_
REVIEWED) and one unchanged record with count accounting, and the identical
snapshot pair reports full registry equality; eight fail-closed fixtures
return exactly INCOMPARABLE_ARTIFACT_KINDS, REGISTRY_VIEW_MISMATCH
(pretty-with-LF snapshot bytes), NON_CANONICAL_SERIALIZATION (BOM, CRLF),
IDENTITY_DIGEST_MISMATCH, REGISTRY_READ_FAILED, REGISTRY_TOO_LARGE and
REGISTRY_COMPARISON_SUMMARY_MISMATCH (doctored captured report) with empty
stdout; summary runs created no files, 463 source files and 12 case files
stayed unchanged and replay is byte-equal.

Before implementation captured52worktrees/51foreign states/28dirty
hashes/427protected hashes against the previous tmp/registry-compare
baseline; protection review PASS:51foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary database/stash/localmain unchanged and the untouched tools,
research_registry.py, the registry package and the previous tests byte-equal
to base. No comprehensive ignored-runtime hash claim.

Seven-file scoped normal feature commit/push and stacked PR against85. Final
exact committed scope/head, clean owned tree, local/origin/live
feature/dependency/main refs, protections and exact-head hosted state
independently reviewed after publication, retained in
tmp/registry-compare-summary/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain85->84->83->82->81->80->79->78->77->76->75->74->
73->71->70->69->68 is unmerged. No automatic merge or following stage. Real
research/statistics/holdout sealed; no real registry dataset, record
production, transition application or promotion.
