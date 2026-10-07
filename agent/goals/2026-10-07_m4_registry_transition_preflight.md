# M4-B registry transition preflight

## Objective
Root directly adds a read-only transition preflight to the registry view:
research registry --record RECORD.json --transition REQUEST.json [--json].
The canonical record and the explicit StateTransitionRequestV1 JSON are
strictly decoded and the request is checked only through the frozen
validate_state_transition. A rejected request is a sanitized exit-code-2
failure with the frozen stable code and empty stdout; an accepted request
prints a receipt that produces, writes and promotes nothing. User
continuation authorizes this bounded engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-registry-view:
15d65ab984b34415558d3fd2128d35c6a0eadad4. PR83 OPEN/MERGEABLE; hosted
6SUCCESS/22pending at initial query (not a complete hosted gate).
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain83->82->81->80->79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-registry-transition-preflight at 15d65ab.
Before code tmp/registry-transition-preflight/baseline.json must verify
50worktrees/49foreign states/28dirty hashes/427protected hashes against the
previous tmp/registry-view baseline; primary3679b1b/localmain966206f/
stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/research_entry.py (only the registry COMMANDS entry
usage tuple grows by one line), src/ashare_research/tools/research_registry.py
(additions plus cli main only), and new
tests/test_research_registry_transition_preflight.py. Every pre-existing
function/class in research_registry.py except cli main stays AST unchanged;
the only added declarations are build_transition_preflight and
render_transition_markdown (plus the frozen REQUEST_FIELDS derivation).
src/ashare_research/mechanism/registry/** and
tests/test_research_registry_view.py stay byte-identical to base.

## Forbidden scope
registry package edits, existing tests, all other src files, schemas/CI/
protected data/foreign worktrees/stash/DB/runtime. No registry writes,
persistence, migration or storage backend; no record production,
transition application, digest repair, promotion, default or real candidate
dataset loading, acquisition, real research/statistics/holdout,
cleanup/overwrite, main/force push, merges or automatic following stage.

## Required behavior
Argument shapes: --record with optional --transition, or --snapshot alone.
--transition combined with --snapshot, or --transition without --record,
rejects INVALID_ARGUMENTS before any IO; --record with --snapshot stays
mutually exclusive. Both explicit files are read exactly once each, capped at
1MiB: OSError is REGISTRY_READ_FAILED and oversize is REGISTRY_TOO_LARGE.
The record is parsed with the same frozen byte entry (including the mapping
fallback for key-set TypeErrors) as the existing view. The request is decoded
with the same strict byte rules (BOM, CR, missing/extra trailing LF, float
token, non-finite constant or duplicate key are NON_CANONICAL_SERIALIZATION;
a non-mapping root is INVALID_RECORD_STRUCTURE) and is passed to the frozen
validate_state_transition as the decoded mapping, so every rejection keeps
the frozen stable code with exit code 2, empty stdout and error: CODE stderr
(catch-all REGISTRY_VIEW_FAILED).
An accepted request emits schema m4_registry_transition_preflight_v1, status
accepted_preflight_only, both source SHA256s, a record block (id, version,
current status, identity digest, record digest, state count), the echoed
seven frozen request fields, and result {accepted: true,
would_be_ordinal: state_count+1, would_be_status: to_state}. The all-false
boundary (execution_authorized/statistics_computed/outcome_read/
holdout_accessed/real_registry_dataset_loaded/registry_written) and Chinese
notes state that the preflight produces, writes and promotes nothing;
acceptance only means the frozen preconditions hold; authorization_ref is
only identifier-checked and the tool does not verify the referenced contract;
registry metadata is not evidence or authorization. Markdown is a compact
Chinese projection of the same receipt. The tool adds or changes no registry
entry point and touches no database, provider, network, clock or holdout.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_registry_transition_preflight.py tests/test_research_registry_view.py tests/test_m4b_hypothesis_registry.py tests/test_research_entry.py tests/test_research_plan_review_summary.py
python -m ruff check src/ashare_research/tools/research_registry.py src/ashare_research/tools/research_entry.py tests/test_research_registry_transition_preflight.py
git diff --check
python tmp/registry-transition-preflight/calculation_review.py
python tmp/registry-transition-preflight/demo.py
python tmp/registry-transition-preflight/verify_protections.py
Cases: legal first-edge acceptance and legal execution-edge acceptance with
exact receipts; delegated entry bytes and Markdown equality; execution
authorization/evidence rejections; illegal edge, from mismatch, reason
mismatch, terminal state and incomplete ESTABLISHED rejections; request
key/type/byte failures; argument shapes rejected before IO; read failures;
one-read counting for both files; offline/no-write/determinism; frozen
13-entry registry surface and unchanged previous view outputs.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 49foreign
registrations/HEAD/branches/statuses,28dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; registry package and the previous view
test byte-equal to base; only the expected AST changes; owned clean;
feature/dependency local/origin/live agree. No full local suite claim;
exact-head hosted pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or
scope expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-registry-view. No
main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted
state.
