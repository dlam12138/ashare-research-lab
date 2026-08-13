# Post-Percentile Scoring North-Star Review — M2 Stage 2K.1R4F

Date: `2026-08-07`
Stage: `M2_STAGE_2K1R4F` (REVIEW / DECISION)
Decision: `VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`

This is a **review / decision** stage. It re-examines the
`valuation_attractiveness` scoring contract against the CI-confirmed R4E.5
trusted percentile profile and freezes the method and boundary of the
next-stage v2 valuation scoring migration. It does **not** modify any scoring
registry, policy, engine, shadow, or sensitivity, and it does **not** compute a
score.

---

## 1. Verified review baseline

- Branch / local HEAD / origin / direct remote: `feat/m2-value-assessment-mvp`
  at `017b656`; local == origin (0/0).
- R4E.5 remote CI: GREEN — run `31151600368` (push `6a088e7`) and run
  `31152356097` (final tip `017b656`); Ubuntu and Windows clean-clone both
  `1665 passed, 3 skipped`; identity-compare pass.
- Default `data/research.duckdb` SHA-256 unchanged:
  `4a71d3c7b88c0b16…` (financial_facts=0, protected baseline).
- Protected baseline: **354 Facts / 102 Metric Results / 16 definitions**.
- R4E.5 decision:
  `PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED`
  — `record_count = 6`, `oracle_identical = true`,
  `all_windows_ready = true`, `non_production = true`,
  `score_eligible = false`.
- Percentile profile: `petrochina_pit_valuation_percentile_profile_v1`,
  rank method `MIDRANK_EMPIRICAL_PERCENTILE`, as-of `2026-07-31`.
- Scoring artifacts reviewed: registry v1, policy v1, shadow v5, sensitivity
  v7, readiness gates v2, post-M2 scoring North-Star review.
- Protected untracked `AGENTS.md`, `agent/goals/`, the existing stash, and the
  pre-existing Stage 2I.2R acceptance wording edit are outside this decision.

---

## 2. References reviewed

1. **MADR / Architecture Decision Records** — the practice of recording a
   decision's context, drivers, options, chosen outcome, consequences, and
   confirmation in a stable, reviewable artifact.
2. **Semantic Versioning (SemVer) semantics** — a frozen, released contract
   must not silently change meaning; a semantically incompatible change must be
   a new version, not an in-place edit.

Reviewed sources grounded in this repository: `config/value_dimension_scoring_registry_v1.json`,
`config/value_dimension_scoring_policy_v1.json`,
`docs/value_scoring_readiness_gates_v2.md`,
`docs/post_m2_closeout_scoring_north_star_review.md`,
`reports/petrochina_dimension_scoring_shadow_v5.json`,
`reports/petrochina_dimension_scoring_sensitivity_v7.json`.

### 2.1 MADR — borrowed, not copied

| Borrowed | Why applicable | Repository-specific cut |
|---|---|---|
| `Context` | The migration happens for a concrete, historical reason (a trusted PIT/dual-window percentile upstream now exists). | Written once per decision record; no new ADR index or numbering system. |
| `Decision Drivers` | The choice must be driven by the North Star and prior frozen policy, not by today's percentile values. | Drivers are the fixed list in §5 of this document. |
| `Considered Options` | Five window models were genuinely considered (§5). | Recorded as a matrix; no legal-style prose duplication. |
| `Decision Outcome` | The chosen dual-window single-component model must be stable and reviewable. | Expressed as a JSON decision artifact, not a prose-only ADR. |
| `Consequences` | The migration's costs and blocked paths must be explicit. | Consequence list in §15. |
| `Confirmation` | The decision must be verifiable (tests + CI). | Static decision tests + full CI. |

**Not copied**: a full ADR infrastructure, a new numbering scheme, any change to
the existing `docs/decisions/` governance, or a one-ADR-per-option library.

### 2.2 Semantic Versioning — borrowed, not copied

| Borrowed | Why applicable | Repository-specific cut |
|---|---|---|
| Frozen released contracts must stay immutable. | `value_dimension_scoring_registry_v1` and `value_dimension_scoring_policy_v1` are frozen and CI-verified. | They are marked `IMMUTABLE_HISTORY`; never overwritten. |
| A semantically incompatible change must be a new version. | TTM/MRQ and dual-window are not backward compatible with the v1 annual/year-end single-window semantics. | The next stage creates `registry_v2.json` / `policy_v2.json` with `supersedes v1`. |

**Not copied**: changing the whole project/package to SemVer, or bumping the
package version for this review.

---

## 3. Scope boundary (what R4F covers)

R4F reviews **only** `valuation_attractiveness`. It does **not** modify or
re-scope `enterprise_quality`, `value_realization_capacity`, or
`risk_and_evidence_integrity`. Risk vetoes remain non-compensatory. No overall
score and no fifth dimension is created.

---

## 4. Method-selection governance (hard rule)

R4F **must not** choose a method because of PetroChina's current percentile
values. The actual midrank percentiles are reported at the end of this document
for evidence only and are **not** part of the option-choice rationale. R4F also
does **not** compute "what would option A score" / "what would option B score"
and then pick the more convenient one.

Method selection uses **only**:

- the North Star (low PE at a possible cycle peak must not auto-score high);
- prior frozen policy (component topology, missingness, coverage, non-production);
- avoiding double counting (do not weight one economic signal twice);
- explainability;
- PIT exactness;
- determinism;
- the existing scoring topology (three va component slots);
- the fewest new free parameters.

---

## 5. Five window options compared on fixed axes

Evaluation axes (fixed): `north_star_alignment`,
`uses_trusted_R4E5_evidence`, `avoids_double_counting`,
`preserves_component_topology`, `adds_free_parameters`, `cycle_safety`,
`explainability`, `determinism`, `migration_complexity`,
`production_false_precision_risk`.

| Option | Verdict | Rationale (no percentiles) |
|---|---|---|
| **A `THREE_YEAR_ONLY`** | REJECT | Closest to the old engine, but it discards the trusted 5y evidence and contradicts the policy/dual-window intent. |
| **B `FIVE_YEAR_ONLY`** | REJECT | Longer look-back, but arbitrarily drops 3y and the North Star asks to observe both 3y and 5y. |
| **C `SIX_SEPARATE_COMPONENTS`** | REJECT | 3y and 5y are overlapping windows of the same valuation signal; splitting them into six components double-counts the same economic signal and breaks the three va-slot topology. |
| **D `DUAL_WINDOW_SINGLE_COMPONENT`** | ACCEPT | Keeps `va_pe/va_pb/va_ps` topology; each component binds both `percentile_3y` and `percentile_5y` as a dual-window evidence bundle; no double counting. |
| **E `EVIDENCE_CARD_ONLY_NO_SHADOW_REFRESH`** | REJECT AS DEFAULT | The North Star already authorizes independent dimension scoring and a non-production shadow exists; refusing migration entirely is too conservative. Production stays blocked regardless. |

The full option matrix is `reports/petrochina_post_percentile_scoring_option_matrix_v1.json`.

---

## 6. Frozen dual-window contract

Decision: `DUAL_WINDOW_SINGLE_COMPONENT`.

- Each of `va_pe`, `va_pb`, `va_ps` remains **one** scoring component.
- Input structure: `percentile_3y`, `percentile_5y`.
- `window_weights`: 3y = 0.5, 5y = 0.5.
- `dual_window_percentile = (percentile_3y + percentile_5y) / 2`.
- Must be **Decimal**, never float identity.
- Identity binds: R4E.5 profile digest, 3y `percentile_record_id`, 5y
  `percentile_record_id`, 3y rank numerator/denominator, 5y rank
  numerator/denominator, and `aggregation_contract_version`.
- Recommended contract: `self_history_dual_window_percentile_v1`.

Why 50/50: no new empirical parameter, honors both 3y and 5y, does not bias to
today's result, does not split one metric into two components, simple,
transparent, recomputable.

Prohibited: 0.7/0.3, 0.3/0.7, volatility-dynamic weighting, result-driven
window selection, machine-learned window weights.

---

## 7. Window spread is diagnostic only

Each component records `window_spread = abs(percentile_3y - percentile_5y)`.
It is **not** a threshold, does not change the score, and does not switch the
window. It is diagnostic evidence; later sensitivity may compare
`3y_only` / `5y_only` / `dual_window_mean`. The formal base contract stays
`dual_window_mean`.

---

## 8. PE cycle guard is a separate decision

This is the North-Star hard boundary. The current v1 `va_pe` is
`direction = lower_better`, which numerically maps a lower percentile to a
higher score; the registry carries a textual cycle warning but no numeric
cycle gate. That is insufficient.

R4F states: PE percentile is `TRUSTED_DESCRIPTIVE_EVIDENCE`, but until a formal
cycle-context contract exists, `va_pe` numeric score contribution is
`NOT AUTHORIZED`.

Recommended next-state status:
- `cycle_context_requirement = required_for_numeric_scoring`
- `cycle_context_status = not_yet_formalized`
- `component_shadow_status = coverage_gap_cycle_context_required`

Prohibited: auto-assign PE 0, auto-assign PE 50, silent deletion, substituting
PB/PS for PE, or "this time the high PE percentiles won't produce a wrong high
score." The North-Star contract must hold for all future states.

---

## 9. PB / PS migration decision

- **PB**: old `latest year-end parent equity` → `PB_A_MRQ`, benchmark = R4E.5
  dual-window percentile, numeric non-production shadow **ALLOWED AFTER V2
  MIGRATION**.
- **PS**: old `latest annual revenue` → `PS_A_TTM`, benchmark = R4E.5
  dual-window percentile, numeric non-production shadow **ALLOWED AFTER V2
  MIGRATION**.

Both remain `direction = lower_better`, but the wording is only "lower
historical valuation position" / "higher historical valuation position" — never
`cheap`, `undervalued`, `overvalued`, or `fair value`.

---

## 10. PE metric semantic migration

Frozen next-stage metric roles:
- `va_pe: PE_A_TTM`
- `va_pb: PB_A_MRQ`
- `va_ps: PS_A_TTM`

The schema/contract strings are read from the actual R4E.4/R4E.5 artifacts
(not invented): candidate v2 schema
`petrochina_pit_valuation_series_candidate_v1`; percentile contract schema
`pit_valuation_historical_percentile_v1` / 1.0; percentile record schema
`petrochina_pit_valuation_percentile_record_v1`. The next
`accepted_contract_versions` must bind these actual contracts;
`value_evaluation_methodology_valuation_pit_v1` can no longer be the **only**
accepted contract.

---

## 11. Component topology and weights retained

`valuation_attractiveness`: `multiple_position = 0.60`, `yield_position = 0.40`
unchanged. `va_pe = va_pb = va_ps = va_fcf_yield = va_dividend_yield = 0.20`
unchanged. Because PE is a temporary coverage gap pending the cycle guard, its
registered 0.20 weight must **not** be deleted, redistributed to PB/PS, or
silently renormalized before the coverage rule. The shadow still computes
coverage under the existing missingness/coverage policy.

---

## 12. Expanding percentile decision

Policy v1 writes `3y/5y/expanding PIT percentiles`, but the trusted R4E.5
contract freezes exactly `3y` and `5y`, and the North Star requires `3y` and
`5y`. Recommended v2 policy:
- `required_windows = ["3y", "5y"]`
- `expanding_percentile = NOT_REQUIRED`
- `future_extension_status = DEFERRED`

Do **not** temporarily recompute an expanding percentile to match the old
policy. If mechanism research later needs an expanding window, open a separate
stage.

---

## 13. Old contracts are immutable

- `value_dimension_scoring_registry_v1` → `IMMUTABLE_HISTORY`
- `value_dimension_scoring_policy_v1` → `IMMUTABLE_HISTORY`

The next stage may only create `config/value_dimension_scoring_registry_v2.json`
and `config/value_dimension_scoring_policy_v2.json`, never overwrite v1.
Each v2 must carry `supersedes: v1` and
`supersession_reason = trusted_pit_ttm_mrq_dual_window_percentile_migration`.

---

## 14. Old shadow's historical identity

`petrochina_dimension_scoring_shadow_v5.json` is preserved as
`VALID_HISTORICAL_NON_PRODUCTION_RESULT`, but its valuation percentile inputs
are `SUPERSEDED_FOR_FUTURE_SHADOWS` (old annual/year-end roles, legacy
percentile source, 3y-only scoring behavior). It is not an error or invalid; it
was legally produced under its contract, and a trusted newer upstream now
exists.

---

## 15. Sensitivity status is not washed away

Current `valuation_attractiveness`: `stability_status = NOT_STABLE`,
`max_score_delta = 3.1637`, `stability_tolerance = 1.0`; other dimensions also
remain NOT_STABLE. R4F does **not** lower tolerance, change bands, change
coverage gates, re-pick weights from new percentiles, or claim production
readiness. The next stage must re-run the full sensitivity after the shadow
refresh.

---

## 16. Production remains explicitly blocked

`production_scoring = NOT_AUTHORIZED`. Reasons at least: sensitivity
NOT_STABLE; one-issuer calibration; missing peer calibration; PE cycle-context
contract incomplete; ROIC evidence gap; dividend / risk evidence gaps; readiness
gates not lifted. A trusted percentile does **not** authorize production scoring.

---

## 17. Risk dimension and other dimensions are not migrated

Only `valuation_attractiveness` is in scope. No modification to
`enterprise_quality`, `value_realization_capacity`, or
`risk_and_evidence_integrity`. Risk veto remains non-compensatory. No overall
score, no fifth dimension.

---

## 18. Migration plan

`reports/petrochina_valuation_scoring_migration_plan_v1.json` records:
`current_registry = v1`, `target_registry = v2`, affected components
`va_pe/va_pb/va_ps`, unchanged components `va_fcf_yield/va_dividend_yield`,
semantic migrations, window contract, dual-window aggregation, cycle-guard
requirement, old-shadow status, expected next artifacts, and explicitly
not-authorized items (production scoring, overall score, rank, recommendation,
target price, peer percentile, M3).

---

## 19. Decision matrix

`reports/petrochina_post_percentile_scoring_option_matrix_v1.json` compares the
five window options on the fixed axes. No option is scored with actual
percentile values.

---

## 20. Formal decision

`reports/m2_stage2k1r4f_decision.json`:
- `decision = VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`
- `selected_window_contract = DUAL_WINDOW_SINGLE_COMPONENT`
- `selected_aggregation = EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN`
- `pe_numeric_scoring = BLOCKED_PENDING_CYCLE_CONTEXT_GUARD`
- `pb_numeric_shadow = ALLOWED_AFTER_V2_MIGRATION`
- `ps_numeric_shadow = ALLOWED_AFTER_V2_MIGRATION`
- `shadow_refresh = ALLOWED_AFTER_V2_MIGRATION`
- `production_scoring = NOT_AUTHORIZED`
- `overall_score = PROHIBITED`
- `peer_acquisition = NOT_AUTHORIZED_IN_THIS_STAGE`
- `M3 = NOT_STARTED`
- `next_stage = M2_STAGE_2K1R4F1_VALUATION_SCORING_CONTRACT_V2_MIGRATION_AND_SHADOW_REFRESH`

---

## 21. Decision gate

Leads to `PASS` (`VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED`) when:
old/new semantic gap complete; options reviewed; decision independent of
PetroChina's current result; dual-window contract frozen; double counting
blocked; PE cycle gap identified and fail-closed; v1 immutable; production
blocked; next stage non-production only.

`POST_PERCENTILE_SCORING_REVIEW_GAPS_REMAIN` (conditional) if upstream contract
identity cannot be confirmed, a migration semantic is ambiguous, or the old
scoring path is not fully audited.

`POST_PERCENTILE_SCORING_REVIEW_NOT_TRUSTED` (fail) if the review peeks at
results to choose a method, allows six-component double weighting, overwrites
v1, allows production, removes the cycle guard, or creates an overall score.

---

## 22. Actual percentile values (evidence only — NOT part of option choice)

Reported for transparency and reproducibility; they did **not** drive the
decision.

| metric | window | midrank percentile | rank numerator/denominator |
|---|---|---|---|
| PE_A_TTM | 3y | 91.964286 | 1339/1456 |
| PE_A_TTM | 5y | 93.270025 | 2259/2422 |
| PB_A_MRQ | 3y | 84.958791 | 1237/1456 |
| PB_A_MRQ | 5y | 90.957886 | 2203/2422 |
| PS_A_TTM | 3y | 91.964286 | 1339/1456 |
| PS_A_TTM | 5y | 95.169282 | 2305/2422 |

These are exactly the six trust-verified R4E.5 records (Python == DuckDB
oracle identical; future-leakage none).

---

## 23. Consequences

- Positive: trusted, PIT-exact, dual-window valuation inputs become the
  sanctioned upstream for the next non-production shadow; method is
  deterministic, explainable, and double-counting-free.
- Cost: registry v2 / policy v2 migration work; the PE cycle-context contract
  must be designed before PE numeric scoring; a full sensitivity re-run is
  mandatory after the shadow refresh.
- Blocked: production scoring, overall score, ranking, recommendation, target
  price, peer percentile, M3 remain not-authorized.

## Confirmation

Static decision tests (`tests/test_m2_stage2k1r4f_post_percentile_scoring_review.py`)
and the full CI pass confirm the decision does not depend on actual percentile
values, does not modify v1 scoring files, and fixes the dual-window contract.