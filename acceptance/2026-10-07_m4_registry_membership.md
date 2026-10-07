# M4-B registry snapshot membership acceptance

Goal: agent/goals/2026-10-07_m4_registry_membership.md. Verified base
codex/m4-registry-compare-summary:
fbe3898be871e0cb578e666f34666d39fb4fde49. PR86 OPEN/MERGEABLE; hosted
36SUCCESS/4pending at the prior publication review, not a complete hosted
gate. Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Root
implemented and reviewed directly, no DSH/delegation.

Delivered research registry-membership --record RECORD.json --snapshot
SNAPSHOT.json [--json]: a read-only mechanical membership check between one
explicit canonical M4-B record and one explicit canonical registry snapshot.
Both files are read exactly once each (max 1MiB); the record side is
validated through the frozen build_record_view entry and the snapshot side
through the frozen build_snapshot_view entry, so every single-side failure
keeps exactly the stable codes frozen by the previous view/preflight/compare
stages and no registry semantic check is re-implemented. Accepted checks
emit schema m4_registry_snapshot_membership_v1 with the record identity block
(file SHA256, hypothesis id/version, status, identity digest, record digest,
state count), the snapshot identity block (file SHA256, registry
schema/version/digest, record count, real demo candidate count) and
membership: found, sorted same-id versions present in the snapshot,
canonical_equal, changed_field_count, the sorted changed-field rows carrying
both sides' values, and the six-key equality map over hypothesis id/version,
status, both digests and state count. status is registered_identical when
the canonical record bytes equal, registered_different when the same key
differs, and not_registered when absent, in which case canonical_equal, the
changed count/list and every equality flag are false/empty.

The check fails closed with REGISTRY_MEMBERSHIP_MISMATCH on any captured-view
invariant violation: record/snapshot view schema, status and source SHA256
against the payload, the exact 26-field record document, the all-true record
verification block, canonical recomputation, the 7-key snapshot document,
the 8-key registry block, the 9-key record projections, embedded entry
parsing/re-serializing/digest recomputation through the frozen entries,
unique sorted embedded keys, record count and real demo count recomputed
through the frozen builder and count_real_demo_candidates, registry digest
recomputation, membership arithmetic (found iff the version is listed,
status derivation, canonical_equal iff zero changed fields), changed-row
shape and unicity against the frozen record fields, equality and digest
coverage consistency (identity_digest changed iff an identity field changed;
record_digest changed iff an identity or mutable field changed), and the
not_registered all-false rule. Report-level verification runs again in main
before any output. All failures stay sanitized: exit code 2, empty stdout,
error: CODE stderr with REGISTRY_MEMBERSHIP_FAILED as the catch-all. Markdown
is a compact Chinese projection; the all-false boundary and Chinese notes
state the check is a read-only mechanical answer that decides no
correctness and is not evidence, conclusion or authorization and touches no
database, provider, network, clock or holdout.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_registry_membership.py tests/test_research_registry_comparison_summary.py tests/test_research_registry_compare.py tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_registry_membership.py src/ashare_research/tools/research_entry.py tests/test_research_registry_membership.py
git diff --check
python tmp/registry-membership/calculation_review.py
python tmp/registry-membership/demo.py
python tmp/registry-membership/verify_protections.py
```

Targeted66passed49.07s (eight new cases plus the unchanged comparison
summary, compare, preflight, view, registry and entry suites). Final
Ruff/diff PASS; no pytest failure, existing test edit or full local-suite
claim. The new cases cover the exact registered-identical report with
delegated entry/CLI/module bytes and the unchanged frozen 13-entry registry
surface, the registered_different sorted changed list/equality map with
Markdown rows, absent keys with and without same-id versions, delegated
frozen failure codes from both sides (BOM and pretty record as
NON_CANONICAL_SERIALIZATION, pretty-with-LF snapshot as
REGISTRY_VIEW_MISMATCH, missing file as REGISTRY_READ_FAILED, oversize as
REGISTRY_TOO_LARGE), doctored-report invariant guards with sanitized
REGISTRY_MEMBERSHIP_MISMATCH CLI failure, argument shapes rejected before any
IO plus help/read failures, and two-file single-read counting with
offline/no-write/determinism guards.

Independent AST review (tmp/registry-membership/calculation-review.json):
research_entry.py keeps every pre-existing function/class and every
pre-existing COMMANDS entry AST-identical, gaining exactly one
registry-membership entry immediately after registry with the frozen module
path and --record/--snapshot usage; the membership module is a new file
whose public callable surface is exactly build_membership/main/
render_markdown with the eleven declared private helpers and
MembershipError/_Parser classes, exactly one --record/--snapshot/--json flag
each, no kwargs, and no sqlite3/duckdb/requests/urllib/subprocess/socket
reference; the membership path partitions the frozen 26 record fields into
22 identity/2 mutable/2 digest with IDENTITY_FIELDS = RECORD_FIELDS[:22];
research_registry.py, research_registry_compare.py, the registry package and
the previous view, preflight, compare and comparison-summary tests are
byte-equal to base.

Actual subprocess demo (tmp/registry-membership/demo/): six previous
invocations (registry view record/snapshot JSON, registry transition
preflight JSON, compare record JSON/Markdown and compare summary JSON) are
byte-equal to the previous worktree; the identical check reports
registered_identical with zero changed fields and all-true equality and the
all-false boundary; the advanced record reports registered_different with
changed fields record_digest/state_history/status and equality
True/True/False/True/False/False; same-id v2 reports not_registered with
same_id_versions [1]; another id reports not_registered with an empty
version list; Markdown carries the frozen title and the status row. Seven
fail-closed fixtures return exactly NON_CANONICAL_SERIALIZATION (BOM, CRLF),
REGISTRY_VIEW_MISMATCH (pretty-with-LF snapshot), IDENTITY_DIGEST_MISMATCH
(tampered digest), REGISTRY_READ_FAILED, REGISTRY_TOO_LARGE and
REGISTRY_MEMBERSHIP_MISMATCH (doctored captured report) with empty stdout;
membership runs created no files, 465 source files and 11 case files stayed
unchanged and replay is byte-equal.

Before implementation captured53worktrees/52foreign states/28dirty
hashes/427protected hashes against the previous tmp/registry-compare-summary
baseline; protection review PASS:52foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary database/stash/localmain unchanged and the untouched tools,
research_registry.py, research_registry_compare.py, the registry package and
the previous view, preflight, compare and comparison-summary tests byte-equal
to base. No comprehensive ignored-runtime hash claim.

Seven-file scoped normal feature commit/push and stacked PR against86. Final
exact committed scope/head, clean owned tree, local/origin/live
feature/dependency/main refs, protections and exact-head hosted state
independently reviewed after publication, retained in
tmp/registry-membership/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain86->85->84->83->82->81->80->79->78->77->76->75->
74->73->71->70->69->68 is unmerged. No automatic merge or following stage.
Real research/statistics/holdout sealed; no real registry dataset, record
production, transition application or promotion.
