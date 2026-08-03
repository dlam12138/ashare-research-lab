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

Validated code HEAD: `7341a2d`. Targeted Stage 2I.2R tests: 76 passed. Full
pytest: 1043 passed, 2 warnings (main worktree 254.94s; clean clone 155.25s).
Fresh, cross-working-directory, and clean-clone formal A/B runs produced digest
`90632b11b4784a019f8765237fe0d4bafcf1b8a80ff5c681a57fba3798da2483`, 12
artifacts, and zero mismatches. Final-head CI run `30825336850` passed on
Ubuntu job `91725407528` and Windows job `91725407544`.

Corrected serialized extraction lineage is independently recomputable. The
final identities, typed specs, and internal committed packet verify against
`cb35113e81016ac9de2cd966b48174af425cfdb2aeb3fc5a0341afbe6cd1e57f`.
Older `a323...` and `1028/1029` figures are superseded historical evidence.
