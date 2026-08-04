# PetroChina Dimension Scoring Shadow v1 (non-production)

Contract: `petrochina_dimension_scoring_shadow_v1`
Symbol: `601857.SH`  Score date: `2026-07-31`

> **NON-PRODUCTION, RESEARCH METHODOLOGY TEST ONLY.** No overall score, no
> ranking, no recommendation, no target price. `score_eligible=false`.

| Dimension | Score | Band | Status | Coverage | Missing components |
|---|---|---|---|---|---|
| enterprise_quality | 73.4738 | B | ordinal_shadow | 0.90 | eq_roic |
| valuation_attractiveness | 12.1733 | E | ordinal_shadow | 0.80 | va_dividend_yield |
| value_realization_capacity | 70.1253 | B | ordinal_shadow | 1.00 | - |
| risk_and_evidence_integrity | 80.4 | A | ordinal_shadow | 1.00 | - |

## Risk-veto overlay

- Triggered vetoes: 0 of 8
- Missing-evidence slots: 2 (not a negative conclusion)
- Canonical gaps: 18 (9 DIV + 2 RISK + 7 ROIC)

## Interpretation boundary

- The valuation dimension is `E` because PE/PB/PS are at 92nd/85th/92nd
  percentiles of PetroChina's own 3y history and FCF yield at 17th percentile;
  this is a self-history reading, not a peer or cycle-adjused claim.
- ROIC is a coverage gap in enterprise_quality, not a zero or poor capital return.
- Missing dividend yield is a coverage gap; it is not zero.
- Risk vetoes are non-compensatory; no high score erases a veto.
- This is a methodology test, not a buy/sell/hold conclusion.

## Deterministic identity

Shadow JSON SHA-256: `108292c807ca31be402eeea1f85793a2f8e4acb0d5a88d0ee9ca22632683e76b`
