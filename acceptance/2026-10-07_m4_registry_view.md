# M4-B registry read-only view acceptance

Goal: agent/goals/2026-10-07_m4_registry_view.md.
Verified base codex/m4-plan-review-summary:
cb5fbedd099ed7c2be2f5c133a9ce0eb7e7a466c. PR82 OPEN/MERGEABLE; hosted checks
pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered research registry --record JSON | --snapshot JSON [--json]: a
read-only view that strictly revalidates one explicit canonical M4-B record or
snapshot file through the frozen 13-entry registry surface and renders a
compact Chinese Markdown view or a bounded JSON view. The tool reads exactly
one explicit file once (max 1MiB), writes only to stdout, and never writes,
repairs, promotes or loads any registry state or dataset. The frozen
mechanism/registry package is byte-identical to base; no registry entry point
was added or changed.

Record mode parses the canonical bytes with the frozen byte entry point and
emits schema m4_registry_record_view_v1, status validated_metadata_only, the
source SHA256, the frozen canonical 26-key document, recomputed identity and
record digests, and a verification block for canonical bytes plus both
digests. When the frozen byte path collapses a missing/extra-key structural
failure into a bare TypeError (it constructs the frozen dataclass before its
key-set checks), the view re-enters the frozen mapping validation with the
same JSON container conversion, so MISSING_REQUIRED_FIELD and
UNKNOWN_RECORD_FIELD keep their documented codes; no registry semantic check
is re-implemented.

Snapshot mode strictly decodes the file (BOM, CR, missing/extra trailing LF,
float token, non-finite constant or duplicate key are
NON_CANONICAL_SERIALIZATION; a non-mapping root is INVALID_RECORD_STRUCTURE),
requires exactly the seven frozen top-level keys, revalidates every record
through canonical re-encode plus the frozen parse, and rebuilds the snapshot
so duplicates are DUPLICATE_HYPOTHESIS_ID/PROVENANCE_REWRITE and over-scale is
SCALE_LIMIT_EXCEEDED. Loaded-specific first errors stay deterministic:
versions/boundary INVALID_ENUM_VALUE, record order INVALID_RECORD_STRUCTURE,
count type/value INVALID_FIELD_TYPE, registry_digest RECORD_DIGEST_MISMATCH,
final byte equality NON_CANONICAL_SERIALIZATION. Output schema is
m4_registry_snapshot_view_v1 with the record count, real-demo candidate count,
both scale ceilings, registry digest, compact per-record list (id, version,
status, feasibility, digests, state count), the echoed interpretation
boundary, the verification block and the same all-false boundary
(execution_authorized, statistics_computed, outcome_read, holdout_accessed,
real_registry_dataset_loaded, registry_written). Both views carry Chinese
notes: the view is read-only and registry metadata is not evidence,
conclusion or authorization.

Arguments accept exactly one of --record/--snapshot plus optional --json;
every other shape is INVALID_ARGUMENTS before any IO. Missing or unreadable
paths are REGISTRY_READ_FAILED, oversize input is REGISTRY_TOO_LARGE, and all
failures stay sanitized: exit code 2, empty stdout, error: CODE stderr with
REGISTRY_VIEW_FAILED as the catch-all. The tool touches no database, provider,
network, clock or holdout.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py tests/test_research_plan_review_summary.py
python -m ruff check src/ashare_research/tools/research_registry.py src/ashare_research/tools/research_entry.py tests/test_research_registry_view.py
git diff --check
python tmp/registry-view/calculation_review.py
python tmp/registry-view/demo.py
python tmp/registry-view/verify_protections.py
```

Targeted45passed50.75s (eight new cases plus the unchanged registry, entry and
plan-summary suites). Final Ruff/diff PASS; no pytest failure, existing test
edit or full local-suite claim. Cases cover the exact record and snapshot JSON
projections with recomputed digests and counts, entry-level delegation bytes,
Markdown renderer equality, canonical byte failures (BOM/CR/LF/float/duplicate
key), digest tamper, missing/extra key, illegal state history and reason,
invalid enum, snapshot order/count/digest/version/boundary/extra/missing/
records-type/scale/duplicate/provenance-rewrite failures, pretty-printed
non-canonical bytes, argument shapes rejected before IO, missing/directory/
oversize inputs, single-read enforcement, offline/no-write guards and the
frozen 13-entry registry surface.

Actual subprocess demo: two previous-stage plan invocations are byte-equal to
the previous worktree; the record view reproduces the frozen canonical
document with recomputed digests; the snapshot view reproduces canonical
record order, 3 records/2 real-demo counts, registry_digest and the
interpretation boundary; thirteen fail-closed fixtures return exactly
NON_CANONICAL_SERIALIZATION, MISSING_REQUIRED_FIELD, UNKNOWN_RECORD_FIELD,
IDENTITY_DIGEST_MISMATCH, INVALID_RECORD_STRUCTURE, INVALID_FIELD_TYPE,
RECORD_DIGEST_MISMATCH, DUPLICATE_HYPOTHESIS_ID, PROVENANCE_REWRITE and
SCALE_LIMIT_EXCEEDED with empty stdout; INVALID_ARGUMENTS,
REGISTRY_READ_FAILED and REGISTRY_TOO_LARGE match; view runs created no files
and both source hashes stayed unchanged. JSON/Markdown/evidence retained in
tmp/registry-view/demo/.

Independent AST review (tmp/registry-view/calculation-review.json):
research_entry.py keeps every pre-existing function/class AST-identical and
changes only the annotated COMMANDS tuple, inserting exactly one registry
entry after plan; the view module exposes exactly the seven expected
functions, none matching forbidden scan/rank/sort/promote/advance/select/
optimize/search/auto_ names and none declaring **kwargs; the registry package
files are byte-equal to base and the frozen callable surface stays exactly 13
entries.

Before implementation captured49worktrees/48foreign states/28dirty hashes
(27previous plus the new Goal file)/427protected hashes against the previous
tmp/plan-review-summary baseline; protection review PASS:48foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary database/stash/localmain unchanged and the untouched tools plus the
registry package byte-equal to base. No comprehensive ignored-runtime hash
claim.

Seven-file scoped normal feature commit/push and stacked PR against82. Final
exact committed scope/head, clean owned tree, local/origin/live
feature/dependency/main refs, protections and exact-head hosted state
independently reviewed after publication, retained in
tmp/registry-view/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain82->81->80->79->78->77->76->75->74->73->71->70->
69->68 is unmerged. No automatic merge or following stage. Real research/
statistics/holdout sealed; no real registry dataset or literature acquisition.
