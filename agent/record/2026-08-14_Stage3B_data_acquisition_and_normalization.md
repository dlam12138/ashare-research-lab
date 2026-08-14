# Work Record: M3 Stage 3B — Data Acquisition and Normalization

Status: in_progress

## Basic information

- Date: 2026-08-14
- Agent: Codex
- Branch: `feat/m3-mechanism-validation-mvp`
- Starting commit: `ae2225f45c984f90b00ca28b3c35b421fe030359`
- Source: user-authorized M3 Stage 3B execution instruction
- Module: mechanism validation / data foundation
- Goal contract: `agent/goals/2026-08-14_m3_stage3b_data_acquisition_and_normalization.md`

## Objective

Acquire and normalize Tier-1 development inputs, construct the PIT-safe
`SH_MARKET_EX_601857` primary proxy if strict inputs are available, and produce deterministic
offline acceptance without reading the sealed holdout or executing mechanism statistics.

## Scope

Stage 3B semantic addenda, source registry, capability-specific acquisition/normalization,
market-proxy construction, immutable external raw manifest, development coverage metadata,
focused tests, README status correction, acceptance evidence, commits, push, and CI closeout.

## Non-goals

Stage 3C; real mechanism inference; holdout access; regression/statistical results; Tier 2/3
acquisition; default DB writes; large raw-data commits; M1/M2 refactors; PR or merge.

## Starting state

- The user-facing workspace was actually on protected dirty M2 branch
  `feat/m2-value-assessment-mvp` at `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d`.
- A separate worktree `D:\量化分析-m3-stage3b` was created for the existing M3 branch.
- M3 local and origin both resolve to Stage 3A final commit `ae2225f45...`; isolated worktree clean.
- One pre-existing stash is present and protected.
- The isolated worktree has no `data/research.duckdb`.
- Stage 3A three-contract SHA-256 values were recorded in the Goal contract.
- README has two stale statements saying M3 has not started.
- Existing `BaseProvider` covers stock basics, trade calendars, stock daily, and index daily;
  it does not provide historical PIT universe/share, oil, or industry capabilities.

## Files read before implementation

- `AGENTS.md`, `CLAUDE.md`, `agent/agent.md`, `agent/record/README.md`
- Three recent work records, including the Stage 3A record
- Both project North-Star documents
- Stage 3A acceptance and all three frozen core contracts
- Existing provider base interface and relevant README status lines

## Risks identified

- Strict historical Shanghai eligibility/share inputs may not be freely obtainable; the required
  response is fail-closed evidence, not a convenient substitute.
- The SSE Composite methodology changed on 2020-07-22; current rules cannot be backfilled.
- Overseas daily closes are not observable by the same A-share close and require explicit lagging.
- Editable-install path leakage previously affected full-suite tests; validation will bind
  `PYTHONPATH` to this isolated worktree.
- The current calendar date is inside the sealed holdout; all acquisition bounds require explicit
  validation before any network request.

## Implementation plan

1. Establish Goal contract and this work record.
2. Research official methodology regimes and freeze semantic/source contracts.
3. Implement scoped acquisition, validation, normalization, proxy, and manifest capabilities.
4. Acquire only warm-up/development inputs into external storage and run offline A/B normalization.
5. Add focused tests and acceptance evidence; update README factually.
6. Run all local gates, commit/push, wait for remote CI, and independently review final evidence.

## Decision log

- Use an isolated M3 worktree to preserve the original dirty M2 checkout exactly.
- Treat absence of strict historical PIT inputs as an allowed fail-closed Stage 3B outcome, never
  authorization to degrade the primary proxy.
- Treat data-quality/coverage metadata as permitted and all return relationship or conditional
  statistics as prohibited.

## Actual operations

1. Read the attached execution instruction.
2. Verified real branch, HEAD, remotes, stash, worktrees, and relevant files.
3. Verified M3 local/origin identity and created the isolated M3 worktree.
4. Read governance, recent records, North Stars, Stage 3A acceptance/contracts, provider interface,
   and README status drift.
5. Recorded frozen Stage 3A hashes and confirmed the default DB is absent in this worktree.
6. Created the Goal contract and this work record before implementation changes.
7. Reviewed official SSE methodology evidence. The applicable regimes are the pre-2020-07-22
   rule (new listings enter on the eleventh trading day; price times issued shares; divisor
   maintenance; risk-warning shares were not excluded) and the rule effective 2020-07-22
   (risk-warning exclusion, one-year/three-month new-listing delay, STAR/CDR eligibility).
8. Inspected installed Akshare 1.18.79 and Baostock 00.9.30 capabilities. Baostock exposes dated
   all-stock snapshots but no issued-share history. Akshare exposes CNINFO company share-change
   and Eastmoney share-structure histories; both require full coverage and share-class audits.
9. Reviewed official EIA/FRED Brent metadata and candidate Shenwan industry-index regimes.
10. Added the three Stage 3B semantic/source contracts and corrected only the stale README status.

## Data and methodology notes

No network acquisition or real market-data read has occurred yet. No holdout data has been read.
No statistic or mechanism result has been computed.

The primary proxy contract explicitly retains the historical SSE methodology break. Oil is frozen
to EIA Europe Brent Spot Price FOB but fails closed unless historical release/vintage timing proves
the observation was visible before the A-share close. The industry control explicitly records the
SW 2014 `801016` to SW 2021 `801960` taxonomy transition instead of silently changing proxies.

## Validation

- Stage 3B JSON parse: PASS for all three semantic/source contracts.
- Frozen Stage 3A SHA-256 recheck: PASS, all three hashes unchanged.
- `git diff --check`: PASS after semantic-contract changes.

## Result

In progress.

## Outstanding issues

- Official methodology and source feasibility investigation pending.
- Tier-1 acquisition and proxy trust decision pending.

## Final file changes

Pending.

## Final Git state

Pending.
