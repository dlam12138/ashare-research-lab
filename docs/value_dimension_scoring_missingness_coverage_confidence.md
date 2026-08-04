# M2 Stage 2K — Missingness, Coverage, and Confidence Contract

Contract: `value_dimension_scoring_missingness_coverage_confidence_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose

Score, coverage, and confidence are three different outputs. This contract
separates them so that a missing input is never zero, never silently dropped,
and never disguised as a business-quality conclusion.

## 2. Definitions

- **eligible weight**: the sum of the registered weights of all components in a
  dimension.
- **covered weight**: the sum of the registered weights of components that have
  a valid input as of the score date.
- **coverage ratio**: `covered weight / eligible weight`.
- **weight renormalization**: scaling the covered weights so they sum to 1.0, so
  the dimension score is computed over the covered set.
- **evidence confidence**: a separate, qualitative assessment of how much the
  underlying evidence is trusted, reduced by explicit Stage 2F/2H/ROIC gaps.

## 3. Rules

1. A missing input is never zero.
2. A missing input is never silently dropped; it appears in `missing_component_ids`
   and `missing_gap_ids`.
3. Weight renormalization is allowed only when `coverage_ratio >= minimum_coverage_gate`
   (0.6 by default). Both original and effective weights are reported.
4. Below the coverage gate, the dimension returns `insufficient_evidence` and no
   numeric score or band.
5. ROIC absence reduces `enterprise_quality` coverage; it is never a zero and
   never described as poor capital return.
6. Stage 2F (dividend) gaps reduce evidence confidence by an explicit rule; they
   do not lower the business-quality score.
7. Stage 2H (risk) missing-evidence slots reduce evidence confidence; they are
   not a negative conclusion and not a risk veto.
8. Evidence confidence is never described as business quality.
9. A trusted high score with low coverage is not a strong conclusion.
10. All missingness and confidence rules are frozen before the shadow run.

## 4. Confidence reduction rule

Evidence confidence is reduced from `full` by:

- 9 Stage 2F dividend exchange-payload gaps: `high_confidence` (trusted metric
  values, dual-source dividend evidence incomplete);
- 2 Stage 2H missing-evidence risk slots: `qualified_confidence`;
- 7 Stage 2I ROIC gaps: `qualified_confidence` for the capital-return reading.

The business-quality score itself is not reduced by these gaps; only the
confidence attached to the evidence is reduced.

## 5. Dimension statuses

Allowed statuses (from the policy):

- `computed_shadow` — a numeric score was computed;
- `ordinal_shadow` — an ordinal band was computed;
- `insufficient_evidence` — coverage below the gate; no score;
- `blocked_by_risk_veto` — a veto flag is set;
- `not_applicable` — the dimension does not apply;
- `not_trusted` — the contract is not trusted.

## 6. Output contract

Every dimension result contains:

- score or band;
- score status;
- eligible weight;
- covered weight;
- coverage ratio;
- evidence confidence/status;
- missing component IDs;
- explicit gap IDs;
- risk-veto flags;
- input IDs;
- methodology and benchmark versions;
- `available_at`;
- deterministic identity.