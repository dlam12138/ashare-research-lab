# PetroChina value profile — one page

As of `2026-07-31`; evidence status `pass_with_explicit_gaps`; market days `1351`.

Valuation is the selected next slice. The six observations are PIT-safe, unadjusted-price, evidence-aware measures. Dividend announcement and payment windows are intentionally separate. ROIC and market mechanism remain outside scope.
Stage 2G.1 status: `pass_with_explicit_gaps`; canonical Fact input: `net_profit.duckdb` (`47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`).

| Observation | Value | Status |
|---|---:|---|
| `a_share_price_to_latest_annual_parent_earnings` | 12.89158710139375214555441126 | `computed` |
| `a_share_price_to_latest_year_end_parent_equity` | 1.278558916853412321468089815 | `computed` |
| `a_share_price_to_latest_annual_revenue` | 0.7079400874030893683960273264 | `computed` |
| `trailing_12m_announced_dividend_yield` | — | `missing_input` |
| `trailing_12m_paid_dividend_yield` | — | `missing_input` |
| `latest_annual_fcf_proxy_yield` | 0.05903773727554334316827771199 | `computed` |

## Risk-veto checks

- `future_data_leakage`: `not_observed_within_bounded_evidence`
- `canonical_identity_break`: `not_observed_within_bounded_evidence`
- `official_exchange_evidence_gap`: `observed`
- `non_positive_comparable_input`: `not_observed_within_bounded_evidence`
- `governance_risk`: `not_evaluated`
- `audit_risk`: `not_evaluated`
- `related_party_risk`: `not_evaluated`
