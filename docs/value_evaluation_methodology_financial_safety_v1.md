# Financial Safety Methodology v1

## Status

`financial_safety_v1` is a frozen methodology contract, not a computed metric release.
The contract is descriptive-evidence-only: every method has `score_eligible=false`, and
it contains no thresholds, grades, weights, target prices, or buy/sell instruction.
The machine-readable contract is
[`config/value_evaluation_methodology_financial_safety_v1.json`](../config/value_evaluation_methodology_financial_safety_v1.json).

The minimum official-fact foundation is allowed as the next implementation stage. No
financial-safety Fact or Metric is computed in Stage 2E-A. ROIC, interest coverage, and
scoring remain blocked.

## Selection evidence

The post-capital-return review compares the four North Star candidates qualitatively.
The dimensions are contribution to the North Star question, ability to change a research
conclusion, official availability, formula/scope disagreement, PIT/restatement complexity,
and reuse of the existing Fact/Context/Unit/PIT/lineage infrastructure. High/medium/low
are descriptive labels, not a weighted ranking.

| Candidate | North Star contribution | Conclusion-changing ability | Official availability | Scope disagreement | PIT/restatement complexity | Infrastructure reuse | Decision |
|---|---|---|---|---|---|---|---|
| ROIC | high | high | medium | high | high | medium | blocked until NOPAT and invested-capital concepts have one defensible contract |
| Financial safety | high | high | high | medium | medium | high | next module; allow minimum official-fact foundation |
| Dividends / realization | medium | medium | high | medium | high | medium | later; separate declaration, approval, ex-date, payment, buyback execution, and share-base events first |
| Valuation | high | high | medium | high | high | medium | later; PIT prices, share base, peer/industry basis, and scenario definitions are not yet frozen |

This selection is evidence-based rather than score-based. Financial safety is the only
candidate whose first four methods can be bounded with direct annual balance-sheet/cash-flow
inputs while preserving the repository's existing eligibility, `available_at`, restatement,
and lineage semantics. It directly answers the North Star risk question and can expose a
hard constraint before valuation or realization is interpreted. The selection does not
claim that financial safety is the final research conclusion.

## Frozen methods

### Asset-liability ratio

`asset_liability_ratio = total_liabilities / total_assets`.

Both inputs are reconciled eligible CAS consolidated instant facts in the same unit at the
same 12-31 date. Missing input is `missing_input`; zero total assets is
`undefined_zero_denominator`; negative total assets is
`not_comparable_negative_denominator`; `available_at` is the maximum of the inputs.

### Gross interest-bearing debt

`gross_interest_bearing_debt = short_term_borrowings +
current_portion_of_interest_bearing_non_current_liabilities + long_term_borrowings +
bonds_payable + lease_liabilities`.

The five gross-debt components are mutually exclusive and must be tied to the same CAS
consolidated 12-31 instant context and unit. `total_liabilities` and the existing generic
`interest_bearing_debt` concept are not substitutes. The current-portion concept may be
eligible only when an evidence-backed derivation sums current long-term borrowings,
current bonds, and current lease liabilities; a separately disclosed current long-term
payables row is excluded. If any component is not supported, the method is blocked; the
engine must not infer, subtract the aggregate, or double-count it.
Missing components remain `missing_input`. A negative component or total is
`not_comparable_negative_debt_component` until a later contract proves a valid sign policy.

### Cash coverage and net interest-bearing debt

`cash_coverage_of_interest_bearing_debt = cash_and_cash_equivalents /
gross_interest_bearing_debt`.

The canonical cash input is period-end `cash_and_cash_equivalents` from the cash-flow
statement. `monetary_funds` is only an explicit, separately evidenced proxy; restricted cash
is not canonical by default. Zero gross debt is `undefined_no_debt`; a negative gross-debt
denominator is not comparable; missing cash is `missing_input`, never zero. `available_at`
uses the maximum of the canonical cash fact and all expanded gross-debt component facts.

`net_interest_bearing_debt = gross_interest_bearing_debt - cash_and_cash_equivalents`.
Negative net debt is retained and displayed as computed; it is not clamped. The output must
show gross debt and canonical cash alongside net debt, with expanded lineage to every direct
component.

### Interest coverage remains blocked

No formula or numerator is frozen. The method cannot use `operating_profit` or
`finance_expense` as a guessed proxy. Before implementation, the contract must define the
interest expense recognition, capitalization, cash-paid, duration, and numerator boundaries.

## Shared input, PIT, and restatement contract

- Inputs are official CAS, consolidated, reconciled, eligible facts; no raw or ineligible
  fact is accepted.
- Balance-sheet and canonical cash inputs are same-date 12-31 instant facts in `万元`.
- `available_at` is the maximum of all direct inputs, including expanded inputs of a derived
  debt value; future facts cannot appear in an earlier AsOfQuery result.
- Missing is explicit and is never converted to zero. Zero denominators have method-specific
  undefined statuses; negative denominators have explicit non-comparable statuses.
- A changed eligible input creates a new metric version and a superseding version link.
  Unchanged inputs create no synthetic version. The 2025 review status remains
  `not_yet_reviewable`.
- Every input role has one lineage edge; derived debt outputs expand lineage to the five
  direct components. No average balance Fact is created.

## Mature-project and standards tailoring

The contract borrows architecture ideas, not code or prose. OpenBB's provider-to-standard-
model separation is trimmed to local concept mapping without network/provider behavior.
FinanceToolkit's reported-statement-to-transparent-derived-metric split is used for formula
disclosure without adopting its source normalization or fiscal-year conversion. Arelle's
Fact/Context/Unit and instant/duration distinctions are used for eligibility without copying
an XBRL processor. Pandera named checks and Great Expectations checkpoints motivate stable
future rule/checkpoint IDs, but neither framework is added. OpenLineage's run/input/output
vocabulary informs future manifests while the repository's existing lineage IDs remain
authoritative.

The current implementation boundary is therefore deliberately small: freeze the contract,
prove the minimum direct official facts, then add metrics only after the input contract and
PIT/restatement tests pass. No scoring gate is changed by this stage.

## Explicit non-goals

No ROIC, interest coverage, valuation multiple, dividend yield, buyback realization metric,
score, threshold, grade, price target, or investment recommendation is produced here.
