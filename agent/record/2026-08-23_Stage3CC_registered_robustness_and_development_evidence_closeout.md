# Work Record — M3 Stage 3C-C Registered Robustness Execution & Development Evidence Closeout

Status: COMPLETED — STOP_FOR_NORTH_STAR_REVIEW

## Execution identity

- Date: 2026-08-23
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `4669eebf2e1837053495d56f68ea414bd76c692d`
- Pre-robustness HEAD: `eb0d51fe46f0c9da38932dad2a51a9073d66864a`
- Final documentation HEAD: recorded after this closeout commit
- Local/origin pre-robustness synchronization: `0/0`
- Stage 3C-C real read boundary:
  `STAGE3CC_REAL_ROBUSTNESS_READ_BOUNDARY_REACHED`

## Pre-robustness gate evidence

- Stage 3C-C pre-robustness lock run `32611064095`: PASS
  (Ubuntu clean-clone, Windows clean-clone, identity-compare)
- Stage 3C-B pre-execution lock run `32611064044`: PASS
- Stage 3C-A-R2 digest identity run `32611064041`: PASS
- Stage 2G protected reproducibility run `32611064040`: PASS after rerunning
  only the artifact-download failure caused by transient `ECONNRESET`
- All gates matched pre-robustness HEAD `eb0d51fe...`; no real capsule was read
  before these gates passed.

## Canonical digests

- Digest algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`
- Upstream inventory:
  `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline:
  `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model:
  `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
- Stage 3C-B execution adapter:
  `9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78`
- Stage 3C-B data manifest:
  `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`
- Stage 3C-C robustness execution:
  `8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527`
- Frozen `robustness.py` SHA-256:
  `4d295343b2c4e60730e1e6b1f1887df17a7149b51d5e1066c84871bf55394fdd`
- Frozen `regression.py` SHA-256:
  `6a52f4f8a435cac9c0acf8221f5448eef68430cca2ad3ffb45b42f5bd5e812a6`

## Real execution and A/B

The existing Stage 3C-B adapter rematerialized the same target, market proxy,
oil, industry, join rule, and development selector. The resulting data
manifest matched exactly. Primary OLS reconstruction matched all committed
coefficients and the frozen counts/gamma. The runner invoked only existing
frozen descriptive, conditional, threshold, BH, extreme-day, and
leave-one-year-out functions.

Same-input A/B was exact: `exact_match=true`, with identical data-manifest
digest `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`.

Observed registered evidence was recorded without post-hoc interpretation:

- full-sample correlation `0.4034839949585595`; last rolling-60d correlation
  `0.08208780048558555`;
- crash mean `-0.009889664894067033` versus ordinary mean
  `0.0018715228952178539`, with mean difference
  `-0.011761187789284887`;
- threshold gammas were positive at `-0.005` and `-0.015`, negative at
  `-0.020`; BH adjusted values were all `0.9879389529356545` and all rejects
  were `false`;
- top-1 removed `2015-07-15`, top-3 removed `2015-07-15`, `2015-07-02`,
  `2015-07-06`; refit gammas were `0.0006960328859629838` and
  `0.0007173882232737825`;
- leave-one-year-out was run for every observed year `2015` through `2022`.

## Boundaries and final state

- Primary decision: permanently unchanged and not established.
- `leave_one_event_out`: not executed because it was not pre-outcome locked.
- Alternative proxies, volume/regimes, and industry ex-target: not executed.
- Development evidence ceiling: `2`; final Level 1/2: `null`.
- Holdout: `SEALED`, `holdout_read=false`.
- No mechanism implementation, execution plan, schema, or computation test
  was changed after the real robustness read boundary.
- Next stage is not authorized; stop for North-Star review.
