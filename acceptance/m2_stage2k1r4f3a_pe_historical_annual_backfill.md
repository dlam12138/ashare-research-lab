# M2 Stage 2K.1R4F.3A — Historical Annual Fact Backfill for 3Y Normalized-Earnings Validation

## Verdict: PASS

Status: completed (local validation only; not committed/pushed)

Decision: `PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED`

Next-stage implementation: **NOT STARTED** (`R4F.4 — 3Y Historical
Normalized-PE Cycle-Guard Validation` is the next authorized step; PE
numeric scoring stays blocked)

This stage backfills the R4F.3 `MINIMUM_3Y_BACKFILL` (5 logical cells:
2017-12-31 equity; 2018/2019 equity + parent NP) from SSE official annual
reports with full PIT/restatement lineage, extends the verified trading
calendar to 2017, and reruns the same R4F.3 readiness engine to show the
frozen 3Y window is now READY.

## 0. Final report card

```
M2 Stage 2K.1R4F.3A:                                   PASS
R4F.3 upstream:                                        TRUSTED
Target logical cells:                                  5
Target cells resolved:                                 5/5
Actual Fact records:                                   8
Restatement versions:                                  3
Exchange-official evidence:                            TRUSTED
Source conflicts:                                      NONE
PIT effective-from:                                    PASS
Fact identity:                                         PASS
2018 ROE:                                              0.04406444893056670969521743267
2019 ROE:                                              0.03737131800228677088723846848
2020 ROE:                                              0.01553816282198941962484192606
Pre-backfill earliest ready date:                      2026-03-31
Post-backfill earliest ready date:                     2023-03-31
3Y required trade days:                                728
3Y ready days:                                         728
3Y blocked days:                                       0
3Y historical validation:                              READY
5Y historical validation:                              BLOCKED
Remaining 5Y fact gaps:                                4 (2015-12-31 equity, 2016-12-31 equity+NP, 2017-12-31 NP)
Full-cycle coverage:                                   NOT_PROVEN
PE numeric scoring:                                    BLOCKED_UNCHANGED
Valuation dimension score:                             NONE
Registry/policy v2:                                    UNCHANGED
Shadow v6:                                             UNCHANGED
Sensitivity v8:                                        UNCHANGED
Default DB:                                            UNCHANGED
Historical calendar v1:                                UNCHANGED
R4F3A historical calendar:                             TRUSTED
Historical calendar range:                             2017-01-03..2026-08-07
Earliest target announcement:                          2018-03-22 (2017 AR)
Calendar overlap reconciliation:                       PASS
Overlap missing dates:                                 0
Overlap extra dates:                                   0
Target PIT calendar gaps:                              0
Decision:                                              PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED
Next-stage implementation:                             NOT STARTED
```

## 1. What was built

- `config/pe_3y_historical_backfill_contract_v1.json` — frozen contract
  (5 target cells, concepts, PIT rule, source policy, scoring boundary).
- `config/pit_valuation_market_calendar_registry_r4f3a_v1.json` — R4F3A
  historical calendar registry (reuses the existing v1 schema; new
  content-addressed object 6a3cf1a0…; baostock; 2017-01-03..2026-08-07;
  extends coverage of calendar v1, `supersedes_calendar=false`).
- `config/pe_3y_historical_backfill_source_evidence_v1.json` +
  `..._cache_registry_v1.json` + `..._extraction_specs_v1.json`.
- `src/ashare_research/pit_valuation/pe_historical_annual_backfill.py` —
  pure functions: extraction, PIT fact construction (reuses R4D
  `build_context_v2` / `build_fact_id` / `load_market_calendar` /
  `next_trading_day`), restatement reconciliation, bundle/overlay
  assembly, Decimal-only ROE.
- 8 Fact records (5 original + 3 restated_1), 4 official SSE PDFs in the
  external content-addressed cache (never committed).
- Artifacts: extraction v1, reported bundle v1, version lineage v1,
  overlay v1, 3y-readiness-after-backfill v1, calendar reconciliation v1,
  reconciliation v1, R4F3A decision.

## 2. Restatement lineage (important finding)

The 2019 AR (announced 2020-03-26, note 6(2)) restates 2018 and 2017
comparatives for the May-2019 Dalian Xitai same-control acquisition:

- equity 2017-12-31: 1,193,810 → 1,192,862 (restated_1)
- equity 2018-12-31: 1,214,570 → 1,214,067 (restated_1)
- NP 2018-12-31: 52,585 → 53,030 (restated_1)

The 2020 AR comparative columns confirm no restatement of 2019 values.
All versions are retained with complete `supersedes_fact_id` chains; PIT
resolution selects the version visible at each as-of date.  **No latest
value is backfilled into the past.**

## 3. Calendar extension

- Calendar v1 (2020-01-02..2026-08-05) unchanged.
- R4F3A calendar (2017-01-03..2026-08-07) pinned by a new content-
  addressed registry; overlap reconciliation with v1: **PASS** (missing
  dates 0, extra dates 0, 1597/1597).
- `next_trading_day` still the existing function; same announcement-date-to-
  next-trading-day-v1 rule; calendar coverage gaps fail closed.

## 4. Readiness (same R4F.3 engine)

- Before (reproduces committed R4F.3 readiness byte-for-byte): earliest
  ready 2026-03-31, ready 84, blocked 1267, 3Y blocked 644.
- After: earliest ready **2023-03-31**, ready 808, blocked 543, **3Y
  blocked 0 (728/728)** → `THREE_YEAR_HISTORICAL_VALIDATION_READY`.
- 5Y stays BLOCKED (403 blocked days).  Residual 5Y gap plan
  (deterministic subtraction of resolved cells from the R4F.3 baseline):
  original minimum 9 − resolved 5 = **remaining 4** — 2015-12-31 equity,
  2016-12-31 equity+NP, 2017-12-31 NP.
- `full_cycle_proven = false` — unchanged, more history is not proof.

## 5. Independent verification

- 5 cells manually checked against official PDF pages (see reconciliation
  report): value, source report/page, announcement date, effective_from,
  Fact ID, restatement version.
- ROE 2018/2019/2020 recomputed Decimal-only and equal to the resolver
  values exactly.
- All 8 Fact IDs unique and canonical; supersedes chains complete.
- A/B builds byte-identical (7/7 artifacts).

## 6. Validation performed (local)

- R4F3A tests: **46 passed** (upstream gate, calendar registry + overlap,
  source/cache, extraction, PIT, restatement, identity, ROE, readiness,
  boundary).
- R4F3 tests: 45 passed; R4F2: 35 passed; R4F1: 19 passed.
- Full offline suite: **1835 passed, 2 warnings**.
- ruff: All checks passed; compileall: pass; git diff --check: pass.
- Secret/path/pollution scan: clean.
- Default DB SHA unchanged (`4a71d3c7…`); stash preserved; protected
  files untouched; calendar v1 + R4D contracts untouched.

## 7. Boundary preserved

- `pe_numeric_scoring_authorized = false`; PE status
  `coverage_gap_cycle_context_required`; valuation dimension no score.
- No normalized PE percentile; no empirical cycle-guard validation; no
  peer; no M3; no default-DB write; no 5Y financial backfill.
- registry v2 / policy v2 / shadow v6 / sensitivity v8 unchanged.
- No manifest schema registered (stage produces isolated reports only;
  `artifact_manifest = NOT_REQUIRED_R4F3A_REPORT_ONLY`).
