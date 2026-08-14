# Goal Contract: M3 Stage 3B — Data Acquisition and Normalization

Status: ACTIVE — local fail-closed acceptance complete; remote CI pending

## Objective

Complete Tier-1 development-period acquisition, point-in-time-safe normalization,
construction of the primary `SH_MARKET_EX_601857` proxy, and deterministic offline
reproducibility acceptance without executing mechanism inference.

## Verified baseline

- Branch: `feat/m3-mechanism-validation-mvp`
- Local HEAD: `ae2225f45c984f90b00ca28b3c35b421fe030359`
- Origin branch HEAD: `ae2225f45c984f90b00ca28b3c35b421fe030359`
- Starting worktree: clean, isolated at `D:\量化分析-m3-stage3b`
- Original M2 worktree: protected, dirty, and not used for implementation
- Existing stash: one protected entry in the shared repository
- Default `data/research.duckdb`: absent in the isolated worktree
- Stage 3A acceptance: PASS; Stage 3B authorized
- Frozen Stage 3A SHA-256:
  - hypothesis contract: `1B5A042432A01D26CE3801A558322B6D0BC20627914AE6BB590AEA0DA1E7DC28`
  - data requirements: `261D692DB3AC30BB7C09249203224D9EF7C4141A5259EFFB92913D412542B35F`
  - statistical protocol: `F8A5B505E36725082A382D5012FDD8E004613DCA124AC5BBDE41F1A5029EB83E`

## Allowed scope

- Add Stage 3B semantic addenda, source registry, development manifest, and coverage report.
- Add `src/ashare_research/mechanism/` data-contract, normalization, market-proxy,
  source-manifest, and capability-specific provider code required by Stage 3B.
- Acquire only 2014-12 warm-up and 2015-2022 development data into an explicit
  external/tmp root; retain immutable raw inputs and hashes outside Git.
- Add deterministic fixtures and approximately 15-25 focused tests.
- Factually update the stale M3 status lines in README.
- Add acceptance and work-record evidence.
- Commit and normally push logical Stage 3B commits to the current feature branch.

## Forbidden scope

- Modify the three frozen Stage 3A JSON contracts.
- Read, acquire, parse, summarize, or analyze outcome data dated 2023-01-01 or later.
- Execute Stage 3C, regression, conditional inference, p-values, confidence intervals,
  bootstrap estimates, effect sizes, evidence grades, crash-day statistics, or intent claims.
- Substitute the SSE Composite, equal-weight proxy, current constituents, survivorship-only
  history, or future constituent information for the primary proxy.
- Add scipy/statsmodels, modify M1/M2 data abstractions unnecessarily, write the default DB,
  commit raw/large market data, create a PR, merge main, force-push, or alter protected M2
  state, tags, branches, stash, artifacts, or local database.

## Required behavior

- Freeze historical methodology regimes actually applicable during 2015-2022.
- Primary proxy must physically exclude `601857.SH`, use PIT-safe Shanghai eligibility and
  applicable share/price inputs, and fail closed when exact inputs are insufficient.
- Distinguish adjusted target analysis return from unadjusted target index-contribution return.
- Use simple price return for the market proxy.
- Freeze a concrete oil benchmark and align the latest observation available before 15:00 CST;
  a same-day overseas close is prohibited.
- Freeze a concrete petrochemical industry index, publisher, return type, timezone, and source.
- Freeze the exact bootstrap block-length formula and positive-evidence decision semantics,
  without running statistics.
- Network-acquire once, lock immutable raw SHA-256, normalize offline twice, and compare
  canonical logical digests.
- Tier 2/3 sources remain `NOT_ACQUIRED_STAGE3B`.
- Reports may contain only schema, source, rows, dates, gaps, duplicates, coverage, hashes,
  normalization, and alignment status; restricted research-output keys must be absent.

## Required tests

- Stage 3A hashes unchanged; Stage 3B contract schema valid.
- Target exclusion and rejection of SSE Composite/equal-weight fallbacks.
- Rejection of future constituent leakage and survivorship-only universes.
- Duplicate/order/schema validation and fail-closed Tier-1 handling.
- Oil same-day future close rejection.
- Warm-up exclusion and rejection of all 2023+ development rows.
- Raw SHA mismatch rejection.
- Offline A/B canonical identity.
- Restricted research-output fields absent.

## Exact validation commands

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python -m pytest -q tests/test_m3_stage3b_*.py
python -m pytest -q
ruff check src/ tests/
python -m compileall -q src tests
git diff --check
```

Additional gates:

- Stage 3A SHA-256 recheck.
- Default DB absence/hash recheck.
- Original M2 worktree and stash preservation check.
- External raw cache manifest SHA verification.
- Offline normalization A/B logical identity check.
- Holdout and repository-pollution scans.
- Local/origin synchronization and remote Windows/Ubuntu/identity CI.

## Acceptance criteria

Trusted completion requires all Tier-1 inputs to be credible and the primary proxy to be
PIT-safe and reproducible. If strict historical universe/share inputs cannot be obtained,
the required accepted outcome is a fail-closed data-gap packet; Stage 3C remains prohibited.
In either case, holdout remains sealed, Stage 3A remains byte-identical, protected state is
unchanged, deterministic tests pass, and evidence is committed and pushed.

## Stop conditions

- Hard stop with data-gap evidence if strict PIT inputs for the primary proxy cannot be obtained.
- Stop for North-Star review after final-tip CI evidence; do not begin Stage 3C.
- Stop before any action that would require changing protected M2 state or weakening the primary
  proxy definition.

## Commit and push requirements

- Use about three logical commits: semantic contracts; data implementation; tests/acceptance.
- A fourth documentation-only CI evidence commit is permitted when needed.
- Push normally to `feat/m3-mechanism-validation-mvp`.
- No PR, merge, amend/force-push, or direct push to main.
