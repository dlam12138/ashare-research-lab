# M2 Stage 2H.1R Historical Risk Completeness and Value-Profile Canonicalization

Date: 2026-08-02
Symbol: `601857.SH`
North-Star gate: `ALLOWED` in `docs/post_valuation_north_star_review.md`
Methodology: `risk_veto_methodology_v2` with v3 event/observation and v1 universe/slot contracts

## Verdict

**CONDITIONAL PASS — trusted engineering contracts with the existing two
explicit official evidence gaps retained.**

The risk universe is complete as eight deterministic slots for every evaluated
PIT date. Observations are emitted only when real PIT-visible inputs permit a
conclusion; missing slots are not fabricated observations. The PetroChina
profile remains `UPDATED WITH EXPLICIT GAPS`: regulatory/discipline retrieval
and historical fund-occupation/related-guarantee search remain
`missing_evidence`, not negative conclusions. `score_eligible=false`.

This finite correction does not start ROIC, scoring, Web, target price,
recommendation, automatic trading, or market-mechanism work.

## Frozen contracts and canonical profile

- `risk_universe_evaluation_v1`: public `evaluate_risk_universe_as_of(...)`
  result with exactly the eight frozen `RISK_IDS`.
- `risk_evaluation_slot_v1`: deterministic slot identity includes symbol,
  risk, as-of date, selected search/event lineage, observation ID or null,
  status, and missing reasons.
- `risk_event_record_v3` and `risk_veto_observation_v3`: separate input,
  supplemental, and all-evidence fields with derived source types.
- Current value-profile consumer path:
  `reports/petrochina_value_profile.json:current_risk_veto_profile`.
- `governance_risk`, `audit_risk`, and `related_party_risk` are retained only
  under `legacy_risk_veto_checks` with `legacy=true`, `current=false`,
  `superseded_at_stage="M2 Stage 2H"`, and
  `do_not_use_for_current_profile=true`.

## PIT results

| As-of date | Slots | Observations | Un-emitted slots | Result |
|---|---:|---:|---:|---|
| 2026-08-02 | 8 | 8 | 0 | current formal cross-section |
| 2025-04-01 | 8 | 7 | 1 | the regulatory slot explicitly has no PIT-visible input |
| 2021-01-01 | 8 | 0 | 8 | all slots explicitly have no PIT-visible input |

The earlier Stage 2H.1 statement of “7 observations” is preserved as a
historical result; it is no longer used as the universe cardinality.

## Evidence split

For current audit-opinion events, issuer annual-report records are
`input_evidence_ids` because they supply the normalized opinion field. Exchange
annual-report copies are `supplemental_evidence_ids` for cross-check/context.
For other event families, the split is derived from the normalization records
and denominator lineage. `all_evidence_ids` is the ordered union, input and
supplemental sets are disjoint, and source-type lists are derived from the
evidence ledger. Supplemental changes do not affect event inputs, triggers, or
`input_lineage_hash`, though they may create a new event version.

## Runs and artifacts

- Real formal: `petrochina_stage2h1r_real_final`, 8 slots / 8 observations,
  conditional pass; published report uses the v3 contracts. The artifact
  logical digest is
  `0d7536b41217ef0f3d091cc2ef67f7ab6cc8150dcb8793c1606ed96a329fbe5f` and the
  manifest SHA-256 is
  `de3766bfa1853cc3d92016172699a0f181d7666aa5f7cfd03e51418c4d8a4f28`.
- Historical: `petrochina_stage2h1r_historical_20250401` (offline formal),
  8 slots / 7 observations / 1 un-emitted slot; artifact logical digest
  `d2da8dc8bac94ae1f622aca63574ed9cdb62ff7ce0e90dcaa69a8e277b1b773b`.
- Earlier no-input cross-section: `petrochina_stage2h1r_early_20210101`
  (offline formal), 8 slots / 0 observations / 8 un-emitted slots; artifact
  logical digest
  `261460a6883a57d5a04ea408275a990e4ffc0d76135f933d24e97a0b76d5861e`.
- Synthetic correction before/after: `stage2h1r_test_capsule` contract gate,
  8 slots in both snapshots with correction supersession retained. Independent
  A/B capsules compare with no differences and share logical digest
  `39aa6bd84490b541c1c5dc97e59d8bd796e3f145323d6af1238dc7a2ee73315a`.
- Independent real-cache A/B formal runs
  (`petrochina_stage2h1r_real_ab`) compare with no differences and share
  logical digest
  `0d7536b41217ef0f3d091cc2ef67f7ab6cc8150dcb8793c1606ed96a329fbe5f`.

The old-to-new mapping is recorded in
`docs/stage2h1r_old_to_new_diff.md`. Artifact logical/file hashes changed
because the event, observation, slot, report, and profile payloads changed;
these are content-addressed outputs, not hash-preserving compatibility shims.

## Verification

- Targeted Stage 2H/2H.1R suite: `15 passed`.
- Protected official financial-safety vertical slice: `5 passed`; its locked
  assertions remain `354 Fact / 102 Metric Result / 16 definitions` and the
  default DB SHA-256 is unchanged.
- Full local suite: `967 passed, 2 warnings`.
- Stage 2G.2 contract/reproducibility gate: `pass_with_explicit_gaps`, offline;
  ruff, compileall, and `git diff --check` pass.
- The local clean-clone preflight is intentionally not run to a false pass:
  the protected worktree has the required stash, pre-existing research data,
  output/runs, and untracked `agent/goals/`. The post-push CI clean-clone job
  is the authoritative clean-checkout gate.
- Default DB SHA-256 before/after is
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`;
  stash and `agent/goals/` remain protected.
- Remote CI before edits was successful (`30744466406`). Post-push workflows
  `30745949298` (the implementation head) and `30746189865` (the final
  closeout head) completed successfully on both Ubuntu and Windows clean-clone
  jobs, including the full offline suite and Stage 2H.1 gates.

## Final boundary

```text
M2 Stage 2H.1R: CONDITIONAL PASS
Historical eight-risk universe: TRUSTED
Risk evaluation slot contract: TRUSTED
Canonical current value-profile status: TRUSTED
Legacy placeholder migration: COMPLETE
Input-evidence lineage: TRUSTED
Supplemental-evidence semantics: TRUSTED
PetroChina risk-veto profile: UPDATED WITH EXPLICIT GAPS
ROIC: NOT YET
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
Next-stage implementation: NOT STARTED
Next-stage selection: NORTH-STAR REVIEW REQUIRED
```
