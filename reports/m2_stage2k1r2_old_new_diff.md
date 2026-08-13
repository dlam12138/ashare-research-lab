# M2 Stage 2K.1R2 — Old → New Diff

Status: `PASS`. Old versions (Stage 2K.1R) are preserved as history; the v2/v3
paths are the formal result.

## 1. Time contract

| Old (Stage 2K.1R) | New (2K.1R2) |
|---|---|
| Single ambiguous `score_date` | Four explicit time points: `market_data_as_of_date` (2026-07-31), `research_evidence_as_of` (2026-08-02), `scorecard_formed_at` (2026-08-02), legacy `score_date` |
| Future availability treated as a confidence finding | Any input `available_at > scorecard_formed_at` or `trade_date > market_data_as_of_date` is a validation **error** (fail-closed) |
| `scorecard_formed_at` not explicitly derived | Derived from / verified against max included input `available_at` |

## 2. Score-Input Capsule

| Old | New |
|---|---|
| `reports/petrochina_score_input_capsule_v1.json` (schema v1) | `reports/petrochina_score_input_capsule_v2.json` (schema v2, digest `3399691...`) |
| `score_date` field | `time_contract` identity object (4 fields + digest) |
| `upstream` single-string artifact | `upstream_refs` typed list (record_id, source_evidence_ids, artifact) |
| `value` as binary float | `value`/`transform_output` as Decimal string; `transform_inputs` recorded |
| observation sets not fully identified | `observation_set` with digest, provider, scope, sample counts (percentile lineage) |
| no `score_input_id` recompute | canonical `score_input_id` (excludes paths/cwd/formatting; includes artifact SHA-256, records, source evidence, transform, value, unit, observation-set digest, time-contract digest) |

## 3. Capsule validator

| Old | New |
|---|---|
| Validator returned `(errors, pit_findings)`; future availability = finding | Fail-closed; any error blocks shadow; PIT is a hard error |
| Did not recompute artifact SHA-256 / record identity / value / score_input_id / capsule_digest | Recomputes all of these; independent value recompute; tamper test fails closed |
| example: `m2_stage2k1r_validate.py` | `m2_stage2k1r2_validate.py` |

## 4. Percentile lineage

| Old | New |
|---|---|
| Percentiles present but no full observation-set identity | `config/value_dimension_scoring_percentile_contract_v1.json` + `reports/petrochina_valuation_percentile_observation_sets_v1.json`; digest `3dcf1beef...` shared with capsule |

## 5. Confidence

| Old | New |
|---|---|
| `value_dimension_scoring_confidence_v1.json`; source_tier registered but engine did not execute it | `value_dimension_scoring_confidence_v2.json`; source-tier registry executed per component; dimension grade = weakest present grade capped at medium on coverage gap |

## 6. Sensitivity

| Old | New |
|---|---|
| Confidence-threshold scenario mutated `minimum_coverage_gate` (gate bug) | Confidence-gate and coverage-gate are independent; confidence gate evaluates the executed v2 grade and never mutates the coverage gate |
| `reports/petrochina_dimension_scoring_sensitivity_v2.json` | `reports/petrochina_dimension_scoring_sensitivity_v3.json` |

## 7. Shadow

| Old | New |
|---|---|
| `reports/petrochina_dimension_scoring_shadow_v2.json` | `reports/petrochina_dimension_scoring_shadow_v3.json` (fail-closed, time_contract identity, scorecard_formed_at derived) |

## 8. Stop Hook

| Old | New |
|---|---|
| Asserted only a local `.codex/` hook file could fix Stop Hook JSON | Verified `.codex/` absent, `.claude/` absent, `.git/hooks/` empty → no local file to fix; documented as hosting-environment concern |