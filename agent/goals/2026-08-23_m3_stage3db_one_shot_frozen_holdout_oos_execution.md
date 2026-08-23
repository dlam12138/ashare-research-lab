# Goal — M3 Stage 3D-B One-Shot Frozen Holdout OOS Execution

Status: ACTIVE_PRE_UNSEAL_LOCK

## Objective

Execute the one and only separately authorized Stage 3D-B frozen primary OOS
analysis for the exact holdout `2023-01-01..2026-08-13`, with a `2022-12-01`
warm-up envelope, immutable inputs, deterministic A/B reproduction, and the
Stage 3D-A interpretation policy. Stop immediately after the aggregate result
and governance evidence are committed.

## Pre-unseal baseline

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Canonical base: `25424aa767e90a098ba11223191fb9e731e1ff25`
- Execution scope: `FROZEN_PRIMARY_ONLY`
- Accepted execution maximum: `1`
- Holdout start/end: `2023-01-01..2026-08-13`
- Warm-up start: `2022-12-01`
- Development primary reversal: `false`
- New model/threshold/proxy/controls/robustness search: prohibited
- Real holdout read: `PROHIBITED_UNTIL_PRE_UNSEAL_CI_PASS`

## Frozen identity

- Upstream: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
- Development manifest: `7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2`
- Stage 3C-C robustness: `8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527`

## Pre-unseal allowed scope

- Add independent Stage 3D-B authorization/schema and OOS acquisition/input/
  execution adapters.
- Prove source identity, bounded requests, date boundaries, old/new semantic
  equivalence on synthetic/pre-2023 fixtures, and adapter digest identity.
- Run synthetic-only tests and pre-unseal CI.

## Post-unseal restrictions

Once `HOLDOUT_UNSEAL_BOUNDARY_REACHED` occurs, computation code, contracts,
schemas, and semantic tests are immutable. Only the real input manifest,
aggregate result, acceptance, work record, and factual README status may be
written. No robustness exploration, alternative source, or second execution
is permitted.

## Stop conditions

Any identity, semantic-equivalence, bounded-response, coverage, estimability,
determinism, or CI failure is fail-closed. In every result case, stop for
North-Star review and do not begin minute-level, index-contribution, or new
development research.
