# Verified saved preparation diagnostics acceptance

Goal: agent/goals/2026-10-07_m4_preparation_delivery_diagnostics.md.
Verified base codex/m4-preparation-direct-delivery:
018624a392b6a6ab496ac1a73f35f322852f0059. PR78 OPEN/MERGEABLE;
23SUCCESS/14pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered prepare-package (--verify DIR | --verify-archive ZIP)
--summary [--role ID (repeatable)] [--gaps-only] [--json].
Both entry modes first reproduce every saved member through the unchanged
verifier, then project the captured verified report with the unchanged
diagnostic build_summary/render_markdown. Stored diagnostics bytes are never
trusted independently and no source/input is reread.

Summary selectors apply only to verification modes; exports, repacking and
direct generation reject them before IO with INVALID_ARGUMENTS. Malformed role
selectors and --role/--gaps-only without --summary reject before IO; a
well-formed but absent role fails UNKNOWN_ROLE only after original verification.
Only cli main changed in preparation_package.py; independent AST review confirms
every calculation, verification, writer and renderer function/class is identical
to base. Evidence: tmp/preparation-delivery-diagnostics/calculation-review.json.

Filters change visible rows/cells only. Original status, quality, coverage
numerator/denominator, rejected dates, identities, boundaries and role counts
over all audit dates are preserved. A role with no matching gaps yields an
explicit NO_MATCHING_GAPS view without turning global rejection into readiness.
Output keeps the existing diagnostics schema/JSON/Markdown, raw observations and
matrix cells excluded; no effects, provenance, sealing, readiness or execution
claim. Without selectors original receipts/JSON/default Markdown are byte-equal
to the baseline CLI. Command stays offline, reads no database/services, creates
no files/directories, extracts nothing and never modifies the delivery.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_delivery_diagnostics.py tests/test_preparation_diagnostics.py tests/test_preparation_package.py tests/test_preparation_archive.py tests/test_preparation_direct_delivery.py
python -m ruff check src/ashare_research/tools/preparation_package.py src/ashare_research/tools/research_entry.py tests/test_preparation_delivery_diagnostics.py
git diff --check
python tmp/preparation-delivery-diagnostics/calculation_review.py
python tmp/preparation-delivery-diagnostics/demo.py
python tmp/preparation-delivery-diagnostics/verify_protections.py
```

Targeted26passed56.27s (six new cases plus twenty unchanged existing cases).
Final Ruff/diff PASS; no pytest failures, existing test edits or full local
suite claim. Tests cover ready/rejected/empty exact projector sides on both
transport modes, legacy full receipts, repeated/reordered roles, gap counts,
known-empty distinction, complete hidden-role forgery and stale/corrupt members
including rewritten inventory, invalid selectors before IO, unknown role after
one verifier call, once-read directory/ZIP mutation handoff, offline guards and
linked-path rejection.

Actual subprocess demo: ready4/4, rejected3/4 and empty0/4 cases each reproduce
the original raw-input projector JSON and default Markdown byte-for-byte from
relocated directories and ZIPs; baseline/current full verification JSON and
Markdown remain byte-equal.81source/delivery hashes unchanged; reading created no
files or directories. A forged hidden-role record with updated inventory fails
PREPARATION_PACKAGE_MISMATCH; real Windows junction directories/ZIPs fail
LINKED_PREPARATION_PACKAGE_PATH. READY state has no FACTOR gaps; rejected state
retains global rejection with NO_MATCHING_GAPS for FACTOR.
JSON/README/evidence retained in tmp/preparation-delivery-diagnostics/demo/.

Before code captured45worktrees/27dirty hashes/427protected hashes after checking
previous foreign baselines. Protection review PASS:44foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary database/stash/
localmain unchanged. Original preparation projector, plan/preparation directory
and ZIP verifiers and both comparison modules byte-equal to base.
No comprehensive ignored-runtime hash claim.

Seven-file scoped feature commit/push and stacked PR against78. Final exact
committed scope/head, clean owned tree, local/origin/live feature/dependency/main
refs, protections and exact-head hosted state independently reviewed after
publication, retained in tmp/preparation-delivery-diagnostics/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending checks
remain pending; chain78->77->76->75->74->73->71->70->69->68 is unmerged.
No automatic merge or following stage. Real research/statistics/holdout sealed.
