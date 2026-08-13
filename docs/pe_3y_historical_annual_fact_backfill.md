# PE 3Y Historical Annual Fact Backfill (R4F.3A) — Method and Validation Protocol

Stage: `2K.1R4F.3A`
Contract: `config/pe_3y_historical_backfill_contract_v1.json`
Status: 2026-08-08, local validation complete — `PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED`

## 1. Purpose

R4F.3 proved that the frozen 3Y historical validation window
(2023-07-31..2026-07-31) could not run: the 5-year consecutive annual ROE
chain needed facts from 2017-2019 that were not in the repository.  This
stage backfills exactly those facts (the `MINIMUM_3Y_BACKFILL` from the
R4F.3 gap plan), preserving original disclosure values, PIT announcement
dates, and restatement lineage — never "latest value backfilled into the
past".

## 2. Target logical cells (from the R4F.3 committed gap plan)

| Cell | Concept | Period end | Required for |
|---|---|---|---|
| A | equity_attributable_to_parent | 2017-12-31 | opening equity, ROE 2018 |
| B | equity_attributable_to_parent | 2018-12-31 | ROE 2018 |
| C | net_profit_attributable_to_parent | 2018-12-31 | ROE 2018 |
| D | equity_attributable_to_parent | 2019-12-31 | ROE 2019 |
| E | net_profit_attributable_to_parent | 2019-12-31 | ROE 2019 |

`target_logical_cell_count = 5`; actual Fact records = 8 (3 restatements
produce additional versioned Facts, as required).

## 3. ROE dependency (machine-checkable)

```
ROE 2018 = NP_2018 / ((Equity_2017 + Equity_2018) / 2)
ROE 2019 = NP_2019 / ((Equity_2018 + Equity_2019) / 2)
ROE 2020 = NP_2020 / ((Equity_2019 + Equity_2020) / 2)   # NP_2020 and Equity_2020 already exist
```

The tests (`tests/test_m2_stage2k1r4f3a_pe_historical_annual_backfill.py`)
verify the dependency function output, not a hand-written conclusion.

## 4. Source policy

- Primary: `exchange_official` — Shanghai Stock Exchange official
  annual-report PDFs (static.sse.com.cn).
- 2017/2018/2019 annual reports downloaded for this stage (external
  content-addressed cache, never committed).
- 2020 annual report re-downloaded for comparative scanning; its sha256
  matches the R4D cache registry exactly (`7aac267c…`), so it is the same
  content object — no duplicate economic fact.
- Issuer-official copies: alias / cross-check only.  No AKShare / Eastmoney
  / news / search-summary / manual-web values used.

## 5. Evidence documents and versions observed

| Filing | Announcement | Role in lineage |
|---|---|---|
| 2017 AR (601857_2017_n.pdf) | 2018-03-22 | original 2017-12-31 equity |
| 2018 AR (601857_2018_n.pdf) | 2019-03-21 | original 2018-12-31 equity + NP |
| 2019 AR (601857_2019_n.pdf) | 2020-03-26 | original 2019-12-31 equity + NP; **restates 2017/2018** (Dalian Xitai SCA, note 6(2)) |
| 2020 AR (R4D object) | 2021-03-26 | comparative scan: 2019 values unchanged — no restatement |

2021/2022 annual reports are excluded by window analysis: their comparative
columns cover only the prior year, so they cannot affect 2018/2019
target-period facts.

## 6. Restatement lineage (Dalian Xitai same-control acquisition)

The 2019 AR note 6(2) states the company completed the acquisition of
Dalian Xitai in May 2019 and adjusted comparative financial information per
same-control combination rules.  The 2019 AR equity-changes statement
(p118) and comparative columns (p114/p115) show:

| Cell | Original (million) | Restated_1 (million) | Delta |
|---|---|---|---|
| equity 2017-12-31 | 1,193,810 | 1,192,862 | -948 |
| equity 2018-12-31 | 1,214,570 | 1,214,067 | -503 |
| NP 2018-12-31 | 52,585 | 53,030 | +445 |

Both versions are retained as Facts with `supersedes_fact_id` forming a
complete, traversable chain.  PIT resolution (`resolve_latest_visible`)
selects the visible version at each as-of date; a future restatement never
changes a historical as-of state.

## 7. PIT time contract

- `available_at` = official announcement date (retained verbatim).
- `effective_from` = next real trading day after announcement,
  `announcement-date-to-next-trading-day-v1`, resolved against the **R4F3A
  historical calendar** (baostock 2017-01-03..2026-08-07).
- Calendar v1 (2020-01-02..) remains unchanged; R4F3A registry
  (`pit_valuation_market_calendar_registry_r4f3a_v1.json`) reuses the same
  schema and pins a new content-addressed object.
- Overlap reconciliation (2020-01-02..2026-08-05): old 1597 == new 1597,
  missing=0, extra=0 — **PASS**.
- Calendar gap → `pit_time_contract_gap = calendar_coverage_gap`, fact
  never enters a PIT-ready bundle (fail closed; none occurred here).

## 8. Facts built (8)

All `source_tier=exchange_official`, unit CNY (raw CNY_million x 1e6),
scope consolidated attributable to parent, canonical FactIdentity via
`build_fact_id`.

| # | Concept | Period | Version | Value (CNY) | Announced | Effective |
|---|---|---|---|---|---|---|
| 1 | equity | 2017-12-31 | original | 1,193,810,000,000 | 2018-03-22 | 2018-03-23 |
| 2 | equity | 2018-12-31 | original | 1,214,570,000,000 | 2019-03-21 | 2019-03-22 |
| 3 | NP | 2018-12-31 | original | 52,585,000,000 | 2019-03-21 | 2019-03-22 |
| 4 | equity | 2019-12-31 | original | 1,230,428,000,000 | 2020-03-26 | 2020-03-27 |
| 5 | NP | 2019-12-31 | original | 45,677,000,000 | 2020-03-26 | 2020-03-27 |
| 6 | equity | 2017-12-31 | restated_1 (supersedes 1) | 1,192,862,000,000 | 2020-03-26 | 2020-03-27 |
| 7 | equity | 2018-12-31 | restated_1 (supersedes 2) | 1,214,067,000,000 | 2020-03-26 | 2020-03-27 |
| 8 | NP | 2018-12-31 | restated_1 (supersedes 3) | 53,030,000,000 | 2020-03-26 | 2020-03-27 |

## 9. Overlay (no historical fact rewritten)

R4F.3 readiness / state ledger / gap plan / decision remain immutable.
The overlay combines the existing trusted fact set (165 facts) with the
backfill bundle (8 facts) and records three deterministic digests
(existing / backfill / combined).

## 10. Readiness re-run (same R4F.3 engine, unchanged)

| Metric | Before | After |
|---|---|---|
| Earliest ready date | 2026-03-31 | **2023-03-31** |
| Ready trade days | 84 | 808 |
| Blocked trade days | 1267 | 543 |
| 3Y blocked days | 644 | **0** |
| 5Y blocked days | 1127 | 403 (still BLOCKED) |
| Gap reason counts | insufficient_roe_history: 1267 | insufficient_roe_history: 543 |

3Y gate: **THREE_YEAR_HISTORICAL_VALIDATION_READY** (728/728).  5Y stays
BLOCKED; the residual 5Y gap plan is the deterministic subtraction of the
resolved cells from the R4F.3 baseline: original minimum 9 − resolved 5 =
**remaining 4** (2015-12-31 equity, 2016-12-31 equity+NP, 2017-12-31 NP).
`full_cycle_proven` remains **false** — more history does not prove a full
cycle.

## 11. Independent ROE verification (Decimal-only)

```
ROE 2018 = 53,030 / ((1,192,862 + 1,214,067) / 2) = 0.04406444893056670969521743267
ROE 2019 = 45,677 / ((1,214,067 + 1,230,428) / 2) = 0.03737131800228677088723846848
ROE 2020 = 19,002 / ((1,230,428 + 1,215,421) / 2) = 0.01553816282198941962484192606
```

Each equals the R4F.3 resolver value exactly (recomputed, never read).
Disclosed ROE figures in the annual reports are cross-check diagnostics
only — never formal inputs (prevents method drift).

## 12. Boundaries preserved

- PE numeric score: BLOCKED_UNCHANGED; valuation dimension: no score.
- No normalized PE percentile; no empirical cycle-guard validation; no
  peer; no M3; no default-DB write.
- registry v2 / policy v2 / shadow v6 / sensitivity v8 unchanged.
- Calendar v1 and R4D CALENDAR_COVERAGE_START unchanged.
- No 5Y financial-fact backfill; 2015/2016 untouched.

## 13. Decision

`PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED` (PASS)

Next stage (not started): R4F.4 — 3Y Historical Normalized-PE Cycle-Guard
Validation.  This authorizes the validation, **not** PE scoring.
