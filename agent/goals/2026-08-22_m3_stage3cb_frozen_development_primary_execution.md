# Goal — M3 Stage 3C-B Frozen Development Primary Execution

Status: ACTIVE — PRE-EXECUTION LOCK

## Objective

Execute one and only one frozen Stage 3C-B development primary specification
against the trusted development inputs after the pre-execution CI gate passes.
The task ends after the primary decision and deterministic same-input A/B
rerun. Registered robustness and holdout remain outside this authorization.

## Verified baseline

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Canonical starting tip: `ef1d1fab4b93ed680004430d72e49c27cb5e874e`
- Local/origin starting synchronization: `0/0`
- Stage 3C-A-R2 relock is present in canonical history.
- Required identities:
  - upstream inventory SHA: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
  - pipeline digest: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
  - model digest: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
  - digest algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`

## Authorization state

- `development_primary_execution = AUTHORIZED_ONLY_AFTER_PREEXECUTION_CI_PASS`
- `registered_robustness = NOT_AUTHORIZED`
- `holdout = SEALED`
- Before the pre-execution CI gate: real target read, real Crash, regression,
  bootstrap, and outcome read are all `NO`.

## Allowed scope

- Stage 3C-B authorization and result-schema contracts;
- independent execution-adapter digest, known-capsule locator, and matrix
  materializer;
- a separate Stage 3C-B CLI;
- synthetic pre-execution tests and CI identity gates;
- after the point-of-no-return, only the committed input manifest, primary
  result, acceptance, work record, and factual README status.

## Forbidden scope

- Any change to the Stage 3C-A model/core, frozen reports, or R2 digest code;
- network acquisition or disk-wide scanning;
- unadjusted target, alternative market/industry proxy, alternative threshold,
  robustness, holdout, year analysis, or extreme-day analysis;
- modifying adapter/model/schema after real outcome read;
- PR, merge, tag, reset, force-push, or automatic next-stage execution.

## Required behavior and method

- Target `target_daily_qfq`, adjusted close-to-close simple return only;
- market `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`;
- R4-aligned Brent `DCOILBRENTEU` and CNI `399439` controls;
- exact-date joins only;
- development sample `2015-03-16..2022-12-30` selected by
  `target_valid AND tier1_joint_valid`;
- frozen `-0.01` Crash, OLS design, 5,000-rep non-circular overlapping moving
  block bootstrap, PCG64, seed `20260813`, percentile 95% CI;
- primary decision uses only `gamma > 0 AND gamma_ci_lower > 0`;
- result evidence level is `null` and status is
  `PENDING_STAGE3CC_REGISTERED_ROBUSTNESS`.

## Required validation and acceptance

- Pre-execution focused tests cover exact identity, old-lock rejection, adapter
  digest, QFQ-only target, hash-first/leak gates, exact join/no double shift,
  CNI identity, Tier-1 readiness, and development-only mode.
- Exact pre-execution HEAD must pass Ubuntu clean-clone, Windows clean-clone,
  identity-compare, and M3 digest identity CI before real target read.
- Post-outcome focused, M3 boundary, full suite, Ruff, compileall, and diff
  check must pass; protected M2 worktree, tag, stash, and database must remain
  unchanged.

## Stop conditions

- Any identity mismatch: `M3_STAGE3CB_LOCK_IDENTITY_MISMATCH` and stop.
- Pre-execution CI failure: real development must not start.
- Any post-outcome implementation mutation: acceptance invalid.
- Any technical failure after outcome read: preserve evidence and stop.
- On either primary decision: `STOP_FOR_NORTH_STAR_REVIEW`.

## Commit/push requirements

Use logical pre-outcome commits for authorization, adapter, and tests; push
normally to `feat/m3-mechanism-validation-mvp`. After CI passes, perform the
single real execution and add only result/acceptance/record/factual README
documentation. Do not merge, tag, or force-push.
