# M3 Stage 3C-A-R Canonical Recovery and M2 Branch Repair

## Verdict boundary

This acceptance packet replaces the misplaced M2 Stage 3C-A packet as the
canonical recovery record. The M2 tip `3679b1b` is invalid as an M3 baseline;
the recovered M3 baseline is `feat/m3-mechanism-validation-mvp` at
`987caffe5b75fa3b0de58d0add43051cc9a55d17`.

The candidate algorithm was reviewed and transplanted file-by-file. No
incident commit was cherry-picked. The frozen method core is unchanged:
adjusted close-to-close simple returns, `Crash_t = 1` for market excess return
at or below `-0.01`, the fixed OLS design, control-only abnormal return,
non-circular overlapping moving-block bootstrap, 5,000 replications, seed
`20260813`, `PCG64`, percentile 95% CI, and evidence cap 3.

## Canonical effective upstream binding

The locked inventory is:

`reports/m3_stage3car_effective_upstream_sha_inventory_v1.json`

Inventory SHA-256:

`f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`

The effective bindings are actual repository files, each checked at runtime
for path, contract ID, version, status, and exact SHA-256:

| Role | File | Contract/version | SHA-256 |
|---|---|---|---|
| Stage 3A hypothesis | `reports/m3_stage3a_mechanism_hypothesis_contract_v1.json` | `M3_STAGE3A_MECHANISM_HYPOTHESIS_CONTRACT_V1` / `1.0.0` | `1b5a042432a01d26ce3801a558322b6d0bc20627914ae6bb590aea0da1e7dc28` |
| Stage 3A statistics | `reports/m3_stage3a_statistical_protocol_v1.json` | `M3_STAGE3A_STATISTICAL_PROTOCOL_V1` / `1.0.0` | `f8a5b505e36725082a382d5012fdd8e004613dca124ac5bbde41f1a5029eb83e` |
| Stage 3A data requirements | `reports/m3_stage3a_data_requirements_v1.json` | `M3_STAGE3A_DATA_REQUIREMENTS_V1` / `1.0.0` | `261d692db3ac30bb7c09249203224d9ef7c4141a5259effb92913d412542b35f` |
| R1 effective market proxy | `reports/m3_stage3br1_primary_proxy_contract_v2.json` | `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` / `1.0.0` | `bab6878cf16b904eeb5bc48cb2b92350313ec503c25627bf614bd31af0a21e6a` |
| R2 oil timing | `reports/m3_stage3br2_oil_timing_resolution_v1.json` | `M3_STAGE3BR2_OIL_TIMING_RESOLUTION_V1` / `1.0.0` | `a5e2a247efc2f0fc3a22ee4d4b4f49fe9eca04915d0524fd8fdebef13d3f3233` |
| R4 source amendment | `reports/m3_stage3br4_source_amendment_v1.json` | `M3_STAGE3BR4_SOURCE_AMENDMENT_V1` / `1.0.0` | `5a588553aad9c15c347fb393e39059ca0ee2a926b18dd48ef6a5ca5b0922f3a2` |
| R4 effective oil transport | `reports/m3_stage3br4_oil_transport_contract_v3.json` | `M3_OIL_CONTROL_V3_TRANSPORT_CONTRACT` / `1.0.0` | `2a468d4188b603062b1c947518733ead0bca1a9f6e7de8282b18f86c61f59980` |
| R4 effective industry | `reports/m3_stage3br4_industry_contract_v2.json` | `CNI_OIL_GAS_INDUSTRY_CONTROL_V2_CONTRACT` / `1.0.0` | `9e71452cfa7d3a23c5358fea9ff78cb88fe7c61a6cf6a762cae964754a25636a` |
| R4 Tier-1 readiness | `reports/m3_stage3br4_tier1_readiness_v3.json` | `M3_STAGE3BR4_TIER1_READINESS_V3` / `1.0.0` | `b297be3d2137dd3e928532193388013113d8755238ee7566d8fab512d961e814` |

The prior exact SSE proxy, Shenwan active industry path, EIA-key-required
transport, and historical target-return contract remain lineage only and are
not effective model-input bindings. No raw/cache file, aligned real matrix,
development outcome, real coefficient, or holdout value is bound or read.

## Recovered contracts and digests

The canonical v2 contracts are:

- `reports/m3_stage3ca_analysis_pipeline_contract_v2.json`
- `reports/m3_stage3ca_model_specification_v2.json`
- `reports/m3_stage3ca_robustness_registry_v2.json`
- `reports/m3_stage3ca_output_schema_v2.json`

They record `WRONG_BASELINE_BRANCH_RECOVERY`, the invalid M2 predecessor chain,
`semantic_method_change = false`, actual SHA fail-closed upstream binding, and
canonical package integration. Model digest exclusions explicitly include real
development coefficients, real crash count, real gamma, real result files, and
holdout values.

Synthetic positive smoke produced:

- `PIPELINE_DIGEST = f667598001e8f63734547f7da281c41cf571c70667d784e35e57b6eddd4e781b`
- `MODEL_DIGEST = 28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11`

The model contract requires `statsmodels>=0.14.6,<0.15`; the verified local
version is `0.14.6`.

## Validation evidence

- Focused Stage 3C-A and recovery tests: `50 passed`.
- Explicit M3 Stage 3A/R1/R2/R3/R4 and recovery boundary set: `183 passed`.
- Canonical full suite: `2106 passed, 3 skipped`.
- M2 protected-boundary checks in the M3 worktree: `110 passed`.
- Ruff: passed (`python -m ruff check src tests`).
- Compile: passed (`python -m compileall -q src tests`).
- Diff check: passed (`git diff --check`).
- Synthetic positive/null/negative/extreme fixtures: all completed; positive
  established the synthetic primary decision, null/negative/extreme remained
  not established as expected.
- Development execution is rejected before input access with
  `REAL_ANALYSIS_NOT_AUTHORIZED`; holdout is sealed by code gate.

## Branch repair gate

M2 repair is permitted only after canonical M3 final-tip CI is green. It must
use a new M2 worktree, inverse no-commit reverts of `3679b1b`, `f5ae24f`,
`0bc0b2e`, `724d6a4`, one revert commit, and
`git diff --exit-code 241c180 HEAD --`. The original dirty M2 worktree,
untracked files, stash, database, and existing M3 worktree are protected.

Stage 3C-B is not started and is not implicitly authorized.
