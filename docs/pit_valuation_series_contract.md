# PIT Valuation Series Contract

Date: `2026-08-06`
Symbol: `601857.SH` (PetroChina)
Stage: M2 Stage 2K.1R4E — PIT valuation series preflight and candidate build
Convention: `A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION` (ADR-VALUATION-002)
Methodology: `value_evaluation_methodology_valuation_pit_v2` (supersedes v1)
Formula registry: `config/pit_valuation_series_formula_registry_v1.json`

This contract freezes the non-production, auditable, day-by-day recomputable
candidate PE-A-TTM / PB-A-MRQ / PS-A-TTM series. It is a **preflight candidate**,
not a production valuation series, and it does **not** compute valuation
percentiles.

## 1. Market scope

```text
valuation_market = SSE_A_SHARE
symbol = 601857.SH
price = A-share unadjusted close
currency = CNY
h_share_price_in_core_valuation = false
h_share_fx_in_core_valuation = false
```

Source: `events/market_data_snapshot_registry.json` (two 1351-row external
content objects: baostock primary, akshare secondary). Primary computation uses
baostock close; every observation binds both provider object SHAs and the
reconciliation contract/digest.

## 2. Formulas (frozen)

```text
PE_A_TTM(t) = A_share_close(t) ÷ PIT_TTM_basic_EPS(t)
PIT_TTM_basic_EPS(t) = PIT_TTM_parent_net_profit(t) ÷ PIT_TTM_weighted_average_total_ordinary_shares(t)

PB_A_MRQ(t) = A_share_close(t) ÷ PIT_parent_BVPS(t)
PIT_parent_BVPS(t) = latest_visible_parent_equity(t) ÷ matching_period_end_total_ordinary_shares(t)

PS_A_TTM(t) = A_share_close(t) ÷ PIT_TTM_sales_per_share(t)
PIT_TTM_sales_per_share(t) = PIT_TTM_revenue(t) ÷ total_ordinary_shares_effective_on_trade_date(t)
```

## 3. TTM construction (frozen)

```text
annual state:  TTM_Y   = latest visible annual value for Y
Q1/H1/Q3 state: TTM_Y_P = latest visible annual value for Y-1
                          + latest visible cumulative value for Y/P
                          - latest visible cumulative value for Y-1/P
```

Every TTM state binds: current cumulative Fact ID, prior-year same-period Fact
ID, prior annual Fact ID, each input's restatement version, each input's
`available_at`/`effective_from`, formula ID/version, max input `available_at`,
state `effective_from`, `financial_state_id`, and canonical state digest.

PIT rules:
1. only select versions visible as of the state's `effective_from`;
2. a restatement changes the state only from its own `effective_from`;
3. never backfill later comparatives into earlier dates;
4. a missing input forms an explicit `missing_ttm_input` state;
5. annual value may not substitute for a missing quarterly TTM;
6. no arbitrary cross-period-type matching;
7. never take a "latest available record" without checking fiscal year/period.

## 4. Share basis (frozen)

The share count is constant (`183,020,977,818`) across the whole TTM duration,
proved by the trusted share-continuity register
(`r4d1-share-continuity-constancy-v1`). Therefore:

- PE: TTM weighted-average shares = constant, bound to `share_continuity_proof_id`.
- PB: equity and period-end shares must share the same `period_end` and the same
  PIT-visible reporting context; never independently pick "latest equity" and
  "latest arbitrary shares".
- PS: TTM revenue uses a duration state; shares use the total ordinary shares
  effective on the trade date (`share_effective_from <= trade_date`); forward/
  nearest prohibited.

If a future share-count change appears, the state is `unsupported_variable_share_count`
and never falls back to period-end or current shares.

## 5. Time connection (frozen)

- Price join: exact `trade_date` match.
- Financial join: latest state with `effective_from <= trade_date`; backward only.
- Both forward and nearest are prohibited.
- Two independent oracles (pure-Python ordered sweep and a DuckDB ASOF join in an
  isolated in-memory DB) must agree row-by-row, or the series is
  `PIT_VALUATION_SERIES_NOT_TRUSTED`.

## 6. Numeric domain (frozen)

All financial values and valuation calculations use `Decimal` throughout.
`Decimal(binary_float)` is prohibited; `Decimal(str(source_value))` is used.
Intermediate values are not prematurely quantized. Output uses `ROUND_HALF_EVEN`
and canonical Decimal strings. No binary float is an authoritative value in JSON.
Ratios are dimensionless.

Invalid-domain handling:

| Metric | Condition | ratio | status |
|---|---|---|---|
| PE | TTM parent net profit <= 0 | null | `nonpositive_earnings` |
| PB | equity <= 0 or shares <= 0 | null | explicit status |
| PS | revenue <= 0 or shares <= 0 | null | explicit status |

All missing/null values are never written as zero, never enter a future
percentile sample, and retain an exclusion reason.

## 7. Observation identity

Each observation carries: `observation_id`, schema/version, `metric_id`, symbol,
`trade_date`, `market_close_decimal`, `market_close_digest`, primary/secondary
market object IDs, market reconciliation digest, `financial_state_id`,
`financial_state_effective_from`, `financial_state_available_at_max`,
`input_fact_ids`, `share_continuity_proof_id`, formula ID/version,
`per_share_denominator_decimal`, `ratio_decimal` (or null), `status`,
`exclusion_reason`, and the flags `non_production=true`,
`percentile_computed=false`, `score_eligible=false`, `production_eligible=false`.

`observation_id` is derived from the canonical payload and never contains
absolute paths, run timestamps, the working directory, JSON indentation,
platform newlines, or platform-dependent float reprs.

## 8. Boundary

- No 3y/5y valuation percentile values are computed or published.
- No `valuation_attractiveness` shadow update, no scoring weight/threshold/
  transform/sensitivity change, no production Metric Result, no canonical value
  profile change, no peer acquisition, no M3, no default-DB write.
- The old `close_percentile` observation set is retained but is never a valuation
  percentile and does not read this candidate series.

## 9. Decision gate

The final gate is one of:

- `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`
- `PIT_VALUATION_SERIES_GAPS_REMAIN`
- `PIT_VALUATION_SERIES_NOT_TRUSTED`

Even when the first is selected, only `PIT_VALUATION_PERCENTILE_PREFLIGHT_ALLOWED`
follows; percentiles are never auto-computed and scoring is never updated.