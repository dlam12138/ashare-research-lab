# M2 Stage 2I.2R — Official Fact Extraction and Lineage Closeout

Status: `IMPLEMENTATION COMPLETE — PENDING SOL FINAL REVIEW`.

This supersedes the Stage 2I.2 extraction interpretation while preserving its
audit artifacts and the economic outcome: 9 acquired cells, 7 explicit gaps,
`ROIC_FACT_GAPS_REMAIN`, `shadow_status=NOT_RUN`, and no production ROIC.

## Corrections

- Numeric values are capture-derived through named groups and Decimal transforms;
  finance core records captured finance and lease operands and recomputes the
  parent from those operands.
- Cache report-year mapping is registry metadata based, not content-hash prefix
  inference.
- Reconciled Facts use `reconciled_derived` / `dual_official_reconciled`, retain
  both ordered input evidence records and an evidence-set digest.
- Seven missing cells carry versioned executed-search ledger fields and
  deterministic IDs.
- `decide_acquisition_gate()` implements READY, explicit-gap, and fail-closed
  unknown/untrusted outcomes with structured explanation.

## Protected state

No default database, protected Fact/Metric/definition baselines, value profile,
Plan v3 IDs/cells, shadow state, or external cache objects were modified.

## Validation

Targeted Stage 2I.2R tests: 20 passed. Full pytest at implementation HEAD
`b7707ad`: 1028 passed, 2 warnings; current documentation-head clean clone
at `ebf901d` reproduced 1029 passed, 2 warnings. Final test-only commits `aa47ce4`,
`6af8a5c`, `a9cb27c`, `90c2d3d`, and `78c4c4e` preserve that result while
refreshing the platform-stable manifest verifier. Final CI run `30816554022`
passed on both Windows and Ubuntu; formal decision is
`ROIC_FACT_GAPS_REMAIN`; shadow remains `NOT_RUN`.

Corrected serialized extraction lineage is independently recomputable. Formal
A/B artifact digest: `a323b4de6e987fa307bbf6b3c47e2e1403512bfa4872b7d1c12cd9574897ca35`.
