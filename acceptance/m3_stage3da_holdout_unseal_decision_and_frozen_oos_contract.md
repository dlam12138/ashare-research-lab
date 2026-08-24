# M3 Stage 3D-A — Holdout Unseal Decision & Frozen OOS Execution Contract

Status: `M3_STAGE3DA_HOLDOUT_UNSEAL_DECISION_ACCEPTED`

## Frozen disposition

- Real holdout read: `NO`; download, parse, and hash: `NO`
- Development primary: `PERMANENTLY NOT_ESTABLISHED`
- Development robustness: `COMPLETED`
- Development evidence ceiling: `2`; evidence level: `null`
- Holdout: `SEALED`
- Holdout window: `2023-01-01..2026-08-13`
- Holdout execution in Stage 3D-A: `NOT PERFORMED`
- Stage 3D-B: `NOT_STARTED`; separate authorization required

The decision to allow a future execution is
`ALLOW_ONE_FROZEN_OOS_PRIMARY_EXECUTION_AFTER_SEPARATE_STAGE3DB_AUTHORIZATION`.
It does not unseal or read the holdout in this stage.

## Frozen Stage 3D-B scope

The future scope is exactly one `FROZEN_PRIMARY_ONLY` OOS execution using the
registered target, market ex-target proxy, strictly-prior Brent alignment,
CNI 399439 industry control, `Crash_t <= -0.01`, OLS, and the pre-registered
5,000-replication PCG64 moving-block bootstrap. The accepted execution count is
one. An A/B rerun is permitted only on the identical immutable analysis matrix
and does not create a new research trial.

New models, thresholds, proxies, controls, robustness searches, and holdout
extension are prohibited. Stage 3D-B will not repeat Stage 3C-C robustness.

## Interpretation boundary

The purpose is `FROZEN_OUT_OF_SAMPLE_FALSIFICATION`, not development-result
rescue. A positive holdout cannot reverse the development primary, establish
an overall primary, support causal or funding-actor claims, or authorize
minute-level research. The machine-readable policy freezes these outcomes:

- development not established + holdout not established →
  `M3_DAILY_MECHANISM_NOT_SUPPORTED_ACROSS_DEVELOPMENT_AND_HOLDOUT`
- development not established + holdout positive →
  `M3_DEVELOPMENT_NOT_ESTABLISHED_HOLDOUT_POSITIVE_CROSS_PERIOD_INSTABILITY`
- technically invalid/insufficient holdout →
  `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`

Index contribution is `DEFERRED_SEPARATE_MECHANICAL_ANALYSIS`; it is not
required for Stage 3D-B and was not executed.

## Evidence

The offline validator and focused tests use only committed contracts and
metadata. They do not import data providers, access the network, materialize a
matrix, run regression/bootstrap, or read holdout observations.

Final stop condition: `STOP_FOR_NORTH_STAR_REVIEW`.
