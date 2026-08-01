# PetroChina PIT valuation report 2021–2026

Run `stage2g_valuation_pit_20260801`; market range `2021-01-04` to `2026-07-31`; `1351` unadjusted trade days.

The runner reuses the existing `stock_daily` model and applies only Facts/Events available by each trade date. The 2024 interim event is the only corrected dual-official Rule007 input in this bounded evidence snapshot; the other nine events remain issuer-only because exact exchange payloads were inaccessible.

## Latest six observations

| Observation | Latest value | Status |
|---|---:|---|
| `a_share_price_to_latest_annual_parent_earnings` | 12.89158710139375214555441126 | `computed` |
| `a_share_price_to_latest_year_end_parent_equity` | 1.278558916853412321468089815 | `computed` |
| `a_share_price_to_latest_annual_revenue` | 0.7079400874030893683960273264 | `computed` |
| `trailing_12m_announced_dividend_yield` | — | `missing_input` |
| `trailing_12m_paid_dividend_yield` | — | `missing_input` |
| `latest_annual_fcf_proxy_yield` | 0.05903773727554334316827771199 | `computed` |

No observation is an opinion output. Historical percentile positions and fixed sample-end stress arithmetic are descriptive only.
