# M3 Integration Closeout — Conditional Closeout and PR Preparation

Status: `IN_PROGRESS`

## Integration-only boundary

This task does not create a new research stage. It changes only confirmed stale
README status wording and integration governance/test artifacts. No real data,
external capsule, research computation, model/result, holdout disposition, or
Stage 3A–3E frozen artifact is changed. M4, minute work, index contribution,
and merge are not authorized.

## Canonical Stage3E decision preserved

The committed Stage3E decision remains:

- decision: `M3_MILESTONE_CONDITIONAL_CLOSEOUT_ALLOWED`;
- milestone: `CONDITIONALLY_CLOSED`;
- daily mechanism: `M3_DAILY_MECHANISM_NOT_ESTABLISHED`;
- development primary: `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`;
- holdout primary: `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`;
- full evidence completion: `false`;
- recovery, minute, index, and M4 authorization flags: `false`.

The source of truth is
[m3_stage3e_milestone_closeout_decision_v1.json](../reports/m3_stage3e_milestone_closeout_decision_v1.json).

## README repair

The project-positioning status `M2 正在实现` was replaced with `M2 已条件关闭`.
The stale Stage 3D-A wording claiming a sealed holdout and separate Stage 3D-B
authorization was replaced with the current Stage 3D-B-R1/R2 coverage-gated
inconclusive holdout status and Stage 3E conditional closeout status. No
historical research fact was rewritten and no “mechanism disproven” inference
was added.

## Evidence and validation

The frozen baseline is recorded in
[m3_integration_frozen_baseline_manifest.json](../agent/record/2026-08-24_M3_integration_frozen_baseline_manifest.json).
It covers the Stage 3A–3E reports and acceptance, mechanism source tree,
workflow identities, and protected M2 scope. The final record must add exact
local/origin sync, final-tip CI run IDs and head SHAs, tag object and dereferenced
commit, PR number/URL/base/head, and protected M2 state.

Required local checks are the README/Stage3E focused tests, M3 boundary tests,
full pytest, Ruff, compileall, diff-check, Stage3E closeout validator, README
stale-string scan, and frozen-artifact regression.

## Final boundary

The annotated tag
`m3-mechanism-validation-conditional-closeout` may be created only after
exact final-tip CI is green and must point to the exact final feature HEAD. A
PR may be created from `feat/m3-mechanism-validation-mvp` to `main`, but
`merge = NOT_PERFORMED`. Final state: `PR_READY_FOR_SOL_REVIEW` and
`STOP_FOR_FINAL_MERGE_REVIEW`.
