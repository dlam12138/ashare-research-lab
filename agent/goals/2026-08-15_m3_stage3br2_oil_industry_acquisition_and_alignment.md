# Goal Contract: M3 Stage 3B-R2 — Oil & Petrochemical Industry Acquisition, PIT Alignment & Tier-1 Closeout

Status: IN_PROGRESS — PRE_OUTCOME_TIER1_DATA_CLOSEOUT

## Frozen stage envelope

- Stage: `M3_STAGE3BR2`
- Type: `PRE_OUTCOME_TIER1_DATA_CLOSEOUT`
- Stage 3C execution: `NOT AUTHORIZED`
- Holdout: `SEALED`
- Development: `<= 2022-12-31` only
- Stage 3B-R1 final-tip CI must PASS before Stage 3B-R2 work begins.

## Gate

Stage 3B-R1 final tip `b7c8bec` full SHA `b7c8becc69fc1e7647fa23b7444cbbbeaf8f0364`.
GitHub Actions run `31871858528`: status `completed`, conclusion `success`; Windows clean-clone =
success, Ubuntu clean-clone = success, identity-compare = success. **GATE PASS.**

## Objective

Complete the two remaining Tier-1 inputs (`oil`, `petrochemical_industry`) required before Stage 3C,
and establish a development-period PIT-safe alignment consistent with the already-trusted
`SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` market proxy. This stage answers only data-readiness
questions: `market_ex_target TRUSTED?`, `oil TRUSTED?`, `petrochemical TRUSTED?`,
`joint Tier-1 dates READY?`. It does NOT answer any PetroChina mechanism/outcome question.

## The oil timing supersession (pre-outcome)

Stage 3B v1 `return_and_timing_contract_v1.json` demanded a per-observation publication/release
timestamp proven earlier than the 15:00 CST A-share close (`timestamp_policy =
OBSERVATION_DATE_IS_NOT_AVAILABLE_AT_RELEASE_OR_VINTAGE_TIMESTAMP_REQUIRED`,
`unproven_release_timestamp_action = FAIL_CLOSED`). North-Star review authorized a
`FORMAL_PRE_OUTCOME_TIMING_SUPERSESSION`: that requirement conflated (1) the underlying Brent
market observation time with (2) a later data-distributor publication time. For a daily
explanatory study the only real hazard is using Brent market changes that occurred after the A-share
close on day t to explain A-share day t. The v1 contract is frozen byte-identical; the correction is
expressed only through new addendum artifacts `m3_stage3br2_oil_timing_resolution_v1.json` and
`m3_stage3br2_oil_contract_v2.json`.

## Baseline

- Branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `b7c8bec` (full `b7c8becc69fc1e7647fa23b7444cbbbeaf8f0364`)
- Working tree: isolated M3 worktree `D:\量化分析-m3-stage3b`, clean
- Original M2 worktree: protected, `feat/m2-value-assessment-mvp` at `241c180`, dirty, unused
- Protected stash: `stash@{0}` (Stage 1B.4 record edit), untouched
- Default `data/research.duckdb`: absent in the isolated worktree
- Stage 3A frozen contracts: SHA-256 verified unchanged (see `contracts.py`)
- Stage 3B v1 frozen contracts: SHA-256 verified unchanged (see `contracts.py`)
- Stage 3B-R1 frozen reports/contracts: immutable, not modified
- Market proxy v2 `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`: TRUSTED for development where the 0.99
  gate passes (2015-03-16 → 2022-12-30, 1,902 OK / 68 gap rows)

## Allowed scope

- Add Stage 3B-R2 goal, work record, oil timing resolution, oil contract v2, source registry,
  development input manifest, data coverage, tier-1 readiness, acceptance, and focused tests.
- Add `src/ashare_research/mechanism/oil.py`, `industry.py`, `alignment.py` and an acquisition CLI
  following the Stage 3B-R1 tool style.
- Attempt bounded, holdout-safe acquisition of Brent (EIA RBRTE / FRED DCOILBRENTEU) and Shenwan
  `801016`/`801960` into an explicit external root; commit only contracts, logical paths, hashes,
  schemas, rows/dates/coverage, code, and tests.
- Build the joint Tier-1 structural readiness date table (coverage only, no research result).
- Commit and normally push logical commits to `feat/m3-mechanism-validation-mvp`.

## Forbidden scope

- Modify any Stage 3A/Stage 3B v1/Stage 3B-R1 frozen artifact.
- Read, acquire, parse, summarize, or analyze any date 2023-01-01 or later.
- `download full history then filter to 2022` for any source — that reads the holdout.
- Any mechanism inference listed in the execution instruction (crash-day, correlation, abnormal
  return, regression, gamma, p-value, CI, bootstrap, effect size, FDR, evidence level, index offset).
- Substitute WTI / Brent futures / Shanghai crude / BZ=F / any other commodity proxy for the frozen
  primary Brent control.
- Substitute an industry ETF / CSI energy / THS oil sector / current-classification backfill for the
  frozen Shenwan primary industry control.
- Rebuild an industry-ex-`601857` proxy or fetch all Shenwan constituents (future robustness only).
- Write the default DB; commit raw/large data; create a PR; merge main; force-push; alter protected
  M2 state, stash, tags, branches, or artifacts.

## Acquisition honesty

If a source path ignores date bounds and returns full history through 2026, it is
`REJECT_SOURCE_PATH_FOR_SEALED_HOLDOUT` and is not used. If EIA needs an unavailable key and FRED
cannot be reached, EIA stays the authoritative source but acquisition is not provably bounded and
oil is reported `NOT_ACQUIRED`/`GAP`. If the SWS endpoint cannot be called without reading 2023+
and no verified development-only immutable cache exists, industry is `INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN`
and reported `GAP`/`BLOCKED`. In all cases the stage ends honestly with the sanctioned GAP verdict —
never by weakening the frozen contract or reading the holdout.

## Required reports

- `reports/m3_stage3br2_oil_timing_resolution_v1.json`
- `reports/m3_stage3br2_oil_contract_v2.json`
- `reports/m3_stage3br2_source_registry_v1.json`
- `reports/m3_stage3br2_development_input_manifest_v1.json`
- `reports/m3_stage3br2_data_coverage_v1.json`
- `reports/m3_stage3br2_tier1_readiness_v1.json`

## Required tests

- Stage 3A / Stage 3B v1 / Stage 3B-R1 frozen SHA unchanged.
- Oil contract v2 explicit supersession; same-day Brent rejected; strict-prior date accepted;
  Chinese-holiday cumulative anchor; weekend behavior; same-anchor => zero return;
  >7-day stale anchor rejected; EIA/FRED source conflict fail-closed; 2023+ oil rejected.
- `801016` regime boundary; `801960` regime start; cross-taxonomy return rejected;
  `2021-12-13` transition gap explicit; missing industry trading date fail-closed;
  industry forward-fill rejected; 2023+ industry rejected.
- Joint readiness requires all three Tier-1 valid; market-proxy R1 gap remains gap;
  no restricted outcome/statistical keys; offline A/B byte identity; raw hash mismatch fail-closed.

## Stop conditions

- Stop for North-Star review after final-tip CI evidence; do not begin Stage 3C.
- If oil or industry cannot be made TRUSTED, report the input gap and stop; never substitute a
  non-frozen proxy or read the holdout to force a PASS.