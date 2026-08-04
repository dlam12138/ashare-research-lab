# ADR-VALUATION-002 — A-Share Per-Share Valuation Convention

Status: `accepted`

## Decision

`A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION`

Core valuation for the product scenario **"only A-shares are traded"** uses:

- **Market side:** the A-share price (SSE A-share, unadjusted close, CNY).
- **Fundamental side:** the **company-wide per-share fundamental** (company total
  ordinary shares), not an A-share-only profit/equity split.

The A/H share split is **not** a core-valuation blocker. H-share price and H-share FX
are **not** in the core PE/PB/PS or the four-dimension score. The A/H premium is an
optional separate reference only.

This supersedes the R4B recommendation that `total_market_cap` (Route A) was the
preferred direction *because* the A/H split was missing. The A/H split is not needed
for the "A-share price ÷ company-wide per-share fundamental" convention.

## Basis

- The product only trades A-shares, so the market numerator is the A-share price.
- The SSE statistical definition (《证券期货业统计指标标准指引》) evaluates per-share
  metrics as `price ÷ per-share fundamental`.
- PetroChina's EPS is computed as parent net profit ÷ ~18.302 billion total ordinary
  shares issued. The company-wide per-share fundamental is therefore the correct
  denominator; no A/H share-count split is required.
- A company-wide per-share fundamental (EPS / BVPS / SPS) is identical regardless of
  which listing's price is used as the numerator; using the A-share price is consistent
  with the A-share-only product scope.

## Contract

### B1. Market scope

```text
valuation_market = SSE_A_SHARE
symbol = 601857.SH
price_series = A_SHARE_UNADJUSTED_CLOSE
currency = CNY

h_share_price_in_core_valuation = false
h_share_fx_in_core_valuation = false
dual_market_cap_in_core_valuation = false
ah_premium = optional_separate_reference
```

H-shares may later be used **only** for: A/H premium, cross-listing liquidity
differences, market-sentiment differences, and cross-market valuation comparison. They
must not enter the core PE/PB/PS or the four-dimension score.

### B2. Fundamental scope

Core valuation is **not** "only the profit attributable to A-shares"; it is:

```text
A-share market price
÷ company-wide per-share fundamental (total ordinary shares)
```

Frozen candidate formulas:

```text
PE_A_TTM(t) = A_share_close(t) ÷ PIT_TTM_basic_EPS(t)
PB_A_MRQ(t) = A_share_close(t) ÷ PIT_parent_BVPS(t)
PS_A_TTM(t) = A_share_close(t) ÷ PIT_TTM_sales_per_share(t)
```

Frozen share-count conventions (single, non-switchable):

| Metric | Denominator | Share-count convention |
|---|---|---|
| PE | TTM parent net profit ÷ weighted-average total ordinary shares for the period | **weighted average** |
| PB | latest visible parent equity ÷ total ordinary shares at period end | **period-end** |
| PS | TTM revenue ÷ total ordinary shares effective on the valuation date | **period-end** (weighted-average only if separately justified) |

"Total ordinary shares" is the company-wide ordinary share count, not the A-share
count. Therefore **the A/H split is not a core-valuation blocker**; the **total
ordinary share timeline remains required** (effective dates, corporate actions,
repo-cancellation, issuance, bonus shares, rights issue).

## Supersession

- Supersedes the R4B route recommendation:
  `route = UNRESOLVED`, `route_recommendation = MARKET_CAP`.
- Effective route: `route = A_SHARE_PRICE_PER_SHARE`, `route_status = FROZEN`,
  `core_market = SSE_A_SHARE`, `a_h_split_required = false`,
  `total_ordinary_share_timeline_required = true`.
- The R4B overall decision **`PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED` is
  unchanged** — the real blocker (no quarterly financial facts) is unchanged.

## Not changed

- No historical PE/PB/PS series, no valuation percentile, no `valuation_attractiveness`
  shadow update, no scoring weights/thresholds, no peer acquisition, no M3.
- The `close_percentile` remains a non-production observation set and is never a
  valuation percentile.

## Reopen conditions

- A product scope change to a multi-listing (A+H) trading scenario.
- A decision to incorporate the A/H premium into the core score.