# PE Normalized-Earnings Prototype and Validation Protocol

M2 Stage 2K.1R4F.3 — PIT normalized-earnings prototype + historical
cycle-guard validation readiness (non-scoring)

## 1. Scope of this stage

R4F.2 (method preflight) decided that `AVERAGE_ROE_X_CURRENT_BVPS` is
`ELIGIBLE_FOR_PROTOTYPE`.  This stage implements that method as a formal
**non-scoring** prototype at 2026-07-31, proves via deterministic property
tests that the normalized denominator removes the direct mechanical
dependence of PE on current TTM EPS, and builds the historical PIT
readiness matrix that decides whether 3y / 5y historical cycle-guard
validation can even start.

It deliberately does **not**:

- restore `va_pe` numeric scoring (stays `coverage_gap_cycle_context_required`);
- modify registry/policy v2, shadow v6, sensitivity v8, or create
  registry v3 / policy v3 / shadow v7 / sensitivity v9;
- create a cycle-peak classifier or any normalized-PE percentile / score;
- fetch facts over the network (backfill is a separate authorized stage,
  R4F.3A).

## 2. Frozen contract

`config/pe_normalized_earnings_prototype_contract_v1.json`

```
contract_id            pe_normalized_earnings_average_roe_v1
symbol                 601857.SH
primary_method         AVERAGE_ROE_X_CURRENT_BVPS
minimum_consecutive_annual_roe  5

normalized_eps(as_of) =
  mean(five most recent eligible consecutive annual ROE visible at as_of)
  × current PIT BVPS(as_of)

annual ROE:
  average_equity_y = (begin_parent_equity_y + end_parent_equity_y) / 2
  roe_y            = parent_net_profit_y / average_equity_y

current BVPS = latest PIT parent equity / company-wide ordinary shares
```

Arithmetic rules: `Decimal(str(...))` only; no `Decimal(float)`, no float
aggregation, no pre-rounding, no winsorize / trim / manual year exclusion.
PIT gate: `available_at <= as_of AND effective_from <= as_of`; array order
never decides visibility.  Restatement gate: latest visible
`effective_from` wins; a tie is resolved deterministically via the
`supersedes_fact_id` chain, otherwise the state fails closed.

## 3. The 5-year contract is a hard boundary

`minimum_consecutive_annual_roe = 5` is frozen (R4F.2).  For historical PIT
dates with only 4 or 3 annual ROE observations the status is
`BLOCKED_INSUFFICIENT_ROE_HISTORY`.  The contract is **never** shortened to
a 3y / 4y average or an expanding-average-with-minimum-2 to manufacture
more historical points; a diagnostic `available_roe_count` may be reported,
but the denominator contract does not change.

## 4. Current prototype (2026-07-31)

Reconstructed from the committed facts through the PIT resolver (no
R4F.2-string copying):

| Field | Value |
|---|---|
| ROE 2021 | `0.07434629055079871379731497929` |
| ROE 2022 (restated, as-of) | `0.1129630958714448405117204395` |
| ROE 2023 (restated, as-of) | `0.1146411949491226163766439180` |
| ROE 2024 | `0.1112006593330161818176293251` |
| ROE 2025 | `0.1014383033385868205396732864` |
| average ROE | `0.1029179088085938346085963897` |
| current parent equity (2026-03-31 MRQ) | `1,624,532,000,000` |
| company-wide shares | `183,020,977,818` |
| current BVPS | `8.876206538550294436827638346` |
| **normalized EPS** | `0.9135206151007635380066173292` |
| prototype status | `TRUSTED_NON_SCORING` |

Every observation carries its Fact IDs (`np_fact_id`, `begin_equity_fact_id`,
`end_equity_fact_id`, `current_equity_fact_id`, `share_fact_id`), and the
state digest binds exactly those identities — never timestamps, machine
names, absolute paths or output directories.

## 5. Current normalized PE

Using the **same** A-share close as the R4E.4 candidate `PE_A_TTM`
2026-07-31 observation (11.08, market reconciliation digest
`4fb3382b…`, observation `98d47da1…`), recomputed from its frozen market
object — never back-derived from PE × EPS:

- raw PE (TTM) = close / current TTM EPS =
  `12.81970638132453345471096950` — **exactly** the candidate ratio.
- normalized PE (ROE) = close / normalized EPS =
  `12.12889979366021109951970404`.
- earnings normalization ratio = TTM EPS / normalized EPS =
  `0.9461136965920940114716739512`.
- raw-to-normalized PE ratio = `1.056955420476423401383024263`.

All are descriptive diagnostics.  No `cheap / expensive / undervalued /
overvalued / cycle top / cycle bottom` output.

## 6. Mechanical-inversion property

`reports/petrochina_pe_mechanical_inversion_audit_v1.json`

Fixed: price, historical 5y ROE chain, current BVPS, normalized EPS.
Shocked: only current TTM EPS, by pure-test multipliers 0.5 / 1.0 / 2.0
(math only, no business threshold meaning).

| EPS shock | raw PE | normalized PE | state ID |
|---|---|---|---|
| 0.5× | 25.6394… | 12.1289… | same |
| 1.0× | 12.8197… | 12.1289… | same |
| 2.0× | 6.4099… | 12.1289… | same |

- `raw_pe_changed = true`
- `normalized_pe_changed = false`
- `direct_current_earnings_denominator_dependence_removed = true`
- `cycle_stage_identified = false` — the property proves only that the
  normalized denominator does not read current TTM earnings; it does **not**
  prove that average ROE is mid-cycle earnings, that normalized PE identifies
  a cycle top, that normalized-PE scoring is better, or that the gate should
  be lifted.
- `cycle_guard_empirically_validated = false`

## 7. Historical PIT readiness

Walk-forward principle: for every trade date T in 2021-01-04..2026-07-31,
only facts with `effective_from <= T AND available_at <= T` are visible.
No look-ahead; no forward fill; a BLOCKED day never inherits a later READY
state.

Result (1351 candidate trade days):

- prototype-ready days: **84** — exactly the range
  **2026-03-31..2026-07-31** (2025 annual report becomes visible on
  2026-03-31, completing the 2021..2025 ROE chain);
- blocked days: 1267, all for `insufficient_roe_history`;
- verdicts:
  - `CURRENT_ASOF_READY = true`
  - `3Y_HISTORICAL_VALIDATION_READY = false` (644 of 644 required trade days
    from 2023-07-31 are blocked)
  - `5Y_HISTORICAL_VALIDATION_READY = false` (1127 of 1127 required trade
    days from 2021-08-02 are blocked)
  - `FULL_CYCLE_VALIDATION_READY = false` (no independent full-cycle proof)

This is **not** a stage failure: the current prototype is trusted while
historical validation has fact gaps —
`CURRENT_PROTOTYPE_TRUSTED, HISTORICAL_VALIDATION_FACT_GAPS_REMAIN`.

## 8. Exact fact gap plan

`reports/petrochina_pe_normalized_earnings_historical_fact_gap_plan_v1.json`

### MINIMUM_3Y_BACKFILL (target 2023-07-31)

Required ROE years: 2018, 2019, 2020, 2021, 2022.  Missing facts (5):

- 2017-12-31 `equity_attributable_to_parent` (opening equity of the 2018 ROE)
- 2018-12-31 `equity_attributable_to_parent`, `net_profit_attributable_to_parent`
- 2019-12-31 `equity_attributable_to_parent`, `net_profit_attributable_to_parent`

### MINIMUM_5Y_BACKFILL (target 2021-08-02)

Required ROE years: 2016, 2017, 2018, 2019, 2020.  Missing facts (9):

- 2015-12-31 `equity_attributable_to_parent` (opening equity of the 2016 ROE)
- 2016-12-31 / 2017-12-31 / 2018-12-31 / 2019-12-31
  `equity_attributable_to_parent` + `net_profit_attributable_to_parent`

All missing facts require source tier `exchange_official` with PIT
announcement / effective dates <= the target trade date; values are
re-verified at acquisition time (R4F.3A).  The plan proves the coverage
path, never invents provider values.  **Priority: satisfy the 3y window
first** (Section 十四) — if the 3y prototype validation itself fails, the
full 5y backfill is never needed.

## 9. What the future validation protocol will verify

Once facts are sufficient, for each historical PIT trade date the
validation constructs raw PE / normalized PE / current-EPS-to-normalized-EPS
and verifies at least:

1. raw PE has the mechanical inverse dependence on current-EPS shocks;
2. normalized PE is invariant to those direct shocks;
3. on annual-report rollover the normalized denominator changes only from
   the effective date onward;
4. restatements never back-fill;
5. the normalized denominator never reads future years;
6. the normalized PE series has no identity-bug discontinuities.

Not verified (ever, under the North Star): "can it predict future returns".
This is not a price-prediction model.

## 10. Decision

`PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN`
(CONDITIONAL PASS):

- current prototype trusted (`TRUSTED_NON_SCORING`);
- mechanical inversion property PASS;
- historical PIT engine trusted (future-fact / later-restatement / array
  order disturbances all proven inert);
- 3y history coverage insufficient → exact fact gap plan frozen;
- next stage `R4F.3A — Historical Annual Fact Backfill` (NOT STARTED).

PE numeric scoring remains **BLOCKED_UNCHANGED**; valuation dimension has
no numeric score; production scoring NOT AUTHORIZED; overall score
PROHIBITED.  **METHOD READY ≠ SCORING READY.**
