# M2 Stage 2K — Scoring Input Eligibility and Input Contract

Contract: `value_dimension_scoring_input_contract_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose

Every scoring component must bind to a stable canonical Metric Result, evidence
observation, or evidence slot. This document records the actual input
eligibility for the PetroChina (`601857.SH`) non-production shadow. It is
derived from the committed value profile, the run-scoped metric results, and
the canonical gap ledger. It does not assume a displayed value is suitable for
scoring; it records the eligibility contract for each.

## 2. As-of date and PIT boundary

The shadow is scored as of `2026-07-31`. A component is eligible only when its
`available_at` (or `conclusion_available_at`) is `<= 2026-07-31`. The FY2025
metric results (`available_at = 2026-03-30`) are visible. The two dividend-yield
observations are `missing_input` at the latest date and are therefore coverage
gaps, not zeros.

## 3. Input inventory

### 3.1 Valuation observations (from `reports/petrochina_value_profile.json`, as of 2026-07-31)

| Role | Metric/observation ID | Value | 3y pct | 5y pct | Status | PIT | Eligible for shadow |
|---|---|---|---|---|---|---|---|
| PE | `a_share_price_to_latest_annual_parent_earnings` | 12.8916 | 0.921 | 0.945 | computed | yes | yes (percentile) |
| PB | `a_share_price_to_latest_year_end_parent_equity` | 1.2786 | 0.845 | 0.893 | computed | yes | yes (percentile) |
| PS | `a_share_price_to_latest_annual_revenue` | 0.7079 | 0.921 | 0.945 | computed | yes | yes (percentile) |
| FCF yield | `latest_annual_fcf_proxy_yield` | 0.0590 | 0.174 | 0.120 | computed | yes | yes (percentile) |
| Announced div yield | `trailing_12m_announced_dividend_yield` | null | null | null | missing_input | — | coverage gap (partial 0.0250 at 2025-09-09) |
| Paid div yield | `trailing_12m_paid_dividend_yield` | null | null | null | missing_input | — | coverage gap (partial 0.0268 at 2025-09-18) |

### 3.2 Capital returns (run-scoped metric results; values in `output/` and acceptance docs)

| Role | Metric ID | FY2025 value | Status | PIT | Eligible |
|---|---|---|---|---|---|
| ROE | `return_on_average_equity_attributable_to_parent` | 0.1014 | computed | yes | yes |
| ROA | `return_on_average_total_assets` | 0.0616 | computed | yes | yes |
| ROIC | `roic` | not computable | not_computable | no | coverage gap (M2G-ROIC-001..007) |

ROE series 2021–2025: 0.0743 / 0.1131 / 0.1146 / 0.1110 / 0.1014.
ROA series 2021–2025: 0.0460 / 0.0631 / 0.0665 / 0.0667 / 0.0616.

### 3.3 Earnings quality and cash flow (run-scoped metric results)

| Role | Metric ID | FY2025 value | Status | PIT | Eligible |
|---|---|---|---|---|---|
| Gross margin | `gross_margin` | 0.2159 | computed | yes | yes |
| Operating margin | `operating_profit_margin` | 0.0819 | computed | yes | yes |
| NP YoY | `net_profit_attributable_to_parent_yoy` | -0.0448 | computed | yes | yes |
| Deducted NP YoY | `net_profit_excluding_non_recurring_yoy` | -0.0670 | computed | yes | yes |
| Revenue YoY | `revenue_yoy` | -0.0250 | computed | yes | yes |
| OCF YoY | `operating_cash_flow_yoy` | 0.0147 | computed | yes | yes |
| OCF/NP | `operating_cash_flow_to_attributable_net_profit` | 2.6224 | computed | yes | yes |
| FCF proxy | `cash_based_free_cash_flow_proxy` | 11,972,100 万元 | computed | yes | yes (level) |
| Capex/revenue | `cash_paid_for_fixed_assets_to_revenue` | 0.1022 | computed | yes | descriptive |

### 3.4 Financial safety (from `reports/petrochina_financial_safety_2021_2025.md`)

| Role | Metric ID | FY2025 value | Status | PIT | Eligible |
|---|---|---|---|---|---|
| Asset/liability | `asset_liability_ratio` | 0.3637 | computed | yes | yes |
| Gross interest-bearing debt | `gross_interest_bearing_debt` | 35,345,000 万元 | computed | yes | descriptive |
| Cash coverage | `cash_coverage_of_interest_bearing_debt` | 0.5833 | computed | yes | yes |
| Net interest-bearing debt | `net_interest_bearing_debt` | 14,728,800 万元 | computed | yes | descriptive |

### 3.5 Dividend realization (from Stage 2F run `dividend_metric_results.json`)

| Role | Metric ID | FY2025 value | Status | PIT | Eligible |
|---|---|---|---|---|---|
| Payout ratio | `cash_dividend_payout_ratio` | 0.5468 | computed | yes | yes |
| OCF dividend coverage | `operating_cash_flow_dividend_coverage` | 4.7955 | computed | yes | yes |
| FCF dividend coverage | `free_cash_flow_proxy_dividend_coverage` | 1.3918 | computed | yes | yes |
| Dividend per share | `implemented_cash_dividend_per_share` | 0.47000 CNY | computed | yes | yes |

### 3.6 Risk-veto slots (from `reports/petrochina_value_profile.json`)

Eight fixed risk slots. Six are `not_observed_within_bounded_evidence`; two are
`missing_evidence`: `formal_regulatory_investigation_or_major_discipline` and
`controlling_shareholder_fund_occupation_or_related_guarantee`. A `missing_evidence`
slot is not a negative conclusion. No veto is triggered.

### 3.7 Canonical gaps (from `reports/m2_explicit_gap_ledger.json`)

18 current gaps: 9 Stage 2F (`M2G-DIV-001..009`), 2 Stage 2H
(`M2G-RISK-001..002`), 7 Stage 2I (`M2G-ROIC-001..007`).

## 4. Eligibility contract

A component is eligible for the shadow only when:

- it binds to a stable Metric Result / evidence ID with a versioned contract;
- its `available_at` is `<=` the score date;
- its value is not fabricated and not a forbidden fallback;
- its directionality and transform are registered.

ROIC is a registered coverage gap, not a zero. The two dividend-yield
observations are coverage gaps at the latest date. The repurchase scan is a
bounded no-event scan, not a zero repurchase fact.

## 5. Forbidden inputs

- Any proxy, residual, plug, or zero-fill ROIC.
- Any peer percentile without a registered peer universe.
- Any LLM-assigned score.
- Any future-distribution percentile for a historical score.
- Missing evidence treated as evidence of no risk.