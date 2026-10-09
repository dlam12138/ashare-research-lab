# M4-B registry read-only view

## Objective
Root directly adds a read-only M4-B registry view to the research entry:
research registry --record JSON | --snapshot JSON [--json]. Explicit canonical
M4-B record or snapshot files are strictly decoded and revalidated through the
frozen 13-entry registry surface; the default output is a compact Chinese
Markdown view and --json is a bounded machine view. The tool
never writes, never repairs, never promotes state and never loads a default or
real candidate dataset. User continuation authorizes this bounded engineering
stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-plan-review-summary:
cb5fbedd099ed7c2be2f5c133a9ce0eb7e7a466c. PR82 OPEN/MERGEABLE; hosted checks
pending at initial query (not a complete hosted gate).
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain82->81->80->79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-registry-view at cb5fbedd.
Before code tmp/registry-view/baseline.json must verify 49worktrees/48foreign
states/27dirty hashes/427protected hashes against the previous
tmp/plan-review-summary baseline; primary3679b1b/localmain966206f/
stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/research_entry.py (one added COMMANDS entry only),
new src/ashare_research/tools/research_registry.py, and new
tests/test_research_registry_view.py. Ignored demo/validation artifacts
allowed under tmp/registry-view/. Every pre-existing function/class in
research_entry.py stays AST unchanged; only the module-level COMMANDS tuple
may change. src/ashare_research/mechanism/registry/** stays byte-identical to
base: the frozen public callable surface remains exactly the 13 IO-free
entries and no registry module is edited.

## Forbidden scope
registry package edits (records/states/snapshot/__init__), all other src
files, existing tests, hypothesis config/compilers/plan tools, preparation and
comparison tools, schemas/CI/protected data/foreign worktrees/stash/DB/runtime.
No registry writes, persistence, migration or storage backend; no default or
real candidate dataset loading; no acquisition, real research/statistics/
holdout, digest repair, extraction, cleanup/overwrite, main/force push,
merges or automatic following stage.

## Required behavior
research registry accepts exactly one of --record JSON or --snapshot JSON plus
optional --json; the mutually-exclusive-required parser rejects every other
argument shape as INVALID_ARGUMENTS before any IO. Exactly one explicit file
is read exactly once, capped at 1MiB: OSError is REGISTRY_READ_FAILED and
oversize input is REGISTRY_TOO_LARGE.
Record mode strictly parses the canonical bytes with the frozen
parse_hypothesis_record and emits schema m4_registry_record_view_v1,
status validated_metadata_only, source_file_sha256, the frozen canonical
document, a verification block that independently recomputes canonical bytes,
identity digest and record digest, an all-false boundary
(execution_authorized/statistics_computed/outcome_read/holdout_accessed/
real_registry_dataset_loaded/registry_written) and Chinese notes. Any
recomputation disagreement fails closed as REGISTRY_VIEW_MISMATCH.
When that frozen byte path collapses a missing/extra-key structural failure
into a bare TypeError (it constructs the frozen dataclass before its key-set
checks), the view re-enters the frozen mapping validation with the same JSON
container conversion so the documented codes such as MISSING_REQUIRED_FIELD
and UNKNOWN_RECORD_FIELD are preserved; the registry package itself is never
modified and no registry semantic check is re-implemented.
Snapshot mode strictly decodes the file (BOM, CR, missing/extra trailing LF,
float token, non-finite constant or duplicate key are
NON_CANONICAL_SERIALIZATION; a non-mapping root is INVALID_RECORD_STRUCTURE),
requires exactly the 7 frozen top-level keys (UNKNOWN_RECORD_FIELD /
MISSING_REQUIRED_FIELD), a records list of mappings, revalidates every record
through canonical re-encode plus parse_hypothesis_record, and rebuilds the
snapshot with build_hypothesis_registry_snapshot so duplicate identities are
DUPLICATE_HYPOTHESIS_ID/PROVENANCE_REWRITE and over-scale is
SCALE_LIMIT_EXCEEDED. Loaded-specific first errors stay deterministic:
versions/boundary INVALID_ENUM_VALUE, record order INVALID_RECORD_STRUCTURE,
count type/value INVALID_FIELD_TYPE, registry_digest RECORD_DIGEST_MISMATCH,
final byte equality NON_CANONICAL_SERIALIZATION. Output schema is
m4_registry_snapshot_view_v1 with the registry block (record count,
real_demo_candidate_count, MAX_RECORDS_PER_SNAPSHOT,
MAX_REAL_DEMO_CANDIDATES, registry_digest, within_scale_limits), the compact
per-record list, the echoed interpretation boundary, the same verification
block, all-false boundary and notes.
Markdown views are compact Chinese projections of the same JSON view and add
no data. All failures are sanitized: exit code 2, empty stdout, error: CODE
stderr, catch-all REGISTRY_VIEW_FAILED. The tool writes only to stdout, never
touches a database, provider, network, clock or holdout, and adds no registry
entry point.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py tests/test_research_plan_review_summary.py
python -m ruff check src/ashare_research/tools/research_registry.py src/ashare_research/tools/research_entry.py tests/test_research_registry_view.py
git diff --check
python tmp/registry-view/calculation_review.py
python tmp/registry-view/demo.py
python tmp/registry-view/verify_protections.py
Cases: exact record/snapshot JSON projections with recomputed digests and
counts; delegated entry bytes equal direct main; Markdown equals the
renderer; one-read enforcement for both modes; canonical byte failures
(BOM/CR/LF/float); digest tamper, missing/extra key, illegal history; snapshot
order/count/digest/version/boundary/scale/duplicate/provenance-rewrite
failures plus pretty-printed non-canonical bytes; argument shapes rejected
before IO; missing/oversize/directory inputs; offline/no-write guards; the
frozen 13-entry registry surface unchanged.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 48foreign
registrations/HEAD/branches/statuses,27dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; registry package and untouched tools
byte-equal to base; only the COMMANDS tuple changed in research_entry.py (AST
review); owned clean; feature/dependency local/origin/live agree. No full
local suite claim; exact-head hosted pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or
scope expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-plan-review-summary.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet
includes actual Goal/base/head/files/tests/acceptance/protections/refs and
hosted state.
