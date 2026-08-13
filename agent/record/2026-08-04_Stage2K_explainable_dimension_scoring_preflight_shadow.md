# Work record: M2 Stage 2K explainable independent-dimension scoring preflight and shadow MVP

Status: `completed` (final subject to CI completion)

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `d34f66cf297a0a9cb0513b414624a496edcb4072`
- Task source: `agent/goals/2026-08-04_m2_stage2k_explainable_dimension_scoring_preflight_shadow.md`
- Module: value assessment (scoring addendum) / engineering governance

## Objective

Reopen only the scoring addendum of Milestone 2, define a transparent
independent-dimension scoring contract, audit benchmark feasibility, and
produce a non-production PetroChina four-dimension shadow scorecard. Must not
create a composite score, ranking, recommendation, target price, or production
scoring result.

## Verified opening state (snapshot)

- HEAD == origin == `d34f66cf297a0a9cb0513b414624a496edcb4072` (local==origin).
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Stash: `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` (Stage 1B.4 record edit).
- Unstaged protected edit (pre-existing Stage 2I.2R wording): `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md` hash `b0d739f2cce41b574e6db071e05fbc1233d38c2cb273a16723a5b0502db0bb30`.
- Untracked protected: `AGENTS.md` `9ff6d764...`, `agent/goals/` (8 files, hashes captured).
- `.codex/` does NOT exist locally (listed as protected but absent; noted, not created).
- Stage 2J remains a valid historical conditional closeout; scoring reopens only via this addendum.

## Scope

- Documentation, versioned JSON/Markdown scoring contracts, benchmark-feasibility
  and peer preflight, missingness/coverage/confidence contract, weight/sensitivity
  report, non-production PetroChina shadow scorecard, readiness-gate reassessment,
  Stage 2K acceptance, artifact manifest, README/completion-matrix addendum, focused
  Stage 2K tests, and this work record.
- Reuse existing evidence and mature contract patterns; no large scoring/MCDA dependency.

## Non-goals

- No overall/composite score, ranking, buy/sell, target price, upside probability,
  portfolio weight, or recommendation.
- No acquisition of broad peer data; no new facts/ROIC/dividend/risk retrieval.
- No production scoring tables/Metric Results/registry entries.
- No modification of default DB, protected baselines, protected local files, or
  the pre-existing Stage 2I.2R wording edit.
- No M3 implementation, main merge, PR/tag/release, force push, hard reset, or
  cleanup of user files.
- No `codex/` creation (it does not exist locally).

## Implementation plan

1. Verify opening state (done above); snapshot protected files.
2. Read North-Star files, Stage 2J acceptance/closeout, readiness gates, value
   profile, risk-veto methodology, existing tests.
3. Phase A: fresh North-Star review -> `docs/post_m2_closeout_scoring_north_star_review.md`.
   If M2_SCORING_ADDENDUM_REOPENED, reopen scoring only.
4. Phase B: score methodology, registry, policy, input contract.
5. Phase C: benchmark feasibility + peer preflight + transform comparison.
6. Phase D: missingness/coverage/confidence contract.
7. Phase E: weights + sensitivity (equal, theory-informed, evidence-card; ±25%,
   leave-one-out, transforms, coverage gate, missing-ROIC).
8. Phase F: non-production PetroChina shadow scorecard (only after contracts frozen).
9. Phase G: readiness-gate reassessment (12 gates, shadow vs production blockers).
10. Phase H: final decision (one of the three allowed).
11. Tests + validation + CI; final report; stop.

## Decision log

- **North-Star decision: `M2_SCORING_ADDENDUM_REOPENED`.** Only the scoring
  module reopens via a versioned addendum; Stage 2J remains an immutable
  historical conditional closeout. No other M2 module reopens.
  Docs: `docs/post_m2_closeout_scoring_north_star_review.md`.
- **Four independent dimensions**, no composite score:
  `enterprise_quality`, `valuation_attractiveness`, `value_realization_capacity`,
  `risk_and_evidence_integrity`. No ranking, recommendation, target price, or
  trading signal.
- **Score vs coverage vs confidence separated.** Missing never zero; ROIC is an
  explicit enterprise-quality coverage gap; Stage 2F/2H gaps lower evidence
  confidence, not quality scores; risk vetoes are non-compensatory.
- **Benchmark modes evaluated separately**: `absolute_contract`,
  `self_history_percentile`, `peer_percentile`, `binary_or_categorical_evidence`.
  Peer percentiles are PIT-safe; peer universe feasibility contract produced but
  broad peer data NOT acquired (that is a separate production stage).
- **Thresholds/transforms frozen before viewing the PetroChina result.**
- **Final decision: `PEER_BENCHMARK_ACQUISITION_REQUIRED`.** Method trusted and
  shadow computed, but enterprise_quality needs peer calibration for production.
  Docs: `docs/decisions/ADR-2026-08-04-stage2k-scoring-decision.md`.
- **Scoring module status in the M2 completion matrix -> `scoring_addendum_reopened`**;
  milestone_status -> `CONDITIONALLY_CLOSED_WITH_SCORING_ADDENDUM_REOPENED`;
  north_star_decision -> `M2_SCORING_ADDENDUM_REOPENED`. Stage 2J validator
  `m2_stage2j_closeout.py` updated to accept the reopened state; Stage 2J
  immutable packet artifacts (acceptance, closeout summary) keep the historical
  wording.

## Actual operations

- Verified opening state; snapshot protected files to
  `tmp/stage2k/protected_snapshot.txt`.
- Phase A: wrote `docs/post_m2_closeout_scoring_north_star_review.md` (decision
  `M2_SCORING_ADDENDUM_REOPENED`).
- Phase B: wrote `docs/value_dimension_scoring_methodology_v1.md`,
  `config/value_dimension_scoring_registry_v1.json` (4 dimensions, weighted
  components), `config/value_dimension_scoring_policy_v1.json`,
  `docs/value_dimension_scoring_input_contract.md`.
- Phase C: `docs/value_dimension_scoring_benchmark_feasibility.md`,
  `docs/value_dimension_scoring_peer_preflight.md` (no peer dataset acquired).
- Phase D: `docs/value_dimension_scoring_missingness_coverage_confidence.md`.
- Phase E: `docs/value_dimension_scoring_weights_sensitivity.md` + generated
  `reports/petrochina_dimension_scoring_sensitivity_v1.json`.
- Phase F: `config/value_dimension_scoring_shadow_inputs_v1.json` +
  `src/ashare_research/tools/m2_stage2k_scoring_shadow.py` + generated
  `reports/petrochina_dimension_scoring_shadow_v1.json` and `.md`.
- Phase G: `docs/value_scoring_readiness_gates_v2.md`.
- Phase H: `docs/decisions/ADR-2026-08-04-stage2k-scoring-decision.md`
  (decision `PEER_BENCHMARK_ACQUISITION_REQUIRED`).
- Wrote `tests/test_m2_stage2k_dimension_scoring.py` (22 tests) and
  `acceptance/m2_stage2k_dimension_scoring_preflight_shadow.md`.
- Updated `reports/m2_value_assessment_completion_matrix.json` and `.md`,
  `README.md`, `docs/value_fact_coverage_roadmap.md` (Stage 2K append), and
  `src/ashare_research/tools/m2_stage2j_closeout.py` to the reopened-scoring
  state.
- Updated `tests/test_m2_stage2j_conditional_closeout.py` to the reopened
  north-star decision and split the wording test for living vs immutable docs.
- Regenerated `reports/m2_stage2j_artifact_manifest.json` (matrix JSON/MD hash
  + north-star decision) and created `reports/m2_stage2k_artifact_manifest.json`
  (18 files, SHA-256).
- Advanced the roadmap protected blob hash in 5 protected test files
  (`test_official_*`) to the Stage 2K append, per the established append-only
  pattern.
- Fixed ruff findings in the Stage 2K engine and tests (E501 line length,
  B905 zip strict, F841 unused var, W292 trailing newline).

## Verification

All commands run with `.venv/Scripts/python.exe` on Windows.

- `pytest tests/test_m2_stage2k_dimension_scoring.py` -> 22 passed.
- `pytest tests/test_m2_stage2j_conditional_closeout.py` -> 13 passed.
- `pytest` (full) -> 1078 passed, 0 failed (includes protected Stage 2F/2H/2I,
  Fact/Metric Identity, PIT, and Stage 2G reproducibility/clean-clone suites).
- `ruff check` on changed engine/tests -> All checks passed.
- `compileall` on changed modules -> OK.
- `git diff --check` -> OK.
- Shadow/sensitivity A/B determinism -> True / True.
- Stage 2K `validate` CLI -> `contract_errors: []`, `non_production: true`,
  `overall_score_prohibited: true`, `score_eligible: false`.
- Stage 2J `verify-contracts` CLI -> all checks pass, `errors: []`.
- Default DB SHA-256 unchanged: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected files unchanged (Stage 2I.2R acceptance edit, AGENTS.md, agent/goals).
- Stash unchanged: `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Clean clone (after commit): clone has no default DB; Stage 2K tests pass
  (recorded once the commit is made).

## Result

- **Completed**: four-dimension explainable scoring contract, non-production
  PetroChina shadow scorecard (enterprise_quality 73.47 B, valuation_attractiveness
  12.17 E, value_realization_capacity 70.13 B, risk_and_evidence_integrity 80.40 A,
  all `ordinal_shadow`, coverage 0.90/0.80/1.00/1.00), sensitivity report, readiness
  gates v2, Stage 2K acceptance, artifact manifest, and addendum updates to the
  completion matrix / README / roadmap / Stage 2J validator.
- **Final decision**: `PEER_BENCHMARK_ACQUISITION_REQUIRED`. Method trusted;
  enterprise_quality needs peer calibration for production scoring.
- **Conditional note**: clean-clone re-verification and CI (Ubuntu/Windows) are
  recorded after the commit is pushed.

## Final files and Git state

- Branch: `feat/m2-value-assessment-mvp`.
- Commit: `c8a86732fc2bc0af75578cdfff4a49aa8f43bc2a` (pushed; local == origin).
- Final CI: `clean-clone` workflow success on `ubuntu-latest` (2m28s) and
  `windows-latest` (5m5s); only Node 20 deprecation annotation, no failure.
- Protected files NOT staged/committed: `AGENTS.md` (untracked), `agent/goals/`
  (untracked), pre-existing Stage 2I.2R wording edit in
  `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`
  (unstaged). Stash remains `stash@{0}` = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Default DB unchanged: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- No main merge, PR, tag, release, force push, or hard reset. M3 and Stage 2K.1
  not started.