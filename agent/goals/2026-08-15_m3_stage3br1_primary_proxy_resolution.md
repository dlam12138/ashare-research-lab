# Goal Contract: M3 Stage 3B-R1 — Primary Proxy Contract Reconciliation & Reconstruction

Status: ACCEPTED — PRE-OUTCOME NORTH-STAR PROTOCOL AMENDMENT

## Verdict

- `M3_STAGE3BR1_PRE_OUTCOME_PROXY_AMENDMENT_ACCEPTED`
- Primary proxy v2 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`: CONSTRUCTED and trusted for the
  development period where the 0.99 coverage gate passes (2015-03-16 → 2022-12-30, 1,902 trading
  days); 68 gap rows (warm-up + Q1-2015 genuine mass suspensions) fail-closed; 11 delisted-within-window
  symbols a bounded documented Sina gap.
- `M3_EXACT_SSE_RECONSTRUCTION_DEFERRED_NON_BLOCKING`, `M3_HOLDOUT_REMAINS_SEALED`,
  `M3_STAGE3BR2_OIL_INDUSTRY_ACQUISITION_ALLOWED`, `M3_STAGE3C_NOT_YET_ALLOWED`,
  `STOP_FOR_NORTH_STAR_REVIEW`.

## Objective

Reconcile the M3 primary market proxy with the North Star's "exclude the target stock from the
market aggregate" semantics by formally superseding the fail-closed Stage 3B v1 divisor-exact
proxy with a reproducible, North-Star-aligned equal-weight ex-target Shanghai A-share proxy, and
reconstruct it from a content-addressed, PIT-capable acquisition without reading the sealed
holdout or executing any mechanism inference.

## Verified baseline

- Branch: `feat/m3-mechanism-validation-mvp`
- Task baseline: `df6242046d0871b81ac8ec2b8816e4229dccab16`
- Actual M3 branch HEAD: `557aa0e779ac24230ecc78fb0b0f84f3bc321bf1` (one governance-closeout
  commit ahead of the task baseline; work proceeds from the current tip)
- Working tree: isolated M3 worktree at `D:\量化分析-m3-stage3b`, clean
- Original M2 worktree: protected, on `feat/m2-value-assessment-mvp`, dirty, not used
- Protected stash: `stash@{0}` (Stage 1B.4 record edit), left untouched
- Default `data/research.duckdb`: absent in the isolated worktree
- Stage 3A: FROZEN, exact-byte SHA-256 unchanged
  - hypothesis: `1b5a042432a01d26ce3801a558322b6d0bc20627914ae6bb590aea0da1e7dc28`
  - data requirements: `261d692db3ac30bb7c09249203224d9ef7c4141a5259effb92913d412542b35f`
  - statistical protocol: `f8a5b505e36725082a382d5012fdd8e004613dca124ac5bbde41f1a5029eb83e`
- Stage 3B v1: CLOSED (fail-closed data-gap acceptance); immutable
  - primary proxy contract v1 SHA-256: `135fe2dbb50aaa203a9fc57648665d6f73359f2ca0662edba37e2d8cde05b4b8`
  - return/timing contract v1 SHA-256: `dd8c1350089cf76bc81221e1721d2515e72e76f037e57ad124c989d3432bf319`
  - source registry v1 SHA-256: `ce8f2a622c42d203369d2b2992945b5e2b948b612893c44344abd65939368e73`
  - data coverage v1 SHA-256: `983086f370c0ce5091dd6ba57326dfd3c5a9b9635b26e7fb669c55d26ae92ede`
  - development input manifest v1 SHA-256: `b564e3432e727d829f4769179b1cf2d8a19ae1dc5371c88a3c0fee34c20bfb79`
- Stage 3C: NOT ALLOWED
- Holdout 2023-01-01+: SEALED

## Allowed scope

- Add Stage 3B-R1 goal, work record, resolution, superseding contract v2, source registry,
  development manifest, data coverage, acceptance, and focused tests.
- Add `src/ashare_research/mechanism/` v2 equal-weight ex-target proxy construction and a
  resumable, content-addressed acquisition/normalization tool.
- Acquire only 2014-12 warm-up and 2015-2022 development data into an explicit external/tmp root;
  commit only contracts, logical paths, hashes, schemas, rows/dates/coverage, code, and tests.
- Reuse the immutable Stage 3B external capsule (`D:\m3_stage3b_external_20260814`) trade calendar
  and `601857.SH` qfq/unadjusted daily when raw SHA-256 match.
- Repair stale README statements that claim M3 has not started.
- Commit and normally push logical commits to the current feature branch.

## Forbidden scope

- Modify the three frozen Stage 3A JSON contracts or any Stage 3B v1 JSON contract.
- Read, acquire, parse, summarize, or analyze any outcome data dated 2023-01-01 or later.
- Execute Stage 3C, regression, conditional inference, p-values, confidence intervals, bootstrap,
  effect sizes, evidence grades, crash-day statistics, abnormal returns, or funding/intent claims.
- Runtime-fall back from Stage 3B v1; v1 remains failed/closed and is not replaced by code reuse.
- Compare candidate proxies by which produces a stronger PetroChina result.
- Pretend the equal-weight v2 proxy is an exact SSE Composite or official index series.
- Alter the frozen oil/industry contracts; only feasibility notes are permitted this stage.
- Add scipy/statsmodels, write the default DB, commit raw/large market data, create a PR, merge
  main, force-push, or alter protected M2 state, tags, branches, stash, artifacts, or databases.

## Required behavior

- Freeze v2 as a formally superseding pre-outcome contract authorized by North-Star review.
- Universe: Shanghai-listed A-share common equities, Main Board + STAR Market, physically excluding
  `601857.SH`, excluding B shares, CDR, ETFs/funds/bonds/indices and other non-common-equity
  instruments; ST/*ST not excluded merely because of risk-warning status.
- PIT membership limited to information known by t-1 close; no current-universe backfill; no future
  listing/delisting knowledge; a new listing enters only with a valid previous close; suspension
  carries the last valid close with zero daily return; a security leaves after its final valid
  trading observation under the frozen delisting rule; missing provider data never silently removes
  a constituent.
- Return is simple close-to-close; daily proxy is the arithmetic equal-weight mean of constituent
  returns from the t-1 eligible universe after physical exclusion of `601857.SH`.
- Freeze `minimum_daily_input_coverage = 0.99`; a date below the gate is
  `PROXY_ROW_INVALID_DATA_GAP`, never silently computed on the available subset.
- Exact SSE Composite ex-`601857` reconstruction remains optional/deferred and non-blocking for the
  M3 primary mechanism MVP; historical target index weight remains a separate contribution pipeline.
- Network acquisition is resumable and content-addressed; raw inputs go to an explicit external
  immutable cache; raw cache -> SHA manifest -> offline normalization A -> offline normalization B ->
  canonical byte/logical identity comparison -> proxy construction.

## Required reports

- `reports/m3_stage3br1_primary_proxy_resolution_v1.json`
- `reports/m3_stage3br1_primary_proxy_contract_v2.json`
- `reports/m3_stage3br1_source_registry_v1.json`
- `reports/m3_stage3br1_development_proxy_manifest_v1.json`
- `reports/m3_stage3br1_data_coverage_v1.json`

## Required tests

- Frozen Stage 3A and Stage 3B v1 SHA-256 unchanged.
- Explicit v2 supersession and no implicit v1 fallback.
- Target exclusion; allowed instrument classification; B/CDR/fund/bond/index rejection.
- t-1 membership; listing/delisting; suspension zero-return; missing-row fail closed.
- 99% coverage gate; 2023+ rejection.
- Raw SHA mismatch; offline A/B identity; restricted-output absence.

## Exact validation commands

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python -m pytest -q tests/test_m3_stage3br1_*.py
python -m pytest -q tests/test_m3_stage3a_mechanism_preflight.py tests/test_m3_stage3b_data_contracts.py
python -m pytest -q
ruff check src/ tests/
python -m compileall -q src tests
git diff --check
```

Additional gates: frozen Stage 3A + Stage 3B v1 SHA-256 recheck; default DB absence; protected M2
worktree/stash preservation; external raw cache manifest verification; offline A/B identity;
holdout and repository-pollution scan; local/origin synchronization.

## Acceptance criteria

Trusted completion: the v2 equal-weight proxy is frozen, reconstructed from a verified
content-addressed acquisition, passes the 99% coverage gate, is reproducible, and all deterministic
tests pass. If full acquisition cannot be completed, the required outcome is an honest fail-closed
data-gap packet with v2 frozen and the reconstruction pipeline built and tested; the proxy is then
reported NOT TRUSTED and Stage 3C remains prohibited. In both cases holdout stays sealed, frozen
Stage 3A/3B v1 stay byte-identical, protected state is unchanged, and evidence is committed/pushed.

## Stop conditions

- Stop for North-Star review after final-tip CI evidence; do not begin Stage 3C.
- Stop before any action that would change protected M2 state or degrade the v1/v2 contract.
- If acquisition is infeasible, stop the acquisition component and report gaps honestly.

## Commit and push requirements

- Use about three logical commits: contract/resolution; implementation; tests/acceptance.
- A documentation-only README/closure commit is permitted when needed.
- Push normally to `feat/m3-mechanism-validation-mvp`.
- No PR, merge, amend/force-push, or direct push to main.