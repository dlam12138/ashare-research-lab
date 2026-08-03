# M2 Stage 2I.2R — Official Fact Extraction and Lineage Closeout

Status: `CONDITIONAL PASS` pending independent Sol review and remote CI.

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

Targeted Stage 2I.2 tests pass with `PYTHONPATH=src`; full contract, clean-clone,
cross-directory and remote CI evidence remains for final Sol review.
