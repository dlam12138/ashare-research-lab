# M2 value-assessment completion matrix

Contract: `m2_module_status_v1`

North-Star decision: `M2_SCORING_ADDENDUM_REOPENED`

Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM REOPENED

This is a status matrix, not a numeric completion score. The machine-readable
authority is `reports/m2_value_assessment_completion_matrix.json`.

| Module | Status | Years | Evidence boundary |
|---|---|---|---|
| Data foundation dependency | `complete_trusted` | 2021–2025 | Canonical Fact/PIT/Identity/reproducibility dependency is trusted; clean clones do not require the default DB. |
| Profitability and cash-flow quality | `complete_trusted` | 2021–2025 | Deterministic accepted results remain trusted; FCF proxy is not a full valuation. |
| ROE | `complete_trusted` | 2021–2025 | Existing accepted ROE results are unchanged; ROE is not ROIC. |
| ROA | `complete_trusted` | 2021–2025 | Existing accepted ROA results are unchanged; ROA is not ROIC. |
| Financial safety | `complete_trusted` | 2021–2025 | Accepted debt/liquidity slice; does not mean no financial risk exists. |
| Dividend realization | `complete_with_explicit_gaps` | 2021–2025 | Nine exchange payload gaps remain; missing inputs are not zero. |
| Repurchase evidence | `complete_with_explicit_gaps` | 2021–2025 | Bounded no-event scan is not a zero-value repurchase Fact. |
| PIT valuation | `complete_with_explicit_gaps` | 2021–2025 | Non-dividend observations are usable; affected dividend observations retain missing/partial status. |
| Valuation history and stress scenarios | `complete_with_explicit_gaps` | 2021–2025 | Descriptive history and fixed stresses are not forecasts, probabilities, or targets. |
| Value-realization layer | `complete_with_explicit_gaps` | 2021–2025 | Dividend/repurchase evidence remains bounded and score-ineligible. |
| Risk-veto layer | `complete_with_explicit_gaps` | 2021–2025 | Two slots remain `missing_evidence`; no veto observed within bounded evidence is not no governance risk. |
| ROIC | `not_computable_under_strict_evidence_contract` | — | Seven exact gaps block numerator/denominator scope matching; no number, shadow, or production result exists. |
| One-page value profile | `complete_with_explicit_gaps` | 2021–2025 | Trusted dimensions plus explicit current gap statuses; no recommendation. |
| Scoring | `scoring_addendum_reopened` | — | Eighteen explicit gaps remain; scoring is a non-production shadow, not a fifth overall score. |
| Market mechanism | `not_started` | — | Only `M3_NORTH_STAR_PREFLIGHT_ALLOWED`; no M3 implementation has started. |

## Current gap links

- Dividend: `M2G-DIV-001` through `M2G-DIV-009`.
- Risk veto: `M2G-RISK-001` and `M2G-RISK-002`.
- ROIC: `M2G-ROIC-001` through `M2G-ROIC-007`.

The canonical definitions, acceptance references, artifacts, conclusions,
prohibited interpretations, readiness, validated commit, CI references, and
supersession mapping are recorded per module in the JSON matrix.

## Boundary

Conditional closeout does not claim that M2 is fully complete, ROIC is
complete, no missing evidence exists, no governance risk exists, or PetroChina
is undervalued. It emits no buy/sell conclusion, target price, rating, or score.
