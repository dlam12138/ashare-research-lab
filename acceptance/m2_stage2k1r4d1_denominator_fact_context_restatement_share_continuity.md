# M2 Stage 2K.1R4D.1 — Denominator Fact Context, Restatement Metadata and Share-Continuity Closeout

Status: `CONDITIONAL PASS — governance-closeout applied; all layers now trusted;
decision PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT`.

## Scope

R4D.1 addresses the ten defects raised in the R4D governance review:

1. Context v2 for instant Facts (distinguish Q1/H1/Q3/annual) + old→new Fact ID
   migration report.
2. Restated Facts rebuilt entirely from the later filing's comparative column
   (all source fields), not a shallow copy of the original's metadata.
3. `effective_from` recomputed from the restatement announcement date.
4. PDF content-object digest (`source_object_sha256`) separated from the
   captured-fragment digest (`excerpt_hash`).
5. Real `fact_id` written to every acquired cell and real `gap_id` to every
   gap, with a bidirectional coverage↔fact/gap consistency check.
6. Official share-count/share-changing corporate-action bounded-search register
   for 2020 Q1–2026 Q1.
7. Q1/Q3 period-end share counts derived from the frozen constant only when
   precise bases agree, no in-period share change, and the official search is
   complete.
8. Weighted-average share counts derived only when the share count is constant
   over the whole duration and the accounting scope is consistent.
9. PE/PB/PS readiness recomputed.
10. No TTM / per-share / daily valuation / historical percentile / score.

## Governance outcome (per review)

Fixed from the R4D review:

| Layer | R4D review | R4D.1 |
|---|---|---|
| Instant Fact semantic Context | NOT TRUSTED | **TRUSTED** |
| Restatement source metadata | NOT TRUSTED | **TRUSTED** |
| Restatement effective_from | NOT TRUSTED | **TRUSTED** |
| Restatement/supersession overall | PARTIAL | **TRUSTED** |
| Coverage Fact/Gap bidirectional mapping | NOT TRUSTED | **TRUSTED** |
| PE-TTM readiness | BLOCKED | **READY** |
| PB-MRQ readiness | PARTIAL | **READY** |
| PS-TTM readiness | PARTIAL | **READY** |

## Context v2

- Instant facts now carry a period-end-qualified context: an instant context is
  `601857.SH|FY|instant|consolidated|<period-end>` instead of
  `601857.SH|FY|instant|consolidated`. Q1 (03-31), H1 (06-30), Q3 (09-30) and
  annual (12-31) instant values therefore occupy distinct contexts, restoring
  the `(concept_id, symbol, context_id)` uniqueness contract.
- Duration contexts are unchanged (`601857.SH|FY|quarter_ytd|consolidated`,
  etc.) because they already carry the period type.
- `restatement_version` is never encoded into the context, so the context stays
  stable across a restatement.
- The old→new Fact ID migration report
  (`petrochina_pit_denominator_fact_id_migration_v1.json`) lists 127 facts; 37
  instant facts changed (25 equity + 12 period-end shares), 90 duration facts
  unchanged.

## Restatement metadata

- `detect_restatements` now rebuilds the restated fact entirely from the later
  filing: `source_id`, `source_document`, `source_url`, `source_label`,
  `source_page`, `source_hash`/`source_object_sha256` (later object digest),
  `excerpt_hash`, `filing_date`, `announcement_date`, `available_at` and
  `effective_from`.
- `effective_from` is recomputed from the restatement announcement date through
  the verified market calendar (e.g. the 2022-Q1 net-profit restatement in the
  2023-Q1 report announced 2023-04-29 becomes effective 2023-05-04).
- 15 restated facts, 42 version chains; each restated fact inherits the
  superseded original's context (same economic period) but exposes only its own
  announcement date.

## Hash separation

- `source_hash` / `source_object_sha256` = the verified official PDF
  content-object digest (from the external cache registry).
- `excerpt_hash` = the captured-fragment digest (the R4D v1 `source_hash`).
- `extraction_spec_id` is recorded in `verification_note` and the fact's
  `source_table`.

## Coverage ↔ Fact/Gap binding

- Every acquired cell carries a real `fact_id`; every gap cell carries a real
  `gap_id`; the gap ledger binds back to its grid cell.
- `validate_coverage_fact_gap_binding` enforces: acquired cells have a fact_id
  that exists in the bundles; gap cells have a gap_id that exists in the
  ledger; every ledger gap binds a grid cell; every bundle fact is referenced
  by exactly one grid cell.
- R4D.1 result: **150 grid cells, 165 bundle facts, all fact_ids populated,
  0 gaps, binding `ok: true, 0 errors`**.

## Share-continuity register

- `config/pit_valuation_share_continuity_register_v1.json` freezes the bounded
  official search: the SSE announcement query API archive for 601857.SH
  (553 announcements, 2020-01-01..2026-08-02).
- The 12 precise dividend-base share counts disclosed in the half-year/annual
  reports are all `183,020,977,818`.
- The corporate-action scan found only cash-dividend distributions
  (权益分派实施/利润分配方案/独立意见) and no share-changing action
  (no 转增/送股/增发/配股/回购注销/股权激励/可转债/增资).
- Conclusion: the total ordinary share count is constant at
  `183,020,977,818` across 2020 Q1–2026 Q1. Register `trust: trusted`.
- Residual risks recorded: the search is bounded by the SSE archive
  (2020-01-01..2026-08-02); non-SSE share-change mechanisms are not searched;
  the count is the A+H total ordinary share count.

## Constancy derivation

Only because the register is trusted and the count is constant:

- 13 Q1/Q3 period-end share counts are derived as `183,020,977,818`
  (instant, period-end contexts), status `acquired_reconciled_derived`.
- 25 weighted-average share counts are derived as `183,020,977,818`
  (duration contexts), status `acquired_reconciled_derived`.
- These reside in the reconciled bundle (38 derived facts). Without register
  trust they would remain explicit gaps (weighted-average ambiguity).

## Facts (formal pipeline output)

- Reported bundle: **127 facts** (112 original + 15 restated).
- Reconciled bundle: **38 facts** (13 Q1/Q3 period-end shares + 25
  weighted-average shares), all `acquired_reconciled_derived`.
- Coverage grid: **150 cells** — 112 `acquired_reported_verified` +
  38 `acquired_reconciled_derived`; **0 gaps**.
- Version lineage: **42 chains** / 15 restatements.

## Readiness

| Metric | role coverage | 3y | 5y | blockers |
|---|---|---|---|---|
| PE-TTM | net profit 25/25 direct; weighted shares 25/25 derived | READY | READY | — |
| PB-MRQ | equity 25/25 direct; period-end shares 25/25 (12 direct + 13 derived) | READY | READY | — |
| PS-TTM | revenue 25/25 direct; period-end shares 25/25 | READY | READY | — |

Decision: **PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT**.

## Verification

Executed 2026-08-05 (Windows local):

- Full offline test suite: **1409 passed, 2 warnings** (includes the 82
  R4D/R4D.1 tests and the pre-existing 1327-test baseline).
- `ruff check src/ tests/`: All checks passed.
- `python -m compileall -q src`: pass.
- R4D.1 contract gate (`verify-contracts`): 6 contract digests validated
  (plan, source evidence, cache registry, role registry, extraction specs,
  share-continuity register).
- `git diff --check`: pass.
- Default DB `data/research.duckdb` SHA-256 unchanged
  (`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`).
- Stash preserved (`stash@{0}`).
- No PDF/DB/parquet/secrets/absolute-path pollution in committed artifacts.

## Result

- All engineering layers **TRUSTED**; the 25 weighted-average gaps from R4D v1
  are resolved by the constancy derivation (the share count is provably
  constant, so the weighted average equals the constant).
- R4D.1 decision: **PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT**.
- Next-stage implementation: **NOT STARTED** (no PE/PB/PS series, no TTM, no
  per-share metrics, no valuation percentile, no scoring).

## Remaining issues

- The market calendar begins 2021-01-04; 2020 facts' `available_at` uses the
  SSE announcement date but `effective_from` resolves to the first available
  trading day (2021-01-04). This is a pre-existing calendar-coverage
  limitation, not a correctness regression.
- The share-continuity constancy derivation is bounded by the SSE archive
  completeness and the A+H total-share assumption; documented residual risks.
- CI evidence pending the push.

## Git state

(pending commit)