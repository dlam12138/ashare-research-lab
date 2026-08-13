# PetroChina value profile 2021–2026

As of trade date `2026-07-31`.

## Evidence-aware reading

The profile integrates the existing earnings/cash-quality, ROE/ROA, financial-safety, dividend, and PIT valuation layers. Announced and paid dividend yields are separate. Nine exact exchange payloads remain finite evidence gaps; their affected dividend inputs are partial or missing while non-dividend valuation continues.

## Capital-return evidence status

- ROE: `trusted_existing_results_unchanged`; accepted Stage 2D results and methodology are preserved.
- ROA: `trusted_existing_results_unchanged`; accepted Stage 2D results and methodology are preserved.
- ROIC: `not_computable_under_strict_evidence_contract`.
- Decision: `ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT`.
- Exact gaps: `M2G-ROIC-001`, `M2G-ROIC-002`, `M2G-ROIC-003`,
  `M2G-ROIC-004`, `M2G-ROIC-005`, `M2G-ROIC-006`, and `M2G-ROIC-007`.
- Shadow status: `not_run`.
- Production metric created: `false`.
- Score eligible: `false`.

No numeric, estimated, proxy, or zero ROIC is reported. This is an evidence
limitation, not a conclusion that PetroChina has poor capital returns. See
`docs/decisions/ADR-ROIC-001-strict-evidence-non-computability.md` and
`reports/m2_explicit_gap_ledger.json`.

Consumer migration: use `capital_return.roic` as the only current ROIC status
node. Do not interpret absence of a numeric value as zero and do not use the
historical `integrated_layers.roic=not_evaluated` state; it is now
`not_computable_under_strict_evidence_contract`.

## Technical integrity checks

- `future_data_leakage`: `not_observed_within_bounded_evidence`
- `canonical_identity_break`: `not_observed_within_bounded_evidence`
- `official_exchange_evidence_gap`: `observed`
- `non_positive_comparable_input`: `not_observed_within_bounded_evidence`

## Canonical current Stage 2H.1R risk profile

Contract `risk_universe_evaluation_v1`; methodology `risk_veto_methodology_v2`; formal status `conditional_pass`.
Missing evidence remains missing evidence and is not a negative conclusion.
- `modified_audit_opinion`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_d774875b76fd626f8dc3111a`
- `going_concern_material_uncertainty`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_36900a36e77ecf40dd8c2c42`
- `formal_regulatory_investigation_or_major_discipline`: `missing_evidence`; emitted `True`; observation `risk_observation_feff9792a99dd226f161cdb5`
- `material_error_restatement`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_052c3846c2a6bfa327cfb5cc`
- `controlling_shareholder_pledge_risk`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_3f80905aa96f00f364715499`
- `material_related_party_transaction_risk`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_fc9149e19ce39d95291879d9`
- `controlling_shareholder_fund_occupation_or_related_guarantee`: `missing_evidence`; emitted `True`; observation `risk_observation_a6fd612c59638073df29dbdf`
- `repeated_equity_financing_or_material_dilution`: `not_observed_within_bounded_evidence`; emitted `True`; observation `risk_observation_3bb97c18f6021ab3be2c7ae6`

Legacy migration: `governance_risk`, `audit_risk`, and `related_party_risk` are retained only under `legacy_risk_veto_checks` with `current=false`, `legacy=true`, and `do_not_use_for_current_profile=true`. Consumers must read `current_risk_veto_profile`.
