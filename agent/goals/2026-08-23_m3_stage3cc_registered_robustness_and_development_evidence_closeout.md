# Goal — M3 Stage 3C-C Registered Robustness Execution & Development Evidence Closeout

Status: IN PROGRESS — REAL ROBUSTNESS NOT YET EXECUTED

## Objective

Execute the robustness and descriptive checks that were both registered in
Stage 3C-A-R v2 and implemented before the Stage 3C-B real outcome read.
Record complete supporting and contrary evidence, preserve the Stage 3C-B
primary conclusion permanently, and stop for North-Star review.

## Verified baseline

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD and `origin/feat/m3-mechanism-validation-mvp`:
  `4669eebf2e1837053495d56f68ea414bd76c692d`
- Local/origin synchronization: `0/0`
- Required upstream inventory SHA:
  `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline digest:
  `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model digest:
  `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
- Stage 3C-B execution adapter digest:
  `9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78`
- Stage 3C-B data manifest digest:
  `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`
- Frozen primary decision:
  `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`

## Allowed scope

- One executable plan projected from the locked Stage 3C-A-R v2 registry.
- One thin orchestration runner that materializes the same Stage 3C-B matrix,
  verifies identities, and calls existing frozen robustness/regression
  functions.
- Synthetic-only focused boundary tests and CI checks before real execution.
- After the read boundary: only the committed Stage 3C-C result, acceptance,
  work record, and factual README status.

## Forbidden scope

- Any change to `src/ashare_research/mechanism/`, especially `robustness.py`
  and `regression.py`.
- New robustness functions, post-outcome thresholds or evidence rules,
  alternative proxies, industry-ex-target data, volume/regime data, or any
  network acquisition.
- Any input date on or after `2023-01-01`; holdout remains sealed.
- Leave-one-event-out execution because no pre-outcome executable function was
  locked.
- Changing the Stage 3C-B primary decision or creating a Level 3 result.

## Required behavior

- Execute only descriptive, conditional, threshold, BH-FDR, top-1/top-3
  extreme-day, and all-calendar-year leave-one-out checks already frozen.
- Use the exact thresholds `[-0.005, -0.015, -0.020]` and BH `q=0.05`.
- Reconstruct the frozen primary OLS only for identity verification and
  extreme-day ranking.
- Run same-input A/B and require exact canonical result equality.
- Keep `development_evidence_ceiling=2`, leave Level 1/2 unassigned unless a
  concrete pre-outcome rule is proven, and always keep the primary decision
  unchanged.

## Required validation

- Focused Stage 3C-C boundary tests.
- Existing M3 boundary tests, full pytest, Ruff, compileall, and diff check.
- Exact pre-robustness CI identity across Ubuntu and Windows before real input.
- Real-run data manifest and frozen-primary identity checks.
- Post-run result A/B byte identity and explicit sealed/gap fields.

## Acceptance criteria

- All executable and pre-outcome-locked registered checks complete.
- `leave_one_event_out` is `NOT_EXECUTED_PREOUTCOME_IMPLEMENTATION_MISSING`.
- Alternative proxies are `NOT_EXECUTED_DATA_NOT_ACQUIRED`.
- Industry ex-target is `NOT_EXECUTED_FUTURE_CANDIDATE`.
- Volume/regimes are `NOT_EXECUTED` with their registered data status.
- Holdout is sealed and absent from all real inputs.
- Primary decision remains
  `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`.
- Final status is `M3_STAGE3CC_REGISTERED_ROBUSTNESS_EXECUTION_ACCEPTED` and
  work stops for North-Star review.

## Stop conditions

- Any identity, manifest, primary reconstruction, frozen implementation, CI,
  holdout, or determinism failure.
- Any need to modify the runner, plan, schema, or mechanism after the real
  robustness read boundary.
- Any proposed post-outcome evidence-level or robustness-trigger rule.

## Commit and push requirements

- Commit authorization/plan, runner/schema/tests, and closeout evidence in
  logical commits as practical.
- Push normally to `feat/m3-mechanism-validation-mvp`.
- Do not merge, tag, reset, force-push, or begin holdout/North-Star work.
