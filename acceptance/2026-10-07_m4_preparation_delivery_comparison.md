# Delivered preparation diagnostic comparison acceptance

Goal: agent/goals/2026-10-07_m4_preparation_delivery_comparison.md.
Verified origin/live base codex/m4-preparation-archive:
44581427dc4b42282085ac9c555243d8c4182f56. PR76 OPEN/MERGEABLE; initial
15SUCCESS/19pending, latest pre-publication36SUCCESS/4pending.
Pending hosted checks are not successful gates. Main remains
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b; root worked directly, no DSH.

Delivered research prepare-delivery-compare
(--left DIR | --left-archive ZIP) (--right DIR | --right-archive ZIP) [--json].
Each distinct caller path/mode uses the unchanged complete directory or native
ZIP verifier. Only identical path and mode reuse a captured report; aliases
still traverse original path/link gates. Verification recompiles saved plans,
rebuilds saved inputs and checks every file, retaining original bounds/errors.
No extraction, input rereading, reconstructed directory or extra source inputs.

Extracted original comparison calculation into build_report_from_reports.
Independent AST inspection confirms the calculation is unchanged. Full old CLI
JSON and default Markdown are byte-equal to the baseline CLI on the demo fixture.
The delivery command returns the same paired-diagnostic JSON schema and content
as the original raw-input comparison; Markdown uses a saved-delivery legend.
Both full diagnostics, input byte-versus-canonical equality, identities, original
quality/denominator and read/execution boundaries remain intact. Plan identity,
domain digest, date or role ordering differences reject; no raw observations,
matrix values, effects, repair, ranking, provenance or execution/readiness claim.
Invalid arguments fail before IO. Either invalid side fails with original
sanitized error/code2/no partial stdout. Command is read-only and offline.

Actual exact validation commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_delivery_compare.py tests/test_preparation_compare.py tests/test_preparation_package.py tests/test_preparation_archive.py
python -m ruff check src/ashare_research/tools/preparation_delivery_compare.py src/ashare_research/tools/preparation_compare.py src/ashare_research/tools/research_entry.py tests/test_preparation_delivery_compare.py
git diff --check
python tmp/preparation-delivery-comparison/demo.py
python tmp/preparation-delivery-comparison/verify_protections.py
```

Targeted16passed43.14s, including five new tests and eleven unchanged existing
tests. Initial Ruff found one101-character call line; wrapped without behavior
changes, final Ruff/diff PASS. No pytest failures, skipped/weakened tests or
full local suite claim. No existing test changes.

Tests cover all four directory/ZIP combinations and reversal, exact original
quality rejection3/4 versus ready4/4, raw-input/canonical equivalence, metadata-only
changes and empty-input boundaries; per-side once-read mutation handoff, same
path/mode10directory reads or1ZIP read, offline/no-extraction/no-executor guards;
forged reports plus rewritten inventories, stale evidence and invalid transport
on either side; invalid flags before IO, different modes sharing a path,
individually valid changed plans/domains, alias/reparse rejection.

Actual subprocess demo independently runs the baseline and current legacy CLI,
then compares saved deliveries: old/current raw JSON and default Markdown match
byte-for-byte; relocated ZIP and mixed-format delivery JSON also exactly match.
Original invented3/4->4/4coverage yields1became-valid among16audit cells.
28source hashes unchanged; relocated archives unchanged and no extraction/output
created by comparison. A forged report/inventory ZIP fails
PREPARATION_PACKAGE_MISMATCH; a real Windows junction to the already compared
left directory fails LINKED_PREPARATION_PACKAGE_PATH, not snapshot reuse.
JSON/Markdown/evidence retained in tmp/preparation-delivery-comparison/demo/.
Independent calculation review: tmp/preparation-delivery-comparison/calculation-review.json.

Before code captured43worktrees/27dirty hashes/427protected hashes after checking
previous foreign baselines. Protection review PASS:42foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, stash/localmain and
primary database unchanged. Original preparation/projector/plan directory and
ZIP verifiers/preparation directory and ZIP verifiers byte-equal to base.
No comprehensive ignored-runtime hash claim.

Nine-file scoped feature commit/push and stacked PR against76; exact committed
scope/head, clean owned tree, local/origin/live refs, protections and hosted
state independently reviewed after publication and retained in
tmp/preparation-delivery-comparison/final-evidence.json.
Local acceptance PASS subject to final publication review. No full hosted-success
claim while pending; dependencies76->75->74->73->71->70->69->68 remain unmerged.
No automatic merge or following stage. Real research/statistics/holdout sealed.
