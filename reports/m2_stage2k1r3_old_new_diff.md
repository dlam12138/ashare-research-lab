# M2 Stage 2K.1R3 — Old → New Diff

Status: `PASS`. Old versions (Stage 2K.1R2) are preserved as history; the v3
true-upstream paths are the formal result.

## 1. Upstream record binding

| Old (Stage 2K.1R2) | New (2K.1R3) |
|---|---|
| Capsule carried `upstream` artifact paths + `value`; resolver bound file-level inputs | Every component binds **concrete upstream records** (`ResolvedRecord`: record_id, record_digest, record_identity_type, field_path, raw_value, unit, available_at, source_tier, source_evidence_ids, gap_ids) |
| Resolver's job was effectively "file exists + artifact SHA" | Resolver's job is to return the **actual record(s)** from the artifact (facts, dividend events, risk slots, gaps, repurchase search, valuation observation) |
| Source tier was a registered label; capsule carried a claim | Source tier is **derived by the resolver** from the real source; the capsule never self-reports it |
| `m2_stage2k1r2_upstream.py` | `src/ashare_research/scoring/lineage.py` (per-type resolvers) + `config/value_dimension_scoring_upstream_registry_v1.json` (24 components) |

## 2. Capsule v3

| Old | New |
|---|---|
| `reports/petrochina_score_input_capsule_v2.json` (schema v2) | `reports/petrochina_score_input_capsule_v3.json` (schema v3, 24 components) |
| `transform_inputs` treated as the value source | `transform_inputs` are `derived_snapshot_only`; the validator recomputes from upstream and never trusts them |
| `validator_must_rebuild` absent | `validator_must_rebuild: true` on every component |
| value could be a binary float | `selected_value_decimal` is a Decimal string; `score_input_id` includes resolved source tier, record digests, artifact SHA-256, observation-set digest, time-contract digest |

## 3. Fail-closed validator

| Old | New |
|---|---|
| `m2_stage2k1r2_validate.py` recomputed artifact SHA-256 / record identity / value / score_input_id / capsule_digest | `m2_stage2k1r3_closeout.validate_capsule` recomputes the **entire score input** from upstream via the shared `_make_score_input` (records → transform → score_input_id) and compares it to the capsule claim |
| Capsule `resolved_records` snapshot was trusted | Validator ignores the capsule's resolved-records snapshot and recomputes from upstream; a tampered snapshot with a correct ID still passes (proving upstream is the source of truth) |
| All registry components not required to be present | Every registry component must be present in the capsule (missing → error) |
| composite tamper not covered | `tests/stage2k1r3/test_composite_tamper.py` proves transform_inputs + value + source_tier + record snapshot + score_input_id + capsule_digest tampering all fail closed |

## 4. Pure-function transform registry

| Old | New |
|---|---|
| scoring inputs computed inline in the capsule builder | `src/ashare_research/scoring/transforms.py`: Decimal pure functions (layer 1: records → metric values) + `config/value_dimension_scoring_transform_registry_v2.json` with explicit layer separation from layer 2 (metric values → scores) |
| divide-by-zero / missing operand silently handled | `TransformError` fail-closed; dividend coverage sums across multiple events |

## 5. Market observation set (real cache)

| Old | New |
|---|---|
| Percentile lineage from committed manifest obs sets | `src/ashare_research/scoring/market_observation_set.py` builds a real observation set from the **verified external cache** (PIT exclusion, per-trade-date observation_id, 3y/5y date-windowed close percentiles, observation-set digest) |
| Real percentile not recomputed from external cache | Real-mode capsule uses the **cache-recomputed** close percentile for price-multiple metrics (PE/PB/PS); yield metrics (FCF/dividend) are marked not-cache-recomputable and stay coverage gaps |
| No committed-percentile fallback distinction | `percentile_source` field distinguishes `external_cache_recomputed` vs `committed_manifest`; real mode never falls back to committed percentiles |

## 6. Confidence / shadow / sensitivity v3 → v4

| Old | New |
|---|---|
| Confidence v2 | Confidence v3 reads only the validated derived source tiers; valuation coverage gaps (e.g. `va_dividend_yield`) are flagged |
| Shadow v3 | Shadow v4 + sensitivity v4 keep `NOT_STABLE` honestly; no production score, no overall, no recommendation |
| risk dimension could be numerically scored | risk dimension is `status_outputs` (`no_merged_numeric_score: true`) |

## 7. CLI orchestration

| Old | New |
|---|---|
| one-off scripts | `m2_stage2k1r3_closeout` CLI: resolve, build-capsule, validate, build-market-observation-set, build-confidence, build-shadow, build-sensitivity, verify-artifacts (real mode via `--market-cache-root --market-registry`) |