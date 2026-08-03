# Stage 2I.2R ROIC extraction and lineage closeout — final record

Date: 2026-08-03  |  Branch: `feat/m2-value-assessment-mvp`

## Baseline and final state

- Verified baseline: `13952788`; final evidence HEAD: `78c4c4eaec0cd63eb17df49b35203e4270cdda24`.
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

- Full pytest at implementation HEAD `b7707ad`: **1028 passed, 2 warnings**;
  independent clean clone of pre-documentation HEAD `ebf901d` reproduced
  **1029 passed, 2 warnings** with Ruff and compileall/import passing.
- Targeted Stage 2I.2R suites: **17 passed**; Ruff all checks passed; compileall/import passed.
- Formal A/B: both 9 economic facts/16 cells, `ROIC_FACT_GAPS_REMAIN`,
  `shadow_status=NOT_RUN`; artifact count 12, mismatches 0; digest
  `ff96e7c1244712280941f077aa94f20eb958788990c636408bbc2bc1314c59f2`.
- Independent clean clone at `D:\tmp\stage2i2r_local_clean_8302188\repo`:
  Ruff/import/compileall passed, full pytest 1018 passed, formal A/B passed.
- Final completed CI evidence before this terminal documentation commit was
  run `30816554022`, with Windows and Ubuntu jobs successful. The terminal
  documentation commit and its CI run are recorded in the Sol final handoff
  because a commit cannot truthfully name its own future hash.

## Protected evidence

Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
Inventory facts: 354. Protected baseline fixture records 102 Metric Results and
16 definitions. Methodology files are verified from their actual repository
hashes in the final acceptance packet. Existing Stage 2F/2H risks remain out of
scope and unresolved.

## Decision

`ROIC_FACT_GAPS_REMAIN`; next-stage implementation is prohibited pending a new
North-Star Review.
