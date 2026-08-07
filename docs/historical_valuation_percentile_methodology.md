# Historical Valuation Percentile Methodology — M2 Stage 2K.1R4E.5

## 1. Purpose

This document freezes the method used to compute the non-production historical
valuation percentile profile for PetroChina (601857.SH) at as-of trade date
**2026-07-31**. It is the methodological companion of the frozen method contract
`config/pit_valuation_percentile_contract_v1.json` (schema
`pit_valuation_historical_percentile_v1`, version 1.0).

The output is a **non-production** percentile profile: 6 observations
(PE_A_TTM / PB_A_MRQ / PS_A_TTM × 3y / 5y). It is **descriptive relative
valuation only** and is **not** mapped to a score, a cheap/expensive label, a
buy/sell recommendation, a target price, or a margin-of-safety conclusion.

## 2. Symbols and scope

- Symbol: `601857.SH`
- As-of trade date: `2026-07-31` (`include_current = true`)
- Metrics: `PE_A_TTM`, `PB_A_MRQ`, `PS_A_TTM`
- Windows: `3y` and `5y` (calendar-year windows mapped to actual trade days)
- Rank method: `MIDRANK_EMPIRICAL_PERCENTILE`
- Sole data input: candidate v2
  (`reports/petrochina_pit_valuation_series_candidate_v2.json`, schema
  `petrochina_pit_valuation_series_candidate_v1`, 4053 observations).

No market re-fetch, no PE/PB/PS recomputation, no registry/candidate mutation,
no peer percentile, no rolling percentile series.

## 3. Ratio representation

Every ratio is a `Decimal` constructed **only from its string form**
(`Decimal(str(...))`), never from a float. Ranking and all comparisons are
performed on `Decimal` values. The DuckDB independent oracle stores ratios as
`DECIMAL(38,28)`, which holds every candidate ratio exactly, and compares with
exact `DECIMAL` comparisons (neither `percent_rank()` nor `cume_dist()` is used
as the official percentile).

## 4. Sample eligibility (fail-closed)

An observation enters the eligible sample `N` for a metric/window **only if**
all of the following hold:

1. `status == "computed"`;
2. `ratio_decimal` is not null;
3. `ratio_decimal > 0` (strictly positive — a non-positive PE is never ranked
   as cheap and never enters `N`);
4. `effective_first[window] <= trade_date <= as_of` (window membership).

Every observation that fails any condition is recorded in the exclusion ledger
with an explicit reason and never enters `N`. Windows:

| window | calendar_start | effective_first_trade_date | minimum_sample_count |
|--------|----------------|----------------------------|----------------------|
| 3y     | 2023-07-31     | 2023-07-31                 | 500                  |
| 5y     | 2021-07-31     | 2021-08-02                 | 900                  |

The 5y calendar start 2021-07-31 is a non-trading day; the effective first
trade date is the first actual trade day on/after it, **2021-08-02**. The
window is `effective_first <= trade_date <= as_of` and includes the as-of
observation.

## 5. Future-leakage gate

The sample must satisfy `max(sample.trade_date) <= as_of`. Any observation with
`trade_date > 2026-07-31` fails the gate and the profile is NOT_TRUSTED. This
ensures the percentile is computed only from information available at the as-of
date.

## 6. Current observation

For each metric there must be **exactly one** as-of observation with
`trade_date == as_of` and `status == "computed"`. It provides the current ratio
`r_current` that is ranked against the sample. Because `include_current =
true`, this observation is also a member of the sample and contributes to `N`.

## 7. Rank statistics and the MIDRANK empirical percentile

For a metric/window, relative to the current ratio `r_current`, count over the
eligible sample:

- `N` — total eligible observations;
- `L` — count with `ratio < r_current`;
- `E` — count with `ratio == r_current` (ties);
- `G` — count with `ratio > r_current`.

By construction `N == L + E + G` (verified and enforced by both the Python core
and the DuckDB oracle).

The three percentile readings (in percent) are exact rationals:

```
strict = 100 * L / N
weak   = 100 * (L + E) / N
midrank = 100 * (2*L + E + 1) / (2*N)
```

with the invariant `0 <= strict <= midrank <= weak <= 100`. The official value
is `midrank`; `strict`/`weak` are audit bounds. Each is carried as an exact
rational `rank_numerator / rank_denominator` (e.g. `1339/1456`) and only
displayed as a truncated Decimal at publication. Ties are averaged via the
midrank convention (the `+1` in the numerator).

## 8. Minimum sample gates

A metric/window is only READY when `N >= minimum_sample_count`
(3y ≥ 500, 5y ≥ 900, frozen). If a window fails its gate the profile is
NOT_TRUSTED with the gap recorded.

## 9. Output records

Exactly 6 records, in fixed order: PE/3y, PE/5y, PB/3y, PB/5y, PS/3y, PS/5y.
Each record binds a `percentile_record_id` that digests the identity fields
(schema, version, symbol, metric, window, dates, current obs id, current ratio,
the N/L/E/G counts, rank fraction, method, and the PE interpretation guard),
**not** paths, timestamps, machine, or working directory.

## 10. Independent DuckDB oracle

A second, independent implementation (`percentile_oracle.py`) loads the
candidate into an isolated in-memory DuckDB and recomputes, per metric/window,
`N/L/E/G` and `rank_numerator/rank_denominator` with exact `DECIMAL(38,28)`
comparisons. The Python core and the DuckDB oracle must agree on all six
records (`all_identical = true`); any mismatch makes the profile NOT_TRUSTED.

## 11. PE interpretation guard

For PE_A_TTM, a low percentile is **not** automatic evidence of undervaluation.
The record carries `pe_guard_id = low_pe_not_automatic_undervaluation_v1` and
`interpretation = DESCRIPTIVE_RELATIVE_VALUATION_ONLY`, and the profile
requires `cycle_warning_required = true`. Percentiles for PE/PB/PS are
descriptive, relative, and at a single as-of point; they make no claim about
regression to a mean or fair value.

## 12. Production boundary

- No historical percentile is mapped to a valuation score.
- No cheap/fair/expensive bucket, buy/sell, target price, or margin-of-safety
  conclusion is produced.
- No production Metric Result is created; the default DB is untouched.
- No scoring weight/threshold/sensitivity change; no M3; no peer acquisition.
- No rolling `1351d × 3m × 2w` percentile series (as-of single point only).