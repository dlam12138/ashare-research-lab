# Stage 2H.1R old-to-new contract and report diff

This note preserves the prior Stage 2H.1 result and records the finite
correction applied by Stage 2H.1R.

| Area | Stage 2H.1 | Stage 2H.1R |
|---|---|---|
| Historical 2025-04-01 result | 7 observations could be mistaken for seven risks | 8 fixed risk slots; 7 observations plus 1 explicit un-emitted `missing_evidence` slot |
| No-input behavior | A risk could disappear from the result array | `risk_universe_evaluation_v1` always emits all 8 slots; no-input slots carry `no PIT-visible input` and no observation ID |
| Current profile | Broad placeholders and Stage 2H detail were siblings | `current_risk_veto_profile` is the only current risk source |
| Old placeholders | `governance_risk`, `audit_risk`, `related_party_risk` were current-looking | Moved to `legacy_risk_veto_checks` with `legacy=true`, `current=false`, and `do_not_use_for_current_profile=true` |
| Evidence semantics | One `evidence_ids` set and one source-type list | `input_evidence_ids`, `supplemental_evidence_ids`, `all_evidence_ids`, and separate derived source types |
| Audit evidence | Issuer and exchange annual reports were not distinguished | Issuer audit opinion is input; exchange annual-report copy is supplemental |
| IDs/contracts | v2 event/observation identity | v3 event/observation identity plus versioned universe/slot IDs |
| Artifacts | Observation-only report payload | Report and artifact include the complete risk universe and slot mapping |

Supplemental evidence remains usable for cross-checks and context but cannot
change event inputs, triggers, or `input_lineage_hash`. Changing supplemental
material may create a new event version because the complete evidence set is
part of event identity; changing input material must change lineage and event
identity. Missing evidence remains missing evidence and is never converted into
a negative conclusion.

The new formal and historical artifacts have new logical and file hashes because
the v3 contracts, split evidence fields, slots, and IDs are real content
changes. The prior Stage 2H.1 acceptance remains the historical record of the
old output.
