# M2 Stage 2J conditional-closeout summary

Milestone 2: CONDITIONALLY CLOSED WITH EXPLICIT EVIDENCE GAPS

## Decision

- North-Star decision: `M2_CONDITIONAL_CLOSEOUT_ALLOWED`
- ROIC decision: `ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT`
- Scoring: `SCORING_DEFERRED_BY_DESIGN`
- M3 next gate: `M3_NORTH_STAR_PREFLIGHT_ALLOWED`

The decision preserves trusted M2 dimensions while refusing to invent a ROIC
number from incomplete scope-matched evidence. It does not claim full M2 or
ROIC completion, absence of governance risk or missing facts, or undervaluation.

## Canonical status

- Completion matrix: `reports/m2_value_assessment_completion_matrix.json`
- Current gap ledger: 9 Stage 2F + 2 Stage 2H + 7 Stage 2I gaps, recomputed
  from source ledgers and represented once each.
- ROE/ROA: trusted existing results unchanged.
- ROIC numeric value: `NOT PRODUCED`.
- ROIC shadow: `NOT RUN`.
- Production ROIC Metric/Result: `NOT CREATED`.
- PetroChina profile: explicit non-numeric ROIC evidence status.
- Market mechanism: NOT STARTED
- Next-stage implementation: NOT STARTED

## Evidence boundary

No current finite high-probability official-source batch resolves all ROIC hard
blockers. The available alternatives require proxy tax, residual associate/JV
allocation, unsupported non-operating-asset deductions, a plug, or weaker
scope matching. All are rejected by the strict contract.

## Validation

- Focused Stage 2J: `13 passed`.
- Protected Stage 2F / 2H / 2I: `22 / 15 / 76 passed`.
- Identity/PIT/Metric protected group: `112 passed`; affected append-only
  roadmap guards: `68 passed`.
- Full local pytest: `1056 passed, 2` pre-existing pandas date warnings.
- Ruff, compile/import, matrix, ledger, cross-format profile, decision,
  artifact, diff, pollution, secret/path, default-DB, stash and source-ledger
  guards: passed.
- Clean clone and final Ubuntu/Windows CI: pending.
