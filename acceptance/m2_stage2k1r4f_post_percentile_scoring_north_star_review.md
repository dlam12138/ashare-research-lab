# M2 Stage 2K.1R4F — Post-Percentile North-Star Review and Valuation Scoring Contract Reconciliation

## Verdict: PASS — LOCAL CANDIDATE

M2 Stage 2K.1R4F: **PASS — LOCAL CANDIDATE**
Remote CI: **GREEN** (run `31155321795` on push `834e6b6`)
decision: `VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`

This stage reconciles the `valuation_attractiveness` scoring contract against
the CI-confirmed R4E.5 trusted percentile profile and freezes the method and
boundary of the next-stage v2 valuation scoring migration. It is a
**review / decision** stage: it does **not** modify any scoring registry,
policy, engine, shadow, or sensitivity, and it does **not** compute a score.

## 0b. Remote CI (run `31155321795` on push `834e6b6`)

- Ubuntu clean-clone: **PASS** (1687 passed, 3 skipped, 3 warnings).
- Windows clean-clone: **PASS** (1687 passed, 3 skipped, 2 warnings).
- identity-compare: **PASS** (`identical: true`, gate `ok`, digest
  `1843da77…`).
- Full pytest (includes R4F static decision tests and R4E.5 protected tests)
  green on both platforms through the full CI suite.

## 0. Final report card

```
M2 Stage 2K.1R4F:                                        PASS — LOCAL CANDIDATE
Stage type:                                              REVIEW / DECISION
Decision:               VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED
Selected window model:  DUAL_WINDOW_SINGLE_COMPONENT
Selected aggregation:   EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN (0.5/0.5, Decimal)
PE numeric scoring:     BLOCKED_PENDING_CYCLE_CONTEXT_GUARD
PB/PS numeric shadow:   ALLOWED_AFTER_V2_MIGRATION
Shadow refresh:         ALLOWED_AFTER_V2_MIGRATION (not run here)
Production scoring:     NOT_AUTHORIZED
Overall score:          PROHIBITED
Peer percentile:        NOT_AUTHORIZED_IN_THIS_STAGE
M3:                     NOT_STARTED
Option choice basis:    method attributes only (NO actual percentile peeking)
Scoring implementation: NOT STARTED
Registry v2:            NOT CREATED
Policy v2:              NOT CREATED
Shadow refresh:         NOT RUN
Sensitivity re-run:     NOT RUN (mandatory in R4F1)
Artifact manifest:      NOT REQUIRED (review-only stage)
Next stage:             M2_STAGE_2K1R4F1 (v2 migration + non-production shadow refresh)
Git:                    COMMITTED + PUSHED (2ab3106, 834e6b6, closeout)
```

## 1. Review baseline

- Branch `feat/m2-value-assessment-mvp` at `017b656`; local == origin (0/0).
- R4E.5 remote CI GREEN (runs `31151600368`, `31152356097`; Ubuntu/Windows
  `1665 passed, 3 skipped`; identity-compare pass).
- Default DB SHA `4a71d3c7b88c0b16…` unchanged; protected baseline
  354 Facts / 102 Metric Results / 16 definitions.
- Percentile profile `petrochina_pit_valuation_percentile_profile_v1`,
  6 records, MIDRANK_EMPIRICAL_PERCENTILE, as-of `2026-07-31`.

## 2. What R4F reviewed (read-only)

- `config/value_dimension_scoring_registry_v1.json`
- `config/value_dimension_scoring_policy_v1.json`
- `reports/petrochina_dimension_scoring_shadow_v5.json`
- `reports/petrochina_dimension_scoring_sensitivity_v7.json`
- `docs/value_scoring_readiness_gates_v2.md`
- `docs/post_m2_closeout_scoring_north_star_review.md`
- R4E.5 percentile profile / contract / record artifacts

None of these were modified.

## 3. Deliverables created (R4F, review-only)

- `reports/petrochina_valuation_scoring_contract_gap_matrix_v1.json`
- `docs/post_percentile_scoring_north_star_review.md`
- `reports/petrochina_post_percentile_scoring_option_matrix_v1.json`
- `reports/petrochina_valuation_scoring_migration_plan_v1.json`
- `reports/m2_stage2k1r4f_decision.json`
- `acceptance/m2_stage2k1r4f_post_percentile_scoring_north_star_review.md`
- `tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`
- `agent/record/2026-08-07_Stage2K1R4F_post_percentile_scoring_north_star_review.md`

## 4. Frozen contract (for R4F1)

- Each of `va_pe/va_pb/va_ps` stays **one** component binding both
  `percentile_3y` and `percentile_5y`.
- `window_weights` 3y = 0.5 / 5y = 0.5; `dual_window_percentile =
  (percentile_3y + percentile_5y) / 2`, **Decimal only**.
- `aggregation_contract_version = self_history_dual_window_percentile_v1`.
- Identity binds R4E.5 profile digest, 3y/5y `percentile_record_id`, 3y/5y rank
  numerator/denominator, and the aggregation contract version.
- Weights `multiple_position 0.60 / yield_position 0.40` and each va component
  `0.20` retained; PE weight not deleted or renormalized.
- `window_spread = abs(percentile_3y - percentile_5y)` is diagnostic only.

## 5. PE cycle guard boundary

- PE percentile is `TRUSTED_DESCRIPTIVE_EVIDENCE`; `va_pe` numeric score
  contribution is `NOT AUTHORIZED` until a formal cycle-context contract.
- `cycle_context_requirement = required_for_numeric_scoring`,
  `cycle_context_status = not_yet_formalized`,
  `component_shadow_status = coverage_gap_cycle_context_required`.
- Prohibited: auto-assign PE 0/50, silent deletion, PB/PS substitution, or
  asserting today's high percentiles are safe.

## 6. PB / PS and old-shadow status

- PB → `PB_A_MRQ`, PS → `PS_A_TTM`; both `direction = lower_better` with
  "lower/higher historical valuation position" wording only (never
  cheap/undervalued/overvalued/fair value).
- Shadow v5 preserved as `VALID_HISTORICAL_NON_PRODUCTION_RESULT`; its valuation
  percentile inputs are `SUPERSEDED_FOR_FUTURE_SHADOWS`.

## 7. Decision gate

`PASS` (`VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`) when: old/new semantic
gap complete; options reviewed; decision independent of PetroChina's current
result; dual-window contract frozen; double counting blocked; PE cycle gap
identified and fail-closed; v1 immutable; production blocked; next stage
non-production only.

`POST_PERCENTILE_SCORING_REVIEW_GAPS_REMAIN` (conditional) if upstream contract
identity cannot be confirmed, a migration semantic is ambiguous, or the old
scoring path is not fully audited.

`POST_PERCENTILE_SCORING_REVIEW_NOT_TRUSTED` (fail) if the review peeks at
results to choose a method, allows six-component double weighting, overwrites
v1, allows production, removes the cycle guard, or creates an overall score.

## 8. Product boundary

- No scoring registry/policy/engine/shadow/sensitivity modification; no
  score computed; no sensitivity re-run.
- No registry v2 / policy v2 / shadow v6 created; no component score change.
- No peer acquisition, no overall score, no rank, no recommendation, no target
  price, no M3.
- No artifact manifest (review-only stage; requires no manifest).
- No default-DB write; no market re-fetch; no percentile recomputation.

## 9. Validation

- R4F static decision tests: **22 passed** (see below).
- Full offline pytest: **1690 passed, 2 warnings**.
- `ruff check` on changed files: **PASS**.
- `git diff --check`: **PASS**.
- Protected files (`AGENTS.md`, `agent/goals/`, `acceptance/m2_stage2i2r_*`,
  stash, default DB, registry v4, R4E.4/R4E.5 artifacts, scoring files)
  untouched.

## 10. Next steps

R4F1 (`M2_STAGE_2K1R4F1_VALUATION_SCORING_CONTRACT_V2_MIGRATION_AND_SHADOW_REFRESH`)
is required to actually migrate: create registry v2 / policy v2, refresh the
non-production shadow, and re-run the full sensitivity. Entry to R4F1 is **not**
authorised by this stage and requires explicit user instruction. R4F is
review-only, committed and pushed, and CI-confirmed (run `31155321795`).