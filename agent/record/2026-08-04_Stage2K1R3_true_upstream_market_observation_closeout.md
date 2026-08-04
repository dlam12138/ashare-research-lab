# Work record: M2 Stage 2K.1R3 — True Upstream Record Binding and Verified Market Observation-Set Closeout

Status: `complete`

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `ccc8954`
- Task source: user directive (M2 Stage 2K.1R3 — True Upstream Record Binding and Verified Market Observation-Set Closeout)
- Module: value assessment (scoring addendum) / engineering governance

## Objective

Finite contract correction over Stage 2K.1R2. Fix four problems:
1. Every scoring component truly binds to upstream *records*, not just a file.
2. Validator regenerates transform inputs from upstream records (does not trust capsule inputs).
3. Source tier is derived by the resolver, not self-reported by the capsule.
4. Valuation percentiles use a real market cache to build observation-set identity.

Preserve the honest business conclusion unless the fixed result independently
proves otherwise. No peer acquisition, no production scoring, no M3.

## Expected final business conclusion (to be preserved unless independently proven)

- `SCORING_CONTRACT_GAPS_REMAIN`
- Sensitivity stability: `NOT_STABLE`
- Peer benchmark acquisition: `NOT ALLOWED`
- Production scoring: `NOT ALLOWED`

Engineering contract PASS must not automatically change these.

## Verified opening state (snapshot)

- Branch `feat/m2-value-assessment-mvp`; HEAD `ccc8954` == origin (ahead 0, behind 0).
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` (unchanged).
- Stash: `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` (Stage 1B.4 record edit).
- Protected untracked: `AGENTS.md`, `agent/goals/`.
- Protected unstaged edit: `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md` (pre-existing wording).
- `.codex/` does NOT exist locally; `.claude/` and `.git/hooks/` empty (Stop Hook is external).
- Stage 2K/2K.1R/2K.1R2 artifacts present (capsule v2, shadow v3, sensitivity v3).
- `src/ashare_research/scoring/` does NOT exist (to be created).
- `src/ashare_research/reproducibility/market.py` exists (MarketSnapshotResolver).

## Scope

- Unified upstream registry + typed ResolvedRecord + per-type resolvers.
- Pure-function transform registry (Decimal).
- Capsule v3 from registry → resolver → transform.
- Validator recomputes from upstream records (never trusts capsule inputs).
- Source-tier derived by resolver, bound into confidence.
- Real market observation-set from external cache (synthetic for CI).
- Acceptance, old→new diff, manifest, tests, verification gates.

## Non-goals

- No peer data acquisition, no production scoring, no score weight/threshold
  changes, no stability_tolerance relaxation, no manual score preservation.
- No modification of scoring dimensions, weights, or thresholds.
- No writing to canonical value profile or Metric Result registry.
- No overall score, ranking, recommendation, target price, position, or signal.
- No M3, no main merge, no PR/tag/release, no force push, no reset --hard, no git clean -fd.
- No modification of default DB, protected baselines, protected files, or the
  pre-existing Stage 2I.2R wording edit. No staging of AGENTS.md / agent/goals/.
- No `.codex/` / `.claude/` / git hook creation. Stop Hook is external
  (`STOP_HOOK_STATUS=NOT_TRUSTED_EXTERNAL`).
- No copying of R2 modules into R3; R2 modules kept as history.

## Implementation plan

1. Verify opening state (done).
2. Map real upstream schemas (fixtures, dividend events, value profile risk
   profile, gap ledger, repurchase scan, market registry).
3. Create `scoring` package + ResolvedRecord + per-type resolvers (lineage.py).
4. Create transform registry + pure-function transforms (transforms.py).
5. Create upstream registry config (24 components).
6. Create Capsule v3 builder (registry → resolver → transform → ScoreInput).
7. Create validator (recompute from upstream; composite tamper test).
8. Create market observation-set builder (real external cache + synthetic).
9. Create confidence v3 (binds validated lineage tier).
10. Create shadow v4 + sensitivity v4.
11. Create closeout CLI orchestrator.
12. Write acceptance, old→new diff, manifest.
13. Write tests.
14. Run verification gates in order + CI + final report.

## Decision log

- **Multi-source canonical fact resolver**: `canonical_fact_bundle_resolver`
  resolves each fact from the first source that contains it (annual vs
  supplemental), with year-tagged field paths (`/facts/{concept}/{fy}`) so
  transforms distinguish 2024 vs 2025. Adopted because facts like
  `operating_cost` live only in the earnings-quality supplemental, not the
  annual bundle. Alternative rejected: per-source hardcoded fact lists (not
  data-driven).
- **Dual-supplier fact extraction**: `_facts_recursive` handles both the flat
  annual structure and the company/exchange nested structure (capex_cash
  fixture uses `cash_paid_for_fixed_assets`). Capex concept remapped in the
  registry to `cash_paid_for_fixed_assets`.
- **Dividend event records**: one `ResolvedRecord` per concept per event
  (`/events/{id}/cash_dividend_per_share` and `/cash_dividend_total`) so
  coverage transforms sum across the interim+final events. `_sum_operands`
  sums all matching records; `_operand` returns a single record.
- **Risk count semantics**: `risk_observed_count_v1` excludes `not_observed`
  (so `rk_veto_triggered`=0); `risk_missing_count_v1` counts only `missing`
  (so `rk_missing_evidence_slots`=2). Fixed a substring bug where
  `"observed" in "not_observed..."` was true.
- **Gap PIT**: gap records use the time-contract `research_evidence_as_of`
  (2026-08-02) as `available_at`, not the ledger regeneration date (08-04),
  so gap evidence is PIT-valid. PIT comparison is date-only (strips
  `T06:30:00+08:00`).
- **Real-mode percentile**: the real-cache observation set recomputes the
  close percentile (3y/5y date-windowed). The real-mode capsule uses it for
  price-multiple metrics (PE/PB/PS, where ratio percentile = close percentile);
  yield metrics (FCF/dividend) are `not_cache_recomputable_yield_series` and
  stay coverage gaps. Never falls back to committed percentiles.
- **Validator recomputes the whole score input**: the shared `_make_score_input`
  builds the score input from recomputed upstream records; the validator
  compares the recomputed `score_input_id`/value/source_tier to the capsule.
  The capsule's `resolved_records` snapshot is ignored (upstream is the source
  of truth).

## Actual operations

1. Verified opening state (HEAD `ccc8954`, DB `4a71d3c7`, stash `cb568efd`,
   protected AGENTS.md / agent/goals/ / Stage 2I.2R edit).
2. Created `src/ashare_research/scoring/` package: `__init__.py`, `lineage.py`
   (ResolvedRecord + per-type resolvers), `transforms.py` (pure Decimal
   transforms), `market_observation_set.py` (real-cache observation-set builder).
3. Generated `config/value_dimension_scoring_upstream_registry_v1.json` (24
   components) via `tmp/stage2k1r3_gen_registry.py`.
4. Created `config/value_dimension_scoring_transform_registry_v2.json`.
5. Created `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (capsule v3
   builder, fail-closed validator, confidence v3, shadow v4, sensitivity v4,
   CLI with resolve/build-capsule/validate/build-market-observation-set/
   build-confidence/build-shadow/build-sensitivity/verify-artifacts).
6. Fixed resolver/concept/semantics issues found by running the pipeline
   (see Decision log).
7. Built the real cache in tmp (copied the committed baostock parquet to a
   tmp cache root; created a baostock-only registry in tmp because the akshare
   provider snapshot is not in the repo).
8. Generated committed reports: capsule v3, confidence v3, shadow v4,
   sensitivity v4, real observation-set manifest v2, artifact manifest,
   old→new diff.
9. Wrote `tests/test_m2_stage2k1r3_true_upstream_capsule.py` (22 tests) and
   `tests/stage2k1r3/test_composite_tamper.py`.
10. Wrote this acceptance file.

## Verification

- `pytest tests/ -q` → **1130 passed** (full suite; includes the 22 new 2K.1R3 tests).
- `pytest tests/test_m2_stage2k1r3_true_upstream_capsule.py -q` → **22 passed**.
- `python tests/stage2k1r3/test_composite_tamper.py` → **ALL PASS** (baseline +
  tamper of inputs/value/source_tier/score_input_id/removed-component/gap-count
  all fail closed; capsule record snapshot ignored in favor of upstream).
- `ruff check src/ashare_research/scoring/ src/ashare_research/tools/m2_stage2k1r3_closeout.py tests/test_m2_stage2k1r3_true_upstream_capsule.py tests/stage2k1r3/` → **All checks passed**.
- Real-mode pipeline: `build-capsule --market-cache-root tmp/market_cache --market-registry tmp/market_registry_baostock_only.json` → validate `pass`; real observation set `real_market_verified: true` (close 3y pct `0.9203`, 5y pct `0.9521`, 1351 observations).
- Synthetic pipeline: `build-capsule` → validate `pass`; confidence grades
  medium with coverage gaps (eq_roic, va_dividend_yield, rk_gap_count);
  shadow EQ 73.67/B, VA 12.17/E, VRC 21.76/D; sensitivity all `NOT_STABLE`
  (EQ delta 9.1, VA 3.2, VRC 29.0).

## Result

- All Stage 2K.1R3 deliverables are implemented and verified.
- Business conclusion preserved: `SCORING_CONTRACT_GAPS_REMAIN`, `NOT_STABLE`,
  peer acquisition `NOT ALLOWED`, production scoring `NOT ALLOWED`.
- No production score, no peer acquisition, no M3.

## Final files and Git state

- Branch: `feat/m2-value-assessment-mvp`.
- `git diff --check` clean (verified).
- New/modified files: scoring package, closeout CLI, two config registries,
  acceptance, reports (capsule v3 / confidence v3 / shadow v4 / sensitivity v4 /
  observation-set manifest / artifact manifest / old-new diff), two test files.
- Protected files untouched: AGENTS.md, agent/goals/, Stage 2I.2R edit, default
  DB, stash.
- Commit(s) created (see `git log`); no force push, no reset --hard, no git clean.