# ROIC Methodology Contract v1 — PetroChina preflight

Methodology ID: `value_evaluation_methodology_roic_v1`
Version: `1`
Status: **frozen for Stage 2I readiness; no production computation**
Score eligible: `false`

This contract answers whether a transparent ROIC implementation is possible for
an integrated oil company. It separates audited facts from analytical choices.
Accounting standards define the source facts and presentation; they do not
define one universally official ROIC formula.

## 1. Core identity and scope

The analytical identity is:

```text
ROIC = NOPAT / average_invested_capital
average_invested_capital = (opening_invested_capital + closing_invested_capital) / 2
```

The primary scope is PetroChina consolidated, CAS, CNY, annual duration
earnings matched to adjacent 12-31 instant balances. A result is canonical
only when every included earnings item and capital item represents the same
economic scope. A gross-capital sensitivity may be descriptive, but it is not
renamed canonical ROIC when a defensible non-operating-asset boundary is absent.

Every output is `score_eligible=false`; this contract contains no weight,
threshold, rating, target price, buy, sell or recommendation field.

## 2. NOPAT candidate comparison and frozen primary

### Candidate A — EBIT bridge

```text
EBIT = profit_before_tax + eligible_interest_expense
NOPAT = EBIT - normalized_operating_tax
```

This is rejected as the primary candidate for the present acquisition batch.
Profit before tax contains investment, fair-value, disposal and other items;
interest expense must also be split from capitalized interest, lease interest
and non-operating finance items. It remains a reconciliation candidate only if
all adjustments are directly evidenced.

### Candidate B — operating-profit bridge (primary acquisition candidate)

```text
operating_earnings_before_tax = operating_profit
                              + finance_cost_adjustment
                              - investment_income_included_in_operating_profit
                              - fair_value_net_change_included_in_operating_profit
                              - asset_disposal_gain_loss_included_in_operating_profit
NOPAT = operating_earnings_before_tax - directly_allocated_operating_tax
```

Stage 2I.1R2 freezes `finance_cost_adjustment` as the deterministic composite
`finance_cost_excluding_lease_interest + lease_interest_expense`. Only the
composite parent enters the bridge. Both official components must be ready;
neither component is added again, and an inseparable disclosure remains
unready rather than becoming a manual plug.

Investment income, fair-value net change and asset-disposal gain/loss are
independent signed adjustments because CAS presents them inside operating
profit. Other non-operating income/expense follows operating profit and is a
secondary reconciliation item, not a primary adjustment. These classifications
are frozen from statement membership before acquisition and never from the
size or sign of PetroChina values.

This is not called clean EBIT. The primary candidate is selected because the
audited operating-profit line already exists in the canonical evidence layer,
while the bridge remains conservative: every adjustment must be an official
fact with a deterministic sign, period, scope and source. If the adjustment or
operating-tax facts are absent, the candidate is not computable.

### Candidate C — directly adjusted operating earnings

This candidate is permitted only when every adjustment is a direct official
fact and the transformation is registered. It cannot use LLM-generated
adjustments, balancing plugs, EBITDA, net profit or parent-attributable profit.
It is not the primary candidate because the current evidence layer does not
provide a complete deterministic adjustment ledger.

The selection is driven by evidence and scope matching, not by the resulting
ratio or by which candidate would produce a more attractive value.

## 3. Tax policy

The canonical order is:

1. directly allocated operating tax from official tax notes or an official
   bridge that separately identifies tax on the matched operating earnings;
2. reported current plus deferred income tax only as an evidence bridge, never
   silently assigned to operating earnings;
3. a normalized multi-year effective tax rate or statutory rate may be shown as
   a labelled proxy in a feasibility analysis, but it cannot produce canonical
   NOPAT or a production Metric Result without an explicit later contract.

The reported effective tax rate is `income_tax_expense / profit_before_tax`.
It is not clipped. Negative pre-tax income, rates outside the ordinary range,
one-off tax effects, loss carryforwards and deferred-tax valuation allowances
are retained as explicit flags. Loss years are `not_computable` for canonical
NOPAT unless direct operating-tax allocation is available. Missing tax facts
are `missing_official_fact`, never zero.

## 4. Invested capital: primary financing view and reconciliation view

### Primary financing view

```text
financing_capital =
    parent_equity
  + non_controlling_interest
  + short_term_borrowings
  + current_interest_bearing_non_current_liabilities
  + long_term_borrowings
  + bonds_payable
  + current_lease_liabilities
  + non_current_lease_liabilities
  + interest_bearing_long_term_payables
  - qualifying_non_operating_assets
```

Lease liabilities are included when lease interest is added back in the NOPAT
bridge. Current debt must be a proven component sum; the generic
`interest_bearing_debt` concept and `total_liabilities` are never substitutes.

### Secondary operating view

```text
operating_capital = operating_assets - non_interest_bearing_operating_liabilities
operating_assets = total_assets - qualifying_non_operating_assets
```

The operating view is used to reconcile the primary view where every operating
asset/liability classification is official and complete. Differences are
explained, not averaged away. A mismatch blocks a canonical result.

## 5. Frozen component policies

| Component | Policy | Required evidence |
|---|---|---|
| Parent equity | Included; consolidated scope only | `equity_attributable_to_parent`, 12-31 instant |
| NCI | Included in financing capital because primary NOPAT is consolidated; no parent-attributable substitution | Direct NCI balance and, where needed, NCI earnings |
| Short/long debt and bonds | Included by component; current portions separately identified | Audited balance sheet/notes, no aggregate proxy |
| Leases | Current and non-current lease liabilities included; lease interest must match the earnings bridge | Lease note and finance/interest breakdown |
| Cash | Never silently subtract all cash; subtract only a registered, evidence-backed qualifying non-operating/excess boundary. Otherwise retain cash and label gross-capital sensitivity descriptive | Cash-flow statement, monetary-funds/restricted-cash note, working-cash boundary |
| Monetary funds | Not interchangeable with cash and cash equivalents; conditional only with an explicit comparable-boundary proof | Audited note and scope proof |
| Restricted cash | Excluded from qualifying cash by default; conditional only when the contract proves availability and scope | Restricted-cash note |
| Financial investments | Excluded from primary operating capital only when the corresponding income is excluded from NOPAT; otherwise included with matching income | Financial-instrument note and fair-value/income items |
| Associates/JVs | Excluded by default together with associate/JV income; inclusion requires both sides and a matching scope decision | Long-term equity investment and associate/JV notes |
| Goodwill | Included by default as acquired operating capital; no automatic impairment reversal or manual plug | Goodwill roll-forward and impairment note |
| Deferred tax | Conditional; include only with a registered operating/non-operating classification and tax bridge | Deferred-tax asset/liability note |
| Operating current liabilities | Included in operating view only when non-interest-bearing classification is direct and complete | Payables, contract liabilities, tax and employee-benefit notes |
| Major operating assets | Included in operating view; oil/gas properties, PPE, construction in progress and exploration expenditure remain distinct evidence concepts | Audited statement and asset notes |

The former mixed `non_operating_asset_boundary` role is superseded. The
amount-free `policy.non_operating_asset_classification` decision is resolved in
`config/roic_methodology_decisions_v1.json`. The monetary
`invested_capital.qualifying_non_operating_assets` is a separate deterministic
derivation and cannot be acquired or entered directly. The rule does not
subtract all cash, never treats restricted cash as freely deductible, does not
guess operating cash, admits financial assets only with official
non-operating-purpose evidence, matches associate/JV deductions to the NOPAT
income adjustment, retains unproven assets with an evidence limitation and
forbids a balance-sheet plug.

## 6. Matching, averaging, PIT and restatement

- Consolidated operating earnings require consolidated invested capital and NCI
  treatment. Parent-attributable profit is never NOPAT.
- Associate/JV income and associate/JV investment are either both included or
  both excluded; otherwise the result is rejected as a scope mismatch.
- Lease earnings treatment and lease-liability treatment must be paired.
- Opening and closing invested-capital balances are both mandatory. Average is
  exactly `(opening + closing) / 2`; ending capital is never a fallback.
- FY2021 requires a valid FY2020 opening balance for every selected component.
- `available_at = max(all numerator, adjustment, opening and closing inputs)`.
- As-of queries use only versions with `available_at <= as_of_date`, selecting
  the latest visible version for the same canonical identity key.
- A restated input creates a superseding shadow result; the prior version is
  retained. A corrected input must not rewrite historical as-of results.
- Decimal precision is 28 with `ROUND_HALF_EVEN` and the repository's canonical
  quantum `0.000000000001`.
- A zero denominator is `undefined_zero_denominator`; a negative denominator is
  `not_comparable_negative_denominator`; no ratio is clipped or force-filled.

## 7. Industry and production boundaries

This contract is applicable to a non-financial integrated oil company, but the
large operating footprint, leases, associates/JVs, goodwill, overseas scope,
commodity cyclicality and capitalized interest make the evidence burden high.
Financial companies are not automatically eligible. This stage freezes policy,
audits readiness and, at most, produces one isolated non-production feasibility
artifact. It does not register a production ROIC definition, create a
production Metric Result, alter the current value profile or open scoring.

## 8. Reference review and repository-specific cuts

References, borrowed design ideas, and non-copied designs are recorded in the
North-Star review and the Stage 2I work record. The implementation reuses the
repository's Fact Identity, Context, Fact Repository, Service, PIT,
version-chain, Metric Engine and run-scoped artifact conventions. No external
financial-analysis framework is added as a runtime dependency.
