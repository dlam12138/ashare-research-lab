# M2 Stage 2K — Weights and Sensitivity Report

Contract: `value_dimension_scoring_weights_sensitivity_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose

Weights are defined only within the four top-level dimensions. There are no
weights across top-level dimensions because no overall score exists. This
report documents the weight schemes compared and the sensitivity results run
after the thresholds and transforms were frozen.

## 2. Weight schemes compared

1. **Equal subdimension weights**: every subdimension weight equal. Used as a
   baseline.
2. **Theory-informed weights**: the registered weights in the registry, chosen
   before the shadow was viewed. For `enterprise_quality`, capital return (0.30)
   > profitability (0.25) = financial safety (0.25) > cash conversion (0.20).
3. **No-aggregation evidence-card mode**: no weighting; each component is shown
   as evidence without a numeric aggregate. Preserved as the primary descriptive
   output alongside the numeric shadow.

## 3. Sensitivity results (frozen transforms, run after threshold selection)

The engine `m2_stage2k_scoring_shadow.py` computes the shadow and runs
perturbations. Results are committed in
`reports/petrochina_dimension_scoring_sensitivity_v1.json`.

### 3.1 Weight perturbation (±25% per component)

| Dimension | Base score | Perturbation range | Band spread |
|---|---|---|---|
| enterprise_quality | 73.47 (B) | 72.36 – 74.47 | B only |
| valuation_attractiveness | 12.17 (E) | 11.92 – 12.48 | E only |
| value_realization_capacity | 70.13 (B) | 69.17 – 70.93 | B only |
| risk_and_evidence_integrity | 80.40 (A) | 78.85 – 81.55 | A/B |

### 3.2 Leave-one-component-out

| Dimension | Base | Range | Band spread |
|---|---|---|---|
| enterprise_quality | 73.47 (B) | 68.05 – 77.59 | B only |
| valuation_attractiveness | 12.17 (E) | 10.43 – 13.59 | E only |
| value_realization_capacity | 70.13 (B) | 65.91 – 75.16 | B only |
| risk_and_evidence_integrity | 80.40 (A) | 73.87 – 88.10 | A/B |

### 3.3 Coverage-gate perturbation

At gates 0.4/0.6/0.8 all dimensions compute. At gate 0.95, `enterprise_quality`
(coverage 0.9, missing ROIC) and `valuation_attractiveness` (coverage 0.8,
missing dividend yield) both return `insufficient_evidence`. This demonstrates
the missing-ROIC and missing-dividend-yield behavior: they are coverage gaps,
never zeros, and push the dimension below a strict gate.

### 3.4 Missing-ROIC scenario

ROIC is a registered `enterprise_quality` component. Its absence reduces coverage
to 0.9 (below the 0.6 gate it still computes; above a 0.95 gate it flips to
`insufficient_evidence`). ROIC is never zero, never silently reweighted away, and
never described as poor capital return.

## 4. Stability assessment

- `enterprise_quality`, `valuation_attractiveness`, `value_realization_capacity`
  are stable across weight perturbation and leave-one-out (band unchanged).
- `risk_and_evidence_integrity` flips A/B at the 80-point band boundary under
  leave-one-out (73.87 when `rk_veto_triggered` is removed, 87.2 when
  `rk_missing_evidence_slots` is removed). The band is therefore **not stable**
  at its boundary.

Per the pre-registered stability rule, a dimension is not production-ready when
a reasonable change moves its band. The risk dimension is therefore **not
production-ready** as a band. It remains a valid shadow output with the A/B
boundary instability disclosed.

## 5. Conclusion

The shadow method is deterministic and its bands are stable for the quality,
valuation, and realization dimensions. The enterprise-quality thresholds are
theory-informed absolute contracts with **no peer or statistical calibration**;
they are not a sufficient production basis without a peer benchmark. The risk
dimension band is unstable at its boundary. The valuation dimension uses
PIT-safe self-history percentiles and is peer-independent.

A production dimension score therefore requires a finite peer benchmark dataset
(to calibrate the enterprise-quality thresholds and cross-check the valuation
reading) and a stability resolution for the risk band. The shadow is a valid
method test, not a production score.