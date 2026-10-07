# Reproducible synthetic preparation package acceptance

Goal: agent/goals/2026-10-07_m4_preparation_package.md.
Verified origin/live dependency codex/m4-preparation-comparison:
7bdb6f0a90db1d257da1618c495e6aa239525670. PR74 OPEN/MERGEABLE,
36SUCCESS/4pending at latest check, not a complete hosted success.
main8d0fb4d unchanged. Root worked directly, no DSH/delegation.

Delivered research prepare-package --package PLAN_DIR --inputs JSON
--output NEW_DIR [--json], and --verify DIR [--json].
Four original plan files and input byte snapshots are read once; unchanged
public plan-file verification recompiles the saved plan. Extracted the original
bounded input byte-reader/strict parser and preparation-from-bytes helper without
duplicating adapter or compiler calculations. Original standalone CLI behavior
retains exact ready/rejected reports, digests and read/execution boundaries.

Ten fixed flat files preserve raw plan/input bytes, complete preparation and
diagnostics JSON/Markdown, plus a deterministic content inventory. Verification
bounded-reads once, re-verifies original plan, rebuilds preparation and compares
every generated file byte-for-byte, including the manifest. An attacker-updated
inventory cannot make a modified statistics/readiness report pass. Consistency
verification is not provenance, historical sealing, authorship or execution authority.
Quality rejection remains a reproducible report with null matrix and no statistics.

Sources bounded1MiB, artifacts16MiB/file, total64MiB; fixed inventory rejects
extra/missing/nonregular/linked entries and linked/reparse ancestor paths.
Validation/rendering finish before exclusive destination creation. Existing
destinations and destinations inside the original plan (including .. aliases)
reject. No source writes, overwrite or cleanup. Write failures preserve partial
owned output and emit only sanitized error/code2/no partial stdout. Publication
is not atomic or a hostile concurrent filesystem sandbox.

Actual exact commands, PYTHONPATH=src and Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_package.py tests/test_synthetic_prepare.py tests/test_preparation_diagnostics.py tests/test_preparation_compare.py
python -m pytest -q tests/test_preparation_package.py
python -m ruff check src/ashare_research/tools/preparation_package.py src/ashare_research/tools/synthetic_prepare.py src/ashare_research/tools/research_entry.py tests/test_preparation_package.py
git diff --check
python tmp/preparation-package/compatibility.py
python tmp/preparation-package/demo.py
python tmp/preparation-package/verify_protections.py
```

Initial targeted13passed9.23s; initial Ruff identified two long lines in the new
test, wrapped without behavioral changes. Review added output-inside-plan
rejection and tests; affected package4passed2.80s. Final Ruff/diff PASS.
No failed pytest cases, full local suite or existing test edits. An initial
standalone compatibility probe unnecessarily imported a test helper without its
path and failed ModuleNotFoundError; corrected to direct example paths, rerun
passed and retained as compatibility.py/compatibility.json.

Meaningful tests: exact original source/report/diagnostic/digests and inventories;
ready/quality rejection, deterministic copied relocation, immutable inputs and
offline/no-statistics guards; source mutation after the five once-read snapshots;
forged report/inventory, stale input evidence and corrupt plan; extra/missing/
nonregular/oversized/total-limited entries; invalid flags before IO; linked/
existing/nested destinations; injected write failure retains partial files.

Actual subprocess ten-file export/relocated verification: REJECTED_QUALITY,
original3/4coverage, null matrix, five source hashes unchanged; forged inventory
and actual Windows junction fail code2/empty stdout. JSON/Markdown/evidence at
tmp/preparation-package/demo/. Original ready/rejected snapshots saved before
refactor compare exactly afterward, compatibility.json retained.

Protection check:40foreign registrations/branches/HEAD/status,27dirty hashes,
427protected hashes, primary database/stash/localmain unchanged. Original
verifiers/diagnostic projector/comparison modules byte-equal to base. No
comprehensive ignored-runtime hash claim.

Local acceptance PASS. Eight-file scope. Final commit/live refs, scoped stacked
PR and exact-head hosted state independently queried after publication and recorded
in final evidence; pending checks remain pending. Chain74->73->71->70->69->68
unmerged. No automatic merge or next stage; real research/holdout/statistics sealed.
