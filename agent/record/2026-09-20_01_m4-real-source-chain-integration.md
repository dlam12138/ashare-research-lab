# Work record: M4 real-source chain integration

Date: 2026-09-20. Contract: [integration Goal](../goals/2026-09-20_m4_real_source_chain_integration.md). Executor and Git operator: Codex. Independent reviewer: DSH.

## Baseline and replay

The worktree was created cleanly from `origin/main@2bacfd7f7f5a51e168f1d386bfe8a93227fa78e7`, the PR #21 merge. The historical linear chain was replayed without conflict in this exact order: `7888553`, `2910502`, `e4fbde5`, `c92dd66`, `228036c`. The replay added only its three Goals, three acceptances, two records, three design documents, K1 source and K1 tests. It did not rewrite those historical commits.

DSH's consolidated read-only audit returned `CHANGES_REQUIRED`. It confirmed the chain was linear, link-complete and path-disjoint from post-PR21 main, and recommended one integration PR rather than three. It required reconciliation of the now-merged PR #20 status and demonstrated three K1 defects: minimal decimal spelling rejected the design's `0.00`; a malformed late value could escape numeric validation; and a holdout date in `calendar_dates` was not rejected.

## Corrections

- Added dated post-PR21 reconciliation sections to the design gate and source-contract design. Historical PR #20 statements remain untouched below those sections; current readers are told that PR #20 and PR #21 are merged while their synthetic evidence remains insufficient for real-source claims.
- Kept decimal inputs as bounded plain strings without float or exponent notation, but accepted meaningful scale, zero and negative forms such as `0.00`, `1.50` and `-0.002`.
- Moved decimal validation before PIT classification, so a malformed value cannot pass merely because its availability is late.
- Rejected any `calendar_dates` member at or after `holdout_start` before raw bytes are touched.
- Added focused regression tests for all three findings. No provider, database, filesystem, network, real-data, holdout-read, execution or statistics surface was added.

## Validation

Run sequentially from this worktree with `PYTHONPATH=src` and `PYTHONDONTWRITEBYTECODE=1`:

- `pytest -q -p no:cacheprovider tests/test_m4_real_daily_kernel.py` → **17 passed in 0.29s**, exit 0.
- The Goal-listed post-PR21 upstream regression over portability, synthetic adapter, plan, governance, matrix, bounded execution, orchestrator and project-entry tests → **299 passed in 236.07s**, exit 0.
- `ruff check --no-cache` on K1 source and tests → `All checks passed!`, exit 0.
- `ruff format --check --no-cache` on K1 source and tests → `2 files already formatted`, exit 0.
- `git diff --check` and `git diff --cached --check` → no output, exit 0.
- All replayed and integration Markdown checked as strict UTF-8 with final newline and without trailing whitespace or conflict markers.

Protected M2 HEAD remained `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash remained `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; the default database was only hashed and remained SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Delivery boundary

The integrated branch may be committed, pushed and submitted as one PR after final DSH review. Merge, K2, provider selection, verified calendar/membership acquisition, real observations, holdout and hypothesis execution remain unauthorized.
