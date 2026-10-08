# M4 direct preparation delivery

## Objective
Root directly completes plan-to-preparation delivery without an intermediate
preparation directory: directory or native ZIP plan + explicit synthetic inputs
can produce a preparation directory or native ZIP. User continuation authorizes
this bounded engineering stage; no DSH/delegation.

## Verified baseline
Origin/live codex/m4-preparation-delivery-comparison:
f8cd69d323da80aabaf2fd98a7bb6ab8bf3a7b6e. PR77 OPEN/MERGEABLE;
13SUCCESS/21pending at initial query, not a complete hosted gate.
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Dependencies77->76->75->74->73->71->70->69->68 remain unmerged.
Fresh clean codex/m4-preparation-direct-delivery atf8cd69d.
Before code tmp/preparation-direct-delivery/baseline.json must verify44worktrees,
27dirty hashes/427protected hashes against previous foreign baselines,
primary3679b1b/localmain966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Nine files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_package,preparation_archive,research_plan_archive,research_entry}.py,
tests/test_preparation_direct_delivery.py. Ignored demo/validation artifacts allowed.
Extract plan ZIP's captured verified file snapshot/read helper, keeping all
existing transport/recompilation gates/error mapping/legacy receipts unchanged.
Extract shared preparation snapshot construction and ZIP writer; no duplicate
compiler/adapter/preparation calculation.

## Forbidden scope
Existing tests, schemas/compilers/adapter/matrix/executor/registry/quality gates,
source preparation/projector/plan directory verifier/comparison calculations,
protected reports/data/CI/foreign worktrees/stash/DB/runtime.
No acquisition, real research/statistics/holdout, input/digest repair, extraction,
temporary reconstructed packages, source writes, cleanup/overwrite, main/force
push, merges or automatic following stage.

## Required behavior
prepare-package (--package PLAN_DIR | --plan-archive PLAN_ZIP) --inputs JSON
(--output NEW_DIR | --output-archive NEW_ZIP) [--json].
Keep existing --verify, --archive PREPARATION_DIR --output NEW_ZIP and
--verify-archive commands/results unchanged.
Each plan-directory file or plan ZIP is bounded-read once; original complete
plan verification must succeed before opening inputs, which are bounded-read
once. Preserve raw plan/input bytes, original ten artifacts, quality rejection
and exact legacy receipts/deterministic ZIP bytes for equivalent sources.
Native plan ZIP gates remain unchanged; preparation ZIP canonical/bounded gates
remain unchanged. Direct flow creates only its final output, no intermediate
directory/files/extraction. ZIP writer independently verifies the full bounded
snapshot and complete encoded ZIP before exclusive creation.
Validate incompatible flags before IO; existing/linked targets reject before
source/input reads. Direct ZIP nested-target checks precede reads; legacy
directory nested checks retain their original post-plan-capture precedence.
Reject existing/linked/reparse targets/ancestors and output within directory
plan source including ..aliases. Original source path/link gates remain active.
Failed owned writes preserve partial output, sanitized error/code2/no stdout;
no automatic retry/delete. Not atomic publication or hostile concurrent-FS sandbox.
Identity/count/hash consistency is not provenance, independent sealing, readiness
or execution authority. No changed schema, invented diagnostics or statistics.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_direct_delivery.py tests/test_preparation_package.py tests/test_preparation_archive.py tests/test_research_plan_archive.py tests/test_preparation_delivery_compare.py
python -m ruff check src/ashare_research/tools/preparation_package.py src/ashare_research/tools/preparation_archive.py src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_entry.py tests/test_preparation_direct_delivery.py
git diff --check
python tmp/preparation-direct-delivery/demo.py
python tmp/preparation-direct-delivery/verify_protections.py
Cases: four source/output combinations with exact legacy artifacts/receipts,
ready/rejected coverage and matrix preservation; offline/no-services/no-extraction
and no intermediate directories; once-read source mutation handoff;
invalid/corrupt/forged/stale/oversized/link inputs before output; corrupt plan
before input reads; invalid flags before IO; existing/nested/linked output and
partial writes preserved. Actual CLI relocation/direct verification, baseline
legacy-byte compatibility and Windows junction rejection.

## Acceptance criteria
Nine-file scope; meaningful tests/Ruff/diff/demo/compatibility pass.
43foreign registrations/HEAD/branches/statuses,27dirty hashes,427protected hashes,
primary DB/stash/localmain unchanged; forbidden modules byte-equal to base.
Owned clean; feature/dependency local/origin/live agree. No full local suite
claim; exact-head hosted pending state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-preparation-delivery-comparison.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted state.
