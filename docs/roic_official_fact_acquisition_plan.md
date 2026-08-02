# ROIC official-fact acquisition plan (Stage 2I)

Status: `REQUIRED` after the Stage 2I readiness audit. This is the smallest official batch that can support one internally consistent pre-production feasibility check for the frozen primary candidate:

`ROIC = NOPAT / average invested capital`

with Candidate B operating-profit bridge and the financing-view invested-capital construction. The plan does not authorize a production Metric, a value-profile update, scoring, or a market-mechanism calculation.

## Minimum batch for one internally consistent feasibility year

Use FY2024 as the feasibility year, with FY2023 as the opening balance. Acquire each item below from the same consolidated CAS scope and the same annual-report family:

### FY2024 duration inputs

- `operating_profit` (already canonical-ready; preserve the current Fact ID and PIT chain).
- Finance-cost decomposition: `finance_cost`, interest expense, lease-interest expense, borrowing-cost capitalization/expense, and material foreign-exchange or other finance components. The bridge must establish which components are eligible to add back and avoid double counting leases.
- Non-operating income/expense decomposition: investment income, associate/JV income, fair-value changes, disposal gains/losses, impairment/reversal, and other material non-operating items. Each exclusion must be matched to the invested-capital scope policy.
- Direct operating tax evidence: current tax and deferred tax expense, tax reconciliation items, and the official note detail needed to allocate tax to the operating bridge. Reported effective tax rate, statutory rate, or a clipped rate is not a canonical substitute.

### FY2023 opening and FY2024 closing balance inputs

- Parent equity and NCI.
- Short-term borrowings; current portions of long-term borrowings and bonds; long-term borrowings; bonds payable.
- Current and non-current lease liabilities, with the lease policy and any current/non-current reclassification evidence.
- Interest-bearing long-term payables, if present; do not substitute total liabilities or a generic debt field.
- Unrestricted monetary funds, restricted cash and other cash-purpose classifications. Do not subtract all cash by default.
- Financial assets at fair value and amortized cost, associate investment and joint-venture investment, plus the corresponding income lines. Goodwill is acquired for the frozen “include unless policy evidence requires otherwise” default and for the operating-view cross-check.
- Total assets and non-interest-bearing operating liabilities for an independent operating-view reconciliation; the financing view remains the primary view and the two views must reconcile within the stated tolerance.

### Official evidence package

For each concept, retain the consolidated annual report, audited financial statements/notes, and the exchange-hosted official copy or official announcement required by the existing dual-source contract. Record source URL, source hash, page/table/label, reporting scope, period end, announcement date, `available_at`, and the restatement supersession link. Use the latest eligible PIT fact, not the latest downloaded file.

## Full FY2020–FY2025 expansion

Repeat the same concept set for FY2020–FY2025. FY2020 is required as the opening balance for FY2021. Re-run the annual restatement chain after each later report and retain both the superseded and superseding Fact IDs. No year may use a different cash, lease, associate/JV, goodwill, tax, or debt policy merely because a source line is inconvenient.

## Acceptance gates

The batch is accepted only when:

1. Candidate B can be written as one deterministic bridge with no net-profit or parent-attributable-profit substitution, EBITDA substitution, manual plug, or LLM inference.
2. Direct operating tax is supported or the year remains non-computable; no silent tax fallback is allowed.
3. Opening and closing financing-view balances are complete, scope-matched, and PIT-selected; an ending balance alone is insufficient.
4. Cash, leases, NCI, associates/JVs and goodwill have explicit classification evidence and matching numerator treatment.
5. A clean-clone replay produces the same canonical Fact IDs, readiness matrix and evidence-gate decision without touching the default database.

Until these gates pass, the official decision remains `ROIC_FACT_ACQUISITION_REQUIRED` and the shadow status remains `NOT_RUN`.
