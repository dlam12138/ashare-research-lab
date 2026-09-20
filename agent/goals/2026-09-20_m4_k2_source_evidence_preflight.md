# Goal: M4 K2 real-source evidence preflight

Date: 2026-09-20. Executor and Git operator: Codex. Independent analyst and reviewer: DSH.

## Objective and verified baseline

Perform a repository-only preflight for the next M4 K2 stage. Determine whether
existing tracked evidence is sufficient to nominate bounded candidates for the
real daily role sources, exchange calendar, security identity/membership,
publication/PIT timing and licensing evidence required by the accepted real
source design. Freeze a fail-closed decision and the smallest later task; do
not acquire data or implement a provider adapter.

- Worktree: `D:/量化分析-m4-k2-preflight`.
- Branch: `codex/m4-k2-source-preflight`.
- Verified base: local tracking and live `origin/main` at
  `bdcfbcef0a4d657fb8be00ca19b50e58efbd4c97` (PR #22 merge).
- Protected state: M2 HEAD
  `3679b1bac7a1634c6452784a4d8f6d139966f222`, stash
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed and forbidden scope

Allowed: read tracked repository contracts, registries, manifests and prior
acceptance evidence; add this Goal, one preflight decision document, one record
and one acceptance file; run Markdown/link/Git validation; commit, push and
open one documentation-only PR after review.

Forbidden: network/provider/API/browser access, credential use, downloads,
database open/query/write, real observations, holdout access, adapter/source
code, tests, dependencies, CI, configuration, frozen reports/contracts,
README, K2 implementation, statistics or hypothesis execution. Do not infer a
license, PIT timestamp, revision policy, calendar or membership history that
is not evidenced by tracked artifacts.

## Required behavior

- Map every required evidence class from
  `docs/m4_real_daily_source_contract_design_v1.md` to tracked candidates or an
  explicit gap: role source/version/raw bytes, calendar, security identity and
  membership, publication/availability timing, return semantics, transport
  bounds and license/redistribution.
- Distinguish reusable principles from M3-specific facts that cannot be
  promoted into a generic M4 source by assumption.
- For each candidate state `CANDIDATE`, `INSUFFICIENT_EVIDENCE`, or
  `OUT_OF_SCOPE`; cite exact tracked paths and missing proofs.
- The decision must not claim that a candidate is verified, selected or safe
  for real execution. If no candidate closes all mandatory evidence, verdict
  is fail-closed and the smallest next task must be a separately authorized,
  bounded provider-evidence acquisition design—not acquisition itself.
- DSH remains read-only and must not edit, commit, push or create a PR.

## Required validation

```powershell
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git worktree list --porcelain
git stash list
Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'
git -C 'D:/量化分析' rev-parse HEAD
```

All new Markdown must be strict UTF-8 with final newline, no trailing
whitespace or conflict markers, and resolvable relative links.

## Acceptance criteria

- Deliverable is documentation-only and based on exact post-PR22 main.
- Every K2 evidence class has a traceable candidate/gap disposition without
  promoting historical case data into generic proof.
- DSH independently challenges the mapping and final verdict.
- Protected state and remote synchronization are unchanged and reported.
- Final verdict is exactly `PASS`, `CHANGES_REQUIRED`, or `BLOCKED`.

## Stop conditions

Stop on main drift, protected-state mismatch, need for network/provider or
database access, unresolved ambiguity that would require inventing evidence,
or any request to implement K2 or consume real/holdout outcomes.

## Commit, push and next-stage requirements

Local commits, push to `codex/m4-k2-source-preflight`, and one PR to `main` are
authorized after validation. Direct push to main, force-push, merge, provider
access, K2 implementation and any real-data stage are not authorized. Final
evidence must report base/final SHAs, files, commands/results, DSH findings,
protected state, synchronization, deviations and residual risks.
