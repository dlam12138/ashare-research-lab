# M4 delivered preparation diagnostic comparison

## Objective
Directly add research prepare-delivery-compare for two saved preparation directories
or native ZIPs. Reproduce both completely before comparing the same verified plan
and declared domain. User continuation authorizes this bounded engineering stage;
root works directly without DSH/delegation.

## Verified baseline
Origin/live codex/m4-preparation-archive:
44581427dc4b42282085ac9c555243d8c4182f56, PR76 OPEN/MERGEABLE.
Latest initial hosted query:15SUCCESS/19pending, not a complete hosted gate.
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged; dependencies
76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-preparation-delivery-comparison at4458142.
Before implementation tmp/preparation-delivery-comparison/baseline.json must
verify43worktrees/27dirty hashes/427protected hashes, previous foreign states,
primary3679b1b/localmain966206f/stashcb568efd and database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Nine files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_delivery_compare,preparation_compare,research_entry}.py,
tests/test_preparation_delivery_compare.py. Ignored demo/validation artifacts allowed.
Extract existing comparison-from-reports helper and configurable fixed Markdown
source legend; preserve exact legacy comparison semantics, JSON and default Markdown.

## Forbidden scope
Existing tests, original preparation/projector/directory/ZIP verifiers, compiler/
adapter/matrix/executor/registry/quality schemas/CI and frozen baselines.
No acquisition, real research/statistics/holdout, source/digest repair, writes,
extraction/reconstructed directories, foreign edits, stash/DB/runtime deletion,
main/force push, merges or automatic following stage.

## Required behavior
prepare-delivery-compare (--left DIR | --left-archive ZIP)
(--right DIR | --right-archive ZIP) [--json].
Use original complete bounded directory or ZIP verifier once per distinct caller
path/mode. Identical path and mode reuse one captured verified report; aliases or
different modes still traverse their own gates. Compare report snapshots only;
never reread saved inputs or call path-based preparation a second time.
Extract original comparison calculation without changing it. Preserve both full
diagnostic identities/qualities, raw-input byte equality versus canonical digest
equality, deterministic audit-date/role counts/transitions and original boundaries.
Reject changed plan identities, domain digests, role/date order or any invalid
side; no partial stdout. No raw observations/matrix values, invented effect,
ranking, repair, provenance or readiness claim. JSON retains the original paired
diagnostic schema; Markdown labels left/right saved deliveries.
Invalid flags reject before IO; sanitized original error codes with exit2.
No output options/writes/extraction/network/database/execution.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_delivery_compare.py tests/test_preparation_compare.py tests/test_preparation_package.py tests/test_preparation_archive.py
python -m ruff check src/ashare_research/tools/preparation_delivery_compare.py src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_delivery_compare.py
git diff --check
python tmp/preparation-delivery-comparison/demo.py
python tmp/preparation-delivery-comparison/verify_protections.py
Exact legacy output comparisons; mixed directory/ZIP and reversal, quality
rejection, formatting equivalence/metadata changes, same path once and per-side
captured-read handoff, forged/corrupt sides and stale evidence, plan/domain drift,
invalid flags before IO, alias/junction rejection, immutable sources/offline guards.

## Acceptance criteria
Nine-file scope; meaningful targeted tests/Ruff/diff/actual CLI demo pass.
42foreign registrations/HEAD/branches/statuses,27dirty hashes,427protected hashes,
primary database/localmain/stash unchanged; original verifiers/projector/preparation
byte-equal to base. Owned clean; local/origin/live feature/dependency agree.
No full local suite claim; independently report exact-head hosted state.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Normal scoped commit/push and stacked PR against codex/m4-preparation-archive.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet reports
actual files/head/tests/acceptance/protections/refs and pending hosted checks.
