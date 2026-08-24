# M3 Stage 3B-R2 — Oil & Petrochemical Industry Acquisition, PIT Alignment & Tier-1 Closeout

Status: ACCEPTED — PRE-OUTCOME TIER-1 DATA CLOSEOUT (HONEST INPUT GAP)

## Verdict and decision

- Governance verdict: `M3_STAGE3BR2_PRE_OUTCOME_TIER1_DATA_CLOSEOUT_ACCEPTED` (input-gap outcome).
- Decision set:
  - `M3_STAGE3BR2_OIL_INPUT_GAP`
  - `M3_STAGE3BR2_INDUSTRY_INPUT_GAP`
  - `M3_TIER1_DEVELOPMENT_INPUTS_NOT_READY`
  - `M3_HOLDOUT_REMAINS_SEALED`
  - `M3_STAGE3C_NOT_ALLOWED`
  - `STOP_FOR_NORTH_STAR_REVIEW`
- The Separation of powers is preserved:
  - **implementation**: PASS (pre-outcome timing supersession, oil/industry/alignment modules, bounded
    acquisition CLI, offline tests all green).
  - **data**: NOT TRUSTED — neither `oil` nor `petrochemical_industry` could be acquired through a
    bounded, holdout-safe path in this environment; both are reported `NOT_ACQUIRED` / `GAP`.
  - **research result**: NOT EXECUTED — no PetroChina mechanism/outcome statistic was computed.

## Stage 3B-R1 final-tip CI gate

- `b7c8bec` full SHA `b7c8becc69fc1e7647fa23b7444cbbbeaf8f0364`; Actions run `31871858528`:
  `completed`, `success`; Windows + Ubuntu clean-clone and identity-compare all success. Gate PASS.

## Pre-outcome oil timing supersession

Stage 3B v1 `return_and_timing_contract_v1.json` demanded a per-observation publication/release
timestamp proven earlier than the 15:00 CST A-share close, failing closed otherwise. North-Star
review authorized a formal pre-outcome supersession: that requirement conflated the underlying Brent
market observation time with a later data-distributor publication time. The corrected, frozen rule
is `OIL_ALIGNMENT_V2 = STRICTLY_PRIOR_BRENT_OBSERVATION_DATE`: each A-share day `t` anchors to the
latest Brent observation date strictly before `t`; the same-calendar-day overseas close remains
prohibited; a 7-day anchor-age staleness gate is frozen with no override. The v1 contract is
byte-identical; the correction is expressed only through the new addendum artifacts.

## Frozen semantics

- Primary Brent benchmark remains Europe Brent Spot Price FOB (EIA RBRTE, FRED mirror DCOILBRENTEU,
  USD/barrel). No substitution to WTI / Brent futures / Shanghai crude / BZ=F / any commodity proxy.
- Chinese-holiday and weekend behavior absorb the whole between-anchor Brent change; a same anchor
  yields a zero return (no new observation), not an artificial forward-fill.
- Shenwan industry regimes unchanged: `801016` (SW_2014) through 2021-12-10; `801960` (SW_2021) from
  2021-12-13; cross-taxonomy returns never computed; 2021-12-13 explicit
  `INDUSTRY_TAXONOMY_TRANSITION_GAP`; missing closes fail closed (no forward-fill).
- Joint Tier-1 readiness reuses the trusted `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` market proxy and
  requires all three Tier-1 inputs valid on a date; missing controls are never forward-filled.

## Acquisition outcome (bounded, holdout-safe)

Both required Tier-1 controls could not be acquired through a bounded path that never reads 2023+:

- **Oil (Brent):** EIA keyless dnav page ignores date parameters and returns full history through the
  current year (`REJECT_SOURCE_PATH_FOR_SEALED_HOLDOUT`); EIA Open Data API v2 requires an API key
  unavailable in this environment (`OIL_EIA_API_KEY_UNAVAILABLE`); FRED (stlouisfed.org) is
  unreachable (`OIL_FRED_UNREACHABLE`). No bounded transport exists.
- **Industry (Shenwan):** the official SWS trend endpoint ignores all date parameters and returns the
  full daily series (1999 → current) for `801016`/`801960`, so any download reads the sealed holdout;
  no verified development-only immutable industry capsule exists
  (`INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN`).

No raw file was written, no holdout date was requested/read/parsed, and no non-frozen proxy was
substituted to force a PASS.

## Scope proof

- No holdout acquisition/read/normalization (no 2023+ date read or written).
- No crash-day count, correlation, positive probability, abnormal return, regression,
  alpha/beta/gamma, p-value, CI, bootstrap, effect size, evidence grade, or index-offset result.
- No Stage 3A / Stage 3B v1 / Stage 3B-R1 artifact mutated (SHA-256 verified unchanged).
- No Stage 3C module; no default DB write; no PR/merge; no protected M2 worktree/stash mutation.

## Local validation

- Focused Stage 3B-R2 tests: 31 passed (frozen 3A/3B-v1/3B-R1 hashes; oil v2 supersession; same-day
  reject; strict-prior accept; holiday cumulative; weekend; same-anchor zero; stale anchor; EIA/FRED
  conflict fail-closed; holdout rejection; industry regimes; transition gap; missing-date fail-closed;
  forward-fill reject; joint readiness; R1 gap remains gap; no restricted outputs; offline A/B
  identity; raw-hash mismatch).
- Stage 3A + Stage 3B v1 + Stage 3B-R1 boundary tests: 52 passed.
- `ruff check src/ tests/`: PASS. `python -m compileall -q src tests`: PASS.
  `git diff --check`: PASS.
- All 6 Stage 3B-R2 JSON reports parse; no restricted research outputs; holdout sealed; no real
  2023+ data (only the declared `holdout_start` boundary constant shared with the frozen Stage 3B v1
  contract); no default `data/research.duckdb` in the isolated worktree.
- Full `pytest -q`: PASS (see work record for counts).
- Protected state: `feat/m3-mechanism-validation-mvp`; `stash@{0}` preserved; M2 worktree untouched.

## Final evidence

- `reports/m3_stage3br2_oil_timing_resolution_v1.json`
- `reports/m3_stage3br2_oil_contract_v2.json`
- `reports/m3_stage3br2_source_registry_v1.json`
- `reports/m3_stage3br2_development_input_manifest_v1.json`
- `reports/m3_stage3br2_data_coverage_v1.json`
- `reports/m3_stage3br2_tier1_readiness_v1.json`

## Stop

`STOP_FOR_NORTH_STAR_REVIEW`. Stage 3C is not allowed. The Tier-1 inputs remain NOT READY until a
bounded, holdout-safe Brent and Shenwan acquisition path is proven (e.g., an EIA API key, a reachable
FRED bounded transport, or a verified development-only immutable source capsule).