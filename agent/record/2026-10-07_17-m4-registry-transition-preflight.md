# M4-B registry transition preflight

User continues bounded engineering and explicitly requests root alone, no DSH.
Verified primary3679b1b/main8d0fb4d/base 15d65ab9, PR83 OPEN/MERGEABLE with
hosted checks pending at initial query. Fresh clean isolated
codex/m4-registry-transition-preflight. Read the previous stage records, the
frozen M4-B registry package and the unified entry/view tests. Goal:
agent/goals/2026-10-07_m4_registry_transition_preflight.md. Before
implementation captured50worktrees/49foreign states/28dirty hashes/427
protected hashes against the previous tmp/registry-view baseline and checked
database/stash/localmain against it; evidence at
tmp/registry-transition-preflight/baseline.json.

Pre-code baseline PASS. Added research registry --record RECORD.json
--transition REQUEST.json [--json] as a read-only preflight in the existing
tools module. The canonical record is parsed with the same frozen byte entry
(including the mapping fallback for key-set TypeErrors) as the view; the
request is strictly decoded with the same byte rules and passed to the frozen
validate_state_transition as the decoded mapping, so every rejection keeps
the frozen stable code and structural validation precedes the final
canonical byte equality exactly as in the frozen record byte path. Acceptance
emits schema m4_registry_transition_preflight_v1, status
accepted_preflight_only, both source SHA256s, the record block, the echoed
seven frozen request fields and result {accepted, would_be_ordinal:
state_count+1, would_be_status}, with the all-false boundary and Chinese
notes stating the preflight produces, writes and promotes nothing,
authorization_ref is only identifier-checked, and registry metadata is not
evidence or authorization. Markdown is a compact Chinese projection.

Actual targeted53passed48.31s; Ruff and git diff --check PASS; no failed
test, existing test edit or full local-suite claim. Eight new cases cover
exact first/execution-edge receipts, delegated entry/CLI/module bytes,
Markdown renderer equality, authorization/evidence/illegal-edge/id/version/
from/reason/terminal/incomplete-ESTABLISHED rejections, request key/type/byte
failures, argument shapes before IO, read failures, two-file single-read
counting, offline/no-write/determinism guards and the frozen 13-entry
registry surface with previous view outputs recomputed. AST review
(tmp/registry-transition-preflight/calculation-review.json):
research_entry.py keeps every pre-existing function/class unchanged and
edits only the registry COMMANDS entry; research_registry.py keeps every
pre-existing declaration except cli main AST-identical and adds exactly
build_transition_preflight and render_transition_markdown; the registry
package and the previous view test are byte-equal to base.

Actual demo: four previous record/snapshot view invocations byte-equal to the
previous worktree; first edge (ordinal 2) and execution edge (ordinal 6)
receipts exact; nine fail-closed fixtures and three argument shapes return
exactly the documented sanitized codes with empty stdout; preflight runs
created no files, source hashes stayed unchanged and replay is byte-equal.
Evidence in tmp/registry-transition-preflight/demo/.

Protection review PASS:49foreign registrations/HEAD/branches/statuses,28dirty
hashes,427protected hashes and database/stash/localmain unchanged; the
untouched plan/prepare/comparison tools, the registry package and the
previous view test are byte-equal to base. Exact commands/cases/limits:
acceptance/2026-10-07_m4_registry_transition_preflight.md.

Seven-file scoped normal feature commit/push and PR stacked on83. Final
actual head/scope/clean tree/refs/protections and hosted state retained in
tmp/registry-transition-preflight/final-evidence.json.
No main/force push, automatic merge or following stage. No transition
application, record production, promotion, default or real candidate
dataset loading, real research/statistics/holdout or literature acquisition.
