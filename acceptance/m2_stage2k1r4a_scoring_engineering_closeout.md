# M2 Stage 2K.1R4A — Scoring Engineering Decomposition and Guard Closeout

Status: `PASS` (CI-backed; no production scores, no peer acquisition, no M3)

## Objective

Small engineering closeout that fixes exactly five problems in the scoring
engineering:

1. `m2_stage2k1r3_closeout.py` is a thin CLI (business logic moved to the
   `ashare_research.scoring` modules).
2. CLI fail-closed exit codes (`validate` / `verify-artifacts` failure returns 1).
3. Validator requires the capsule's `resolved_records` audit snapshot to match
   the authoritative upstream recomputation (`capsule_snapshot_mismatch`).
4. Risk status never emits `clear`; the honest enum state is reported.
5. Sensitivity v5 restores the full 6 scenario classes from the v3 baseline.

Preserve the honest business conclusion (`NOT_STABLE`, `SCORING_CONTRACT_GAPS_REMAIN`).
No peer acquisition, no production scoring, no M3.

## Scope

- `src/ashare_research/scoring/capsule.py` (capsule builder + shared helpers)
- `src/ashare_research/scoring/validator.py` (fail-closed validator + audit
  snapshot consistency)
- `src/ashare_research/scoring/confidence.py` (confidence v3)
- `src/ashare_research/scoring/shadow.py` (shadow v5 + risk status enum)
- `src/ashare_research/scoring/sensitivity.py` (sensitivity v5, 6 scenario classes)
- `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (now a thin CLI, ~170 lines)
- Reports: `petrochina_score_input_lineage_validation_v2.json`,
  `petrochina_dimension_scoring_shadow_v5.json`,
  `petrochina_dimension_scoring_sensitivity_v5.json`,
  `m2_stage2k1r4a_old_new_diff.json`, `m2_stage2k1r4a_artifact_manifest.json`.
- Tests: `tests/test_m2_stage2k1r4a_engineering_closeout.py` (31) + updated
  `tests/test_m2_stage2k1r3_true_upstream_capsule.py` (22) +
  `tests/stage2k1r3/test_composite_tamper.py`.

## Non-goals

- No historical PE/PB/PS PIT denominator series, no valuation-percentile method
  change, no `valuation_attractiveness` production interpretation.
- No peer data, no production scoring, no composite score / rank / recommendation
  / target price / position / signal.
- No canonical value profile writes, no M3, no main merge, no PR/tag/release.
- No fixed denominator / close percentile / same percentile standing in for PE/PB/PS.
- No modification of `src/ashare_research/scoring/market_observation_set.py`
  (except none — it is untouched this round).
- No modification of the default DB, protected baselines, protected local files,
  or the pre-existing Stage 2I.2R wording edit.
- No relaxing `stability_tolerance=1.0`; no weight/threshold changes; no
  `.codex/` / `.claude/` / git hook creation.

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Thin CLI (business logic moved to scoring modules) | DONE | `m2_stage2k1r3_closeout.py` ~170 lines; `test_business_logic_moved_out_of_cli`, `test_cli_is_thin_orchestrator` |
| 2 | CLI fail-closed exit codes (0/1/2/3) | DONE | `EXIT_*` constants; `test_cli_*` (validate pass 0, fail 1, internal 2, no-args 2, cache missing 3) |
| 3 | Capsule Audit Snapshot Consistency (`capsule_snapshot_mismatch`) | DONE | `validator.validate_capsule` authoritative + audit comparison; `test_validator_*` audit tests |
| 4 | Risk status semantics (finite enum, no `clear`, no complete-absence claim) | DONE | `shadow.RISK_STATUS_ENUM`; `test_risk_status_*`; PetroChina=`no_trigger_observed_with_missing_evidence` |
| 5 | Sensitivity v5 restores 6 scenario classes | DONE | `sensitivity.build_sensitivity`; `test_sensitivity_restores_all_six_scenario_classes` |
| 6 | Coverage/confidence gates independent | DONE | `coverage_gate_sensitivity` + `confidence_gate_sensitivity`; `test_sensitivity_*` |
| 7 | Business conclusion preserved | DONE | `NOT_STABLE` across all scored dims; `SCORING_CONTRACT_GAPS_REMAIN`; no production/peer/M3 |
| 8 | Reports + old-new diff + manifest | DONE | 5 new report files |
| 9 | Tests | DONE | 31 new + 22 R3 + composite tamper |
| 10 | Engineering & acceptance gates | DONE | see Validation |
| 11 | Commits | DONE | see Git state |
| 12 | Final report | DONE | see Final report |

## Validation

- `pytest tests/ -q` → **1183 passed** (full suite; includes the 31 new R4A tests
  and the 22 R3 tests; the real-cache observation-set tests run because the
  committed baostock snapshot is present).
- `pytest tests/test_m2_stage2k1r4a_engineering_closeout.py -q` → **31 passed**.
- `pytest tests/test_m2_stage2k1r3_true_upstream_capsule.py -q` → **22 passed**.
- `python tests/stage2k1r3/test_composite_tamper.py` → **ALL PASS** (baseline;
  tamper of inputs/value/source_tier/score_input_id/capsule_digest/removed
  component/gap count all fail closed; tampered resolved_records snapshot now
  fails closed with `capsule_snapshot_mismatch`).
- `ruff check src/ashare_research/scoring/ src/ashare_research/tools/m2_stage2k1r3_closeout.py tests/test_m2_stage2k1r4a_engineering_closeout.py tests/test_m2_stage2k1r3_true_upstream_capsule.py tests/stage2k1r3/` → **All checks passed**.
- CLI exit codes verified: `validate` → 0, `build-capsule` → 0,
  `verify-artifacts` → 0, `build-market-observation-set` (no cache) → 3,
  `build-shadow` → 0, `build-sensitivity` → 0.
- Real-mode pipeline (verified in prior acceptance) unchanged; market
  observation set builder untouched.

## Judgement

Preserved business conclusion (unchanged unless independently proven):

- **`SCORING_CONTRACT_GAPS_REMAIN`** — only 18 of 24 inputs are fully ACQUIRED +
  VERIFIED; ROIC and 5 other components remain explicit gaps.
- **`NOT_STABLE`** — every scored dimension is `NOT_STABLE` under the frozen
  scenario set (max score deltas: EQ 9.11, VA 3.16, VRC 29.0).
- **Peer acquisition: NOT ALLOWED** — no peer data was acquired.
- **Production scoring: NOT ALLOWED** — `score_eligible: false`, all artifacts
  are `non_production`, no overall score, no recommendation.
- **M3: NOT STARTED**; next stage max `PIT_VALUATION_READINESS_REVIEW_ALLOWED`.

## Final report

- The scoring business logic is decomposed into five `ashare_research.scoring`
  modules; the CLI is a thin orchestrator with fail-closed exit codes.
- The validator now enforces Capsule Audit Snapshot Consistency: a tampered
  `resolved_records` snapshot fails closed with `capsule_snapshot_mismatch`.
- Risk status is a finite enum that never emits `clear`; PetroChina is honestly
  reported as `no_trigger_observed_with_missing_evidence`.
- Sensitivity v5 restores all 6 scenario classes from the v3 baseline with the
  coverage and confidence gates kept independent.
- The honest business conclusion is preserved: `NOT_STABLE`, `SCORING_CONTRACT_GAPS_REMAIN`.
- No production score, no peer acquisition, no M3.

## Git state

- Branch: `feat/m2-value-assessment-mvp`.
- Commit pushed to `origin/feat/m2-value-assessment-mvp`; CI run PASS (ubuntu +
  windows). No force push, no reset --hard, no git clean.
- Protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash)
  are untouched.