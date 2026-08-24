# Goal — M3 Stage 3D-A Holdout Unseal Decision & Frozen OOS Execution Contract

Status: COMPLETED — STOP_FOR_NORTH_STAR_REVIEW

## Objective

Freeze the governance contract for a future, separately authorized, one-shot
Stage 3D-B out-of-sample primary execution without reading, downloading,
parsing, hashing, or otherwise accessing any 2023-01-01+ holdout data.

## Verified baseline

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD and origin: `e33373be513ef36f407bc5662caa6e9e2f2e5943`
- Local/origin synchronization: `0/0`
- Stage 3C-B primary: `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`
- Stage 3C-C robustness: `M3_REGISTERED_EXECUTABLE_DEVELOPMENT_ROBUSTNESS_COMPLETED`
- Development evidence ceiling: `2`; evidence level: `null`
- Holdout: `SEALED`; Stage 3D-B: `NOT_STARTED`

## Allowed scope

- Read committed contracts and development metadata only.
- Add the Stage 3D-A decision contract, frozen OOS execution contract, and
  machine-readable interpretation policy.
- Add an offline validator and synthetic-only boundary tests.
- Add factual acceptance, work-record, Goal, README, and independent CI evidence.

## Forbidden scope

- Any real holdout read, download, parse, hash, row count, outcome, or matrix.
- Any regression, bootstrap, gamma calculation, development re-analysis, or
  Stage 3C-B/C conclusion change.
- Any new model, threshold, proxy, control, robustness search, minute-level
  escalation, index-contribution execution, or causal/actor inference.
- Reset, force-push, merge, tag, PR, or operation on the original M2 dirty worktree.

## Required behavior

- Freeze holdout exactly as `2023-01-01..2026-08-13` and keep it `SEALED`.
- Allow only `ALLOW_ONE_FROZEN_OOS_PRIMARY_EXECUTION_AFTER_SEPARATE_STAGE3DB_AUTHORIZATION`.
- Freeze `FROZEN_PRIMARY_ONLY`, accepted execution count `1`, and identical-
  immutable-matrix A/B reproducibility rerun only.
- Freeze the Stage 3C-B identity anchors and the exact gamma/lower-CI decision rule.
- Encode A/B/C final dispositions fail-closed; holdout cannot reverse or rescue
  the development primary and cannot establish causality.

## Required validation

- Stage 3D-A focused synthetic-only tests.
- M3 boundary tests, full pytest, Ruff, compileall, and `git diff --check`.
- Offline validator readiness report and JSON parse validation.
- Protected-artifact SHA regression against starting HEAD.
- Existing M3 and protected Stage 2G CI workflows plus independent Stage 3D-A
  contract CI on clean Ubuntu/Windows clones and identity comparison.

## Acceptance criteria

- `holdout_read=false`, no network acquisition, holdout remains sealed.
- All canonical identities match the frozen Stage 3C-B/C anchors.
- Stage 3C-B primary and Stage 3C-C robustness conclusions are byte- and
  semantically unchanged.
- Stage 3D-B is eligible only after separate authorization and is not started.
- Final status is `M3_STAGE3DA_HOLDOUT_UNSEAL_DECISION_ACCEPTED` and work stops
  for North-Star review.

## Stop conditions

- Any identity, boundary, protected SHA, CI, determinism, or contract failure.
- Any requirement to access 2023-01-01+ data or to execute Stage 3D-B.
- Any proposed reversal, rescue, causal interpretation, or automatic minute-level escalation.

## Commit and push requirements

- Use no more than four logical commits where practical.
- Push normally to `feat/m3-mechanism-validation-mvp` after local gates pass.
- Do not merge, tag, reset, force-push, or begin Stage 3D-B.
