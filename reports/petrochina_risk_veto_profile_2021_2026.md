# PetroChina canonical risk-veto profile 2021–2026

As of `2026-08-02`; formal run `conditional_pass`; methodology `risk_veto_methodology_v2`.
Universe `risk_universe_6231c32047f90529316d931e`; contract `risk_universe_evaluation_v1`; exactly `8` fixed risk slots.

## Canonical current risk profile

| Risk ID | Evaluation status | Observation emitted | Observation ID | Search register |
|---|---|---:|---|---|
| `modified_audit_opinion` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_d774875b76fd626f8dc3111a` | `pc-search-modified-audit-opinion-v2` |
| `going_concern_material_uncertainty` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_36900a36e77ecf40dd8c2c42` | `pc-search-going-concern-v2` |
| `formal_regulatory_investigation_or_major_discipline` | `missing_evidence` | `true` | `risk_observation_feff9792a99dd226f161cdb5` | `pc-search-regulatory-v2` |
| `material_error_restatement` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_052c3846c2a6bfa327cfb5cc` | `pc-search-restatement-v2` |
| `controlling_shareholder_pledge_risk` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_3f80905aa96f00f364715499` | `pc-search-pledge-v2` |
| `material_related_party_transaction_risk` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_fc9149e19ce39d95291879d9` | `pc-search-rpt-v2` |
| `controlling_shareholder_fund_occupation_or_related_guarantee` | `missing_evidence` | `true` | `risk_observation_a6fd612c59638073df29dbdf` | `pc-search-fund-occupation-v2` |
| `repeated_equity_financing_or_material_dilution` | `not_observed_within_bounded_evidence` | `true` | `risk_observation_3bb97c18f6021ab3be2c7ae6` | `pc-search-financing-v2` |

Observations emitted: `8`; slots: `8`; un-emitted slots: `0`. A missing observation is not treated as a negative conclusion.

## Evidence semantics

- `input_evidence_ids` are reconstructed from normalization and denominator lineage and alone drive event inputs, triggers, and `input_lineage_hash`.
- `supplemental_evidence_ids` are retained for cross-check/context only; they are disjoint from inputs and excluded from input lineage.
- For the current audit-opinion events, issuer annual-report evidence is input and exchange annual-report copies are supplemental.

## Explicit gaps and boundaries

- Regulatory/discipline and historical fund-occupation/related-guarantee search gaps remain `missing_evidence`.
- Key audit matters are not modified opinions; ordinary accounting-policy/common-control recasts are not error risk; ordinary related-party transactions are not abuse; proposed financing is not realized dilution.
- `score_eligible=false`; ROIC, scoring, target price, recommendation, automatic trading, and market mechanism are not started.
