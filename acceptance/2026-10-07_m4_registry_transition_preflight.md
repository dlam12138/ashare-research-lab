# M4-B registry transition preflight acceptance

Goal: agent/goals/2026-10-07_m4_registry_transition_preflight.md.
Verified base codex/m4-registry-view:
15d65ab984b34415558d3fd2128d35c6a0eadad4. PR83 OPEN/MERGEABLE; hosted
checks pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered research registry --record RECORD.json --transition REQUEST.json
[--json]: a read-only transition preflight that strictly decodes one
canonical record and one explicit StateTransitionRequestV1 document and
checks the request only through the frozen validate_state_transition entry.
The tool reads exactly two explicit files once each (max 1MiB), writes only
to stdout, and produces, writes or promotes nothing. The frozen
mechanism/registry package and the previous view test stay byte-identical to
base; no registry entry point was added or changed.

Accepted requests emit schema m4_registry_transition_preflight_v1, status
accepted_preflight_only, both source SHA256s, a record block (hypothesis id,
version, current status, identity digest, record digest, state count), the
echoed seven frozen request fields (hypothesis_id, hypothesis_version,
from_state, to_state, reason_code, authorization_ref, evidence_kind) and
result {accepted: true, would_be_ordinal: state_count+1, would_be_status:
to_state}. The all-false boundary (execution_authorized,
statistics_computed, outcome_read, holdout_accessed,
real_registry_dataset_loaded, registry_written) and Chinese notes state that
the preflight produces, writes and promotes nothing; acceptance only means
the frozen preconditions hold; authorization_ref is only identifier-checked
and the tool does not verify the referenced contract; registry metadata is
not evidence, conclusion or authorization. Markdown is a compact Chinese
projection of the same receipt.

The record is parsed with the same frozen byte entry (including the mapping
fallback for key-set TypeErrors) as the existing view. The request is decoded
with the same strict byte rules as the view documents: BOM, CR, missing or
extra trailing LF, a float token, a non-finite constant or a duplicate key
are NON_CANONICAL_SERIALIZATION; a non-mapping root is
INVALID_RECORD_STRUCTURE. The decoded mapping goes to the frozen validator,
so every rejection keeps the frozen stable code with exit code 2, empty
stdout and error: CODE stderr (catch-all REGISTRY_VIEW_FAILED): missing or
extra keys MISSING_REQUIRED_FIELD/UNKNOWN_RECORD_FIELD, wrong value types
INVALID_FIELD_TYPE, a wrong hypothesis id/version/from_state or an illegal
edge/reason ILLEGAL_STATE_TRANSITION, an empty or malformed execution
authorization_ref MISSING_AUTHORIZATION_REF/INVALID_IDENTIFIER, a wrong
execution evidence_kind ILLEGAL_STATE_TRANSITION, a request out of a
terminal state TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION, and an ESTABLISHED
request without three distinct execution authorization refs
ESTABLISHED_EVIDENCE_INCOMPLETE. Structural validation precedes the final
canonical byte equality exactly as in the frozen record byte path, so a
pretty-printed valid request is NON_CANONICAL_SERIALIZATION while a
pretty-printed missing-key request keeps MISSING_REQUIRED_FIELD.

Arguments accept --record with optional --transition, or --snapshot alone;
--transition with --snapshot, --transition without --record, both sources or
unknown options are INVALID_ARGUMENTS before any IO. Missing or unreadable
paths are REGISTRY_READ_FAILED and oversize requests are REGISTRY_TOO_LARGE.
The tool touches no database, provider, network, clock or holdout.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py tests/test_research_plan_review_summary.py
python -m ruff check src/ashare_research/tools/research_registry.py src/ashare_research/tools/research_entry.py tests/test_research_registry_transition_preflight.py
git diff --check
python tmp/registry-transition-preflight/calculation_review.py
python tmp/registry-transition-preflight/demo.py
python tmp/registry-transition-preflight/verify_protections.py
```

Targeted53passed48.31s (eight new cases plus the unchanged view, registry,
entry and plan-summary suites). Final Ruff/diff PASS; no pytest failure,
existing test edit or full local-suite claim. Cases cover the legal first
edge and the legal execution edge with exact receipts, delegated
entry/CLI/module bytes, Markdown renderer equality, execution
authorization/evidence rejections, illegal edge, id/version/from/reason
mismatch, terminal and incomplete-ESTABLISHED rejections, request key/type
failures, byte failures (BOM/CR/LF/float/duplicate key/NaN/pretty), argument
shapes rejected before IO, missing/directory/oversize reads, single-read
counting of both files, offline/no-write/determinism guards and the frozen
13-entry registry surface with the previous view outputs recomputed.

Actual subprocess demo (tmp/registry-transition-preflight/demo/): four
previous record/snapshot view invocations (JSON and Markdown) are byte-equal
to the previous worktree; the first edge DISCOVERED->LITERATURE_REVIEWED
preflight matches would_be_ordinal 2 and the PRE_REGISTERED->
DEVELOPMENT_EXECUTED preflight matches would_be_ordinal 6 with exact
receipts; nine fail-closed fixtures return exactly ILLEGAL_STATE_TRANSITION,
MISSING_AUTHORIZATION_REF, TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION,
ESTABLISHED_EVIDENCE_INCOMPLETE, MISSING_REQUIRED_FIELD, UNKNOWN_RECORD_FIELD,
INVALID_FIELD_TYPE and NON_CANONICAL_SERIALIZATION with empty stdout;
INVALID_ARGUMENTS matches; preflight runs created no files, source hashes
stayed unchanged and replay is byte-equal.

Independent AST review (tmp/registry-transition-preflight/calculation-review.json):
research_entry.py keeps every pre-existing function/class AST-identical and
changes only the registry COMMANDS entry (appended one --transition usage
line, updated summary); research_registry.py keeps every pre-existing
declaration AST-identical except cli main, adds exactly
build_transition_preflight and render_transition_markdown, and restricts
top-level changes to the docstring, the frozen import and the new
REQUEST_FIELDS/SCHEMA_TRANSITION_PREFLIGHT/PREFLIGHT_STATUS/PREFLIGHT_NOTES
constants; the tool exposes exactly the nine expected functions with no
**kwargs and no forbidden names; the registry package and the previous view
test are byte-equal to base and the frozen callable surface stays exactly 13
entries.

Before implementation captured50worktrees/49foreign states/28dirty
hashes/427protected hashes against the previous tmp/registry-view baseline;
protection review PASS:49foreign registrations/HEAD/branches/statuses,28dirty
hashes,427protected hashes, primary database/stash/localmain unchanged and
the untouched tools, the registry package and the previous view test
byte-equal to base. No comprehensive ignored-runtime hash claim.

Seven-file scoped normal feature commit/push and stacked PR against83. Final
exact committed scope/head, clean owned tree, local/origin/live
feature/dependency/main refs, protections and exact-head hosted state
independently reviewed after publication, retained in
tmp/registry-transition-preflight/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain83->82->81->80->79->78->77->76->75->74->73->71->
70->69->68 is unmerged. No automatic merge or following stage. Real
research/statistics/holdout sealed; no real registry dataset, transition
application, record production, promotion or literature acquisition.
