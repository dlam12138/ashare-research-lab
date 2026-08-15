# M3 Stage 3B-R1 — Primary Proxy Contract Reconciliation & Reconstruction

Status: ACCEPTED — PRE-OUTCOME NORTH-STAR PROTOCOL AMENDMENT

## Verdict and decision

- Governance verdict: `M3_STAGE3BR1_PRE_OUTCOME_PROXY_AMENDMENT_ACCEPTED`.
- Decision: `M3_STAGE3BR1_PRE_OUTCOME_PROXY_AMENDMENT_ACCEPTED`.
- Primary proxy v2: `SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2` (CONSTRUCTED, trusted for the
  development period where the 0.99 coverage gate passes).
- Primary proxy v2 coverage: 1,970 trading days; **1,902 OK rows (coverage ≥ 0.99)** from
  2015-03-16 to 2022-12-30; **68 gap rows** (23 Dec-2014 warm-up + 45 Jan–Mar-2015 genuine mass
  suspensions), all fail-closed (`PROXY_ROW_INVALID_DATA_GAP`), never silent-subset.
- Primary proxy v2 data gap: 11 delisted-within-window symbols (Sina unserved; Eastmoney
  unreachable) — bounded, documented, fail-closed on their listing days, never pushing a
  clean-period day below 0.99.
- Exact SSE Composite ex-`601857` reconstruction: `DEFERRED_NON_BLOCKING`.
- Holdout: `M3_HOLDOUT_REMAINS_SEALED` (no 2023+ date read or written).
- Next stage: `M3_STAGE3BR2_OIL_INDUSTRY_ACQUISITION_ALLOWED`.
- Stage 3C: `M3_STAGE3C_NOT_YET_ALLOWED`.
- Stop: `STOP_FOR_NORTH_STAR_REVIEW`.

## Pre-outcome supersession rationale

The North Star defines the primary market proxy as the market aggregate that excludes the target
stock. The exact SSE Composite equivalent divisor reconstruction is a separate research task, not a
precondition for the primary mechanism MVP. Stage 3A defines `estimated_index_offset` as a
SEPARATE_ESTIMATION_PIPELINE. Stage 3B v1 strengthened the primary proxy to exact
SSE-Composite-equivalent divisor reconstruction, which failed closed because the strict inputs
(complete official historical index eligibility, full-market issued shares, corporate actions,
divisor continuity) are not obtainable under current free-data conditions.

Because a market proxy must not be degraded at runtime, v2 is frozen as a formally superseding
pre-outcome contract authorized by North-Star review and independent of any research result. The
equal-weight ex-target Shanghai A-share proxy is a reproducible, North-Star-compliant
implementation for the M3 primary mechanism MVP. This is a supersession, not a runtime fallback;
Stage 3B v1 remains failed/closed and immutable, and is not replaced by code reuse.

## Frozen semantics (v2)

- Universe: Shanghai-listed A-share common equities (Main Board `60x` + STAR `688x`), physically
  excluding `601857.SH`; excludes B-shares (`90x`), CDR (`689`), and ETFs/funds/bonds/indices;
  ST/*ST are not excluded merely because of risk-warning status.
- PIT membership uses only information known at the previous trading-day close; no current-universe
  backfill; no future listing/delisting knowledge; a new listing enters only once a valid previous
  close exists; suspension carries the last valid close with zero daily return; a security leaves
  after its final valid observation under the frozen delisting rule; missing provider data never
  silently removes a constituent.
- Return is simple close-to-close; the daily proxy is the arithmetic equal-weight mean of
  constituent returns from the t-1 eligible universe after physical exclusion of `601857.SH`.
- `minimum_daily_input_coverage = 0.99`; a date below the gate is `PROXY_ROW_INVALID_DATA_GAP`,
  never silently computed on the available subset.
- Exact SSE Composite ex-`601857` reconstruction remains an optional, deferred, non-blocking
  research enhancement; historical target index weight remains a separate contribution pipeline.

## Source feasibility for Stage 3B-R2

Performed source-feasibility only; the frozen oil/industry contracts were not altered.

- Shenwan industry index: akshare `index_hist_sw` returns the full historical daily series for
  `801016` (SW2014, 5,559 development rows from its 1999 start) and `801960` (SW2021, 251
  development rows from its 2021-12-13 start), matching the frozen taxonomy transition. Feasible.
- EIA/FRED Brent: the daily spot series is retrievable, but the principal Stage 3B-R2 blocker is
  proving the PIT release/observation timestamp was available before the 15:00 CST A-share close;
  the frozen policy requires this and fails closed otherwise.

## Acquisition (bounded, resumable, content-addressed)

External root is not committed; only logical paths, hashes, schemas, rows/dates/coverage, code, and
tests are in Git. Every request was bounded at `2022-12-31`; no 2023+ market outcome was requested,
read, or normalized.

- Security master: Shanghai 主板A股 + 科创板 + 主板B股 + delist lists via akshare.
- Trade calendar: reused from the immutable Stage 3B capsule (SHA-256 verified).
- Daily series: one bounded full-development series per ever-eligible symbol via akshare (Sina).
- Offline normalization A/B with canonical byte/logical identity comparison.

## Scope proof

- No holdout outcome acquisition/read/normalization.
- No crash-day count, return relationship, correlation, positive probability, abnormal return,
  regression, alpha/beta/gamma, p-value, CI, bootstrap, effect size, evidence grade, or
  year-by-year mechanism result.
- Proxy choice fixed from North-Star semantics and data feasibility only, never by which proxy
  strengthens a PetroChina result.
- No funding-actor/support-market claim; no official index point attribution.
- No Stage 3A or Stage 3B v1 mutation; no Stage 3C module; no scipy/statsmodels; no PR/merge; no
  default DB write; no protected M2 worktree/stash mutation.

## Local validation

- Full `pytest -q` (with worktree `src` on `PYTHONPATH`): 1985+ passed, 3 skipped, 0 failed.
- Focused Stage 3B-R1 tests: 20 passed (target exclusion, t-1 PIT membership, listing/delisting,
  suspension zero-return, missing-row fail-closed, 0.99 gate, 2023+ rejection, offline A/B
  identity, frozen Stage 3A/3B-v1 hashes unchanged, restricted-output absence).
- `ruff check src/ tests/`: PASS. `python -m compileall -q src tests`: PASS.
  `git diff --check`: PASS.
- All 5 Stage 3B-R1 JSON reports parse; no restricted research outputs; no holdout (2023+) date
  string in any committed report; proxy/audit/daily/calendar artifacts all end 2022-12-30.
- Offline A/B (label a vs label b): normalized daily series byte- and canonical-identical.
- Frozen Stage 3A (3 artifacts) and Stage 3B v1 (5 artifacts) SHA-256: unchanged.
- Protected state: `feat/m3-mechanism-validation-mvp`; `stash@{0}` preserved; no
  `data/research.duckdb` in the isolated worktree.
- Proxy coverage: 1,970 trading days; 1,902 OK (≥ 0.99) 2015-03-16→2022-12-30; 68 gap (warm-up +
  Q1-2015 genuine mass suspensions), fail-closed.

## Final evidence

- `reports/m3_stage3br1_primary_proxy_resolution_v1.json`
- `reports/m3_stage3br1_primary_proxy_contract_v2.json`
- `reports/m3_stage3br1_source_registry_v1.json`
- `reports/m3_stage3br1_development_proxy_manifest_v1.json`
- `reports/m3_stage3br1_data_coverage_v1.json`