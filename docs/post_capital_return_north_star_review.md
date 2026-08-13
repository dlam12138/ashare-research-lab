# Post-Capital-Return North Star Review

## Review outcome

After the ROE/ROA capital-return layer became trusted, the next North Star review compares
four candidates: ROIC, financial safety, dividends/realization, and valuation. The result is
not a numeric rank and does not authorize scoring. Financial safety is selected as the next
module because it has the strongest evidence-supported first implementation boundary and
answers the North Star's risk question before later valuation or realization interpretation.

```text
Next module: FINANCIAL SAFETY
Financial safety methodology: TRUSTED
Minimum official fact foundation: ALLOWED
Interest coverage: BLOCKED
ROIC: NOT YET
Scoring: STILL NOT YET
```

## Qualitative comparison

High/medium/low describe evidence and engineering fit only. There is no aggregation,
weighting, threshold, grade, or trade decision.

| Candidate | North Star contribution | Conclusion-changing ability | Official availability | Scope disagreement | PIT/restatement complexity | Existing infrastructure reuse | Selection state |
|---|---|---|---|---|---|---|---|
| ROIC | high | high | medium | high | high | medium | not next; NOPAT and invested capital are not uniquely registered |
| Financial safety | high | high | high | medium | medium | high | selected next; methodology frozen, foundation allowed |
| Dividends / realization | medium | medium | high | medium | high | medium | later; payment/execution and share-base event chain not frozen |
| Valuation | high | high | medium | high | high | medium | later; PIT market inputs and scenario/peer definitions not frozen |

## Evidence and scope

The North Star asks whether a company merits long-term research, what could invalidate that
view, and how value may be realized. Financial safety directly covers asset-liability load,
interest-bearing debt composition, cash coverage, net debt, and contingencies/guarantees as
future evidence. The first four methods can use direct annual statement lines and reuse the
existing Fact/Context/Unit, `available_at`, PIT, restatement, and lineage controls.

ROIC remains blocked because NOPAT and invested capital require choices about tax, interest,
goodwill, operating leases, excess cash, and period averaging that are not yet one
reconciled contract. Dividends and realization require separate declaration, approval,
ex-date, payment, buyback authorization/execution, cancellation, and share-base events;
announced distribution is not execution evidence. Valuation requires PIT prices, shares,
market-cap/enterprise-value definitions, peer/industry basis, historical percentile rules,
and scenario assumptions; a low multiple alone is not a margin-of-safety conclusion.

These are scope decisions, not statements that the candidates are unimportant. They preserve
the existing rule that missing evidence is visible and that no candidate is converted into a
score before the scoring-readiness gates are satisfied.

## Methodology contract selected

The selected contract is
[`value_evaluation_methodology_financial_safety_v1.md`](value_evaluation_methodology_financial_safety_v1.md)
with machine form at
[`config/value_evaluation_methodology_financial_safety_v1.json`](../config/value_evaluation_methodology_financial_safety_v1.json).
It freezes asset-liability ratio, gross interest-bearing debt, cash coverage, and net
interest-bearing debt boundaries. Interest coverage remains blocked until its numerator and
interest expense/capitalization/cash-paid boundary are evidenced.

## Mature-project and standards references

The review borrows and trims established patterns: OpenBB's provider-to-mapping-to-standard-
model separation; FinanceToolkit's reported-fact-to-derived-metric transparency; Arelle's
Fact/Context/Unit and instant/duration model; Pandera and Great Expectations' named checks and
checkpoint validation; and OpenLineage's run/input/output lineage vocabulary. None of these
introduces a network provider, a new schema, a copied implementation, or an override of the
repository's existing identity, PIT, reconciliation, and lineage contracts.

## Explicitly not selected yet

ROIC is `NOT YET`; interest coverage is `BLOCKED`; scoring remains `STILL NOT YET`. No ROIC,
score, grade, threshold, price target, or buy/sell output is created by this review.
