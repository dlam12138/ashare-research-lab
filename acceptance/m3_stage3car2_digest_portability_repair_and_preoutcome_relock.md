# M3 Stage 3C-A-R2 Digest Portability Repair & Pre-Outcome Relock

Status: PRE-OUTCOME RELock ACCEPTED LOCALLY — FINAL CI PENDING

## Scope and boundary

Stage 3C-A-R2 repaired digest identity infrastructure only. No real target,
market, oil, industry, external capsule, development outcome, holdout row,
`Crash_t`, regression, or bootstrap was read or executed.

Research semantics remain unchanged: adjusted close-to-close simple return,
the frozen `-0.01` crash threshold, frozen design matrix and OLS estimator,
`gamma` as the primary parameter, and the registered 5,000-replication
PCG64 moving-block bootstrap remain locked in the existing Stage 3C-A
contracts.

## Root cause and relock

The old model payload included the checkout-specific absolute
`upstream_inventory_path`. The old `source_hashes()` also fell back to an
absolute path for outside-repository inputs. Both behaviors were replaced by
`M3_REPOSITORY_RELATIVE_DIGEST_V2`: resolved repository-relative POSIX keys,
fail-closed outside-repository handling, logical-path ordering, and an
explicit algorithm identifier in both digest payloads.

| Identity | Value | Status |
| --- | --- | --- |
| Effective upstream inventory | `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031` | unchanged |
| Historical pipeline digest | `f667598001e8f63734547f7da281c41cf571c70667d784e35e57b6eddd4e781b` | superseded by pre-outcome repair |
| Historical model digest | `28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11` | superseded non-portable lock |
| Blocked recomputation | `2b02d5a82aad0eca940f5decbce0e837086ef700dfcc3dfcba4740e82c20c85a` | non-canonical old algorithm |
| New pipeline digest | `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b` | relocked |
| New model digest | `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d` | relocked |
| Digest algorithm | `M3_REPOSITORY_RELATIVE_DIGEST_V2` | locked |

The required contract and effective upstream inventory bytes remain unchanged.

## Identity evidence

Two clean worktrees at commit `99c64aec8ddac404f5be161558852aa855c2353d`,
under different absolute roots, produced exact-equal payloads and exact-equal:

- upstream inventory SHA;
- pipeline digest;
- model digest;
- digest algorithm;
- absolute-path leakage flag (`false`).

Evidence is recorded in
`reports/m3_stage3car2_cross_checkout_identity_v1.json`. The new CI workflow
`.github/workflows/m3-stage3car2-digest-identity.yml` creates Ubuntu and
Windows clean-clone envelopes and an `identity-compare` job that compares all
four identity fields plus both payloads. Final remote CI is pending this push.

## Validation

- R2 focused plus Stage 3C-A and recovery tests: `60 passed, 1 skipped`.
- M3 Stage 3A–R4/CAR/R2 boundary set: `183 passed, 1 skipped`.
- Full suite: `2116 passed, 4 skipped, 2 warnings`.
- Ruff: passed.
- Compileall: passed.
- `git diff --check`: passed.
- Cross-checkout probe: `M3_STAGE3CAR2_DIGEST_IDENTITY_MATCH`.

## Governance state

- Stage 3C-A v2 contracts: unchanged.
- Effective upstream inventory: unchanged.
- M2 worktree, restored M2 tree, tag, stash, default database, and external
  M3 data capsule: protected and untouched.
- Stage 3C-B: not started and not authorized by this acceptance.
- Real development: not read.
- Holdout: sealed and not read.

After final Ubuntu/Windows/identity-compare CI is green, this task stops for
North-Star review. Stage 3C-B requires separate authorization and must use the
new relocked digests.
