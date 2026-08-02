# ROIC Input Contract v1

This contract defines the evidence boundary for `value_evaluation_methodology_roic_v1`.
It is an input/readiness contract, not permission to write the default database or
create a production ROIC Metric Result.

## Common requirements

Every accepted input must be a canonical Fact or an explicitly registered
deterministic derivation with:

- exact canonical `concept_id` and `concept_version`;
- PetroChina `601857.SH`, CAS, consolidated scope;
- `unit=万元` and matching currency;
- annual duration for earnings and 12-31 instant for balances;
- official annual-report statement/note locator and source hash;
- canonical Fact ID, Context ID, `available_at`, fact version and restatement chain;
- `verification_status` verified/reconciled and `eligible_for_metrics=true`;
- no approximate mapping, PDF-only value, third-party proxy or silent zero.

## Primary bridge input roles

| Role | Concept ID | Period | Status requirement |
|---|---|---|---|
| operating earnings base | `operating_profit` | annual duration | exact official fact |
| finance adjustment | `finance_cost` / `interest_expense` | annual duration | official composition; no generic proxy |
| lease interest | `lease_interest_expense` | annual duration | required when leases are included |
| investment income | `investment_income` | annual duration | required when removing associate/investment scope |
| fair-value adjustment | `fair_value_change` | annual duration | required if included in operating profit |
| disposal/other adjustment | `asset_disposal_gain_loss`, `other_non_operating_income_expense` | annual duration | exact official note mapping |
| operating tax | `operating_tax_expense` or direct allocated tax bridge | annual duration | required for canonical NOPAT |

## Primary financing-view invested-capital roles

| Role | Concept ID | Period | Policy |
|---|---|---|---|
| parent equity | `equity_attributable_to_parent` | instant | included |
| NCI | `non_controlling_interest` | instant | included for consolidated NOPAT |
| debt | `short_term_borrowings`, `long_term_borrowings`, `bonds_payable` | instant | components only |
| current debt | `current_portion_of_interest_bearing_non_current_liabilities` | instant | derived from proven components only |
| leases | `current_portion_of_lease_liabilities`, `lease_liabilities` | instant | matched to lease-interest treatment |
| other debt | `interest_bearing_long_term_payables` | instant | conditional; no aggregate proxy |
| non-operating asset exclusions | `cash_and_cash_equivalents`, `monetary_funds`, `restricted_cash`, `financial_investments`, `associates_and_joint_ventures` | instant | classification must be explicit and matched to numerator |
| goodwill | `goodwill` | instant | included by default |
| deferred tax | `deferred_tax_assets`, `deferred_tax_liabilities` | instant | conditional scope |

## Secondary operating-view roles

`total_assets`, major operating assets (`property_plant_equipment`,
`oil_and_gas_properties`, `construction_in_progress`, `exploration_expenditure`),
and non-interest-bearing operating liabilities (`accounts_payable`,
`contract_liabilities`, `taxes_payable`, `employee_benefits_payable`,
`provisions`) are required to reconcile the operating view. A component that is
not exact remains `methodology_unresolved` or `missing_official_fact`; it is not
mapped from a nearby label.

## Period, PIT and restatement

FY2020 is needed as the opening balance for FY2021. A FY2020 comparative value
from the FY2021 report may serve as a `comparison_only_opening_baseline`, but it
does not become a standalone FY2020 annual duration fact. Each FY2021-FY2025
calculation requires both opening and closing inputs. `available_at` is the
maximum of all numerator, adjustment and denominator input dates. A later
comparative restatement supersedes the prior Fact and creates a new shadow
result; it never rewrites an earlier as-of view.

## Explicit non-acceptance

The following are never accepted as NOPAT or key inputs: net profit, parent-
attributable profit, EBITDA, total liabilities as debt, generic interest-bearing
debt as the five-component debt decomposition, all-cash subtraction without an
evidence-backed boundary, an ending balance when opening capital is missing,
manual plugs, or LLM-generated adjustments.
