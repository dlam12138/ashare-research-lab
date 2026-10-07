# Preparation comparison role summary acceptance

Goal: agent/goals/2026-10-07_m4_preparation_comparison_summary.md.
Verified base codex/m4-preparation-delivery-diagnostics:
34572a8286c5eb2670879e4138e263983bc554db. PR79 OPEN/MERGEABLE;
19SUCCESS/16pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered prepare-compare and prepare-delivery-compare
--summary [--role ID (repeatable)] [--json]. Both entry points first run the
untouched complete comparison (raw: one original preparation build per distinct
side; delivery: one original directory/ZIP verification per distinct side or
mode), then project that captured report into per-role transition counts and
role-filtered changes. No reread, no extraction, no write, no new cell
comparison; stored diagnostics are never trusted independently.

Selectors reject before IO: --role without --summary is INVALID_ARGUMENTS and a
malformed role is INVALID_ROLE, both before any plan/input/package read. A
well-formed but absent role fails UNKNOWN_ROLE only after the complete
comparison or verification ran. Summary preserves both sides' status, quality,
coverage numerator/denominator, gates, rejected dates, plan/input/dataset/matrix
identity, classification, boundary and the global audit-count fields exactly;
filters change only displayed role rows and changes, and a selected role with no
change yields NO_MATCHING_CHANGES. Per-role tallies must reconcile with the
captured global counts, roles and transitions or the projection fails closed
with COMPARISON_SUMMARY_MISMATCH; sanitized errors keep code2 and empty stdout.
New schema m4_paired_synthetic_preparation_diagnostics_summary_v1; JSON is the
compact Chinese Markdown table view, raw observations and matrix cells stay
excluded, and no effect/readiness/execution claim is made. Without --summary
original JSON and default Markdown are byte-equal to the base CLI.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_comparison_summary.py tests/test_preparation_compare.py tests/test_preparation_delivery_compare.py tests/test_preparation_delivery_diagnostics.py tests/test_preparation_package.py tests/test_preparation_archive.py
python -m ruff check src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/preparation_delivery_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_comparison_summary.py
git diff --check
python tmp/preparation-comparison-summary/calculation_review.py
python tmp/preparation-comparison-summary/demo.py
python tmp/preparation-comparison-summary/verify_protections.py
```

Targeted33passed110.59s (nine new cases plus twenty-four unchanged existing
cases). Final Ruff/diff PASS; no pytest failure, existing test edit or full
local-suite claim. Cases cover raw/delivery exact projections on all four
transport combinations, repeated/reordered role dedupe, NO_MATCHING_CHANGES,
global counts/quality/identity/boundary preservation, legacy output equality,
once-read snapshot handoff and single-read reuse, unknown role only after the
complete comparison/verification, invalid flags and patterns before IO,
doctored-report invariant guards including sanitized CLI failure, offline/
no-extraction/no-write guards and a real Windows junction rejection.

Actual subprocess demo: before REJECTED_QUALITY3/4, after READY_SYNTHETIC4/4,
16compared/15unchanged/1became_valid/0became_invalid/0metadata_changed;
legacy JSON and default Markdown byte-equal to the base worktree; all four
delivery transports and relocated directories/ZIPs project identically;
role-order dedupe gives TARGET_OUTCOME before CONTROL_0002 and FACTOR shows
NO_MATCHING_CHANGES while counts/quality stay unchanged. Unknown role,
malformed role and --role without --summary reject; real junction and a forged
hidden audit cell with rewritten inventory fail closed.38source/delivery hashes
unchanged and summary runs created no files. JSON/Markdown/evidence retained in
tmp/preparation-comparison-summary/demo/.

Independent AST review (tmp/preparation-comparison-summary/calculation-review.json):
every pre-existing function/class except cli main in both comparison modules is
AST-identical to base; only the intended projection additions and cli main
changed. Before implementation captured46worktrees/45foreign states/27dirty
hashes/427protected hashes; protection review PASS:45foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary database/
stash/localmain unchanged and the unchanged preparation projector, plan/
preparation directory and ZIP verifiers byte-equal to base. No comprehensive
ignored-runtime hash claim.

Eight-file scoped normal feature commit/push and stacked PR against79. Final
exact committed scope/head, clean owned tree, local/origin/live feature/
dependency/main refs, protections and exact-head hosted state independently
reviewed after publication, retained in
tmp/preparation-comparison-summary/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain79->78->77->76->75->74->73->71->70->69->68 is
unmerged. No automatic merge or following stage. Real research/statistics/
holdout sealed.
