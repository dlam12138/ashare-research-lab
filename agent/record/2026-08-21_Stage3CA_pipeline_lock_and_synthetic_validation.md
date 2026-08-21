# M3 Stage 3C-A work record

**Final status: PASS — CI CONFIRMED / STOP_FOR_NORTH_STAR_REVIEW**

## Scope

Locked the mechanism-analysis pipeline before any real PetroChina mechanism
result is viewed. The implementation is synthetic-only and preserves the
holdout seal.

## Baseline

- Branch: `feat/m2-value-assessment-mvp`
- Base HEAD: `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`
- Remote observed synchronized at the same tip before implementation.
- The checked-out baseline contained no M3 Stage 3A/3C implementation and no
  R4 readiness work record to edit. The final state is recorded here rather
  than fabricating an upstream R4 artifact.

## Completed

- Frozen four machine-readable Stage 3C-A contracts.
- Added the isolated mechanism analysis package and synthetic CLI.
- Added statsmodels OLS with explicit constant and `missing="raise"`.
- Added control-only abnormal return semantics, fixed crash rule, PCG64 MBB,
  descriptive/conditional layers, extreme/year/threshold robustness, BH-FDR,
  evidence level cap, execution gate, and separate digests.
- Added 35 focused tests and synthetic positive/null/negative/extreme fixtures.
- Updated README status and added the Stage 3C-A acceptance file.

## Prohibited data check

No R1/R4 external raw file, real 601857 outcome row, real crash date/count,
real regression matrix, or holdout row was read. Digest upstream references are
identity hashes only because those source artifacts were absent from the
verified baseline.

## Stop condition

Do not run real development or holdout analysis. Proceed only after explicit
North-Star review and a separately authorized Stage 3C-B task.
