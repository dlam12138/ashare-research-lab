# Work Record — M3 Stage 3D-A Holdout Unseal Decision & Frozen OOS Execution Contract

Status: COMPLETED — STOP_FOR_NORTH_STAR_REVIEW

## Git and baseline

- Date: 2026-08-23
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `e33373be513ef36f407bc5662caa6e9e2f2e5943`
- Final HEAD: recorded in the final evidence packet after closeout
- Starting local/origin synchronization: `0/0`
- No reset, force-push, merge, tag, or operation on the original M2 worktree

## Frozen identity anchors

- Digest algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`
- Upstream inventory: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
- Stage 3C-B execution adapter: `9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78`
- Stage 3C-B data manifest: `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`
- Stage 3C-C robustness execution: `8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527`

## Contracts and evidence

- Goal: `agent/goals/2026-08-23_m3_stage3da_holdout_unseal_decision_and_frozen_oos_contract.md`
- Decision: `reports/m3_stage3da_holdout_unseal_decision_v1.json`
- Frozen OOS execution: `reports/m3_stage3da_frozen_oos_execution_contract_v1.json`
- Interpretation policy: `reports/m3_stage3da_holdout_interpretation_policy_v1.json`
- Validator: `src/ashare_research/tools/m3_stage3da_contract_check.py`
- Acceptance: `acceptance/m3_stage3da_holdout_unseal_decision_and_frozen_oos_contract.md`

## Execution boundary

- Holdout window: `2023-01-01..2026-08-13`
- Holdout status: `SEALED`
- Real holdout read: `NO`
- Network acquisition: `NO`
- Regression/bootstrap/gamma: `NOT EXECUTED`
- Stage 3D-B: `NOT_STARTED`; separate authorization required
- Stage 3C-B primary remains `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`
- Stage 3C-C robustness remains `M3_REGISTERED_EXECUTABLE_DEVELOPMENT_ROBUSTNESS_COMPLETED`

## Validation and protected state

- Focused Stage 3D-A tests: recorded in final evidence packet
- M3 boundary tests, full suite, Ruff, compileall, diff-check: recorded in final evidence packet
- Final-tip CI: recorded in final evidence packet
- Protected M3 artifacts: SHA regression against starting HEAD passed
- Original M2 dirty worktree, stash, tag state, and database: unchanged

Final stop condition: `STOP_FOR_NORTH_STAR_REVIEW`.
