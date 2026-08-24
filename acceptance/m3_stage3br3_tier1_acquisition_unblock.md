# M3 Stage 3B-R3 — Tier-1 Acquisition Unblock & Data Closeout

Status: ACCEPTED — PRE-OUTCOME TIER-1 SOURCE-GAP CLOSEOUT (HONEST UNBLOCK ATTEMPT)

## Verdict and decision

- Governance verdict: `M3_STAGE3BR3_TIER1_SOURCE_GAPS_REMAIN` (both Tier-1 controls remain not
  acquired through a bounded, holdout-safe path in this environment).
- Decision set:
  - `M3_STAGE3BR3_OIL_AUTH_INPUT_REQUIRED` (oil blocked only by a missing `EIA_API_KEY`)
  - `M3_STAGE3BR3_INDUSTRY_DEVELOPMENT_CAPSULE_REQUIRED` (industry blocked by no bounded SWS
    transport and no official development capsule)
  - `M3_TIER1_DEVELOPMENT_INPUTS_NOT_READY`
  - `M3_HOLDOUT_REMAINS_SEALED`
  - `M3_STAGE3C_NOT_ALLOWED`
  - `STOP_FOR_NORTH_STAR_REVIEW`
- Separation of powers:
  - **implementation**: PASS — bounded EIA Open Data API v2 transport (secret-redacted, official
    route discovery, server-side bounded, response validation), Shenwan official-source-resolution
    ladder, Stage 3B-R3 acquisition CLI, and offline tests all green.
  - **data acquisition**: NOT ACQUIRED — oil reports `OIL_EIA_API_KEY_REQUIRED`;
    petrochemical_industry reports `INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED`.
  - **data trust**: NOT TRUSTED for oil and industry; joint Tier-1 dates NOT_READY. The market
    proxy v2 remains TRUSTED from Stage 3B-R1.
  - **research execution**: NOT EXECUTED — no PetroChina mechanism/outcome statistic was computed.

## Stage 3B-R2 final-tip CI gate

- `2042e44` full SHA `2042e44e6d571e968febeb6389d93141bea389e9`; Actions run `31877910646`:
  `completed`, `success`; Windows + Ubuntu clean-clone and identity-compare all success. Gate PASS.

## Oil outcome (bounded, holdout-safe)

- Primary transport: EIA Open Data API v2 for Europe Brent Spot Price FOB (RBRTE), USD/barrel,
  daily, server-side bounded `2014-12-01` (warm-up) .. `2022-12-31` (development).
- Auth: `ENVIRONMENT_API_KEY` read via `os.environ.get("EIA_API_KEY")`; never persisted or logged.
  The current process environment has no key, so the acquisition step reports
  `OIL_EIA_API_KEY_REQUIRED` and writes no raw file. The transport is fully implemented and tested
  (mock-transport secret-redaction and bounded-acquisition tests), so setting the key and rerunning
  only the bounded oil acquisition step will complete it.
- FRED `DCOILBRENTEU` is a secondary distribution of EIA and is `OPTIONAL_SECONDARY_DISTRIBUTION_
  CROSSCHECK`; it is not a gate. FRED network unreachability is
  `FRED_CROSSCHECK_UNAVAILABLE_NON_BLOCKING` and never blocks oil when the EIA authoritative bounded
  path is trusted.
- No WTI / Brent futures / Shanghai crude / BZ=F / commodity-ETF substitution was made.

## Industry outcome (source-resolution ladder)

- Frozen identity: Shenwan Petroleum and Petrochemicals Industry Price Index, `801016` (SW_2014,
  through 2021-12-10) and `801960` (SW_2021, from 2021-12-13); `2021-12-13` transition gap;
  within-regime simple returns.
- Route A (official SWS bounded transport): the three official endpoint families present in AKShare
  (`index_publish/trend/`, `index_publish/details/timelines/`,
  `index_analysis/index_analysis_report/`) all ignore server-side date bounds and return full
  history through the current year; none is a bounded transport. The unbounded adapter is not
  re-invoked (that would read the sealed holdout).
- Route B (existing development-only official capsule): none exists in the repo, `tmp/`, or the
  `%USERPROFILE%\.codex\external-cache\ashare-research\` root.
- Route C (user-provided official development capsule): none present;
  `INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED`.
- Route D (same-series third-party transport): no transport with provable series identity/lineage is
  available; unproven mirrors are `UNVERIFIED_MIRROR_REJECTED`.
- No industry ETF / CSI energy / THS sector / current-classification backfill was substituted.

## Scope proof

- No holdout acquisition/read/parse/store/analyze (no 2023+ value read or written).
- No crash-day, correlation, abnormal return, regression, gamma, p-value, CI, bootstrap, effect
  size, or index-offset result.
- No Stage 3A / Stage 3B v1 / Stage 3B-R1 / Stage 3B-R2 JSON artifact mutated (SHA-256 verified
  unchanged). The only historical markdown edits are the R2 Goal status, the R2 work-record
  status/final-CI closeout, and the README factual status.
- No Stage 3C or 3C-A module; no default DB write; no PR/merge/force-push/tag; no protected M2
  worktree/stash mutation.

## Local validation

- Focused Stage 3B-R3 tests: 29 passed (frozen 3B-R2/R3 hashes; key-absent fail-closed; key never in
  exceptions/reports/manifests/snapshots; redacted endpoint stable; source contains no test-secret
  literal; route discovery; bounded-end required; end>=2023 rejected; wrong series/units rejected;
  duplicate date rejected; malformed numeric rejected; response past development end fail-closed;
  offline A/B identity for oil and industry; industry ladder no-source/capsule-accepted/holdout-
  rejected/SHA-mismatch/unproven-mirror/cross-taxonomy).
- Stage 3B-R2 + Stage 3A + Stage 3B v1 + Stage 3B-R1 boundary tests: all green.
- `ruff check src/ tests/`: PASS. `python -m compileall -q src tests`: PASS.
  `git diff --check`: PASS.
- All 6 Stage 3B-R3 JSON reports parse; no restricted research outputs; holdout sealed; no real
  2023+ date (only the frozen `2021-12-10` / `2021-12-13` regime boundaries and the development
  `<= 2022-12-31` bound); no default `data/research.duckdb` in the isolated worktree.
- Full `pytest -q`: PASS (see work record for counts).
- Protected state: branch `feat/m3-mechanism-validation-mvp`; `stash@{0}` preserved; M2 worktree
  untouched; no `data/research.duckdb`.

## Final evidence

- `reports/m3_stage3br3_source_resolution_v1.json`
- `reports/m3_stage3br3_oil_development_manifest_v1.json`
- `reports/m3_stage3br3_industry_development_manifest_v1.json`
- `reports/m3_stage3br3_data_coverage_v1.json`
- `reports/m3_stage3br3_tier1_readiness_v2.json`
- `reports/m3_stage3br3_joint_input_manifest_v1.json`

## Stop

`STOP_FOR_NORTH_STAR_REVIEW`. Stage 3C and Stage 3C-A are not allowed. To make the Tier-1 inputs
TRUSTED, provide the exact unblock inputs named below, then rerun only the corresponding bounded
acquisition step. Do not substitute a non-frozen proxy and do not read the holdout.

### Exact unblock inputs

- **Oil**: set `EIA_API_KEY` in the local execution environment (never in chat, Goal, or Git), then
  rerun only the bounded oil acquisition step.
- **Industry**: provide an official Shenwan development-only immutable capsule containing
  `industry_801016.csv` and `industry_801960.csv` (columns `trade_date`, `close`; only
  development dates `<= 2022-12-31`; SHAs recorded), then rerun the industry ladder / offline
  normalize / align steps.