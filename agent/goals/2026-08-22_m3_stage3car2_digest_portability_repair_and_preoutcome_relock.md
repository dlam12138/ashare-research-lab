# M3 Stage 3C-A-R2 — Digest Portability Repair & Pre-Outcome Relock

Status: ACTIVE — PRE-OUTCOME DIGEST PORTABILITY REPAIR

## Objective

Repair the canonical Stage 3C-A digest identity algorithm so that identical
repository bytes produce identical pipeline and model digests across checkout
roots and Windows/Ubuntu clean clones. This is infrastructure-only and occurs
before any real development outcome is read.

## Verified baseline

- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Canonical base: `8ad14e0`
- Real development outcome read: NO
- Real `Crash_t`, regression, bootstrap, and holdout read: NO
- Old pipeline digest: `f667598001e8f63734547f7da281c41cf571c70667d784e35e57b6eddd4e781b`
- Old model digest: `28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11`
- Blocked recomputation under the non-portable algorithm: `2b02d5a82aad0eca940f5decbce0e837086ef700dfcc3dfcba4740e82c20c85a`
- Effective upstream inventory SHA: `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`

## Allowed scope

- Add the R2 digest portability contract, probe, acceptance, record, and tests.
- Modify `model_digest.py` only for repository-relative, fail-closed digest
  identity portability.
- Extend the existing CI identity envelope/compare path to include the new
  M3 digest identity fields.
- Update README with factual pre-outcome repair status.

## Forbidden scope

- Any real data read or external capsule access.
- Stage 3C-B, robustness, holdout, or result execution.
- Changes to Stage 3A/3B/3C-A research contracts or upstream inventory.
- Changes to statistical semantics, model core, thresholds, bootstrap, or
  evidence rules.
- Reset, force-push, merge, tag movement, stash changes, or M2 worktree edits.

## Required behavior

- Digest path identity is repository-relative POSIX only.
- Outside-repository and symlink-escaped paths fail closed.
- Pipeline and model payloads explicitly use
  `M3_REPOSITORY_RELATIVE_DIGEST_V2`.
- Identical bytes under different roots produce identical payloads and digests.
- Real development remains prohibited and holdout remains sealed.

## Required validation

- Pre-fix cross-worktree divergence reproduction.
- Focused R2 portability tests, existing Stage 3C-A/recovery tests, M3 boundary
  tests, and full suite.
- Ruff, compileall, and diff-check.
- Two clean checkout identity comparison and CI Windows/Ubuntu exact field
  comparison.
- Frozen contract and upstream inventory SHA verification.

## Acceptance criteria

- New repository-relative pipeline/model digests are stable across roots.
- New digest values are recorded without rewriting historical R3C-A-R evidence.
- CI compares upstream SHA, pipeline digest, model digest, and algorithm.
- No real development or holdout observation was read.

## Stop conditions

Stop for North-Star review if portability cannot be proven, if any research
semantic/core file must change, if canonical upstream bytes change, if remote
moves unexpectedly, or if any real outcome is read.

## Commit/push requirements

Use the isolated repair worktree and normal commits/push only after local
validation. Push to `feat/m3-mechanism-validation-mvp`; no PR, merge, tag, or
force-push. After final-tip CI, stop before Stage 3C-B.
