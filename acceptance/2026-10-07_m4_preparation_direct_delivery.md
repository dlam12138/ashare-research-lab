# Direct preparation delivery acceptance

Goal: agent/goals/2026-10-07_m4_preparation_direct_delivery.md.
Verified base codex/m4-preparation-delivery-comparison:
f8cd69d323da80aabaf2fd98a7bb6ab8bf3a7b6e. PR77 OPEN/MERGEABLE;
13SUCCESS/21pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered research prepare-package
(--package PLAN_DIR | --plan-archive PLAN_ZIP) --inputs JSON
(--output NEW_DIR | --output-archive NEW_ZIP) [--json].
Existing directory export/verify, directory-to-ZIP export and ZIP verify remain
available with unchanged receipts/artifacts. Equivalent plan-directory/ZIP
sources produce identical preparation directories or native ZIP bytes.
Direct ZIP flow creates no intermediate directories, files or extracted plans.

Extracted plan ZIP's bounded captured verified member reader, retaining original
transport gates, complete recompilation and error mapping. Each plan file or ZIP
is read once; complete plan verification finishes before inputs are opened once.
Preparation construction reuses the original byte-based calculation/projector.
Shared ZIP snapshot writer checks full snapshot bounds and reproduction before
encoding, then independently verifies the encoded ZIP before exclusive creation.
Ten-member layout/limits/metadata and quality rejection remain unchanged.
No new schema, compiler/adapter logic, input repair, statistics or authority claim.

Incompatible flags reject before IO. Existing/linked/reparse outputs/ancestors
reject before sources. Direct ZIP outputs within a directory plan reject before
reads; legacy directory export keeps its original post-plan-capture nested-path
check precedence. Source path/link gates remain active. Failed writes preserve
owned partial output, code2/sanitized stderr/no stdout, no overwrite/delete/retry.
Publication is not atomic and is not a hostile concurrent filesystem sandbox.
Consistency/hashes do not establish provenance, sealing or research readiness.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_direct_delivery.py tests/test_preparation_package.py tests/test_preparation_archive.py tests/test_research_plan_archive.py tests/test_preparation_delivery_compare.py
python -m pytest -q tests/test_preparation_direct_delivery.py
python -m ruff check src/ashare_research/tools/preparation_package.py src/ashare_research/tools/preparation_archive.py src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_entry.py tests/test_preparation_direct_delivery.py
git diff --check
python tmp/preparation-direct-delivery/calculation_review.py
python tmp/preparation-direct-delivery/demo.py
python tmp/preparation-direct-delivery/verify_protections.py
```

Initial23-case targeted run:22passed/1failed60.88s. The new test incorrectly
expected INPUT_LIMIT_EXCEEDED for oversized input; the unchanged input reader
correctly returned INPUT_TOO_LARGE. Corrected the expectation to the original
contract, without changing or weakening production gates. Initial Ruff found
four loop-closure binding findings in test helpers; bound per-case values
explicitly. A subsequent Ruff line-length finding on the bound signature was
wrapped. Affected direct tests7passed12.01s, final Ruff/diff PASS. Sixteen
unchanged existing compatibility cases passed in the initial targeted run.
No existing tests changed/skipped/weakened and no full local suite claim.

Tests cover ready/rejected four-way plan/output combinations with exact legacy
bytes/receipts/identities; no services/extraction/execution/intermediate mkdir;
all four source snapshot mutation handoffs and single reads; invalid plan before
input reads, original malformed/oversized plan errors; stale/duplicate/oversized
inputs, invalid flags before IO, existing/nested/linked outputs and retained
partial ZIP/directory writes; snapshot bounds/reproduction before encoding.

Actual subprocess baseline/current legacy comparison and direct-delivery demo:
READY_SYNTHETIC4/4 and REJECTED_QUALITY3/4/null matrix cases each preserve exact
original files/receipts/ZIP bytes across all four combinations. Baseline/current
plan verification JSON and preparation JSON/default Markdown are byte-equal.
Direct ZIP generation creates only its final file. Relocated ZIP verification
exactly matches original directory reproduction.34source/legacy-delivery hashes
unchanged. Real Windows junction plan/input/output paths reject original linked
path codes with code2/no stdout/no output. JSON/Markdown/evidence retained in
tmp/preparation-direct-delivery/demo/.

Independent AST review confirms ten original calculation/transport functions
unchanged. Plan ZIP decoder only returns original captured files beside original
verification; original read/path gates and OSError mapping remain identical.
Evidence: tmp/preparation-direct-delivery/calculation-review.json.

Before code captured44worktrees/27dirty hashes/427protected hashes and checked
previous foreign baselines. Protection review PASS:43foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary database/stash/
localmain unchanged. Original synthetic preparation/projector/plan directory
verifier/both comparison modules byte-equal to base.
No comprehensive ignored-runtime hash claim.

Nine-file scoped feature commit/push and stacked PR against77. Final exact
committed scope/head, clean owned tree, local/origin/live feature/dependency/main
refs, protections and exact-head hosted state independently reviewed after
publication, retained in tmp/preparation-direct-delivery/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending checks
remain pending; dependency chain77->76->75->74->73->71->70->69->68 is unmerged.
No automatic merge or following stage. Real research/statistics/holdout sealed.
