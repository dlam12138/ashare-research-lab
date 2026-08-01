# M2 Stage 2E-A：Financial Safety Methodology Contract

## Acceptance result

This stage freezes methodology and selection evidence only. It does not compute a financial
safety Fact or Metric and does not change the existing capital-return layer.

```text
M2 Stage 2E-A: PASS
Next module: FINANCIAL SAFETY
Financial safety methodology: TRUSTED
Minimum official fact foundation: ALLOWED
Interest coverage: BLOCKED
ROIC: NOT YET
Scoring: STILL NOT YET
```

## Candidate review

The four candidates were compared qualitatively on North Star contribution, conclusion-
changing ability, official availability, scope disagreement, PIT/restatement complexity, and
reuse of existing infrastructure. High/medium/low labels are descriptive; no weighted rank,
threshold, grade, or score was produced. Financial safety was selected because direct annual
balance-sheet/cash-flow boundaries are available to freeze and fit the existing Fact, PIT,
restatement, and lineage controls. The review is in
`docs/post_capital_return_north_star_review.md`.

## Frozen contract

- `asset_liability_ratio = total_liabilities / total_assets`;
- `gross_interest_bearing_debt` is the sum of five mutually exclusive direct components;
- `cash_coverage_of_interest_bearing_debt` uses canonical period-end cash and gross debt;
- `net_interest_bearing_debt = gross debt - canonical cash`, with negative values retained;
- interest coverage has no formula yet and is blocked;
- all methods are CAS consolidated, same 12-31 instant, `万元`, PIT-aware, explicit about
  missing/zero/negative/restatement status, and `score_eligible=false`.

The exact machine contract is
`config/value_evaluation_methodology_financial_safety_v1.json`; input boundaries are in
`docs/financial_safety_input_contract.md`.

## Protected boundaries

- No Fact, Metric, Schema, Identity, PIT, Engine, ROE/ROA, Rule 001—005, default DB, stash,
  or scoring-gate state changed.
- No network, PDF, cache, or default DB access was used for a computation.
- No ROIC, interest coverage, score, grade, threshold, price target, or investment instruction
  was generated.
- The Stage 2F baseline remains 201 Facts, 12 definitions, 77 results, 73 computed, 4
  insufficient, 17 links, 164 lineage, 60 final-latest, and 56 final-computed.

## Verification

`tests/test_financial_safety_methodology.py` validates the frozen method IDs, formulas,
input roles, official scope, status boundaries, direct debt-component policy, cash proxy
policy, blocked interest coverage, reference tailoring, and absence of scoring fields.
The complete command and result log is in
`agent/record/2026-08-01_1700_m2_stage2ea_financial_safety_methodology.md`.
