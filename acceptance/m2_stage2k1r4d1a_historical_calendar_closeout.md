# M2 Stage 2K.1R4D.1a — Historical Market Calendar and PIT Time Contract Closeout

Status: `CONDITIONAL PASS — calendar coverage extended through 2026-08-02; 2020 facts
resolved to real next trading days; no backfill; final gate
PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT confirmed after push + reviewer
file review`.

## Scope

R4D.1a is a narrow closeout on top of R4D.1. It does not redo R4D.1 and does not
start the PE/PB/PS series:

1. Extend the verified trading-day calendar so `calendar_start <= 2020-01-01`
   and `calendar_end >= evidence_cutoff (2026-08-02)`.
2. Recompute every 2020 fact's `effective_from`, `effective_from_derivation`,
   calendar object ID and calendar digest.
3. Forbid the backfill fallback (announcement before the calendar's first day →
   first trading day). Correct behavior: insufficient calendar coverage →
   explicit `calendar_coverage_gap` → fail-closed.
4. Tests for: 2020 Q1 → real next trading day; weekend announcement → next
   trading day; holiday announcement crossing suspension; calendar start later
   than announcement fails; no uniform backfill to 2021-01-04; 2020 facts'
   `available_at` unchanged while only `effective_from` is fixed; Fact ID
   migration decided by the identity contract (calendar not an identity field);
   3y/5y readiness recomputed independently.
5. Gap definition updated: before the fix there is at least
   `historical_market_calendar_coverage_gap`; classified
   `economic_fact_gaps` vs `pit_time_contract_gaps`.

Boundaries (unchanged): daily PE/PB/PS series preflight NOT YET; valuation
percentile NOT ALLOWED; valuation shadow update NOT ALLOWED; peer acquisition
NOT ALLOWED; M3 NOT STARTED. The default database is never written.

## Calendar

- Rebuilt the 601857.SH daily market calendar from baostock (a single query,
  `adjustflag='3'` unadjusted, 2020-01-01..2026-08-10). Stored as the
  content-addressed object
  `77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d.parquet`
  under `tmp/market_cache/baostock/`.
- 1597 complete trading days: **2020-01-02 .. 2026-08-05**. The data range
  begins 2020-01-01; the first trading day is 2020-01-02 because 2020-01-01 is
  a statutory holiday.
- Calendar coverage check: `required_start` is the earliest in-scope
  announcement (~2020-04-30, 2020 Q1) and `required_end` is the evidence
  cutoff (2026-08-02). A calendar whose first/last trading day does not cover
  a required boundary fails closed with `CalendarCoverageGapError`.
- The market registry
  (`tmp/market_registry_baostock_only.json`) now points at the extended
  object (2020-01-02..2026-08-05, 1597 rows).

## 2020 facts recomputed

- `next_trading_day` resolves the 2020 Q1/H1/Q3 announcements to real next
  trading days:

  | announcement | available_at | effective_from |
  |---|---|---|
  | 2020-04-30 (Q1) | 2020-04-30 | 2020-05-06 (Wed, after May Day) |
  | 2020-08-28 (H1) | 2020-08-28 | 2020-08-31 (Mon) |
  | 2020-10-30 (Q3) | 2020-10-30 | 2020-11-02 (Mon, after National Day) |
  | 2021-03-26 (annual 2020) | 2021-03-26 | 2021-03-29 (Mon) |

- `available_at` is unchanged (the announcement date); only `effective_from`
  is fixed. No 2020 fact is backfilled to 2021-01-04.
- Every reported/reconciled fact now carries `effective_from_derivation`
  (rule + calendar object + digest + announcement + selected next trading
  day), `calendar_object_id` and `calendar_sha256`.

## Fail-closed (no backfill)

- A calendar whose first trading day is after the announcement raises
  `CalendarCoverageGapError`; the fact's `effective_from` is left unresolved
  and its cell is marked `calendar_coverage_gap` (a `pit_time_contract` gap,
  not an economic-fact gap). The announcement date is never lost and never
  silently replaced by the nearest calendar boundary.
- The pre-fix short calendar (began 2021-01-04) cannot resolve 2020
  announcements and now fails closed instead of producing the old 2021-01-04
  backfill.

## Gap classification

- Gap ledger entries carry `gap_class`: `pit_time_contract` for
  `calendar_coverage_gap`, `economic_fact` for all other gaps.
- `build_readiness` reports `economic_fact_gaps` and `pit_time_contract_gaps`
  separately.
- `decide_from_readiness` fails the gate closed when
  `pit_time_contract_gaps > 0` (the PIT time-contract layer is not trusted),
  returning NOT_TRUSTED. Economic-fact gaps alone keep the gate in
  GAPS_REMAIN territory.
- After the calendar fix the pipeline reports `economic_fact_gaps = 0` and
  `pit_time_contract_gaps = 0`.

## Facts (formal pipeline output with the extended calendar)

- Reported bundle: **127 facts** (112 original + 15 restated).
- Reconciled bundle: **38 facts** (13 Q1/Q3 period-end shares + 25
  weighted-average shares), all `acquired_reconciled_derived`.
- Coverage grid: **150 cells** — 112 `acquired_reported_verified` +
  38 `acquired_reconciled_derived`; **0 gaps**; binding `ok: true, 0 errors`.
- Fact ID migration report: **127 entries, 0 changed**. The calendar (and
  `effective_from`) is not a FactIdentity field, so a calendar coverage fix
  does not change any fact_id.

## Readiness

| Metric | role coverage | 3y | 5y | blockers |
|---|---|---|---|---|
| PE-TTM | net profit 25/25 direct; weighted shares 25/25 derived | READY | READY | — |
| PB-MRQ | equity 25/25 direct; period-end shares 25/25 | READY | READY | — |
| PS-TTM | revenue 25/25 direct; period-end shares 25/25 | READY | READY | — |

Decision: **PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT** (confirmed after
the calendar-fix push + reviewer file review).

## Verification

Executed 2026-08-05 (Windows local):

- Full offline test suite: **1421 passed, 2 warnings** (1409 R4D.1 baseline +
  12 new R4D.1a tests).
- New R4D.1a tests: 12 passed (2020 Q1 next trading day, weekend, May Day /
  National Day holiday crossing, short-calendar fail-closed, no 2021-01-04
  backfill, available_at unchanged / effective_from fixed, fact-id migration 0
  changes, readiness pit-gap fail-closed + no-gap READY).
- `ruff check src/ tests/`: All checks passed.
- `python -m compileall -q src`: pass.
- `git diff --check`: pass.
- Default DB `data/research.duckdb` SHA-256 unchanged
  (`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`).
- Stash preserved (`stash@{0}`). Protected items untouched
  (`acceptance/m2_stage2i2r_*`, `AGENTS.md`, `agent/goals/`).

## Git state

- Branch `feat/m2-value-assessment-mvp`. This accepts the calendar fix and
  evidence; the work record and acceptance doc are committed with it.
- Push planned: 4 commits (4d28d11, 9057494, calendar fix, acceptance/CI
  evidence) + final dual-platform CI.