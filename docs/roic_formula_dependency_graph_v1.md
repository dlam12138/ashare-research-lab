# ROIC formula dependency graph v1

The machine authority is `config/roic_formula_dependency_graph_v1.json`.
Registry v2, readiness and acquisition plan v3 must validate against its
digest and node semantics.

## Frozen primary bridge

```text
finance_cost_adjustment
  = finance_cost_excluding_lease_interest + lease_interest_expense

operating_earnings_before_tax
  = operating_profit
  + finance_cost_adjustment
  - investment_income
  - fair_value_net_change
  - asset_disposal_gain_loss

NOPAT = operating_earnings_before_tax - operating_tax_expense
```

Only `finance_cost_adjustment` contributes to the final bridge. Its two
components must both be official, signed inputs; neither is added again. If
either component is absent or cannot be separated from official disclosure,
the composite remains unready. A manual plug is forbidden.

Investment income, fair-value net change and asset-disposal gain/loss are
separate signed adjustments. CAS presents all three inside operating profit,
so each is primary. Other non-operating income/expense follows operating
profit in the CAS statement and is therefore secondary reconciliation only.
This classification is based on statement membership, not PetroChina values.

Direct operating tax remains an independent hard blocker. Effective tax rate,
net-profit rate, statutory rate and silent zero are not substitutes.

## Invested capital and policy split

`policy.non_operating_asset_classification` is a resolved methodology choice:
it has no amount, unit, currency or Fact identity. The separate
`invested_capital.qualifying_non_operating_assets` role is an amount-bearing
deterministic derivation. It cannot be directly acquired or hand-entered.

The frozen policy never subtracts all cash, never treats restricted cash as
freely available, never guesses operating cash, admits financial assets only
with official non-operating proof, matches associate/JV deductions with the
investment-income adjustment, retains unproven assets with an evidence
limitation, and never creates a balancing plug.

## No-double-count rules

- Composite components have `included_in_parent=true` and zero independent
  formula membership.
- A parent and its component cannot both be acquisition contributions.
- Finance/lease scope matching and associate/JV numerator/denominator matching
  are fail-closed.
- Operating-tax has no derivation or fallback edge.
