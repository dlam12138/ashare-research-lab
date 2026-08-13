# 3Y Historical Normalized-PE Cycle-Guard Validation (R4F.4)

Stage: `2K.1R4F.4`
Contract: `config/pe_3y_cycle_guard_validation_contract_v1.json`
Status: 2026-08-08, local validation

## 1. Frozen research question

> Does the PIT-safe Average-ROE × Current-BVPS normalized earnings
> denominator provide a **repeatable historical guard** against the
> mechanical compression of raw PE when current TTM earnings rise above the
> normalized-earnings proxy?

This is a **mechanism validation** — not "is this a cycle top?", not "can
normalized PE predict future returns?", not "what threshold should I buy
at?".  The four sub-questions (A: deterministic 3Y PIT series rebuild;
B: multiple independent denominator states; C: the mechanical direction
relation; D: no PIT/restatement/state-transition/identity anomalies) are
answered by the artifacts in this stage.

## 2. Method references and cuts

### A. CFA normalized earnings

- **Borrowed**: normalized EPS = average historical ROE × current BVPS
  (the committed `AVERAGE_ROE_X_CURRENT_BVPS` contract); historical
  trailing PE must be lagged (no look-ahead).
- **Not copied**: analyst forecasts, forward PE, peer comparison, DCF,
  recommendations.

### B. Time-series walk-forward principle

- **Borrowed**: a past as-of reads only information visible then (the R4F.3
  PIT/restatement gate).  No sklearn runtime dependency introduced.

### C. SciPy percentile-rank semantics

- **Borrowed**: the frozen R4E.5 `MIDRANK_EMPIRICAL_PERCENTILE` (tie
  averaging, exact rational rank) for the current normalized-PE 3Y
  percentile.  No scipy runtime dependency — the midrank computation is
  implemented in pure Decimal and cross-checked with an independent DuckDB
  oracle.

### Repository-specific cuts

- No new normalization method: the committed `pe_normalized_earnings_average_roe_v1`
  contract is reused unchanged (5 consecutive annual ROE; no 3y/4y fallback,
  no expanding window, no winsorize/trim/manual exclusion).
- No second resolver: the R4F.3 `pe_normalized_earnings_prototype.py`
  functions (ROE chain, BVPS, normalized EPS, normalized PE) are reused.
- No new raw-TTM identity: the R4E.4 `financial_state_id` (official
  upstream state identity) is bound directly.

## 3. Data

- Facts: R4F3A overlay = committed R4D reported/reconciled bundles (165)
  + R4F3A backfill (8) = 173 facts, PIT/restatement-gated by the R4F.3
  resolver.
- Market: R4E.4 candidate v2 `PE_A_TTM` observations (1351 days), 728 in
  the frozen 3Y window 2023-07-31..2026-07-31.  All 728 are `computed`
  with `per_share_denominator_decimal`, `ratio_decimal`, and
  `financial_state_id` present — no `RAW_TTM_EPS_IDENTITY_GAP`.
- Current TTM EPS comes only from `per_share_denominator_decimal`;
  `close / current_ttm_eps == ratio_decimal` is the cross-check, never the
  primary path.

## 4. Series construction (per trade day)

```
raw_pe          = close / current_ttm_eps
normalized_eps  = average_roe × current_bvps      (R4F.3 resolver)
normalized_pe   = close / normalized_eps
earnings_normalization_ratio = current_ttm_eps / normalized_eps
normalized_to_raw_pe_ratio   = normalized_pe / raw_pe
```

Identity (Decimal-only, required for every day):

```
normalized_pe / raw_pe == current_ttm_eps / normalized_eps
raw_pe / normalized_pe == normalized_eps / current_ttm_eps
```

## 5. Denominator-state identities

- **`normalized_denominator_state_id`** (new, R4F4): payload contains only
  contract_id, the five selected ROE years, all annual NP fact IDs, all
  begin/end equity fact IDs, current equity fact ID, current share fact ID,
  average ROE, current BVPS, normalized EPS — **no trade date, no price,
  no market observation, no PE**.  Adjacent days with identical economic
  inputs get the same ID.
- **`raw_ttm_denominator_state_id`** = R4E.4 `financial_state_id` (official
  upstream).  Price-only days never change it.
- The R4F.3 `normalized_earnings_state_id` (a daily observation identity
  that includes `as_of_trade_date`) is **unchanged** — R4F4 adds the
  episode-friendly identity rather than rewriting history.

## 6. State segmentation (run-length)

Trade days are grouped into contiguous segments of identical
`(raw_ttm_denominator_state_id, normalized_denominator_state_id)` pairs.
**728 daily rows are not 728 independent observations** — the primary
evidence unit is the unique denominator state / segment.

## 7. Direction audit and protective direction

Per day:
- Case A `current_eps > normalized_eps` → must have `normalized_pe > raw_pe`
- Case B `current_eps < normalized_eps` → must have `normalized_pe < raw_pe`
- Case C equality → PE equality

Any violation fails the audit.  `PROTECTIVE_DIRECTION_OBSERVED` means
Case A holds: with current TTM EPS above the normalized proxy, the PE with
a normalized denominator does not sit mechanically lower.  It does **not**
mean cycle peak.

**Identification note (reviewer correction)**: the relation
`current_eps > normalized_eps ⇒ normalized_pe > raw_pe` is *algebraically
implied* by `raw_pe = price/current_eps` and
`normalized_pe = price/normalized_eps` for positive operands.  A zero
violation count therefore verifies **implementation correctness**
(`mechanical_direction_consistency = PASS`), not independent empirical
cycle evidence.

## 8. Recurrence gate (pre-registered, corrected semantics)

`REPEATED_PROTECTIVE_DIRECTION_OBSERVED` requires **≥ 2 distinct raw TTM
denominator states** with current EPS > normalized EPS, all agreeing on
the direction.  One state → `SINGLE_PROTECTIVE_DIRECTION_STATE_ONLY`;
zero → `NO_PROTECTIVE_DIRECTION_EPISODE_OBSERVED`.  This is a minimum
recurrence gate, not a significance threshold; no amplitude/duration
cutoffs.  The gate is frozen before the actual outcome is observed.

The observed condition is interpreted strictly as
**`CONDITION_OBSERVED_ACROSS_MULTIPLE_DENOMINATOR_STATES`** — it does
**not** mean the cycle mechanism was independently replicated, because
the direction relation itself is algebraic.  Where the observed
protective direction forms a single contiguous regime
(`protective_direction_segments = 1`), that is **one** regime, not
multiple independent cycle episodes.

## 9. Transition audit

A `normalized_denominator_state_id` may change only when its upstream
(annual ROE chain, current equity, share state) changes; a raw TTM state
only when its TTM inputs change.  A pure market-price day must not
transition either state.  `orphan_* = 0` expected.

## 10. Restatement / PIT perturbation

The R4F3A 2017/2018 restated_1 facts (Dalian Xitai SCA) must be invisible
before their 2020-03-27 effective_from.  A synthetic later restatement
(effective after the historical date) must leave historical normalized EPS
/ PE byte-identical.

## 11. Percentile (current, 3Y only)

`MIDRANK_EMPIRICAL_PERCENTILE` over the 728 PIT-valid normalized-PE
observations, include_current = true, exact rational
`rank_numerator/rank_denominator` = `(2L+E+1)/(2N)`, Decimal-only,
cross-checked with an independent DuckDB oracle.  No 5Y percentile; the
percentile is descriptive, never a scoring input.

## 12. Interpretation boundary (reviewer-corrected)

The stage verdict is **CONDITIONAL PASS**.  Engineering and
mechanical-guard validation pass, but **independent cycle-context
validation is NOT ESTABLISHED**: the direction relation is an algebraic
identity and the observed protective direction is a single contiguous
regime (11 distinct raw denominator states, 1 segment) — it cannot
establish repeated independent cycle episodes.

The mechanical denominator guard is **CONFIRMED**; normalized earnings as
a valid cycle proxy is **NOT_YET_VALIDATED**; cycle-guard empirical
validation is **NOT_ESTABLISHED**.  This is **not** "cycle top
identified", **not** "true mid-cycle EPS", **not** "PE scoring may
resume" — full_cycle remains NOT_PROVEN, 5Y validation remains BLOCKED,
and this is a single issuer.  The percentile shift (raw 91.96% vs
normalized 22.32%) proves only that the denominator choice materially
changes the historical valuation position (`DESCRIPTIVE_DENOMINATOR_NORMALIZATION_COMPARISON`);
it is not evidence of normalization correctness.

Next stage: **R4F.4A — Independent Cycle-Context Validation Preflight**
(to freeze a falsifiable cycle-context validation contract not defined by
the raw/normalized PE arithmetic itself).  The remaining 5Y 4 facts are
`DEFERRED_PENDING_IDENTIFICATION_REVIEW` — not cancelled, but sequenced
after the identification question is settled.
