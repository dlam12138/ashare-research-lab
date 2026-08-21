# M3 Stage 3C-A-R — Canonical Recovery and M2 Branch Repair

## Objective

Recover the misplaced Stage 3C-A synthetic-only implementation onto canonical
M3 `feat/m3-mechanism-validation-mvp` at `987caffe`, rebind the model to the
actual effective Stage 3A/R1/R2/R4 contract bytes, rebuild fail-closed pipeline
and model digests, pass canonical M3 synthetic/boundary/full/CI validation, and
only then revert the four misplaced commits from the M2 branch.

## Verified baseline

- Canonical M3 branch: `feat/m3-mechanism-validation-mvp`
- Canonical base: `987caffe5b75fa3b0de58d0add43051cc9a55d17`
- Canonical recovery worktree: `D:\量化分析-m3-stage3ca-recovery`
- Recovery branch: `repair/m3-stage3ca-canonical-recovery`
- Remote canonical M3 was verified at the same base, clean, ahead/behind `0/0`.
- Misplaced M2 branch: `feat/m2-value-assessment-mvp` @ `3679b1b`; incident chain
  is `724d6a4 -> 0bc0b2e -> f5ae24f -> 3679b1b`.
- Existing M2 dirty worktree, untracked files, stash, database, and existing
  M3 worktree `D:\量化分析-m3-stage3b` are protected and out of scope.

## Allowed scope

- Recovery-only changes in the new M3 worktree: Stage 3C-A v2 contracts,
  effective-upstream inventory, analysis modules/CLI/tests, dependency,
  README, recovery acceptance/record, and recovery commits.
- File-by-file reuse and correction of the misplaced implementation as a
  candidate; no cherry-pick.
- After canonical M3 local/final-tip CI passes, a separate isolated M2 worktree
  may receive the four inverse `git revert --no-commit` operations and one
  revert commit, followed by normal pushes.

## Forbidden scope

- Reading or computing from real 601857 development rows, real aligned 1902-row
  research matrices, real crash dates/counts, coefficients, p-values, CIs,
  abnormal returns, external market/oil/industry raw/cache, or holdout data.
- New data acquisition, proxy/oil/industry redesign, Stage 3C-B execution,
  holdout unseal, cherry-picking the misplaced commits, reset, force-push,
  stash pop, cleanup of the original M2 worktree, PR, merge, or tag movement.
- Replacing canonical Stage 3B package exports or data-preparation modules.

## Required behavior

- Recreate all Stage 3C-A contracts as v2 with recovery provenance and actual
  canonical upstream path/contract_id/version/SHA-256/effective status.
- Fail closed on missing, mismatched, wrong-id, wrong-version, or superseded
  effective upstream bindings; never fall back to declared identity strings.
- Preserve the frozen method core: adjusted close-to-close simple return,
  exact crash threshold, fixed design order, explicit statsmodels OLS,
  control-only abnormal return, PCG64 MBB 5000/seed 20260813, evidence cap 3,
  and synthetic-only execution gate.

## Validation

- Canonical Stage 3A, 3B, 3B-R1, 3B-R2, 3B-R3, 3B-R4 boundary tests.
- New Stage 3C-A-R recovery tests and focused synthetic tests.
- Full canonical M3 suite, Ruff, compileall, diff-check, positive/null/negative/
  extreme synthetic smoke, and final-tip CI evidence where available.
- After M3 success only: isolated M2 revert worktree, tree identity against
  `241c180`, M2 regressions, final-tip CI, and normal push.

## Stop conditions

Stop before M2 revert if any canonical upstream binding, integration, local
validation, or M3 CI check fails. Stop after both branch recoveries and CI pass;
do not start Stage 3C-B.

## Acceptance

Final success tokens are the recovery acceptance tokens from the user task,
including `M3_STAGE3CAR_CANONICAL_RECOVERY_ACCEPTED`,
`M2_TREE_RESTORED_TO_241C180_CONTENT_IDENTITY`,
`M3_STAGE3CB_NOT_STARTED`, and `STOP_FOR_NORTH_STAR_REVIEW`.

## Commit/push requirements

Use four focused canonical M3 commits and normal fast-forward push to the
canonical feature branch. After M3 CI passes, use one auditable M2 revert
commit and normal fast-forward push. Never force-push.
