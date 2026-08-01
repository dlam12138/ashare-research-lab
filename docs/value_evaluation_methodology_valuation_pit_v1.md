# Valuation PIT methodology v1

## Scope

This methodology evaluates six transparent observations for `601857.SH` from 2021-01-01 through the latest common unadjusted trade date available by 2026-07-31. It is an observation and comparability layer, not an opinion layer.

Every observation is evaluated using only financial Facts and corrected dividend Events whose `available_at` is on or before the trade date. A report period date is not a substitute for availability. Decimal arithmetic uses precision 28, `ROUND_HALF_EVEN`, and a final quantum of `0.000000000001`.

## Observation definitions

1. `a_share_price_to_latest_annual_parent_earnings`: close divided by latest annual parent net profit per applicable total ordinary shares. Non-positive earnings are `not_comparable_non_positive_earnings`.
2. `a_share_price_to_latest_year_end_parent_equity`: close divided by latest annual parent equity per applicable total ordinary shares. Non-positive equity is `not_comparable_non_positive_equity`.
3. `a_share_price_to_latest_annual_revenue`: close divided by latest annual revenue per applicable total ordinary shares. Non-positive revenue is `not_comparable_non_positive_revenue`.
4. `trailing_12m_announced_dividend_yield`: sum of trusted DPS values with `implementation_available_at` in `(trade_date - 365 days, trade_date]`, divided by close. This is not a payment yield.
5. `trailing_12m_paid_dividend_yield`: sum of trusted DPS values with `payment_date` in `(trade_date - 365 days, trade_date]`, divided by close.
6. `latest_annual_fcf_proxy_yield`: `(latest annual OCF - latest annual capex proxy) / applicable shares / close`. This is explicitly a proxy and may be negative; it is not canonical FCF.

Dividend values are trusted only when the corrected evidence gate passes. A source gap produces `partial_evidence` or `missing_input` with the affected event IDs; it never produces a zero substitute.

## Lineage and repeatability

Each row carries a deterministic observation ID, financial Fact IDs, dividend event IDs, source evidence IDs, market snapshot hash, share timeline ID, formula version, and PIT transition. Re-running the same run ID from the same committed contract and registered cache snapshot produces byte-stable JSON/Parquet content.

## Deliberate exclusions

There are no score, weight, rating, target, probability, buy, sell, upside, or downside fields. Historical percentiles are descriptive positions only. Scenarios stress the six multiples/yields at fixed sample-end dates and do not imply a future price.
