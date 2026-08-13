# M2 Stage 2K.1R4F.4A1 acceptance

Status: PASS — LOCAL CANDIDATE; closeout authorized; remote CI pending.

## Task contract

- Objective: acquire exactly the four frozen 5Y logical cells from SSE official annual reports, preserve PIT/restatement lineage, recover full frozen-5Y normalized-earnings readiness, and derive 5Y episode/outcome-readiness metadata without reading future EPS values.
- Verified baseline: `feat/m2-value-assessment-mvp` at `284d3081e9ff9b58a740d1e63a61e0aace58c8c9`; origin synchronized; R4F.4A final-tip CI run 31250897525 succeeded.
- Allowed scope: R4F.4A1 contracts, source/cache/extraction metadata, side-by-side historical calendar, narrow generic episode/readiness helpers, isolated bundle/overlay/reports, thin offline CLI, tests, docs, acceptance, and work record.
- Forbidden scope: upstream R4F3/R4F3A/R4F4/R4F4A artifacts or contracts, existing calendar pin, protected scoring artifacts, default DB, 2014-or-earlier economic facts, future outcome values, Brent, PE percentiles, scoring, production results, M3, commit, and push.
- Required behavior: canonical aliases only; exact four-cell dependency; SSE primary evidence; actual SSE announcement metadata; version chains; next-trading-day PIT; Decimal ROE; 1211/1211 readiness; window-first episode derivation; metadata-only 4Q/8Q maturity; frozen-5Y stop rule.
- Required tests: upstream/alias/source/calendar/extraction/restatement/context/ROE/readiness/backward-compatibility/episode/outcome/stop-rule/boundary tests, A/B byte identity, full regression, Ruff, compileall, diff check, secret/path/pollution scan, protected hashes, default DB, stash, and worktree audit.
- Exact validation commands: recorded after implementation in this file and the stage work record.
- Acceptance: all four cells trusted, no unresolved source/calendar/PIT conflict, deterministic artifacts, upstream artifacts byte-identical, no future leakage, no scoring change, and exact decision gate.
- Stop conditions: stop locally after validation; no commit/push; no future outcome execution; no next stage; no automatic extension beyond 5Y.

## Result

**PASS**

Closeout state: `PASS — LOCAL CANDIDATE`; Remote CI: `PENDING`.

- Upstream R4F.4A: trusted; committed decision and three 3Y artifacts verified.
- Target logical cells: 4/4 resolved using canonical concepts only.
- Official evidence: 6/6 pinned SSE annual-report objects verified; 2017 object
  identity reused from R4F.3A.
- Actual Fact records: 4; restatement versions: 0; ambiguity/conflict: none.
- Side-by-side calendar: 2016-01-04..2026-08-07; old overlap 2330 and new
  overlap 2330; missing/extra/target PIT gaps = 0/0/0.
- ROE 2016: `0.006668672896107563161406786092`.
- ROE 2017: `0.01913624531469271226661618072`.
- Frozen 5Y: 1211/1211 ready, 0 blocked; no forward fill.
- Episode result: 1 candidate regime, 0 observed onsets, 1 left-censored
  regime, 0 valid onset-anchored episodes.
- Outcome metadata: protocol-valid mature +4Q/+8Q = 0/0; no future EPS value
  read.
- Decision:
  `PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY`.
- Reason: `NO_OBSERVED_ONSET / LEFT_CENSORED_REGIME`.
- Stop rule: `STOP_FOR_NORTH_STAR_REVIEW`; no >5Y extension, Brent, scoring,
  production result, or outcome-validation stage. Machine-readable next stage:
  `NONE_PENDING_NORTH_STAR_REVIEW`.

## Validation evidence

Exact commands and results:

1. `python src/ashare_research/tools/m2_stage2k1r4f4a1_pe_5y_historical_backfill.py external-verify`
   — 6/6 official PDF objects PASS.
2. `python src/ashare_research/tools/m2_stage2k1r4f4a1_pe_5y_historical_backfill.py build --output-root tmp/r4f4a1_build_a`
   and the same command for `build_b`, followed by SHA-256 comparison — 11/11
   artifacts byte-identical.
3. `python src/ashare_research/tools/m2_stage2k1r4f4a1_pe_5y_historical_backfill.py verify`
   — 11/11 committed-stage outputs PASS.
4. `python src/ashare_research/tools/m2_stage2k1r4f4a_independent_cycle_validation_preflight.py verify`
   — all three protected 3Y outputs PASS.
5. `python -m pytest tests/test_m2_stage2k1r4f4a1_pe_5y_historical_backfill.py -q`
   — 21 passed.
6. `python -m pytest` over R4F.4A1, R4F.4A, R4F.4, R4F.3A, R4F.3,
   R4F.2, and R4F.1 suites — 236 passed.
7. `python -m pytest -q` — 1926 passed, 2 pre-existing pandas date-parser
   warnings.
8. `python -m ruff check src tests` — PASS.
9. `python -m compileall -q src tests` — PASS.
10. `git diff --check` — PASS.
11. Secret and absolute-path scans over all new stage files — PASS (22 files).
12. Protected tracked artifacts checked with `git diff --exit-code HEAD -- ...`
    — unchanged; scoring-related tracked paths have zero diff.
13. `data/research.duckdb` SHA-256 remains
    `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
14. Branch/HEAD remain `feat/m2-value-assessment-mvp` /
    `284d3081e9ff9b58a740d1e63a61e0aace58c8c9`; local/origin = 0/0;
    stash remains unchanged.

External PDFs and the extended parquet remain gitignored external-cache
objects. Temporary visual-QA renders and A/B output roots were removed after
verification.
