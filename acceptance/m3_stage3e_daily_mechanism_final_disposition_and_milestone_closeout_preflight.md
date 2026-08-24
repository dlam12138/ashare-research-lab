# M3 Stage 3E — Daily Mechanism Final Disposition & Milestone Closeout Preflight

Status: `M3_STAGE3E_DAILY_MECHANISM_FINAL_DISPOSITION_ACCEPTED`

## Scope and boundary

Stage 3E is a governance and North-Star review of committed Stage 3A through
Stage 3D-B-R2 evidence. It reads no new real data, external capsule, price
content, or network source. It does not rerun development or holdout, compute a
statistic, change a provider/proxy/threshold/model, add robustness, repair the
holdout, analyze minutes or index contribution, or authorize M4.

## Evidence disposition

The frozen Stage 3C-B development primary remains:

- sample `2015-03-16` through `2022-12-30`, `nobs=1902`, `crash_count=330`;
- `gamma=0.0005072734676652487`;
- bootstrap 95% CI `[-0.0021987423016553366, 0.0033325010311833106]`;
- `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`.

Registered Stage 3C-C robustness completed. All three threshold tests were
false under BH correction; threshold directions were mixed and leave one year
out directions were mixed. The five registered unexecuted items remain
explicit gaps and are not automatic follow-up work.

Stage 3D-B-R2 resolved all 159 security identities (146 A, 13 B), with no
unresolved or extra expansion rows. The corrected universe retained 2,514
master rows, 2,367 `EVER_ELIGIBLE` rows, 147 `NEVER` rows, 57 true required
missing rows, zero retry successes, minimum market coverage
`0.9736963544070143`, and the frozen `0.99` gate. Therefore the holdout is
`UNSEALED_CONSUMED`, but its accepted primary count is `0`, no primary
statistic was observed, and its disposition is
`M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`. No holdout gamma
exists.

The complete machine-readable disposition is
[m3_stage3e_daily_mechanism_final_disposition_v1.json](../reports/m3_stage3e_daily_mechanism_final_disposition_v1.json).
The explicit gap register is
[m3_stage3e_explicit_evidence_gaps_v1.json](../reports/m3_stage3e_explicit_evidence_gaps_v1.json).

## North-Star conclusion

The final daily disposition is `M3_DAILY_MECHANISM_NOT_ESTABLISHED`. This is
not a claim that the mechanism was disproven: the development evidence did not
establish a stable positive controlled relation, while the holdout could not
produce a primary statistic under the frozen coverage gate.

Development evidence has ceiling
`M3_DEVELOPMENT_EVIDENCE_CEILING_LEVEL_2`; the final numeric evidence level is
unassigned because the descriptive relationship criterion was not prelocked.
Further holdout recovery is not authorized. Minute escalation is
`M3_MINUTE_LEVEL_ESCALATION_NOT_JUSTIFIED`; index contribution is
`M3_INDEX_CONTRIBUTION_DEFERRED_SEPARATE_MECHANICAL_ANALYSIS` and is not
authorized by this closeout.

## Milestone decision

The closeout decision is
`M3_MILESTONE_CONDITIONAL_CLOSEOUT_ALLOWED`, with milestone status
`CONDITIONALLY_CLOSED`. This is neither `FULLY_COMPLETE` nor `FAILED`: the
fail-closed daily MVP and its answer are recorded, and the unresolved evidence
gaps are preserved. M4, M5/minute work, index contribution, and a new
PetroChina mechanism hypothesis are not authorized.

See [m3_stage3e_milestone_closeout_decision_v1.json](../reports/m3_stage3e_milestone_closeout_decision_v1.json)
for the machine-readable contract. The final stop condition is
`STOP_FOR_NORTH_STAR_REVIEW`.
