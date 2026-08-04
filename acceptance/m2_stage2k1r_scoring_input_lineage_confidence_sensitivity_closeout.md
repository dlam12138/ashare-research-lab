# M2 Stage 2K.1R — scoring-input lineage, confidence, and sensitivity closeout

Status: `PASS` (CI-backed; no production scores, no peer acquisition)

## CI evidence

- GitHub Actions `stage2g-reproducibility.yml` run
  [30878513390](https://github.com/dlam12138/ashare-research-lab/actions/runs/30878513390),
  head `d3668a0`.
- `clean-clone (ubuntu-latest)` → **success**; `clean-clone (windows-latest)` → **success**.
- Every step (offline preflight, static/import gates, contract gates, capsule
  A/B builds and runs, full offline test suite) completed with **success** on both
  matrix runners.

## Decision and Git boundary

- Goal: `agent/goals/2026-08-04_m2_stage2k1r_scoring_input_lineage_confidence_sensitivity_closeout.md`
- Branch: `feat/m2-value-assessment-mvp`
- Start HEAD: `b974de94`
- North-Star decision: `M2_SCORING_ADDENDUM_REOPENED` (unchanged)
- Stage 2K.1R decision: `SCORING_CONTRACT_GAPS_REMAIN`
- Milestone 2: `CONDITIONALLY CLOSED; SCORING ADDENDUM REOPENED`

Stage 2K.1R does not reopen any other M2 module. Stage 2K acceptance remains
immutable historical evidence. The scoring module remains open through the
versioned addendum.

## Scope

This stage replaced the hand-maintained shadow-input JSON with a deterministic
**score-input capsule** built from committed canonical artifacts only. It
introduced a per-dimension evidence-confidence contract, separated the risk
dimension into veto status + evidence integrity (no merged risk score), and
completed a full frozen sensitivity with machine-derived stability.

## Deliverables

- Capsule builder: `src/ashare_research/tools/m2_stage2k1r_capsule.py`
- Capsule validator: `src/ashare_research/tools/m2_stage2k1r_validate.py`
- Confidence contract: `config/value_dimension_scoring_confidence_v1.json`
- Confidence engine: `src/ashare_research/tools/m2_stage2k1r_confidence.py`
- Shadow engine (capsule-backed): `src/ashare_research/tools/m2_stage2k1r_shadow.py`
- Sensitivity engine: `src/ashare_research/tools/m2_stage2k1r_sensitivity.py`
- Score-input capsule: `reports/petrochina_score_input_capsule_v1.json`
- Shadow scorecard: `reports/petrochina_dimension_scoring_shadow_v2.json`
- Confidence report: `reports/petrochina_dimension_scoring_confidence_v1.json`
- Sensitivity report: `reports/petrochina_dimension_scoring_sensitivity_v2.json`
- Artifact manifest: `reports/m2_stage2k1r_artifact_manifest.json`
- Acceptance: `acceptance/m2_stage2k1r_scoring_input_lineage_confidence_sensitivity_closeout.md`

## Four dimensions

1. `enterprise_quality`
2. `valuation_attractiveness`
3. `value_realization_capacity`
4. `risk_and_evidence_integrity`

No fifth overall score exists. No ranking, recommendation, target price, or
trading signal is produced.

## Non-production shadow result (score date 2026-07-31)

| Dimension | Score | Band | Coverage | Status |
|---|---|---|---|---|
| enterprise_quality | 73.47 | B | 0.90 | ordinal_shadow |
| valuation_attractiveness | 12.17 | E | 0.80 | ordinal_shadow |
| value_realization_capacity | 70.13 | B | 1.00 | ordinal_shadow |
| risk_and_evidence_integrity | — | — | — | veto=clear, integrity=medium |

The three scored dimensions reproduce the Stage 2K shadow A/B exactly
(73.47 / 12.17 / 70.13). The risk dimension is **no longer a merged numeric
score**; it is reported as separate `risk_veto_status` (clear, non-compensatory)
and `evidence_integrity` (medium) outputs. This is the semantic reassessment:
merging risk and integrity into one number could mask a serious veto.

## Evidence confidence (per-dimension, separate from score)

| Dimension | Grade | Driving reason |
|---|---|---|
| enterprise_quality | medium | ROIC coverage gap (M2G-ROIC-001..007) |
| valuation_attractiveness | medium | dividend-yield coverage gap |
| value_realization_capacity | medium | Stage 2F dividend exchange-payload gaps (M2G-DIV-001..009) |
| risk_and_evidence_integrity | medium | risk missing-evidence slots (M2G-RISK-001..002) |

Confidence is a separate product from the score. ROIC absence lowers
enterprise coverage/confidence but is never a zero or a poor-capital-return
claim. Risk vetoes remain non-compensatory.

## Sensitivity (machine-derived stability)

Thresholds (weights, coverage gates, confidence gates, transform breakpoints)
were frozen before the rerun. Synthetic ROIC values are labeled synthetic and
are never company facts. Per dimension the engine emits min/max score,
max_score_delta, band_flip_count, insufficient-evidence count, veto-block
count, scenario count, stability_status, and production_readiness_reason.

| Dimension | min | max | delta | band_flip | insufficient | veto | status |
|---|---|---|---|---|---|---|---|
| enterprise_quality | 68.05 | 77.59 | 9.54 | 0 | 1 | 0 | NOT_STABLE |
| valuation_attractiveness | 10.43 | 13.59 | 3.16 | 0 | 1 | 0 | NOT_STABLE |
| value_realization_capacity | 65.91 | 75.16 | 9.25 | 0 | 0 | 0 | NOT_STABLE |

The frozen `stability_tolerance` is 1.0. Under ±25% single-component weight
perturbation and leave-one-out, each scored dimension moves by several points
beyond 1.0, and the 0.95 coverage gate exceeds the achieved 0.90/0.80 coverage.
`NOT_STABLE` is the honest machine-derived outcome. The tolerance was **not**
relaxed to force a pass; doing so would be modifying thresholds to obtain a
conclusion. This is the concrete basis for decision `SCORING_CONTRACT_GAPS_REMAIN`.

## Old → new diff

- **Inputs**: `config/value_dimension_scoring_shadow_inputs_v1.json` (hand-maintained)
  → `reports/petrochina_score_input_capsule_v1.json` (deterministic, committed-
  artifact-only, digest `dab07d9f…`). Every component binds to upstream artifact
  SHA-256, contract, record, value, unit, date, and available_at.
- **Risk dimension**: merged score 80.40 / A → separate `risk_veto_status` +
  `evidence_integrity`, no merged numeric score.
- **Confidence**: new per-dimension evidence-confidence contract (was absent).
- **Sensitivity**: replaced by complete frozen scenario set with machine-derived
  stability (was weight/LOO/coverage only).

## Protected baseline evidence

- Default DB SHA-256 at start:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected inventory: 354 Facts / 102 Metric Results / 16 definitions.
- Protected untracked `AGENTS.md`, `agent/goals/`, the existing stash, and the
  pre-existing Stage 2I.2R acceptance wording edit are outside this stage.
- The canonical `reports/petrochina_value_profile.json` is not modified.

## Validation

Full validation (targeted tests, protected Stage 2F/2H/2I suites, Identity/PIT,
full pytest, Ruff, compileall, A/B, artifact verification, portability, clean
clone, Ubuntu/Windows CI) is recorded in the work record. Levels:

- Local (`data/` present): full pytest **1102 passed**; ruff all checks;
  compileall OK; shadow/sensitivity A/B matches Stage 2K; default DB unchanged.
- Clean clone (properly installed package, as CI does): full pytest **1102 passed**.
- CI (ubuntu + windows): **all steps success** (run 30878513390).

The Stage 2K.1R PASS is CI-backed and reportable.

## Non-goals

- No peer data acquired, no new facts, no production score/table/Metric Result/
  registry entry, no exact target price.
- No composite score, ranking, recommendation, or trading signal.
- Peer benchmarks may be acquired only in a separately authorized production stage.
- ROIC, dividend, and risk-evidence gaps retain their current status.