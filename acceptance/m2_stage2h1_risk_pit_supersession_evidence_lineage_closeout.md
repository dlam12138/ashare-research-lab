# M2 Stage 2H.1 Risk Search PIT, Supersession and Evidence-Lineage Closeout

Date: 2026-08-02
Symbol: `601857.SH`
Methodology: `risk_veto_methodology_v2`
Formal as-of: `2026-08-02`

## Result

**CONDITIONAL PASS.** The v2 search PIT, event supersession, evidence-lineage,
official-cache and observation-availability contracts are trusted. The
PetroChina profile remains conditional because regulatory/discipline search and
the historical fund-occupation/related-guarantee search remain
`missing_evidence`. Neither gap is a negative conclusion.

The implementation preserves the v1 acceptance and ledgers, reuses the Stage
2G.2 path-independent resolver, artifact verifier and clean-clone capsule, and
keeps `score_eligible: false`.

## Final risk statuses

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

The preserved boundaries are: KAMs are not modified opinions; normal
accounting-policy/common-control restatements are not error risk; routine
inquiries are not major discipline; ordinary related-party transactions are
not abuse; and proposed financing is not realized dilution.

## Evidence and reproducibility

- v2 search ledger: eight risk registers with PIT timestamps and explicit
  completeness/gap fields.
- v2 event ledger: 36 events with deterministic IDs and supersession-ready
  semantic keys.
- Normalization ledger: 105 field-level records, each tied to an official
  evidence field and transform.
- Official cache: 10 evidence IDs, 8 unique PDF objects, complete registry
  mapping, real SHA-256 and byte-size checks.
- Real formal run: `petrochina_stage2h1_real_final`, conditional pass,
  artifact logical digest `a18db13689cb28c1492b068800740039f1a34ac72b5d55865c135c04fb50e36e`.
- Historical as-of run: `petrochina_stage2h1_historical_20250401`, with
  seven explicit missing-search observations because the v2 registers were not
  yet PIT-visible.
- Synthetic correction capsule: before/after PIT runs pass; the correction
  supersedes the earlier event only after its `available_at`.

No ROIC, scoring, Web, target-price, recommendation, automatic-trading or
market-mechanism work was started.

## Stage 2H.1R follow-up correction

The historical seven-observation result above is retained as the actual Stage
2H.1 output. Stage 2H.1R does not rewrite that history; it changes the public
evaluation contract so a historical run always returns the frozen eight-risk
universe as eight `risk_evaluation_slot_v1` slots. For the 2025-04-01 PIT
rerun, seven observations are emitted from visible evidence and the regulatory
risk has one explicit un-emitted `missing_evidence` slot with
`no PIT-visible input`.

The event contract is now `risk_event_record_v3` and the observation contract is
`risk_veto_observation_v3`. Input, supplemental, and all evidence IDs are
separate; supplemental material is excluded from `input_lineage_hash` and
trigger reconstruction. The canonical current profile is now
`current_risk_veto_profile`; the former broad placeholders are retained only
as explicitly legacy, non-current, superseded checks. The Stage 2H.1R
acceptance records the new hashes and gates without deleting this historical
closeout.
