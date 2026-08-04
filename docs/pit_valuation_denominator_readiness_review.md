# PIT Valuation Denominator Readiness Review

Date: `2026-08-04`
Symbol: `601857.SH` (PetroChina)
Stage: M2 Stage 2K.1R4B Phase B (readiness review only — no valuation series built)

> **Superseded in part by ADR-VALUATION-002 (M2 Stage 2K.1R4C).** The R4B route
> recommendation here (`route = UNRESOLVED`, recommended `MARKET_CAP`) is **superseded**
> by the A-share per-share valuation convention: `route = A_SHARE_PRICE_PER_SHARE`,
> `route_status = FROZEN`. The A/H split is **not** a core-valuation blocker (the core
> convention is "A-share price ÷ company-wide per-share fundamental", no A/H split
> needed). The overall decision **`PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED` is
> unchanged** — the real blocker is the absence of quarterly financial facts, not the
> A/H split. The historical R4B judgement is preserved below, not erased.

## Scope and honesty

This document reviews whether historical PIT PE/PB/PS valuations are implementable
from the current repository. It is a **review only**: no historical PE/PB/PS series,
no valuation-percentile vNext, no downloads, no scoring expansion. Every claim below
was verified against the actual repository, not inferred from the README.

## 1. Current market numerator data

The committed market snapshot registry is `events/market_data_snapshot_registry.json`
(contract `market_data_snapshot_registry_v2`). The resolved external cache frame
(`tmp/market_cache/baostock/<sha>.parquet`, sha256 `defd0b9507…`) carries these fields:

| Field | Present | Notes |
|---|---|---|
| `close` | YES | unadjusted, CNY/share, 2021-01-04 → 2026-07-31, 1351 rows |
| `open`/`high`/`low`/`pre_close` | YES | unadjusted |
| `volume`/`amount`/`turnover_rate` | YES | CN shares / CNY / ratio |
| `total_market_cap` | **NO** | not present in the frame |
| `total_shares` | **NO** | not present in the frame |
| `adjusted shares` | **NO** | not present |
| `trade_date` | YES | string trade date |
| observation `available_at` | YES | `market_data_as_of_date` (PIT exclusion applied) |
| provider object identity | YES | `sha256`, `object_key`, `provider`, `provider_version` |
| 复权口径 | YES | `adjustment = none` (unadjusted) |

Two verified providers (baostock, akshare) reconcile (`close_differences_within_0_01`
= true, `reconciliation_status = pass`). The market observation set built by
`market_observation_set.py` is a **close-price** observation set (percentile of the
close series), not a PE/PB/PS percentile.

**Gap:** the market frame has **no `total_market_cap`, no `total_shares`, no adjusted
shares**. The price (numerator) side is available as `close`; the market-cap numerator
for Route A and the share-count for Route B are both absent.

## 2. Current financial denominator data

The canonical fact inventory `config/roic_canonical_fact_inventory_v2.json`
(354 facts, 20 concepts) is the authoritative fact source. The default DB
(`data/research.duckdb`) stores schema/metadata only — its `financial_facts` table is
empty; facts live in the JSON inventory. Verified coverage:

| Concept | Period type | Years | available_at | restatement | TTM/MRQ possible? |
|---|---|---|---|---|---|
| `net_profit_attributable_to_parent` | **annual** | 2021–2025 | yes | yes (original/restated_1) | **NO** (no quarterly) |
| `revenue` | **annual** | 2021–2025 | yes | yes | **NO** (no quarterly) |
| `equity_attributable_to_parent` | **instant** (year-end) | 2020–2025 | yes | yes | PB@annual only (no MRQ) |
| `total_assets` / `total_liabilities` | instant (year-end) | 2020–2025 | yes | yes | n/a |
| `share_capital` / `total_shares` | — | **0 share concepts** | — | — | **NO** |

The period-type distribution is **instant (201) + annual (153); there are zero
quarterly facts** (no single-quarter, no quarterly-cumulative). Therefore:

- **PE-TTM**: cannot construct a trailing-twelve-month net profit from annual facts
  alone. A daily-frequency TTM denominator is **not** deterministically constructible.
- **PB**: `equity_attributable_to_parent` is available as an annual year-end instant
  fact with `available_at` and restatement versions. A PIT-valid PB can be built only
  at **annual step resolution** (latest-equity step function), not true MRQ.
- **PS-TTM**: cannot construct TTM revenue from annual facts alone. **Not** available.

The Stage 2G valuation artifacts (`runs/stage2g/stage2g_valuation_pit_20260801/`)
confirm this: the PE/PB/PS observations (`a_share_price_to_latest_annual_*`) are
`computed` for 1050 rows and `missing_input` for 301 rows, but they use the **latest
annual** denominators, not a TTM/MRQ series.

## 3. Share capital timeline

The Stage 2G artifact `share_capital_timeline.json` (contract
`ordinary_share_capital_timeline_v1`) records `total_ordinary_shares = 183020977818`
(183.02B), **constant** across 2021-09-09 → 2026-07-31, with `available_at` and
`effective_from`/`effective_to` per dividend-implementation announcement.

Critical limitations:
- `canonical_market_cap_definition: false` — it is explicitly **not** a canonical
  market-cap definition (it is the dividend DPS basis).
- `a_shares`/`h_shares` are `null`; `share_validation_status: missing_evidence_a_h_split`.
  The timeline is **total ordinary (A+H)**, while the market close is **A-share only**.
  An A-share price × total ordinary shares would be a mislabeled
  `a_share_price_implied_total_ordinary_equity_value`, not a canonical market cap.
- Coverage is `evidence_bounded_interval` (announcement-sampled), so the window
  before the first announcement (2021-01-01 → 2021-09-08) has no share-count evidence.
- There is **no corporate-actions / share-change effective-date timeline** in the fact
  inventory.

## 4. Time coverage (as of 2026-07-31)

- Market close: 2021-01-04 → 2026-07-31 (covers 3y and 5y windows; 5y warm-up for the
  price side is fine).
- 3y window starts 2023-07-31; 5y window starts 2021-07-31.
- To construct the window-first-day **TTM** denominator, quarterly financial data is
  needed for the ~12 months before the window start (warm-up). **No quarterly
  financial data exists**, so the TTM warm-up is missing for both windows.
- PB-at-annual resolution is PIT-valid from 2021-01-04 (price side) × latest annual
  equity (first equity fact available_at 2022-03-31, so a PB observation at 2021
  trade dates would fall back to the 2020 equity available_at 2022-03-31 — a
  **historical-availability gap** for the earliest window dates).

## 5. Route comparison (candidate only — not implemented)

### Route A — market-cap numerator
```
PE_TTM(t) = total_market_cap(t) / PIT_TTM_parent_net_profit(t)
PB_MRQ(t) = total_market_cap(t) / PIT_parent_equity(t)
PS_TTM(t) = total_market_cap(t) / PIT_TTM_revenue(t)
```
- Numerator `total_market_cap(t)`: **not present** in the market frame → must be
  acquired or derived from a trusted share count (also absent).
- Denominator units (万元) must be converted to match market-cap units (CNY).
- Advantages: avoids per-share share-counting errors; a single market-cap series is
  directly comparable across issuers.

### Route B — per-share numerator
```
PE_TTM(t) = close(t) / PIT_TTM_EPS(t)
PB_MRQ(t) = close(t) / PIT_BVPS(t)
PS_TTM(t) = close(t) / PIT_TTM_sales_per_share(t)
```
- Numerator `close(t)`: available (unadjusted).
- Denominator requires a reliable `total_shares` timeline with effective dates and
  matching adjustment (复权) semantics. The only share timeline is total-ordinary
  (A+H), constant, non-canonical for market cap, and lacks the A/H split → **per-share
  metrics would be wrong for A-share close**.

### Recommendation
Neither route is currently implementable from committed data. Given the A/H split
absence and the total-ordinary share timeline being non-canonical for market cap,
**Route A (market cap) is the preferred direction** if a trusted historical
`total_market_cap(t)` series becomes available, because it avoids the A/H-share
mis-matching that blocks Route B. Because neither numerator is currently present, the
route is **UNRESOLVED** and both require acquisition.

## 6. Frozen candidate metric definitions (proposed only — not implemented)

Proposed metric identities (for the acquisition-required phase):

| metric_id | formula (Route A) | numerator identity | denominator identity | units | valid domain | negative/zero policy |
|---|---|---|---|---|---|---|
| `pe_ttm_market_cap` | `total_market_cap(t) / PIT_TTM_parent_net_profit(t)` | `total_market_cap(t)` | `PIT_TTM_net_profit_attributable_to_parent` | `ratio` (CNY/CNY) | TTM denominator > 0 | negative TTM → not a cheap signal; zero → no observation |
| `pb_market_cap` | `total_market_cap(t) / PIT_parent_equity(t)` | `total_market_cap(t)` | `PIT_equity_attributable_to_parent` | `ratio` | equity > 0 | equity ≤ 0 → no observation |
| `ps_ttm_market_cap` | `total_market_cap(t) / PIT_TTM_revenue(t)` | `total_market_cap(t)` | `PIT_TTM_revenue` | `ratio` | revenue > 0 | revenue = 0 → no observation |

Each must carry: PIT context (available_at ≤ valuation effective time), restatement
policy (use the value visible at available_at; never backfill a restated value),
share-capital policy (Route A needs no share count; Route B would need the A/H-split
timeline), exclusion rules (no close-percentile standing in for a valuation percentile;
no current-denominator backfill; no annual value effective before report end), and
lineage requirements (every observation binds market_observation_id,
financial_context_id, denominator Fact/Metric Result IDs, denominator available_at,
restatement/supersession identity, formula version, value digest).

## 7. PIT time-selection contract (draft — not implemented)

Per trade day `t`:
1. Market record: `trade_date = t`; market record `available_at` no later than the
   valuation-forming time.
2. Financial context: select only records with `available_at <= valuation_effective_time(t)`;
   match backward by `available_at`; under the same `available_at` apply the existing
   supersession/version priority. No nearest-forward; no join directly on report period.
3. An announcement with only a date (no time) → `effective_from` = the next trading
   day (conservative). If the repo already has a stricter trusted rule, reuse it.
4. Weekend/non-trading-day announcements → effective from the next trading day.
5. Restatement: keep the pre-restatement visible value until the restatement
   `available_at`; use the restated value after it; never backfill a restated value to
   before the restatement.
6. Each valuation observation binds market_observation_id; financial_context_id;
   denominator Fact/Metric Result IDs; denominator available_at; restatement/
   supersession identity; formula version; value digest.

Time joins may borrow the backward semantics of ASOF JOIN / merge_asof, but must be
constrained by the repo's own PIT contract.

## 8. Four implementation approaches compared

| Criterion | 1 INTERNAL_PIT_RECONSTRUCTION | 2 EXTERNAL_DAILY_VALUATION_SERIES | 3 HYBRID_VALIDATED_SERIES | 4 CLOSE_PRICE_PROXY |
|---|---|---|---|---|
| North-Star fit | high | medium | medium | **rejected** |
| Data availability | blocked (no quarterly, no market cap) | unverified (no source preflight) | unverified | cheap but wrong |
| PIT correctness | high if data present | depends on provider | depends on provider | **wrong** (close ≠ valuation) |
| Lineage quality | high (internal chain) | provider-dependent | provider + internal | n/a |
| Reproducibility | high | provider-dependent | provider-dependent | high but meaningless |
| Provider dependence | none | high | high | none |
| Clean-clone behavior | clean | may need live fetch | may need live fetch | clean |
| Implementation effort | high | medium | high | low |
| Risk of silent leakage | low–medium | medium | low | **high** |
| 3y feasibility | blocked | unverified | unverified | (rejected) |
| 5y feasibility | blocked | unverified | unverified | (rejected) |

Approach 4 (close-price proxy) is **explicitly rejected** as a valuation percentile;
it is already the current non-production observation set and must not be renamed a
historical PE/PB/PS percentile.

## 9. Readiness decision

**`PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED`**

- Market data (close, trade_date, available_at, provider identity, unadjusted 复权)
  is sufficient for the price side.
- But quarterly profit (PE-TTM), quarterly revenue (PS-TTM), quarterly equity granularity
  (PB-MRQ), a canonical historical `total_market_cap` series, and a canonical A/H-split
  share-capital timeline are **not** present. The current financial facts are annual-only;
  the share timeline is total-ordinary and non-canonical for market cap.
- No hard blocker on the market side; the blocker is the financial denominator and
  share/market-cap numerator data.

This round does **not** implement the series builder, even though the decision is
allowed. The route is `UNRESOLVED` (recommended direction: Route A market-cap).

## 10. Boundary confirmation

- No historical PE/PB/PS series, no valuation-percentile vNext, no new capsule, no
  production Metric Result, no peer database, no M3 artifact.
- No modification to `market_observation_set.py` business semantics, scoring weights,
  thresholds, or valuation results.
- `valuation_attractiveness` shadow remains `NON_PRODUCTION_AND_NOT_INTERPRETABLE`.