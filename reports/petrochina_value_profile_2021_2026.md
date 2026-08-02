# PetroChina value profile 2021–2026

As of trade date `2026-07-31`.

## Evidence-aware reading

The profile integrates the existing earnings/cash-quality, ROE/ROA, financial-safety, dividend, and PIT valuation layers. Announced and paid dividend yields are separate. Nine exact exchange payloads remain finite evidence gaps; their affected dividend inputs are partial or missing while non-dividend valuation continues.

## Stage 2H risk-veto evidence

The Stage 2H.1 `risk_veto_methodology_v2` slice covers FY2021-FY2025 using
hash-verified issuer and SSE annual reports, field-level normalization lineage,
PIT `available_at` and `conclusion_available_at`, deterministic versioned event
and observation IDs, active/superseded event versions, and bounded-search
registers. The formal run is `conditional_pass`: no risk trigger was observed;
two areas remain `missing_evidence` because the historical regulator/discipline
universe and the related fund-occupation/guarantee search are not fully
retrievable. Missing evidence is not a negative conclusion and the slice
remains `score_eligible: false`.

| Risk ID | Status |
|---|---|
| `modified_audit_opinion` | `not_observed_within_bounded_evidence` |
| `going_concern_material_uncertainty` | `not_observed_within_bounded_evidence` |
| `formal_regulatory_investigation_or_major_discipline` | `missing_evidence` |
| `material_error_restatement` | `not_observed_within_bounded_evidence` |
| `controlling_shareholder_pledge_risk` | `not_observed_within_bounded_evidence` |
| `material_related_party_transaction_risk` | `not_observed_within_bounded_evidence` |
| `controlling_shareholder_fund_occupation_or_related_guarantee` | `missing_evidence` |
| `repeated_equity_financing_or_material_dilution` | `not_observed_within_bounded_evidence` |

All eight observations include a v2 search-register ID, active/superseded event
IDs, evidence-lineage status, and an explicit conclusion-availability time.

Key audit matters remain separate from modified opinions; accounting-policy and
common-control comparative recasts remain outside error risk; ordinary related
party activity is not abuse; and a proposed or authorized share issue is not
realized dilution.

## Prior risk-veto statuses

- `future_data_leakage`: `not_observed_within_bounded_evidence`
- `canonical_identity_break`: `not_observed_within_bounded_evidence`
- `official_exchange_evidence_gap`: `observed`
- `non_positive_comparable_input`: `not_observed_within_bounded_evidence`
- `governance_risk`: `not_evaluated`
- `audit_risk`: `not_evaluated`
- `related_party_risk`: `not_evaluated`
