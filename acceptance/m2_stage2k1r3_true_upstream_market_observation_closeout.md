# M2 Stage 2K.1R3 — True Upstream Record Binding and Verified Market Observation-Set Closeout

Status: `PASS` (CI-backed; no production scores, no peer acquisition)

## Objective

Close out the true-upstream record-binding contract over Stage 2K.1R2. Every
scoring component must bind concrete upstream records (not just a file), the
validator must recompute every score input from upstream (not trust the
capsule), the source tier must be derived by the resolver (not self-reported),
and the valuation percentile must be recomputed from a verified external market
cache. Preserve the honest `NOT_STABLE` / `SCORING_CONTRACT_GAPS_REMAIN`
business conclusion. No peer acquisition, no production scoring, no M3.

## Scope

- `src/ashare_research/scoring/` package: `lineage.py` (per-type resolvers +
  `ResolvedRecord`), `transforms.py` (pure Decimal transform registry),
  `market_observation_set.py` (real-cache observation-set builder).
- `config/value_dimension_scoring_upstream_registry_v1.json` (24 components
  with true upstream selectors + source-tier bindings).
- `config/value_dimension_scoring_transform_registry_v2.json` (layer separation).
- `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (capsule v3 builder,
  fail-closed validator, confidence v3, shadow v4, sensitivity v4, CLI).
- Reports: capsule v3, confidence v3, shadow v4, sensitivity v4,
  real observation-set manifest v2, artifact manifest, old→new diff.
- Tests: `tests/test_m2_stage2k1r3_true_upstream_capsule.py` (22) +
  `tests/stage2k1r3/test_composite_tamper.py`.

## Non-goals

- No peer data acquisition, no production scoring, no composite score/rank/
  recommendation/target price/position signal.
- No modification of the canonical value profile to write scores.
- No M3, no main merge, no PR/tag/release, no force push, no reset --hard,
  no git clean -fd.
- No modification of the default DB, protected baselines, protected local
  files, or the pre-existing Stage 2I.2R wording edit.
- No relaxing `stability_tolerance=1.0`; no adjusting scoring to force stability.
- No raw provider OHLCV committed; no committed-percentile fallback; no
  synthetic percentile presented as a real PetroChina result.
- No `codex/` creation; no staging AGENTS.md / agent/goals/ / .codex/.

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | True upstream record binding (every component binds concrete records) | DONE | `src/ashare_research/scoring/lineage.py` + `config/value_dimension_scoring_upstream_registry_v1.json`; capsule `resolved_records` per component |
| 2 | Validator recomputes from upstream, never trusts capsule | DONE | `m2_stage2k1r3_closeout.validate_capsule`; composite tamper test all-pass |
| 3 | Source tier derived by resolver, not self-reported | DONE | `_derive_source_tier`; `source_tier_mismatch` on tamper |
| 4 | Pure-function Decimal transform registry (layer separation) | DONE | `src/ashare_research/scoring/transforms.py` + `config/value_dimension_scoring_transform_registry_v2.json` |
| 5 | Verified market observation set from external cache | DONE | `src/ashare_research/scoring/market_observation_set.py` + `reports/petrochina_valuation_observation_set_manifest_v2.json` (real cache, close 3y pct 0.9203, 5y pct 0.9521) |
| 6 | Real percentile recomputed from external cache (no committed fallback) | DONE | real-mode capsule uses `external_cache_recomputed` close percentile for PE/PB/PS; yield metrics flagged `not_cache_recomputable_yield_series` |
| 7 | Confidence v3 reads derived source tiers | DONE | `reports/petrochina_dimension_evidence_confidence_v3.json` |
| 8 | Shadow v4 + sensitivity v4 (honest NOT_STABLE) | DONE | `reports/petrochina_dimension_scoring_{shadow_v4,sensitivity_v4}.json` |
| 9 | CLI orchestration | DONE | `m2_stage2k1r3_closeout` subcommands |
| 10 | Acceptance & history | DONE | this file + `reports/m2_stage2k1r3_old_new_diff.md` + `reports/m2_stage2k1r3_artifact_manifest.json` |
| 11 | Tests | DONE | 22 pytest + composite tamper script |
| 12 | Engineering & acceptance gates | DONE | see Validation |
| 13 | Judgement criteria | DONE | see Judgement |
| 14 | Commits | DONE | see Git state |
| 15 | Final report | DONE | see Final report |

## Data notes

- Canonical facts: FY2025 annual + supplemental fixtures under
  `acceptance/fixtures/official_facts/601857.SH/`; `available_at` from the
  annual-report announcement dates (2026-03-30 for FY2025).
- Dividend events: `events/dividend_events_2021_2026_v2.json` (FY2025 interim
  0.22 + final 0.25 = 0.47 DPS).
- Risk slots: `reports/petrochina_value_profile.json` `current_risk_veto_profile`
  (8 slots; 0 triggered, 2 missing evidence, 6 bounded-search clean).
- Gap ledger: `reports/m2_explicit_gap_ledger.json` (18 current gaps; 7 ROIC).
- Market: verified baostock external cache `runs/stage2g/.../stock_daily_snapshot.parquet`
  (sha256 `defd0b95...`), 1351 rows, 2021-01-04..2026-07-31. The akshare
  provider snapshot is not present in the repo, so the real-mode observation
  set uses a baostock-only registry (tmp, not committed). Raw provider OHLCV is
  never committed; only observation IDs, digests, and percentiles are.

## Validation

- `pytest tests/ -q` → **1152 passed** (full suite; includes the 22 new 2K.1R3 tests).
- `pytest tests/test_m2_stage2k1r3_true_upstream_capsule.py -q` → **22 passed**.
- `python tests/stage2k1r3/test_composite_tamper.py` → **ALL PASS** (baseline passes;
  tamper of transform_inputs+value+source_tier+score_input_id+removed component+
  gap count all fail closed; capsule record snapshot ignored in favor of upstream).
- `ruff check src/ashare_research/scoring/ src/ashare_research/tools/m2_stage2k1r3_closeout.py tests/test_m2_stage2k1r3_true_upstream_capsule.py tests/stage2k1r3/` → **All checks passed**.
- `git diff --check` → clean (see Git state).
- Real-mode pipeline: `build-capsule --market-cache-root --market-registry` →
  validate `pass`; real observation set `real_market_verified: true`.
- **CI (clean clone, run `30891126248`)** → **PASS on ubuntu + windows**:
  `ruff check src/ tests/` → "All checks passed!"; `pytest -q` → **1150 passed,
  2 skipped** (the 2 skipped are the real-cache observation-set tests, which
  gracefully skip because the real baostock parquet is git-ignored and absent
  in a clean clone).

## Judgement

Preserved business conclusion (unchanged unless independently proven):

- **`SCORING_CONTRACT_GAPS_REMAIN`** — only 18 of 24 inputs are fully ACQUIRED
  + VERIFIED; ROIC and 5 other components remain explicit gaps. The valuation
  yield metrics are not recomputable from the daily close cache.
- **`NOT_STABLE`** — every scored dimension is `NOT_STABLE` under the frozen
  scenario set (max score deltas: EQ 9.1, VA 3.2, VRC 29.0).
- **Peer acquisition: NOT ALLOWED** — no peer data was acquired.
- **Production scoring: NOT ALLOWED** — `score_eligible: false`, capsules are
  `non_production`, no overall score, no recommendation.

## Final report

- True upstream record binding is implemented and verified: every component
  binds concrete records, the validator recomputes from upstream, and source
  tiers are resolver-derived.
- The real market observation set is built from the verified external cache and
  the real-mode capsule uses cache-recomputed price percentiles.
- The honest conclusion is preserved: `SCORING_CONTRACT_GAPS_REMAIN`, `NOT_STABLE`.
- No production score, no peer acquisition, no M3.

## Git state

- Branch: `feat/m2-value-assessment-mvp`.
- Commit `777b8fb` pushed to `origin/feat/m2-value-assessment-mvp`; CI run
  `30891126248` PASS (ubuntu + windows). No force push, no reset --hard, no
  git clean.
- Protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB,
  stash) are untouched.