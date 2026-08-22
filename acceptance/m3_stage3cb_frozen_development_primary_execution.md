# M3 Stage 3C-B — Frozen Development Primary Execution Acceptance

Status: `COMPLETED — STOP_FOR_NORTH_STAR_REVIEW`

## Scope and authorization

Exactly one frozen `development-primary` analysis was completed after the
pre-execution identity gate. Registered robustness was not executed and the
holdout was not read. No Stage 3C-A core, frozen contract, alternate proxy,
threshold, year, or post-outcome implementation was changed.

The first invocation failed at input location with
`INPUT_LOCATOR_MISSING:target_daily_qfq` before target bytes were read. The
registered Stage 3B capsule stores the manifest-relative raw path beneath its
`raw` subdirectory, so the same locked execution was rerun with
`D:\\m3_stage3b_external_20260814\\raw` as the target raw root. No source
mutation occurred between the two invocations.

## Identity and gate evidence

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Starting baseline: `ef1d1fab4b93ed680004430d72e49c27cb5e874e`
- Final execution HEAD: `95359971771a43f8efe57541d9270e72daf65ea4`
- Pre-execution CI: run `32566610112`, Ubuntu clean-clone, Windows
  clean-clone, and identity-compare all `success`
- M3 Stage 3C-A-R2 digest identity: run `32566610106`, `success`
- Stage 2G protected reproducibility: run `32566610115`, `success`
- Upstream inventory: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
- Algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`
- Execution adapter digest:
  `9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78`

## Frozen result

- Data manifest digest:
  `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`
- Sample: `2015-03-16` through `2022-12-30`, `nobs=1902`
- Crash rule: `-1%`; crash count: `330`
- `alpha=-0.0003785919801081104`
- `beta_market=0.3648969021551963`
- `beta_oil=0.060367946977032155`
- `beta_industry=0.17210333884909473`
- `gamma=0.0005072734676652487`
- 5,000-rep non-circular overlapping moving-block bootstrap, block length 12,
  PCG64 seed `20260813`
- 95% CI for gamma:
  `[-0.0021987423016553366, 0.0033325010311833106]`
- Primary decision:
  `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`
- Evidence status: `PENDING_STAGE3CC_REGISTERED_ROBUSTNESS`
- Same-input A/B: `exact_match=true`; both runs used the same data manifest,
  adapter digest, model digest, and primary result.

The result does not establish positive controlled abnormal performance. It
does not support causal, actor-intent, policy-intervention, or “护盘/国家队”
inferences. Those questions remain outside this result contract.

## Input evidence

- Target raw SHA-256:
  `e5700ddfa965db80efd12188b8529c3d5f6f42fdfeabe08135e0663a106b2ee2`
- Target logical digest:
  `c0485b55e07551a1a98c1f4cd33f3791814b6c3df6c1351d4ca634a97eebb1ab`
- Market implementation: `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`, 1,902 valid
  rows and 68 gap rows
- Oil raw SHA-256:
  `185080c6937d09b1dc3a2db46746a8e9bbdac5d17d8165596e9211fcc45e2d53`
- Oil aligned logical digest:
  `1de98bf258b2a21090b46b179485dace61fc9b3027587b61a652970e1e20e5f7`
- Industry CNI `399439`; raw SHA-256:
  `c80a609c6dc1ff461b6010f0b1ebcd2230095f466af4f257be91d74faf9afee6`
- Industry aligned logical digest:
  `a0bb7fa659f56e5f325f09b112d62443e26391b7d961b193689cff56172a6567`
- Tier-1 readiness logical digest:
  `801e877568d83021e71ebafe977e6b26d571155c2f61c6ca8f8ee265f90e264c`

All bounded date scans passed with maximum date `2022-12-30`; holdout status
is `SEALED` and `holdout_read=false`.

## Validation and closeout

Pre-execution focused and boundary tests passed: `182 passed, 1 skipped`.
Ruff, compileall, and `git diff --check` passed before the real execution.
The post-outcome result and manifest were checked against the frozen schema and
forbidden-field boundary; no p-value, t-value, R², robustness, or holdout
result was emitted.

Stop condition: `STOP_FOR_NORTH_STAR_REVIEW`. Stage 3C-C, registered
robustness, holdout access, and further research execution are not authorized
by this task.
