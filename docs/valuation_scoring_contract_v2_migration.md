# Valuation Scoring Contract v2 Migration — M2 Stage 2K.1R4F.1

Date: `2026-08-07`
Stage: `M2_STAGE_2K1R4F1` (IMPLEMENTATION / non-production shadow refresh)
Decision: `VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS`

This stage migrates the `valuation_attractiveness` scoring contract to v2 and
refreshes the non-production shadow and full sensitivity. It is implementation
of the frozen R4F decision (`VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`:
`DUAL_WINDOW_SINGLE_COMPONENT`, `EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN`). It is a
**non-production** stage: PE numeric scoring remains blocked, and
production scoring / overall score / rank / recommendation / target price /
peer percentile / M3 all remain prohibited.

---

## 1. What changed

New immutable v2 contracts replace the v1 valuation semantics (v1 files are
kept as immutable history):

| Contract | v1 (frozen) | v2 (new) |
|---|---|---|
| Registry | `value_dimension_scoring_registry_v1` | `..._registry_v2` |
| Policy | `value_dimension_scoring_policy_v1` | `..._policy_v2` |
| Shadow inputs | `..._shadow_inputs_v1` | `..._shadow_inputs_v2` |
| Shadow | `..._shadow_v5` | `..._shadow_v6` |
| Sensitivity | `..._sensitivity_v7` | `..._sensitivity_v8` |

Valuation components migrated (semantic + benchmark):

| Component | v1 metric role | v2 metric role | v2 benchmark |
|---|---|---|---|
| `va_pe` | `a_share_price_to_latest_annual_parent_earnings` | `PE_A_TTM` | `self_history_dual_window_percentile` |
| `va_pb` | `a_share_price_to_latest_year_end_parent_equity` | `PB_A_MRQ` | `self_history_dual_window_percentile` |
| `va_ps` | `a_share_price_to_latest_annual_revenue` | `PS_A_TTM` | `self_history_dual_window_percentile` |

The three components remain **single components** (no splitting into six). Each
binds `percentile_3y + percentile_5y` with window weights `3y=0.5 / 5y=0.5`,
and the dual-window percentile is `(p3y + p5y) / 2` computed with **Decimal
arithmetic only** (never float identity). The aggregation contract is
`self_history_dual_window_percentile_v1`.

## 2. PE cycle-context hard gap (Section 三 of the task spec)

`va_pe` carries the frozen hard-gap status `coverage_gap_cycle_context_required`.
The policy v2 adds `non_renormalizable_gap_statuses = [coverage_gap_cycle_context_required]`.
When a registered valuation component carries that status, the
`valuation_attractiveness` dimension:

- **must not** produce a numeric score;
- **must not** renormalize the remaining weights;
- still reports `eligible_weight`, `covered_weight`, `coverage_ratio`,
  `missing_component_ids`, and `blocked_component_ids`;
- has dimension `status = insufficient_evidence_cycle_context`, `score = null`,
  `band = null`.

Blocked is **not** `score = 0`; the component is **not** deleted and its
registered `0.20` weight is **not** reassigned. The PE percentile remains
`TRUSTED_DESCRIPTIVE_EVIDENCE` only.

## 3. Shadow v6 result

In `reports/petrochina_dimension_scoring_shadow_v6.json`:

- `valuation_attractiveness`: `score = null`, `band = null`,
  `status = insufficient_evidence_cycle_context`, `coverage_ratio = 0.6`,
  `missing = [va_pe, va_dividend_yield]`, `blocked = [va_pe]`.
- `va_pb` component score `12.0417`, `va_ps` component score `6.4332`
  (visible per-component, but **no dimension-level numeric score**).
- `enterprise_quality` (73.6694 / B) and `value_realization_capacity`
  (21.7562 / D) are unchanged from shadow v5 — the v5→v6 diff is confined to
  the valuation dimension.

## 4. Sensitivity v8

`reports/petrochina_dimension_scoring_sensitivity_v8.json` re-runs the full
weight-perturbation sweep (38 scenarios) over the v2 contracts. The valuation
dimension remains blocked (`insufficient_evidence_cycle_context`) in every
scenario because `va_pe` always carries the hard-gap status; no scenario
renormalizes past the gap. Non-valuation dimensions show the expected
perturbation deltas.

## 5. Engine extension

`src/ashare_research/tools/m2_stage2k_scoring_shadow.py` was extended
(Section 八 of the task spec):

- Added `self_history_dual_window_percentile` benchmark support in
  `_component_score` (reads `dual_window_percentile_decimal` as a Decimal
  string, computes `score = 100 - dual` for `lower_better`, never from floats).
- Added the cycle-context hard-gap status handling (blocked, not zero).
- Added the hard-gap policy check in `compute_dimension`
  (`non_renormalizable_gap_statuses` → `insufficient_evidence_cycle_context`).
- Added `--registry / --policy / --inputs` CLI args (default v1).

The **v1 default path is byte-identical**: the golden regression test confirms
the v1 registry/policy + capsule-derived inputs reproduce shadow v5 core
results exactly (enterprise_quality 73.6694, valuation 12.1733,
value_realization_capacity 21.7562).

## 6. Explicitly not authorized / not done

- **PE numeric scoring**: not produced; blocked pending a formal cycle-context
  contract.
- **Production scoring**: NOT_AUTHORIZED.
- **overall score / rank / recommendation / target price / peer percentile /
  M3**: all prohibited.
- **PE cycle-context method**: not designed this stage.

## 7. Artifacts

- `config/value_dimension_scoring_registry_v2.json`
- `config/value_dimension_scoring_policy_v2.json`
- `config/value_dimension_scoring_shadow_inputs_v2.json`
- `reports/petrochina_score_input_capsule_v5.json`
- `reports/petrochina_dimension_scoring_shadow_v6.json`
- `reports/petrochina_dimension_scoring_shadow_v5_to_v6_diff.json`
- `reports/petrochina_dimension_scoring_sensitivity_v8.json`
- `reports/m2_stage2k1r4f1_decision.json`
- `reports/m2_stage2k1r4f1_artifact_manifest.json`
- `docs/valuation_scoring_contract_v2_migration.md`
- `acceptance/m2_stage2k1r4f1_valuation_scoring_v2_migration.md`
- `tests/test_m2_stage2k1r4f1_valuation_scoring_v2_migration.py`
- `agent/record/2026-08-07_Stage2K1R4F1_valuation_scoring_v2_migration.md`