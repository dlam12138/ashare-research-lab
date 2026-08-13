# PetroChina ROIC official-fact readiness audit v2 (FY2020–FY2025)

- Formula candidate: `B_operating_profit_bridge_financing_view`
- Assessment as-of: `2026-08-03`
- Evidence gate: **BLOCKED_WITH_EXPLICIT_GAPS**
- Shadow: **NOT_RUN**
- Registry SHA256: `dd3dd0bc522344b50df375a72ca220255ae5678e111d11f2a3c1cc7e45bc25f8`
- Canonical inventory SHA256: `b9ed4d8df84017671ebe66255dc78726d154fe5903a8a70a3ef66e5325261661`

This is an evidence gate. It does not calculate ROIC, create a Metric Result, or modify the value profile.

## Coverage by year

| FY | Ready | Partial | Missing | Scope | Period | PIT | Restatement | Methodology | N/A |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 3 | 1 | 26 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2021 | 13 | 1 | 16 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2022 | 13 | 1 | 16 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2023 | 14 | 1 | 15 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2024 | 15 | 2 | 13 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2025 | 13 | 1 | 16 | 0 | 0 | 0 | 0 | 0 | 1 |

## Primary-formula blocking gaps

- FY2020 `nopat.operating_profit` / `operating_profit`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **missing_official_fact** (registry_components_unready)
- FY2021 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **missing_official_fact** (registry_components_unready)
- FY2022 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **missing_official_fact** (registry_components_unready)
- FY2023 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **missing_official_fact** (registry_components_unready)
- FY2024 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **partially_ready** (one_or_more_registry_components_unready)
- FY2025 `nopat.finance_cost_adjustment` / `finance_cost_adjustment`: **missing_official_fact** (registry_components_unready)
- FY2020 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2025 `nopat.lease_interest_expense` / `lease_interest_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `nopat.investment_income` / `investment_income`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.investment_income` / `investment_income`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.investment_income` / `investment_income`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.investment_income` / `investment_income`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `nopat.investment_income` / `investment_income`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2025 `nopat.investment_income` / `investment_income`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2025 `nopat.fair_value_net_change` / `fair_value_net_change`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2025 `nopat.asset_disposal_gain_loss` / `asset_disposal_gain_loss`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `nopat.other_non_operating_income_expense` / `other_non_operating_income_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `tax.operating_tax_expense` / `operating_tax_expense`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `tax.profit_before_tax` / `profit_before_tax`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2024 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (fact_not_eligible, source_type_not_allowed)
- FY2025 `invested_capital.non_controlling_interest` / `non_controlling_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.short_term_borrowings` / `short_term_borrowings`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.current_portion_of_long_term_borrowings` / `current_portion_of_long_term_borrowings`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.current_portion_of_bonds_payable` / `current_portion_of_bonds_payable`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.long_term_borrowings` / `long_term_borrowings`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.bonds_payable` / `bonds_payable`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.current_portion_of_lease_liabilities` / `current_portion_of_lease_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.lease_liabilities` / `lease_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.cash_and_cash_equivalents` / `cash_and_cash_equivalents`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.associate_investment` / `associate_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.joint_venture_investment` / `joint_venture_investment`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.goodwill` / `goodwill`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.noninterest_bearing_operating_liabilities` / `noninterest_bearing_operating_liabilities`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.interest_bearing_debt_total` / `interest_bearing_debt_total`: **missing_official_fact** (registry_components_unready)
- FY2020 `nopat.finance_cost_excluding_lease_interest` / `finance_cost_excluding_lease_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `nopat.finance_cost_excluding_lease_interest` / `finance_cost_excluding_lease_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `nopat.finance_cost_excluding_lease_interest` / `finance_cost_excluding_lease_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `nopat.finance_cost_excluding_lease_interest` / `finance_cost_excluding_lease_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `nopat.finance_cost_excluding_lease_interest` / `finance_cost_excluding_lease_interest`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2021 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2022 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2023 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2024 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2025 `invested_capital.qualifying_non_operating_assets` / `qualifying_non_operating_assets`: **partially_ready** (one_or_more_registry_components_unready)
- FY2020 `invested_capital.restricted_cash` / `restricted_cash`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.restricted_cash` / `restricted_cash`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.restricted_cash` / `restricted_cash`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.restricted_cash` / `restricted_cash`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2020 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2021 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2022 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2023 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2024 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)
- FY2025 `invested_capital.non_operating_financial_assets` / `non_operating_financial_assets`: **missing_official_fact** (canonical_concept_absent_for_fiscal_year)

## Frozen controls

- NOPAT is never net profit or parent-attributable profit.
- Invested capital requires opening and closing balances; ending-only is not computable.
- Cash is purpose-classified; all cash is never silently subtracted.
- PIT selects the latest legal visible chain tip; disconnected chains are unresolved.
