# Reproducible synthetic preparation delivery

## Objective
Root directly adds research prepare-package export/verification, delivering the
original plan and explicit synthetic input bytes with reproducible reports.
No DSH/delegation. User continuation authorizes this bounded engineering stage.

## Verified baseline
origin/live codex/m4-preparation-comparison:
7bdb6f0a90db1d257da1618c495e6aa239525670; PR74 OPEN/MERGEABLE,
36SUCCESS/4pending at latest check, not a successful complete hosted gate.
main8d0fb4d unchanged; unmerged chain74->73->71->70->69->68.
Fresh clean codex/m4-preparation-package starts at7bdb6f0.
Ignored tmp/preparation-package/baseline.json records41worktrees/27dirty hashes/
427protected hashes, localmain966206f/stashcb568efd and primary DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Original ready/rejected preparation outputs captured before refactor.

## Allowed scope
Eight files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_package,synthetic_prepare,research_entry}.py,
tests/test_preparation_package.py. Ignored evidence and exclusively new demo dirs.

## Forbidden scope
Existing tests; original compilers/adapter/matrix/executor/registry/verifiers/
diagnostic projector/schema/method/quality gates, protected data/CI; acquisition,
real research/holdout/statistics, source/digest repair, source writes, foreign
worktrees/stash/databases, main/force push/merge/destructive cleanup.

## Required behavior
prepare-package --package PLAN_DIR --inputs JSON --output NEW_DIR [--json],
or --verify DIR [--json]. First version consumes a directory plan only.
Capture its four fixed regular files and input bytes once with original bounds,
reject linked/reparse paths/ancestors. Use unchanged public verify_package_files
to recompile the plan; extract preparation byte-reader/byte-builder helpers while
preserving existing public CLI JSON/Markdown and all original input/policy gates.
No parsing/calculation duplication. Retain raw hypothesis/input byte identities.
Create ten flat fixed regular files: four plan-* copies, inputs.json, complete
preparation JSON/Markdown, complete diagnostics JSON/Markdown and manifest.
Per-file limits1MiB for original hypothesis/input,16MiB for other artifacts,
64MiB total. Exact inventory; no directories/extras/links/nonregular entries.
All rendering/verification finish before exclusive output mkdir; parent must
exist. No overwrite/delete/cleanup; partial failed owned output preserved, no
success receipt. Not atomic publication or a hostile concurrent filesystem sandbox.
Verification bounded-reads once, re-verifies original plan bytes, rebuilds
preparation from saved input and compares every deterministic file byte-for-byte,
including manifest. Forged inventory alone cannot make modified reports valid.
Quality-rejected inputs remain reproducible diagnostics with no matrix/statistics.
Manifest is content consistency inventory, not provenance/authenticity/sealing or
research authority. True observation-read flags retained; original false execution/
statistics/holdout/source-validation/readiness boundaries retained. No host paths/
timestamps. Flags/errors fail closed with sanitized stderr/code2/no partial stdout.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_package.py tests/test_synthetic_prepare.py tests/test_preparation_diagnostics.py tests/test_preparation_compare.py
python -m ruff check src/ashare_research/tools/preparation_package.py src/ashare_research/tools/synthetic_prepare.py src/ashare_research/tools/research_entry.py tests/test_preparation_package.py
git diff --check
Actual CLI export/relocated verify and Windows linked-path demo; compare original
ready/rejected snapshots and final foreign/protected hashes.
Cases: exact original source/report/digest/quality/diagnostics, once-read mutation
handoff/offline/no-execution guards, deterministic relocation, forged report/manifest,
corrupt input/plan, missing/extra/large/nonregular/linked files, invalid flags,
existing destination and injected write failure without overwrite or deletion.

## Acceptance criteria
Eight-file scope; targeted checks/demo and original output compatibility pass.
40foreign tree identities/statuses/27dirty hashes/427protected hashes, primary
database/stash/localmain unchanged; owned clean/local-origin-live synchronized.
No local full-suite claim; exact-head hosted state recorded separately.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected concurrent edits
or scope expansion. No automatic merge or following stage.

## Commit and push requirements
Normal scoped commit/push and stacked PR against codex/m4-preparation-comparison.
Explicit chain74->73->71->70->69->68; no main/force push or automatic merge.
Final PASS/CHANGES_REQUIRED/BLOCKED packet distinguishes local and hosted evidence.
