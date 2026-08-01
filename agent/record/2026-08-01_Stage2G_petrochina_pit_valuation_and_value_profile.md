# Work record: M2 Stage 2G PetroChina PIT valuation and value profile

Date: 2026-08-01
Starting HEAD: `ace3e947d6e11b91b76a2d49881c1ebadbee3a75` (`ace3e94`)
Branch: `feat/m2-value-assessment-mvp`

## Contract and protected baseline

Read and followed `agent/goals/2026-08-01_m2_stage2g_dividend_correction_and_valuation_profile.md` as the authoritative contract. Phase A was not skipped. The repository North Star, branch, HEAD, protected baseline, stash, default DB, and current v1 ace3e94 implementation were recorded before edits. The untracked goal contract is preserved.

Frozen invariants: pre-Stage2F 354 Fact / 102 Metric Result / 16 definitions; ROE/ROA and financial safety; Fact/Identity/PIT gates; default DB SHA-256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`; stash `stash@{0}` unchanged. The v1 event ledger and v1 runner remain historical compatibility artifacts.

## Work completed

1. Added `dividend_event_record_v2` with canonical versioned IDs, superseded v1 IDs, prior-authority semantics, corrected chronology, `implementation_available_at`, `payment_date`, and explicit as-of statuses.
2. Added 20 exact source evidence records with separated issuer/exchange types, locator hashes, real payload hashes where retrieved, cache metadata, independent extraction flags, and finite retrieval gaps. No URL hash is used as a content hash and no PDF is committed.
3. Added North Star review, valuation PIT methodology/config/input contract, and the offline/acquisition-separated valuation runner.
4. Reused the existing `stock_daily` model and fetched/reconciled Baostock/AKShare unadjusted data into the external cache. Added share scope timeline and explicit non-canonical market-cap diagnostic name.
5. Added six PIT observations, transparent percentiles, fixed sample-end scenarios, lineage, gap register, reports, acceptance documents, and focused tests.

## Formal result

Run `stage2g_valuation_pit_20260801` covers 1,351 market days through 2026-07-31, emits 8,106 observation rows, reconciles the two providers at 0.00 close difference, and records one Rule007 eligible dual-official event plus nine issuer-only evidence gaps. The formal runner is offline and does not mutate the default DB.

## Tests and remaining gates

Stage2G focused tests: `9 passed`; full pytest: `929 passed, 2 warnings`; full Ruff: passed; compileall: passed; `git diff --check`: passed. The five protected-roadmap expectations were aligned to the actual ace3e94 blob without changing the protected roadmap. No ROIC, scoring, Web, target, rating, or market-mechanism work was started. Scoped commit and remote-push verification remains for final handoff.
