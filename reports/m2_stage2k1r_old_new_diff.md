# M2 Stage 2K.1R — old → new diff

Scope: Stage 2K (hand-maintained shadow inputs) → Stage 2K.1R (capsule-backed,
confidence-contracted, risk-reassessed). All scores are non-production.

## 1. Inputs: hand-maintained JSON → deterministic capsule

| Aspect | Old (Stage 2K) | New (Stage 2K.1R) |
|---|---|---|
| Input source | `config/value_dimension_scoring_shadow_inputs_v1.json` (hand-maintained) | `reports/petrochina_score_input_capsule_v1.json` (built by `m2_stage2k1r_capsule.py`) |
| Artifact binding | none recorded | every component → upstream artifact SHA-256, contract version, record, value, unit, date, available_at |
| Determinism | manual | `build_capsule()` deterministic; digest `dab07d9f1f6c04a7bc45cb55a703a57f07610e5e74cd742f94aa7885150301cb` |
| Percentile binding | naked `percentile_3y` | observation-set ID, window, sample count, set digest, observation dates, method, artifact hash |
| Missing upstream identity | absent | coverage gap (ROIC / dividend yield), never zero |

## 2. Scored dimensions — unchanged (A/B match)

| Dimension | Old score | New score | Band | Match |
|---|---|---|---|---|
| enterprise_quality | 73.47 | 73.47 | B | MATCH |
| valuation_attractiveness | 12.17 | 12.17 | E | MATCH |
| value_realization_capacity | 70.13 | 70.13 | B | MATCH |

## 3. Risk dimension — semantic reassessment

| Aspect | Old (Stage 2K) | New (Stage 2K.1R) |
|---|---|---|
| Representation | merged numeric score 80.40 / band A | `risk_veto_status` (clear) + `evidence_integrity` (medium) |
| Merged score | yes | no — `no_merged_numeric_score: true` |
| Veto | non-compensatory | non-compensatory (unchanged) |
| Rationale | risk conflated into one number | veto and integrity are separate products; a merged score can mask a serious veto |

## 4. Confidence — new product

Old had no per-dimension evidence-confidence separation. New emits a versioned
confidence contract (`config/value_dimension_scoring_confidence_v1.json`) and a
per-dimension grade with reasons and supporting gap IDs. All four dimensions are
`medium`. ROIC absence lowers confidence but is never zero; stage gap IDs are
carried through.

## 5. Sensitivity — complete frozen set

Old sensitivity covered weight / leave-one-out / coverage-gate only. New adds
frozen transform alternatives, confidence-threshold gates, and missing-ROIC
scenarios (current gap, synthetic-neutral test, no-ROIC comparison), and emits
machine-derived stability per dimension.

| Dimension | Old max-delta signal | New max_score_delta | New stability_status |
|---|---|---|---|
| enterprise_quality | n/a | 9.54 | NOT_STABLE |
| valuation_attractiveness | n/a | 3.16 | NOT_STABLE |
| value_realization_capacity | n/a | 9.25 | NOT_STABLE |

Tolerance (`stability_tolerance=1.0`) is frozen and was not relaxed. `NOT_STABLE`
is the honest machine-derived result; it is the concrete basis for decision
`SCORING_CONTRACT_GAPS_REMAIN`.

## 6. Production boundary — unchanged

Both stages: `non_production=true`, `research_methodology_test_only=true`,
`overall_score_prohibited=true`, `recommendation_prohibited=true`,
`score_eligible=false`. No production score, table, Metric Result, or registry
entry is written. `reports/petrochina_value_profile.json` is untouched.