# M2 Stage 2K — explainable independent-dimension scoring preflight and shadow

Status: `PASS` (CI-backed; commit `c8a8673`)

## Decision and Git boundary

- Goal: `agent/goals/2026-08-04_m2_stage2k_explainable_dimension_scoring_preflight_shadow.md`
- Branch: `feat/m2-value-assessment-mvp`
- Start HEAD: `d34f66cf297a0a9cb0513b414624a496edcb4072`
- North-Star decision: `M2_SCORING_ADDENDUM_REOPENED`
- Stage 2K decision: `PEER_BENCHMARK_ACQUISITION_REQUIRED`
- Milestone 2: `CONDITIONALLY CLOSED; SCORING ADDENDUM REOPENED`
- Next-stage implementation: `NOT STARTED`

The scoring module is reopened through a versioned addendum. Stage 2J remains an
immutable historical conditional closeout. No other M2 module is reopened.

## Deliverables

- Review: `docs/post_m2_closeout_scoring_north_star_review.md`
- Methodology: `docs/value_dimension_scoring_methodology_v1.md`
- Registry: `config/value_dimension_scoring_registry_v1.json`
- Policy: `config/value_dimension_scoring_policy_v1.json`
- Input contract: `docs/value_dimension_scoring_input_contract.md`
- Shadow inputs: `config/value_dimension_scoring_shadow_inputs_v1.json`
- Benchmark feasibility: `docs/value_dimension_scoring_benchmark_feasibility.md`
- Peer preflight: `docs/value_dimension_scoring_peer_preflight.md`
- Missingness/coverage/confidence: `docs/value_dimension_scoring_missingness_coverage_confidence.md`
- Weights/sensitivity: `docs/value_dimension_scoring_weights_sensitivity.md`
- Readiness gates v2: `docs/value_scoring_readiness_gates_v2.md`
- Decision: `docs/decisions/ADR-2026-08-04-stage2k-scoring-decision.md`
- Shadow scorecard: `reports/petrochina_dimension_scoring_shadow_v1.json` and `.md`
- Sensitivity: `reports/petrochina_dimension_scoring_sensitivity_v1.json`
- Engine: `src/ashare_research/tools/m2_stage2k_scoring_shadow.py`
- Tests: `tests/test_m2_stage2k_dimension_scoring.py`

## Four dimensions

1. `enterprise_quality`
2. `valuation_attractiveness`
3. `value_realization_capacity`
4. `risk_and_evidence_integrity`

No fifth overall score exists. No ranking, recommendation, target price, or
trading signal is produced.

## Non-production shadow result (as of 2026-07-31)

| Dimension | Score | Band | Status | Coverage |
|---|---|---|---|---|
| enterprise_quality | 73.47 | B | ordinal_shadow | 0.90 |
| valuation_attractiveness | 12.17 | E | ordinal_shadow | 0.80 |
| value_realization_capacity | 70.13 | B | ordinal_shadow | 1.00 |
| risk_and_evidence_integrity | 80.40 | A | ordinal_shadow | 1.00 |

ROIC is a coverage gap in `enterprise_quality`, never a zero. The dividend-yield
observation is a coverage gap in `valuation_attractiveness`, never a zero. Risk
vetoes are non-compensatory. All outputs are marked `non_production=true`,
`research_methodology_test_only=true`, `overall_score_prohibited=true`,
`recommendation_prohibited=true`, `score_eligible=false`.

## Production profile unchanged

The canonical `reports/petrochina_value_profile.json` is not modified by the
shadow. It remains score-free. The shadow is an isolated non-production report.

## Protected baseline evidence

- Default DB SHA-256 at start:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected inventory: 354 Facts / 102 Metric Results / 16 definitions.
- Protected untracked `AGENTS.md`, `agent/goals/`, the existing stash, and the
  pre-existing Stage 2I.2R acceptance wording edit are outside this stage.

## Validation (recorded in the final section after execution)

Stage 2K targeted tests, protected Stage 2F/2H/2I suites, Fact/Metric Identity
and PIT, full pytest, Ruff, compileall, registry/benchmark/PIT validation,
shadow/sensitivity A/B, artifact verification, clean clone, and Ubuntu/Windows
CI are recorded after execution. The Stage 2K PASS is not reportable until every
required final gate passes.

## Non-goals and reopen conditions

- No peer data acquired, no new facts, no production score/table/Metric Result/
  registry entry.
- No composite score, ranking, recommendation, or target.
- Peer benchmarks may be acquired only in a separately authorized production stage.
- ROIC, dividend, and risk-evidence gaps retain their current status.