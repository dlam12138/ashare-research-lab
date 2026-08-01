# Financial Safety Input Contract

This document is the input boundary for `financial_safety_v1`. It authorizes a future
minimum official-fact foundation; it does not authorize fetching or computing it in
Stage 2E-A.

## Common eligibility

Every direct input must be:

- an official annual-report fact;
- CAS, consolidated, and reconciled/eligible;
- `unit=万元`;
- an instant fact at the same `12-31` period end;
- selected with `AsOfQuery.get_latest_available()` at the requested as-of date; and
- traceable to source, context, unit, `available_at`, and reconciliation evidence.

Raw, ineligible, unconsolidated, non-CAS, mixed-unit, future, and PDF/cache-only values are
not acceptable. Missing is not zero.

## Minimum direct inputs

| Concept | Required role | Source boundary | Current readiness |
|---|---|---|---|
| `total_assets` | asset-liability denominator | 12-31 consolidated balance sheet | concept exists; coverage must be proven |
| `total_liabilities` | asset-liability numerator | 12-31 consolidated balance sheet | concept exists; coverage must be proven |
| `short_term_borrowings` | gross-debt component | 12-31 consolidated balance sheet | concept exists; direct coverage must be proven |
| `current_portion_of_interest_bearing_non_current_liabilities` | gross-debt component | current portion, only when directly disclosed and mutually exclusive | not yet proven; absence blocks gross debt |
| `long_term_borrowings` | gross-debt component | 12-31 consolidated balance sheet | concept exists; direct coverage must be proven |
| `bonds_payable` | gross-debt component | 12-31 consolidated balance sheet | concept exists; direct coverage must be proven |
| `lease_liabilities` | gross-debt component | 12-31 consolidated balance sheet | concept exists; direct coverage must be proven |
| `cash_and_cash_equivalents` | canonical cash | period-end cash-flow statement line | concept exists; statement-source coverage must be proven |

The existing generic `interest_bearing_debt` concept is not accepted as a replacement for
the five-component gross-debt decomposition. `total_liabilities` is never a debt proxy.
If a filing combines current and non-current items, record the split as unresolved and stop;
do not infer, allocate, or count a component twice.

## Cash policy

`cash_and_cash_equivalents` is canonical. `monetary_funds` may be used only if the filing
explicitly establishes the same comparable boundary and the run records that proxy choice.
Restricted cash is excluded from the canonical value unless a future contract separately
proves comparability. No cash shortfall is filled with zero.

## Method-to-input map

| Method | Direct/expanded inputs | Missing or denominator boundary |
|---|---|---|
| `asset_liability_ratio` | `total_liabilities`, `total_assets` | missing; zero assets undefined; negative assets not comparable |
| `gross_interest_bearing_debt` | five direct debt components | any missing blocks; negative component/total not comparable |
| `cash_coverage_of_interest_bearing_debt` | canonical cash + five expanded debt components | missing; zero debt `undefined_no_debt`; negative debt not comparable |
| `net_interest_bearing_debt` | canonical cash + five expanded debt components | missing; negative result remains computed |
| `interest_coverage` | none authorized yet | blocked until expense/capitalization/cash-paid/numerator boundary |

## PIT and restatement rules

The future runner must be offline and run-scoped. At each annual-report availability date it
must query only facts whose `available_at` is not later than that date. A changed eligible
fact creates a new metric version and supersedes the prior version; unchanged years do not
create fake versions. The 2025 state is `not_yet_reviewable` until the review window opens.
Every direct input contributes one lineage edge, and derived debt outputs retain expanded
lineage to all five components.

## Foundation gate

The minimum foundation is allowed but not yet computed. The next implementation may proceed
only when it can prove direct official coverage, source/context/unit identity, reconciled
eligibility, PIT visibility, and restatement behavior for the table above. Until then the
methodology remains trusted while computation remains blocked.
