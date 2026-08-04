# M2 Stage 2K — Explainable Independent-Dimension Scoring Methodology v1

Contract: `value_dimension_scoring_methodology_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose and boundary

This methodology defines a transparent, independent-dimension scoring contract
for the M2 value-assessment product. It is deliberately **not** a composite
stock score. It produces four independent dimension results and never an
overall score, ranking, recommendation, target price, upside probability, or
portfolio weight.

Every score component binds to a stable canonical Metric Result, evidence
observation, or evidence slot. No component may reference a value by display
label alone. No component may be produced by an LLM. All scoring is
deterministic and reproducible from committed inputs.

## 2. The four dimensions

The top-level dimensions are fixed for this stage and there is no fifth
overall dimension:

1. `enterprise_quality` — is this a good business?
2. `valuation_attractiveness` — is the current price attractive?
3. `value_realization_capacity` — how is value realized (dividends, buybacks)?
4. `risk_and_evidence_integrity` — what risk and evidence gaps exist?

The North Star requires separating "good company", "good price", and "good
investment". These four dimensions preserve that separation. `valuation_attractiveness`
answers "good price"; `enterprise_quality` answers "good company";
`value_realization_capacity` answers "good investment path"; and
`risk_and_evidence_integrity` captures the veto and evidence constraints that
must not be averaged away.

## 3. Score, coverage, and confidence are three different outputs

Every dimension result contains three distinct values:

- **score / grade** (or `insufficient_evidence`): the dimension's own ordinal
  or descriptive result.
- **coverage**: how much registered weight is actually covered by valid inputs.
- **evidence confidence**: how much the underlying evidence is trusted, reduced
  by explicit Stage 2F/2H/ROIC gaps.

A high score with low coverage or low confidence must not be described as a
strong conclusion. A missing input is never zero and never silently dropped.

## 4. Benchmark modes

Four benchmark modes are recognized and evaluated separately. Modes are never
blended without an explicit transform and rationale.

1. `absolute_contract` — a frozen, sourced threshold or piecewise band on the
   raw value. Used where no peer or long history exists.
2. `self_history_percentile` — the PIT-safe percentile of the current value
   within the issuer's own 3y/5y/expanding history. Only observations visible
   as of the score date are used.
3. `peer_percentile` — percentile within a peer universe. **Not available in
   this stage** because only one issuer vertical slice exists. This is a
   bounded future enhancement, disclosed, never fabricated.
4. `binary_or_categorical_evidence` — a deterministic flag or category from an
   evidence slot (e.g. risk-veto status, PIT/lineage status). Used for the
   risk/evidence dimension.

## 5. Representation

The primary representation is a transparent **ordinal band A–E** plus a
**numeric 0–100 shadow score** used for sensitivity analysis. The band is the
final output; the numeric score is internal and disclosed. The band mapping is
frozen before any shadow result is viewed:

- `A` → 80–100
- `B` → 60–80
- `C` → 40–60
- `D` → 20–40
- `E` → 0–20

A dimension may also output `insufficient_evidence`, `blocked_by_risk_veto`,
`not_applicable`, or `not_trusted` instead of a band.

Thresholds and transforms are frozen before the PetroChina shadow run. No
threshold is selected after inspecting which result is more attractive.

## 6. Missingness, coverage, and confidence rules

1. A missing input is never zero.
2. A missing input is never silently dropped; it appears in `missing_component_ids`.
3. Weight renormalization is allowed only under a frozen policy and only above
   `minimum_coverage_gate` (registered per dimension).
4. Both original and effective weights are reported when renormalization is used.
5. Below the coverage gate, the dimension returns `insufficient_evidence` and
   no numeric score.
6. ROIC absence reduces `enterprise_quality` coverage; it is never a zero and
   never described as poor capital return.
7. Stage 2F/2H gaps reduce evidence confidence according to an explicit rule
   (see policy); they do not automatically lower the business-quality score.
8. Evidence confidence is never disguised as business quality.
9. A trusted high score with low coverage is not a strong conclusion.
10. All missingness and confidence rules are frozen before the shadow run.

## 7. Risk vetoes are non-compensatory

Risk-veto slots are separate flags. A triggered veto (e.g. modified audit
opinion, formal regulatory investigation) sets the `risk_and_evidence_integrity`
dimension to `blocked_by_risk_veto` and is surfaced beside every dimension. No
high enterprise, valuation, or realization score may erase a veto flag. Missing
risk evidence is never interpreted as no risk.

## 8. Weights

Weights are defined only within the four top-level dimensions. There are no
weights across top-level dimensions because no overall score exists. Weights
are justified by theory or evidence, never merely as "reasonable". The policy
documents the equal-weight, theory-informed, and no-aggregation evidence-card
comparisons.

## 9. Sensitivity and stability

Before a dimension is considered production-ready, the following are run and
recorded:

- each weight ±25% within the dimension;
- leave-one-component-out;
- an alternative allowed transform;
- coverage-threshold perturbation;
- one-grade/band stability;
- missing-ROIC scenario;
- unresolved dividend/risk-evidence scenario.

A dimension is **not** production-ready when a reasonable change moves its
score or band by more than a pre-registered stability tolerance.

## 10. Cycle and industry interpretation

A cyclical company (oil/gas) is interpreted with an explicit cycle rule. A low
PE at a possible cycle peak must not automatically receive a high valuation
score. The valuation dimension reports the historical percentile and the cycle
limitation together; it does not claim a low PE is a buy.

## 11. Prohibited fallbacks

The following are always forbidden:

- substituting a missing value with zero;
- silently reweighting away ROIC or any unavailable metric;
- using a tax rate, residual split, or plug for ROIC;
- treating missing evidence as evidence of no risk;
- using an unregistered peer as a benchmark;
- producing an overall score, ranking, recommendation, or target;
- running an LLM to assign a score;
- selecting thresholds after viewing the PetroChina result.

## 12. References

- Both North-Star files.
- OECD/JRC composite-indicator guidance (theoretical framework, normalization,
  missing-data treatment, weight transparency, sensitivity reporting, and the
  warning that composites can mislead). Not copied: country-ranking assumptions
  and indiscriminate aggregation into one index.
- FinanceToolkit (transparent formula and input/output contracts). Not copied:
  US-GAAP-ratio assumptions and Piotroski/Altman as a universal A-share score.
- CFA equity-research guidance (separate business quality, valuation, and risk;
  multiple valuation methods; peer-group rationale). Not copied: target-price
  and recommendation sections.
- Repository Stage 2G artifact reproducibility, Stage 2H non-compensatory risk
  slots, Stage 2I fail-closed missing assignment, and Stage 2J canonical gap
  ledger.

See `docs/value_dimension_scoring_input_contract.md` for the exact input
eligibility and `config/value_dimension_scoring_registry_v1.json` for the
machine-readable component registry.