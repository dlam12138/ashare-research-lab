# Work Record — M3 Stage 3C-A-R2 Digest Portability Repair

## Baseline and blocked event

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Canonical start HEAD: `8ad14e0981990f61969468631c18aea05d83a036`
- Repair branch: `repair/m3-stage3car2-digest-portability`
- Real development outcome read before repair: NO
- Blocked old recomputation: `2b02d5a82aad0eca940f5decbce0e837086ef700dfcc3dfcba4740e82c20c85a`
- Root cause: absolute checkout path in model payload and absolute outside-repo fallback in `source_hashes()`.

## Pre-fix portability reproduction

The same clean `8ad14e0` tree was evaluated from two worktrees:

- logical checkout A: `REDACTED_ROOT_A` — old model digest `2b02d5a…`;
- logical checkout B: `REDACTED_ROOT_B` — old model digest `a6a24674cac7e4b9a63de3900690a2553f973a74d621d2f3da6fcb2311ae807d`.

Both had upstream inventory SHA
`f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031` and old
pipeline digest `f667598…`. This established
`PRE_FIX_PORTABILITY_REPRODUCTION` without loading real data.

## Implementation and relock

- `a58508d`: freeze R2 portability contract and pre-outcome Goal.
- `99c64ae`: add repository-relative digest helper, fail-closed source hashing,
  digest probe, relocked digest report, and portability tests.
- `22b855e`: add the separate M3 Ubuntu/Windows identity workflow and exact
  cross-checkout evidence; restore the existing M2 workflow byte-for-byte.
- Documentation closeout was recorded after local validation; final CI
  evidence is recorded below.

New identities:

- upstream inventory SHA: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`;
- pipeline: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`;
- model: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`;
- algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`.

## Identity and validation evidence

- Actual different-root worktrees at `99c64ae`: exact payload and digest match;
  probe result `M3_STAGE3CAR2_DIGEST_IDENTITY_MATCH`.
- Focused R2 + Stage 3C-A/R: `60 passed, 1 skipped`.
- M3 Stage 3A–R4/CAR/R2 boundaries: `183 passed, 1 skipped`.
- Full suite: `2116 passed, 4 skipped, 2 warnings`.
- Ruff, compileall, and diff-check: passed.
- New CI workflow: `.github/workflows/m3-stage3car2-digest-identity.yml`;
  M3 R2 run `32553184789` succeeded on headSha
  `db86da9ae0781dd3681fdc7bb83c8fc25b3600e7` with Ubuntu/Windows
  clean-clone and identity-compare.
- Existing Stage 2G run `32553184678` also succeeded on the same headSha.

## Protected state and stop boundary

The original M2 dirty worktree, M2 restored tree, M2 tag, stash, default DB,
and `D:\量化分析-m3-stage3b` external real-data capsule were not modified.
Real target read, real `Crash_t`, regression, bootstrap, and holdout read all
remain NO. Stage 3C-B is not started.
