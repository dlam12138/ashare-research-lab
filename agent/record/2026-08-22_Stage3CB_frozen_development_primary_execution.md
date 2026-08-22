# Work Record — M3 Stage 3C-B Frozen Development Primary Execution

Status: ACTIVE — PRE-EXECUTION LOCK

## Basic information

- Date: 2026-08-22
- Agent: Codex
- Branch: `feat/m3-mechanism-validation-mvp`
- Canonical starting HEAD: `ef1d1fab4b93ed680004430d72e49c27cb5e874e`
- Task source: user-authorized M3 Stage 3C-B execution contract
- Module: mechanism validation / frozen development primary execution

## Objective

Execute exactly one frozen Stage 3C-B development primary specification after
pre-execution identity, adapter, and cross-platform CI gates pass. Preserve the
Stage 3C-A model and all frozen upstream contracts. Stop after the primary
decision; do not run registered robustness or read holdout data.

## Scope

Allowed: Stage3C-B goal and execution contracts, immutable real-input locator
and matrix materializer, Stage3C-B CLI, focused pre-execution tests, committed
analysis-input manifest, one primary result, acceptance, work record, and factual
README status updates.

Forbidden: changes to Stage3C-A model/core or frozen reports, network
acquisition, disk-wide scans, alternative specifications, robustness,
holdout, outcome-driven filtering, and any post-outcome implementation change.

## Verified starting state

- Canonical worktree `D:\\量化分析-m3-stage3b` was clean after fast-forwarding from
  `8ad14e0` to `ef1d1fa`.
- `HEAD == origin/feat/m3-mechanism-validation-mvp == ef1d1fa`; no unknown remote
  commits were present after `git fetch origin --prune`.
- M2 worktree remains dirty and protected at `3679b1b`; its tag, stash, and
  `data/research.duckdb` are preserved.
- Relocked identities are expected to be:
  - upstream `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`;
  - pipeline `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`;
  - model `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`;
  - algorithm `M3_REPOSITORY_RELATIVE_DIGEST_V2`.
- Before pre-execution CI passes: real target outcome, real Crash, regression,
  bootstrap, and holdout reads are `NO`.

## Implementation plan

1. Verify the identity gate and inspect existing Stage3B/R1/R4 input APIs and
   committed manifests without reading real target outcome bytes.
2. Add Stage3C-B authorization/schema contracts and an adapter digest contract.
3. Add synthetic-only adapter/CLI tests covering all pre-execution gates.
4. Commit and push the pre-execution lock in logical commits; wait for exact
   Ubuntu, Windows, and identity-compare CI to pass.
5. Reconfirm the point-of-no-return, then perform one hash-first, development-
   only real execution and deterministic same-input A/B rerun.
6. Add only result/acceptance/record/factual README evidence after outcome read,
   run final validation, and stop for North-Star review.

## Data and method lock

- Target: `target_daily_qfq`, adjusted close-to-close simple return.
- Development: `2015-03-16` through `2022-12-30`; holdout starts `2023-01-01`.
- Market: `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`.
- Oil: R4-aligned `DCOILBRENTEU` / `oil_return`; no re-alignment.
- Industry: CNI `399439`; no alternative proxy.
- Model: frozen `-1%` Crash, OLS design, 5,000-rep PCG64 moving-block
  bootstrap, seed `20260813`, percentile 95% CI, primary parameter `gamma`.

## Actual operations

- Read the pasted Stage3C-B contract, North-Star documents, CLAUDE.md,
  shared AGENTS.md, agent/agent.md, record README, R2 acceptance, recovery
  acceptance, recent records, and required frozen report inventory.
- Fast-forwarded the existing clean canonical M3 worktree to `ef1d1fa`.
- Created this record before modifying implementation files.

## Validation and result

Pending. This section will contain only commands actually executed and their
observed results.

## Final state

Pending. Stage 3C-C, robustness, holdout, and any further research execution
remain prohibited after this task.
