# M2 Stage 2K.1R4E.1 — Dual-Source Market Reconciliation, PB Lineage and Release-Gate Closeout

## Verdict: CONDITIONAL PASS (decision `PIT_VALUATION_SERIES_GAPS_REMAIN`)

Pinned AKShare object: **NOT_FOUND** — the exact content object `203ddfd7…` is
absent from every local cache. All engineering defects are closed and tested,
but the real double-source reconciliation cannot be completed locally, so the
release gate honestly stays `GAPS_REMAIN` (formal exit 1).

- PE/PB/PS engineering coverage: **READY / READY on reconciled fixtures** (synthetic dual-source, CI only).
- Formal PE/PB/PS candidate v2: **NOT PUBLISHED** (blocked by missing secondary market object).
- Formal percentile eligibility: **BLOCKED**.

## 1. Scope

This stage tightened the R4E candidate series' market double-source proof, PB
input lineage, CLI exit code contract and artifact manifest. It did **not**
compute historical percentiles, update scoring, redo R4D, or start M3.

## 2. Deliverables

### 2.1 New module — `src/ashare_research/pit_valuation/market_reconciliation.py`

- `load_and_validate_market_object` — independently validates one provider
  object (object key, regular-file existence, real SHA-256, Parquet readability,
  row count, required columns `symbol/trade_date/close/is_trading`, symbol
  `601857.SH`, `adjustment=none`, trade_date uniqueness/ordering, first/last
  date, trading-row count, Decimal-parseable closes). Never substitutes another
  Parquet, never trusts a pre-written registry `pass`, never checks only the SHA.
- `reconcile_market_close_series` — exact `trade_date` alignment, canonical
  Decimal daily close comparison (`Decimal(str(...))`; `float(...)` and
  `Decimal(binary_float)` prohibited), recomputing primary/secondary/common
  trade days, both-only dates, per-day closes, `max_abs_difference`,
  `nonzero_difference_count`, `differences_over_tolerance_count`. Tolerance
  `0.01 CNY/share` read from the versioned formula-registry contract.
- `build_mismatch_ledger`, `build_reconciliation_digest`,
  `build_reconciliation_report`, `validate_reconciliation_report` — the ledger
  of over-tolerance differences and a digest binding both object SHAs, row
  counts, date ranges, tolerance, date-set summary, daily close-comparison
  summary, ledger digest and contract version.

Fail-closed: missing object → `MarketObjectMissingError` (GAPS_REMAIN); any
invalid object / date-set / schema / close conflict →
`PIT_VALUATION_SERIES_NOT_TRUSTED`.

### 2.2 PB complete-input lineage — `financial_state.py`

Each PB state now binds the complete equity + period-end-share input Facts:
`equity_fact_id`, `period_end_shares_fact_id`, `input_fact_ids` (both, sorted),
both inputs' `available_at`/`effective_from`, `available_at_max` and
`effective_from` as the maximum of the two inputs, the same `period_end`, the
same PIT-visible reporting context, and the share-continuity proof id. Share
selection is deterministic (supersession/PIT, never list order) and fails closed
on ambiguity. A share Fact not yet visible keeps the PB state from going
effective early → `unmatched_equity_share_context`.

### 2.3 Fail-closed CLI exit codes — `m2_stage2k1r4e_series_preflight.py`

`decision_to_exit_code` freezes 0 = ALLOWED, 1 = GAPS_REMAIN, 2 = NOT_TRUSTED /
any contract/input/schema/hash/internal failure. Formal behavior:
- A. secondary pinned object absent → gap decision, no candidate v2, exit 1;
- B. secondary present but hash/schema/date/close fails → NOT_TRUSTED, exit 2;
- C. full double-source gate passes → candidate v2 + all reports, ALLOWED, exit 0.

`--output-root` never swallows the real exit code; fixtures uses the same map.
Structured error output carries `status / decision / exit_code / failed_contract /
error_type / message`.

### 2.4 Verifiable artifact manifest v2

`artifact_manifest.py` now accepts `m2_stage2k1r4e1_artifact_manifest_v2`
(added to the allow-list and `V2_SCHEMAS`). The CLI writes a real manifest with
LF-normalized digests, no self-inclusion, repo-relative logical paths, no `..`,
no duplicate paths, and a separately computed `manifest_digest`, then verifies
it with the real verifier.

## 3. Validation

- Full offline suite: **1509 passed, 2 pre-existing warnings**.
- R4E 42 + R4E.1 34 tests pass; R4D/R4D.1/R4D.1a/R4D.1b protected tests pass.
- ruff (all changed files): All checks passed; compileall pass; `git diff --check` pass.
- Fixtures (CI synthetic dual-source) CLI: decision
  `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`, exit 0,
  manifest v2 `pass` (9 files), dual oracle identical, **engineering** coverage
  READY/READY (synthetic only), identity migration: PB & observation ids
  changed, ratios & status unchanged, non-production unchanged.
- Formal (real cache, akshare missing): decision `PIT_VALUATION_SERIES_GAPS_REMAIN`,
  exit 1, no candidate v2 published, structured gap error emitted. The fixture
  ALLOWED result is **synthetic-engineering evidence only** and never substitutes
  for the real-data gate.
- Real `reports/m2_stage2k1r4e1_decision.json` + v2 manifest verified `pass`.

## 4. Product boundary

No percentile computed; no shadow / sensitivity modified; no production Metric
Result; default DB unchanged (`4a71d3c7…`); no peer acquisition; M3 not started;
R4E v1 artifacts preserved.

## 5. Known limitation

The real double-source reconciliation (and therefore the real candidate v2,
identity-migration and reconciliation reports) is **blocked** until the pinned
AKShare object `203ddfd7…` is recovered into the market cache. The fixtures path
demonstrates the full mechanism with synthetic dual-source data only.

## 6. Decision

`PIT_VALUATION_SERIES_GAPS_REMAIN` — formal exit code 1.
Historical percentile preflight: **NOT YET**.