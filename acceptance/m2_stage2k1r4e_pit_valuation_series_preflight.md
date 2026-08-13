# M2 Stage 2K.1R4E — PIT Valuation Series Preflight and Candidate Build

Status: `CONDITIONAL PASS` — engineering trusted; formal candidate series is
blocked on the missing akshare secondary market cache object.

## Verdict

```text
M2 Stage 2K.1R4E: CONDITIONAL PASS
Valuation methodology v2: TRUSTED
Legacy annual/proxy methodology: SUPERSEDED
Market close reconciliation: BLOCKED (akshare secondary cache object missing)
Financial-state timeline: TRUSTED
TTM parent net profit: TRUSTED
TTM revenue: TRUSTED
MRQ parent equity: TRUSTED
Share basis: TRUSTED
Restatement PIT behavior: TRUSTED
Python backward join: TRUSTED
DuckDB ASOF oracle: TRUSTED
Dual-oracle equality: IDENTICAL
Decimal calculation: TRUSTED
PE invalid-domain policy: TRUSTED
PB invalid-domain policy: TRUSTED
PS invalid-domain policy: TRUSTED
PE 3y/5y candidate coverage: READY/READY
PB 3y/5y candidate coverage: READY/READY
PS 3y/5y candidate coverage: READY/READY
Historical percentiles: NOT COMPUTED
Valuation scoring: UNCHANGED_NON_PRODUCTION
Production Metric Results: NOT CREATED
Default DB: UNCHANGED
Peer acquisition: NOT ALLOWED
M3: NOT STARTED

R4E decision:
PIT_VALUATION_SERIES_GAPS_REMAIN
  (explicit market-cache gap: akshare secondary object absent locally)

Next-stage implementation:
NOT STARTED
```

## Scope

R4E builds the non-production, auditable, day-by-day recomputable candidate
PE-A-TTM / PB-A-MRQ / PS-A-TTM series from the accepted official quarterly
denominator facts (reported 127 / reconciled 38) and the external market close,
freezes the TTM/MRQ and per-trade-date PIT time-connection contract, and
determines whether percentile preflight is allowed. It computes no valuation
percentile and updates no scoring artifact.

## Deliverables

- `config/pit_valuation_series_formula_registry_v1.json` — frozen PE/PB/PS
  formulas, share basis, numeric-domain and identity contracts.
- `config/value_evaluation_methodology_valuation_pit_v2.json` — supersedes
  v1 (PE-TTM / PB-MRQ / PS-TTM replace latest-annual / latest-year-end proxies).
- `docs/pit_valuation_series_contract.md` — the frozen series contract.
- `src/ashare_research/pit_valuation/` — series_contract, financial_state, ttm,
  temporal_join, valuation_series, series_validation, fixtures.
- `src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py` — thin CLI.
- `reports/` — timeline, candidate, coverage, audit samples, dual-oracle
  validation, decision, artifact manifest.
- Five test files (42 tests).

## What is trusted

- **Valuation methodology v2** supersedes v1 for the current valuation-series
  contract; v1 is retained unmodified for historical audit.
- **Formulas** (PE-A-TTM, PB-A-MRQ, PS-A-TTM) are frozen and validated.
- **Financial-state timeline** (25 states per metric) is built PIT-visibly from
  the reported/reconciled bundles with correct annual/Q1/H1/Q3 TTM, MRQ equity,
  constant share basis, and restatement PIT behaviour (restated 2022-Q1 net
  profit is used as the 2023-Q1 prior input from its effective_from; never
  backfilled).
- **Dual-oracle equality**: the pure-Python ordered backward sweep and the
  in-memory DuckDB ASOF join are IDENTICAL on all 4053 observations (1351 trade
  days x 3 metrics).
- **Identity/ratio recomputation**: every observation_id and ratio is
  independently recomputed and matches.
- **Coverage**: PE/PB/PS each have 3y (728 >= 500) and 5y (1211 >= 900)
  effective samples; the 5y window starts 2021-08-02 (2021-07-31 is a
  non-trading Saturday, so the first real trade day is used).
- **Invalid-domain policy**: no negative PE; missing values are never written
  as zero and never enter a percentile sample.

## The blocking gap

- The akshare secondary market-cache object
  (`203ddfd7…`, 1351 rows) is **absent** from the local verified cache
  (`tmp/market_cache/akshare/`). The baostock primary object is present and
  verified. Per the frozen market-data contract, any missing external market
  cache yields `BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE`; no network refresh,
  no provider switch, and no use of a committed close percentile.
- Therefore the formal candidate series is computed from the baostock primary
  close (valid) but the dual-provider market reconciliation cannot be
  re-verified locally. The decision is **PIT_VALUATION_SERIES_GAPS_REMAIN**.

## When the gate can be upgraded

Restore the akshare secondary object (or both objects) into the verified
market cache, re-run `formal`, and re-verify the dual-provider reconciliation;
then the gate may move to
`PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`.
Percentiles are still never auto-computed and scoring is never updated.

## Evidence

- Full offline test suite: **1475 passed, 2 warnings** (1433 prior baseline +
  42 new R4E tests).
- `ruff check`: All checks passed. `compileall`: pass. `git diff --check`: pass.
- Formal CLI run: decision `PIT_VALUATION_SERIES_GAPS_REMAIN`,
  `market_reconciliation: BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE`.
- Fixtures (CI) CLI run: `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`
  (synthetic reconciled market), demonstrating the engineering gate.
- Cross-directory identity: committed observation ids byte-identical to an
  independent rebuild.
- Default DB SHA-256 unchanged; stash preserved; protected items untouched.