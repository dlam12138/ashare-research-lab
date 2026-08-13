# M2 Stage 2G PetroChina PIT valuation and value profile acceptance

Date: 2026-08-01
Formal run ID: `stage2g_valuation_pit_20260801`
Formal output: `runs/stage2g/stage2g_valuation_pit_20260801/`

## Phase B — North Star and methodology

`PASS`. The North Star review selects valuation because the existing five-year quality/cash-flow, ROE/ROA, financial-safety, and corrected dividend layers support a PIT price-versus-information profile. ROIC remains deferred for NOPAT/invested-capital boundary disputes; market-mechanism work remains later. References reviewed and repository-specific cuts are recorded in `docs/post_dividend_north_star_review.md`. No framework or identity/PIT override was added.

## Phase C — market and share foundation

`PASS WITH EXPLICIT GAPS` for the bounded official-anchor subcheck; provider reconciliation `PASS`.

- Existing `stock_daily` is reused; no canonical parallel market model or `market_observations.parquet` is created.
- Baostock 0.9.3 and AKShare 1.18.79 both provide 1,351 unadjusted rows from 2021-01-04 through 2026-07-31.
- Common-day close maximum absolute difference is 0.00 CNY; duplicate/date/adjustment checks pass.
- External content-addressed snapshots are registered in `events/market_data_snapshot_registry.json` under `D:/量化分析-cache/market-data/601857.SH/<provider>/`.
- Official SSE anchor checks are `not_available_in_offline_acquisition`, an explicit bounded limitation rather than a fabricated exchange claim.
- The share-capital timeline distinguishes A shares `161,922,077,818`, H shares `21,098,900,000`, and total ordinary shares `183,020,977,818`. A-close × total ordinary shares is named `a_share_price_implied_total_ordinary_equity_value` and is not canonical market capitalization.

## Phase D — PIT observations

`PASS`. `valuation_observations.parquet` contains 8,106 rows: six `ValuationObservation_v1` types for each market day. Decimal precision is 28 with `ROUND_HALF_EVEN` and 1e-12 quantization. Every row carries deterministic identity, trade-date availability, Fact/Event/source lineage, and formula version.

The six formulas are latest annual parent earnings multiple, latest year-end parent equity multiple, latest annual revenue multiple, trailing 12-month announced-dividend yield, trailing 12-month paid-dividend yield, and latest annual FCF-proxy yield. Announcement and payment windows are independent. Missing/partial evidence is explicit and never zero-filled. The 2025 final remains unavailable before its 2026-06-22 implementation announcement and 2026-06-26 payment date.

Latest 2026-07-31 observations are approximately 12.8916 earnings multiple, 1.2786 equity multiple, 0.7079 revenue multiple, missing announced yield, missing paid yield, and 0.05904 FCF-proxy yield. The missing dividend values reflect the bounded evidence gaps, not a zero dividend.

## Phase E — historical positions and scenarios

`PASS WITH EXPLICIT GAPS`. Expanding, 3-calendar-year, and 5-calendar-year percentile positions are descriptive historical positions only. Minimum effective samples are 120/500/900; dividend windows remain below the longer-window minima and disclose that limitation. Fixed sample-end stresses cover net profit, FCF proxy, announced DPS, and paid DPS at -20%/-30%. No target, trade conclusion, or probability is emitted.

## Phase F/G — profile, offline runner, and evidence

`PASS`. Reports are:

- `reports/petrochina_valuation_pit_2021_2026.md`
- `reports/petrochina_value_profile_2021_2026.md`
- `reports/petrochina_value_profile_one_page.md`
- `reports/petrochina_value_profile.json`

The profile integrates earnings/cash quality, ROE/ROA, financial safety, dividend announced/paid evidence, PIT valuation, scenarios, and explicit gaps. Risk-veto statuses are bounded (`observed`, `not_observed_within_bounded_evidence`, `not_evaluated`, or `missing_evidence`); no unresearched risk is called absent. ROIC and daily market mechanism are `not_evaluated`.

The formal runner is network-free and does not open the default DB, PDFs, or shared cache. It emits normalized stock_daily snapshot, share timeline, valuation observations/latest/percentiles/scenarios, PIT transitions, lineage, evidence gaps, manifest, and summary. A second formal run with the same run ID is byte-idempotent.

## Gate summary

| Gate | Status |
|---|---|
| Phase A corrected evidence | PASS WITH EXPLICIT GAPS |
| North Star/methodology | PASS |
| Market/provider reconciliation | PASS |
| Official exchange anchor limitation | PASS WITH EXPLICIT GAPS |
| Share scope/market-cap naming | PASS |
| PIT/no-future-leakage | PASS |
| Six observations and dividend separation | PASS |
| Percentiles/sample limits | PASS WITH EXPLICIT GAPS |
| Scenarios/no opinion fields | PASS |
| Offline/idempotence | PASS |
| ROIC/scoring/Web/market mechanism | NOT STARTED BY CONTRACT |
