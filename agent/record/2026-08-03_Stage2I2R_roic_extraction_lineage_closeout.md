# Stage 2I.2R ROIC extraction and lineage closeout — final record

Date: 2026-08-03  |  Branch: `feat/m2-value-assessment-mvp`

## Baseline and final state

- Validated code HEAD: `7341a2d`.
- Local, origin, and remote branch are equal; protected `.codex/`, `AGENTS.md`,
  `agent/goals/`, and stash entry are unchanged.
- Historical Stage 2I.2 report paths were restored unchanged. Corrected outputs
  are committed under `reports/*stage2i2r*`.

## Delivered behavior

Capture-derived Decimal extraction, finance/lease operand derivation,
registry-based report-year mapping, reconciled-derived dual evidence semantics,
executed seven-cell versioned bounded-search ledger, PIT-safe timestamps, and
fail-closed three-state acquisition gate. No new acquisition, shadow ROIC,
production Metric/Result, default DB, value profile, scoring, market work, or
Stage 2I.3 was started.

## Validation evidence

- Targeted Stage 2I.2R suites: **76 passed**; Ruff all checks passed; compileall/import passed.
- Full pytest: **1043 passed, 2 warnings** (main worktree 254.94s; clean clone 155.25s).
- Fresh, cross-cwd, and clean-clone formal A/B: both 9 economic facts/16 cells,
  `ROIC_FACT_GAPS_REMAIN`, `shadow_status=NOT_RUN`; artifact count 12,
  mismatches 0; digest `90632b11b4784a019f8765237fe0d4bafcf1b8a80ff5c681a57fba3798da2483`.
- Independent clean clone at `D:\tmp\stage2i2r_local_clean_8302188\repo`:
  Ruff/import/compileall passed, full pytest 1018 passed, formal A/B passed.
- Final-head CI run `30825336850`: Ubuntu job `91725407528` and Windows job
  `91725407544` both successful.

## Protected evidence

Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
Inventory facts: 354. Protected baseline fixture records 102 Metric Results and
16 definitions. Methodology files are verified from their actual repository
hashes in the final acceptance packet. Existing Stage 2F/2H risks remain out of
scope and unresolved.
The committed internal packet digest is
`cb35113e81016ac9de2cd966b48174af425cfdb2aeb3fc5a0341afbe6cd1e57f`;
older `a323...`, `1028`, and `1029` figures are superseded historical evidence.

## Decision

`ROIC_FACT_GAPS_REMAIN`; next-stage implementation is prohibited pending a new
North-Star Review.
