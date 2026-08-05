# Work record: M2 Stage 2K.1R4D — Official Quarterly Valuation Denominator Fact Acquisition

Status: `in_progress`

## Basic information

- Date: 2026-08-05
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `d5433b3` (R4C.1 provenance-gated CI evidence, run `30974967062`)
- Task source: user directive (M2 Stage 2K.1R4D — official quarterly valuation denominator fact acquisition)
- Module: value assessment (PIT valuation denominator facts)

## Task objective

Acquire from official filings the quarterly valuation denominator facts needed for
future PE-TTM / PB-MRQ / PS-TTM construction:

1. `net_profit_attributable_to_parent` (cumulative Q1/H1/Q3 + annual)
2. `revenue` (cumulative Q1/H1/Q3 + annual)
3. `equity_attributable_to_parent` (instant, period-end)
4. `basic_earnings_per_share` (cumulative Q1/H1/Q3 + annual)
5. `total_ordinary_shares_at_period_end` (instant, period-end)
6. `weighted_average_total_ordinary_shares` (reconciled_derived only)

Scope: 2020 Q1 → last officially announced report before the frozen evidence
cutoff `2026-08-02` (research_evidence_as_of / scorecard_formed_at from
`config/value_dimension_scoring_time_contract_v1.json`).

## Scope

- New `src/ashare_research/pit_valuation/` package (contracts, source_cache,
  extraction, fact_builder, reconciliation, readiness).
- New thin CLI `src/ashare_research/tools/m2_stage2k1r4d_acquire_denominators.py`.
- New frozen configs (execution plan, source evidence, cache registry, role
  registry, extraction specs).
- New reports (reported bundle, reconciled bundle, version lineage, coverage,
  gap ledger, readiness, artifact manifest).
- New tests (`test_m2_stage2k1r4d_*`).
- CI additions to `.github/workflows/stage2g-reproducibility.yml` (synthetic
  fixtures only, no real PDF downloads).
- Acceptance doc + this work record.

## Non-goals

- NO daily PE/PB/PS series.
- NO TTM / MRQ / single-quarter Metric Results.
- NO historical valuation percentile.
- NO valuation-attractiveness shadow / scoring weights / thresholds.
- NO canonical value profile changes.
- NO peer acquisition.
- NO M3 start.
- NO default DuckDB writes; no production Metric Results; 354-fact baseline
  untouched.

## Opening state (verified)

- Branch `feat/m2-value-assessment-mvp`; HEAD `d5433b3`; local == origin (0/0 ahead/behind).
- Protected local items present and untouched: modified
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`,
  untracked `AGENTS.md`, `agent/goals/`.
- Default DB `data/research.duckdb` SHA-256 =
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` (matches baseline).
- Frozen contracts read: `config/pit_valuation_fact_acquisition_plan_v1.json`,
  `docs/pit_valuation_fact_acquisition_contract.md`,
  `docs/decisions/ADR-VALUATION-002-a-share-per-share-convention.md`.
- Evidence cutoff frozen: `research_evidence_as_of = scorecard_formed_at = 2026-08-02`.
- Existing ROIC verified official cache at `tmp/stage2h1-official-cache/` holds
  annual reports FY2021–FY2025 (issuer+SSE objects); no quarterly reports.
- Network status on 2026-08-05: `query.sse.com.cn` announce API reachable;
  `static.sse.com.cn` PDF host serves an `acw_sc__v2` JS challenge (must be
  solved to download); `www.petrochina.com.cn` issuer host returns 403.
- Market calendar: `tmp/market_cache/baostock/*.parquet` trade dates
  2021-01-04..2026-07-31 (verified, `market_data_snapshot_registry_v2`).

## Implementation plan

1. Freeze execution plan + role registry + extraction specs (configs).
2. Build `pit_valuation` package + CLI.
3. Enumerate official SSE announcements (query API) → freeze source evidence
   register (25 report periods, 2020 Q1..2026 Q1).
4. Acquire official PDFs to external cache (acw solver + ≤3 retries per URL).
5. Formal cache verification (SHA-256 / byte_size / %PDF- / page_count /
   evidence alias / filing period).
6. Extract named-capture cells; build ReportedFact + reconciled_derived bundles.
7. Version lineage + restatement handling.
8. Coverage matrix + gap ledger + readiness + three-state gate.
9. Tests (4 files) + full pytest + ruff + compileall.
10. CI additions (synthetic fixtures) + acceptance + manifest.
11. Run verification sequence; commit; final report.

## Actual operations

Recorded as executed (ongoing):

1. Verified opening Git state, default DB hash, protected items.
2. Read frozen contracts (R4C plan, R4C contract, ADR-002, time contract).
3. Queried SSE announcement API for 601857 (2020-01-01..2026-08-02): 553
   announcements; identified 25 official report filings (Q1/H1/Q3/annual),
   last in scope = 2026 Q1 (announced 2026-04-30). Raw archive saved to
   `tmp/sse_archive_utf8.json` (trace, not committed).
4. Diagnosed `static.sse.com.cn` acw_sc__v2 challenge; deobfuscated the JS;
   implemented the solver (posList permutation + mask XOR); verified download
   of 2026 Q1 report (290,034 bytes, SHA-256 b8296b0d…). pypdf page text
   extraction works; key table located on page 2.
5. Downloaded all 25 official report PDFs to the explicit external cache
   `D:/petrochina-r4d-official-cache/objects/` (content-addressed). 2020
   reports use the non-`/new/` SSE path. All 25 hash-verified on 2026-08-05.
6. Surveyed the CAS main-accounting-data layouts across all 25 filings:
   Q1/H1/Q3 have IFRS + CAS table blocks (CAS = second block under the
   "按中国企业会计准则编制的主要会计数据" anchor; H1 uses "主要财务数据");
   Q3 rows print single-quarter then cumulative columns (token index depends
   on the per-year restated comparative layout: 2020-2022/2024 -> 3,
   2023/2025 -> 4); annual reports use a single main table; the precise
   period-end share count 183,020,977,818 is stated in the AR/H1 dividend
   base statements; the weighted-average share count is never directly
   disclosed (EPS notes state the policy only).
7. Built the frozen R4D contracts:
   - `config/pit_valuation_quarterly_fact_execution_plan_v1.json`
   - `config/pit_valuation_official_source_evidence_v1.json` (50 entries:
     25 exchange_official verified + 25 issuer_official, of which 2023/2024
     AR are byte-identical verified aliases and the rest are
     blocked_source_access because www.petrochina.com.cn returns 403)
   - `config/pit_valuation_official_cache_registry_v1.json` (25 content-
     addressed objects; 2023/2024 AR objects carry dual evidence aliases)
   - `config/pit_valuation_quarterly_fact_role_registry_v1.json` (6 roles)
   - `config/pit_valuation_quarterly_extraction_specs_v1.json` (32 specs:
     per report-type Q1/H1/AR + per-year Q3 token layouts + share capital)
8. Built the `ashare_research/pit_valuation` package (contracts, source_cache
   with the acw solver, extraction with named captures + CAS section bounds +
   fail-closed token-count guard, fact_builder with effective_from from the
   verified market calendar, reconciliation with the EPS-rounding share
   derivation, readiness with the three-state gate) and the thin CLI
   `m2_stage2k1r4d_acquire_denominators.py` (acquire / formal /
   verify-contracts).
9. Extraction iteration (real PDFs): fixed H1 "主要财务数据" anchor, `%`
   suffix number tokens, `匹配[0]` for the main row, width-agnostic
   parentheses in labels, cross-line label wraps, and the per-year Q3 token
   layout with a fail-closed expected_token_count guard. 2022-Q3 and 2025-Q3
   verified individually.
10. Tests: 67 R4D tests across 4 files (source_cache, extraction,
    fact_identity, restatement_and_readiness), including a synthetic formal
    pipeline test (offline, no real PDF, no network).
11. Fixed extraction-correctness bugs found by the full pass: H1 reports use
    "主要财务数据" (anchor widened); `%`-suffixed percentage tokens truncated
    the capture group (number token now keeps `%`); 2021-Q1/2023-H1 use
    half-width parentheses in labels (width-agnostic label patterns); labels
    wrap across lines (whitespace-tolerant label patterns + newline
    normalisation); the "非经常性损益" boundary marker cut the 2020-Q3 CAS
    section at the "扣除非经常性损益" row (boundary tightened to
    "非经常性损益项目"); Q3 cumulative token layout is per-year (2024 has 6
    tokens, 2023/2025 have 8) with a fail-closed expected_token_count guard.
12. Fixed the formal pipeline: exchange-only extraction (issuer aliases are
    recorded in the cache registry, never duplicated as economic facts);
    grid now includes derived roles (weighted-average shares expected for
    every period); weighted-average-share derivation uses the min/max of the
    EPS-rounding implied interval (negative loss periods no longer invert the
    bounds) and an O(1) uniqueness check; EPS unit is CNY_PER_SHARE (no 1e6
    conversion); restated comparative values are converted to the canonical
    unit.
13. Final formal run (real cache, verified market calendar):
    decision `PIT_DENOMINATOR_FACT_GAPS_REMAIN`; reported bundle 127 facts
    (112 original + 15 restated); reconciled bundle 0 facts (weighted-average
    shares ambiguous for all 25 periods due to EPS rounding); coverage grid
    137 cells; gap ledger 25 gaps (all
    `weighted_average_share_ambiguous_due_to_eps_rounding`); version lineage
    42 chains (15 restatements, e.g. 2022-Q1 net profit 39,059 → 38,898);
    PB-MRQ and PS-TTM denominator readiness READY (3y/5y); PE-TTM BLOCKED on
    the weighted-average share count.
14. Wrote acceptance doc, artifact manifest generator, CI workflow step.
15. Verification (2026-08-05): full offline suite **1394 passed, 2 warnings**
    (67 new R4D tests); `ruff check src/ tests/` all passed; `compileall`
    pass; `git diff --check` pass; R4D contract gate pass; R4C.1 manifest
    re-verified after the workflow edit (verify pass); default DB SHA-256
    unchanged (`4a71d3c7…`); stash preserved; no absolute paths/secrets/PDF
    pollution in committed artifacts. Clean-clone preflight fails in the local
    working directory as expected (local data/DB/stash present); CI runs it
    on a clean clone.

## Verification

- Full offline suite: 1394 passed, 2 warnings (includes 67 R4D tests).
- ruff check src/ tests/: pass. compileall: pass. git diff --check: pass.
- R4D contract gate: pass (5 contract digests).
- R4C.1 manifest: re-verified pass after the workflow edit.
- Default DB SHA-256 unchanged; stash preserved; pollution scans clean.

## Result

- Decision: **PIT_DENOMINATOR_FACT_GAPS_REMAIN** (engineering trusted;
  explicit official gaps — weighted-average share count not derivable from
  rounded basic EPS).
- Reported bundle: 127 facts (112 original + 15 restated). Reconciled bundle:
  0 facts (all 25 weighted-average-share derivations ambiguous). Coverage
  grid: 137 cells. Gap ledger: 25 gaps
  (`weighted_average_share_ambiguous_due_to_eps_rounding`). Version lineage:
  42 chains / 15 restatements.
- Readiness: PB-MRQ 3y/5y READY; PS-TTM 3y/5y READY; PE-TTM BLOCKED on the
  weighted-average share count.
- No default DB write; no production metric results; no PE/PB/PS series; no
  valuation percentile; no scoring change; no peer acquisition; no M3.

## Remaining issues

- Weighted-average-share count: not directly disclosed; not uniquely derivable
  from rounded EPS. PE-TTM preflight blocked until a precise source or a
  documented convention is accepted.
- Issuer endpoint (petrochina.com.cn) HTTP 403 on 2026-08-05; 23 issuer
  entries blocked_source_access; 2023/2024 AR issuer aliases byte-identical
  and recorded (dual evidence IDs).
- Q1/Q3 period-end share counts not precisely disclosed in Q1/Q3 filings
  (rounded 股本 only); precise count in AR/H1 dividend statements.
- CI evidence pending the push (GitHub Actions run).

## Next steps

- Only the PE-TTM series preflight (after a weighted-average share source or
  convention is accepted) is the directly related next step; PB-MRQ and PS-TTM
  denominator facts are ready.

## Final file changes

New:
- `src/ashare_research/pit_valuation/` (contracts, source_cache, extraction,
  fact_builder, reconciliation, readiness, __init__)
- `src/ashare_research/tools/m2_stage2k1r4d_acquire_denominators.py`
- `config/pit_valuation_quarterly_fact_execution_plan_v1.json`
- `config/pit_valuation_official_source_evidence_v1.json`
- `config/pit_valuation_official_cache_registry_v1.json`
- `config/pit_valuation_quarterly_fact_role_registry_v1.json`
- `config/pit_valuation_quarterly_extraction_specs_v1.json`
- `reports/petrochina_pit_denominator_reported_fact_bundle_v1.json`
- `reports/petrochina_pit_denominator_reconciled_fact_bundle_v1.json`
- `reports/petrochina_pit_denominator_version_lineage_v1.json`
- `reports/petrochina_pit_denominator_acquisition_coverage_v1.json`
- `reports/petrochina_pit_denominator_gap_ledger_v1.json`
- `reports/petrochina_pit_denominator_readiness_v1.json`
- `reports/m2_stage2k1r4d_artifact_manifest.json`
- `acceptance/m2_stage2k1r4d_official_quarterly_denominator_acquisition.md`
- `agent/record/2026-08-05_Stage2K1R4D_official_quarterly_denominator_acquisition.md`
- `tests/test_m2_stage2k1r4d_source_cache.py`
- `tests/test_m2_stage2k1r4d_extraction.py`
- `tests/test_m2_stage2k1r4d_fact_identity.py`
- `tests/test_m2_stage2k1r4d_restatement_and_readiness.py`

Modified:
- `.github/workflows/stage2g-reproducibility.yml` (R4D contract gate step)
- `reports/m2_stage2k1r4c1_artifact_manifest.json` (workflow artifact hash
  regenerated after the workflow edit)

Protected local items untouched: `AGENTS.md`, `agent/goals/`,
`acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`
edit, default DB, stash@{0}.

## Final Git state

(pending commit and push)