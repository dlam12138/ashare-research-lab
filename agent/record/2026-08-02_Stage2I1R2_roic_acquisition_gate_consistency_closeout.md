# Work record: M2 Stage 2I.1R2 ROIC acquisition gate consistency closeout

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `7e9c04d6377f519374140a112e5b198f220b6119`
- Task source: user-provided Stage 2I.1R2 contract
- Module: value assessment / ROIC methodology and engineering governance

## Objective

Make the ROIC methodology, formula dependency graph, concept registry,
readiness matrix and minimum FY2023/FY2024 official-fact acquisition plan one
executable contract. The acquisition gate may be allowed only when a
structured validator proves complete, correctly layered, non-duplicated
coverage.

## Scope

Versioned ROIC dependency/methodology/registry contracts, readiness and plan
validators, generated readiness/coverage artifacts, portability controls,
tests, documentation and acceptance evidence are in scope.

## Non-goals

Do not acquire, download, parse or enter new ROIC official facts; do not run a
ROIC shadow calculation; do not create a production ROIC Metric or Metric
Result; do not alter the current value profile; do not score; do not start Web,
target-price, recommendation, automatic-trading or market-mechanism work.

## Starting state

- Local and origin branch both point to the expected starting HEAD; ahead /
  behind is `0/0`; no intervening commit exists.
- One worktree exists. The only untracked path is the user-owned
  `agent/goals/`, which is protected and will not be staged or removed.
- Existing stash: `stash@{0}: protect pre-existing Stage 1B.4 record edit
  before Stage 1C`; it will remain unchanged.
- Default `data/research.duckdb` SHA-256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline: `354 Fact / 102 Metric Result / 16 definitions`.
- Latest pre-edit CI: GitHub Actions run `30750735015`, HEAD `7e9c04d`, with
  successful Ubuntu and Windows clean-clone jobs.
- Historical Stage 2I and Stage 2I.1R acceptance is retained. Stage 2I.1R2
  will supersede only the old acquisition-allowed decision.

## Known consistency defects recorded before implementation

1. Registry and minimum plan disagree on primary/secondary classification.
2. `lease_interest_expense` is a primary hard blocker but is absent from the
   plan.
3. `asset_disposal_gain_loss` and
   `other_non_operating_income_expense` are primary in the registry but placed
   in the secondary plan layer.
4. The inclusion relationship between `finance_cost_adjustment` and lease
   interest is not frozen, risking omission or double adjustment.
5. `non_operating_asset_boundary` is an unresolved methodology choice but
   readiness reports it as resolved/not-applicable.
6. The acquisition validator does not prove complete hard-blocker coverage.
7. The committed readiness report leaks a machine-local absolute path.
8. Therefore the current hand-written `Next-stage acquisition: ALLOWED` is
   not trusted.

## Implementation plan

1. Freeze a machine-readable primary formula dependency graph and a separate
   non-operating-asset methodology decision contract.
2. Migrate formal readiness to registry v2 and validate registry membership,
   derivations, decisions, signs and double-count exclusions against the graph.
3. Make methodology readiness state-driven, canonical and path-independent;
   regenerate FY2020-FY2025 reports and old-to-new differences.
4. Build the true minimum FY2023/FY2024 plan v3 and a structured coverage
   validator that is the sole authority for the acquisition gate.
5. Add independent consistency, portability and protection tests; run all
   required local, alternate-workdir, clean-clone and remote CI gates.
6. Update historical correction notes, acceptance and this record, then stop
   without performing acquisition or shadow work.

## Decision log

- Finance/lease composition uses scheme 1. The deterministic parent equals
  finance cost excluding lease interest plus lease interest; only the parent
  contributes to NOPAT once. Missing separation fails closed.
- Asset disposal is primary because CAS presents it inside operating profit.
  Other non-operating income/expense is secondary because it follows operating
  profit. The decision is statement-membership based, not value based.
- The non-operating-asset classification rule is resolved before acquisition.
  Its monetary result is a separate derivation and remains incomplete until
  canonical supporting components are ready.
- Secondary reconciliation gaps do not block primary feasibility. Only the
  structured v3 coverage validator can issue acquisition permission.

## Actual operations

- Read the two North-Star documents, governance files, latest/relevant work
  records, both predecessor acceptances and the specified ROIC contracts,
  code, reports and tests before implementation.
- Verified the expected starting branch/HEAD, remote, worktree, stash, DB hash
  and latest remote CI.
- Added the dependency graph, decision contract and registry v2 migration;
  updated methodology and input contracts.
- Corrected methodology readiness, canonicalized serialized logical paths and
  regenerated the 186-cell readiness report plus v2-to-R2 diff.
- Added the 11-item plan v3 and structured coverage generator. The validator
  reports 38 covered blocker/year cells and no uncovered, orphan, mislayered
  or duplicate contributions.
- Added independent negative tests for both finance/lease designs, missing
  components, sign/double-count drift, registry/plan alignment, methodology
  states, minimum batch, portability and production safeguards.

## Data and methodology

This task uses only the already committed canonical inventory and existing
references. No network fact collection or fact mutation is permitted.

## Verification

- Stage 2I/2I.1R/2I.1R2 targeted: `29 passed`.
- Full suite: `996 passed, 2 warnings`; warnings are the pre-existing pandas
  date-format warnings in `tests/test_quality.py`.
- Fact Identity/PIT/restatement group: `106 passed`.
- ROE/ROA/financial-safety group: `130 passed`; the protected vertical-slice
  assertions remain 354 Facts / 102 Metric Results / 16 definitions.
- Stage 2G snapshot/artifact group: `32 passed`.
- Stage 2H/2H.1R protected group: `15 passed`.
- Ruff, compileall/import and `git diff --check`: passed.
- Readiness A/B, coverage A/B and alternate-working-directory runs: identical.
  Readiness digest:
  `0f0bf2d53202419d871bc086c23a45513d658907e4dc3a30da755069cc0adc9d`;
  plan digest:
  `aedaebcaa5b85fd4bbfa39f77c2ac09a55c548cf2bb099cdc008271aa3340215`.
- New/modified formal artifact path scan: 15 files, zero leaks. Secret and
  DB/PDF/cache/raw-response changed-file scans: zero findings.
- Inventory remains 354 Facts / 122 eligible / 11 Contexts with snapshot digest
  `cb675690dd619d01534872c2bc98e9e0f6da80ff4f2ff586978d464c70fece57`
  and file SHA-256
  `4deb1a8ff00bb0270bf4c1cddf1d8b08b05b748ffb1f99b5a1b5ddede1b1e041`.
- Default DB, stash and untracked goals remain unchanged. Commit-state clean
  clone and final remote Ubuntu/Windows CI are pending.

## Result

Implementation and local gates pass. Final acceptance and acquisition remain
blocked until commit-state clean clone and final Ubuntu/Windows CI succeed.

## Open issues

Stage 2F retains nine exchange-evidence gaps and Stage 2H retains its two
bounded-search missing-evidence slots. These pre-existing evidence gaps were
not changed or hidden by this contract closeout.

## Final files and Git state

Scoped commits so far:

- `d0817a3 refactor: freeze ROIC formula dependency graph`
- `a6dd79f fix: separate ROIC methodology decisions from fact roles`
- `136921f test: enforce complete ROIC acquisition gate coverage`

Final documentation/record commits, push and CI are pending. `agent/goals/`
remains untracked and protected.
