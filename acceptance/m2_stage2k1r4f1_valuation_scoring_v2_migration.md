# M2 Stage 2K.1R4F.1 — Valuation Scoring Contract v2 Migration and Non-Production Shadow Refresh

## Verdict: PASS — LOCAL CANDIDATE

M2 Stage 2K.1R4F.1: **PASS — LOCAL CANDIDATE**
Remote CI: **PENDING** (local validation complete; not yet committed/pushed at closeout time)
decision: `VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS`

This stage migrates the `valuation_attractiveness` scoring contract to v2 and
refreshes the non-production shadow and full sensitivity, implementing the frozen
R4F decision (`DUAL_WINDOW_SINGLE_COMPONENT`,
`EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN`). It is a **non-production** migration: PE
numeric scoring remains blocked, and the remaining weights are not renormalized.

## 0. Final report card

```
M2 Stage 2K.1R4F.1:                                     PASS — LOCAL CANDIDATE
Stage type:                                              IMPLEMENTATION / NON-PRODUCTION
Decision:               VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS
Registry v2:            CREATED (value_dimension_scoring_registry_v2)
Policy v2:              CREATED (value_dimension_scoring_policy_v2)
Shadow inputs v2:       CREATED (value_dimension_scoring_shadow_inputs_v2)
Shadow refresh:         RUN (shadow v6)
Sensitivity re-run:     RUN (sensitivity v8, full)
PE numeric scoring:     BLOCKED (cycle-context hard gap)
Valuation dimension:    insufficient_evidence_cycle_context (no numeric score)
PB numeric shadow:      ALLOWED (per-component score only)
PS numeric shadow:      ALLOWED (per-component score only)
Production scoring:     NOT AUTHORIZED
Overall score:          PROHIBITED
Peer percentile:        NOT_AUTHORIZED_IN_THIS_STAGE
M3:                     NOT_STARTED
PE cycle-context method:NOT STARTED
Git:                    NOT COMMITTED / NOT PUSHED (per instruction)
```

## 1. Migration baseline

- Branch `feat/m2-value-assessment-mvp`; R4F decision
  `VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED` on the CI-confirmed final tip.
- R4E.5 trusted percentile profile `petrochina_pit_valuation_percentile_profile_v1`,
  6 records, MIDRANK_EMPIRICAL_PERCENTILE, as-of `2026-07-31`.
- shadow v5 (v1 contract) preserved as `VALID_HISTORICAL_NON_PRODUCTION_RESULT`.

## 2. What v2 migrated

- `va_pe` → `PE_A_TTM`, `va_pb` → `PB_A_MRQ`, `va_ps` → `PS_A_TTM`,
  each `benchmark_mode = self_history_dual_window_percentile`.
- `window_weights` 3y = 0.5 / 5y = 0.5; `dual_window_percentile =
  (percentile_3y + percentile_5y) / 2`, **Decimal only**;
  `aggregation_contract_version = self_history_dual_window_percentile_v1`.
- Each component stays **one** component (no six-component split).
- `multiple_position 0.60 / yield_position 0.40` and each va component `0.20`
  retained; PE weight not deleted or reassigned.

## 3. PE cycle-context hard gap

- `va_pe` status `coverage_gap_cycle_context_required`;
  policy v2 `non_renormalizable_gap_statuses = [coverage_gap_cycle_context_required]`.
- `valuation_attractiveness` dimension → `score = null`, `band = null`,
  `status = insufficient_evidence_cycle_context`, `coverage_ratio = 0.6`,
  `missing = [va_pe, va_dividend_yield]`, `blocked = [va_pe]`.
- **No dimension-level renormalization**; the remaining weights are not rescaled.
- Blocked is **not** `score = 0`; the component is not deleted.

## 4. Shadow v6 result

- `valuation_attractiveness`: no numeric score; PB component `12.0417`,
  PS component `6.4332` (per-component, no dimension score).
- `enterprise_quality` (73.6694 / B) and `value_realization_capacity`
  (21.7562 / D) unchanged from shadow v5 — the v5→v6 diff is confined to
  valuation.

## 5. Sensitivity v8

- Full weight-perturbation sweep (38 scenarios) over the v2 contracts.
- Valuation dimension stays `insufficient_evidence_cycle_context` in every
  scenario (PE always blocked); no scenario renormalizes past the gap.
- Non-valuation dimensions show the expected perturbation deltas.

## 6. Engine

- `src/ashare_research/tools/m2_stage2k_scoring_shadow.py` extended:
  `self_history_dual_window_percentile` support, cycle-context hard-gap policy,
  and `--registry / --policy / --inputs` CLI args (default v1).
- v1 default path byte-identical (golden regression: v1 inputs → shadow v5 core
  results unchanged).

## 7. Decision gate

`PASS` (`VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS`)
when: v2 contracts created and supersede v1; semantic migration complete;
dual-window Decimal aggregation applied; PE cycle-context hard gap blocks the
valuation numeric score with no renormalization; shadow v6 and full sensitivity
v8 refreshed; non-valuation dimensions unchanged; production / overall score /
rank / recommendation / target price / peer / M3 all prohibited; v1 immutable.

`VALUATION_SCORING_V2_MIGRATION_INCOMPLETE` (conditional) if a v2 contract is
missing, the PE hard gap is not enforced fail-closed, the shadow v6 still
produces a valuation numeric score, or a non-valuation dimension changed.

`VALUATION_SCORING_V2_MIGRATION_NOT_TRUSTED` (fail) if production scoring is
enabled, an overall score is created, PE is assigned a numeric score, v1 is
overwritten, or the engine v1 golden path changes.

## 8. Product boundary

- No production scoring; no overall score / rank / recommendation / target
  price / peer percentile / M3.
- No **PE cycle-context method** designed this stage (PE numeric scoring
  remains blocked).
- No default-DB write; no market re-fetch; no percentile recomputation.
- v1 registry / policy / shadow v5 / sensitivity v7 / R4E.5 artifacts preserved
  as immutable history.

## 9. Validation (local)

- R4F.1 static/regression tests: see below.
- Full offline pytest, ruff, `git diff --check`, artifact-manifest verifier,
  secret-path scan, clean-clone check: see validation section of the work record.
- Protected files (`AGENTS.md`, `agent/goals/`, `acceptance/m2_stage2i2r_*`,
  stash, default DB, registry v4, R4E.5 artifacts, R4F decision) untouched.