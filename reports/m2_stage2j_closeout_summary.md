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
- Independent clean clone at `fc3072f`: preflight, Stage 2J `13 passed`,
  contract/artifact validators, Ruff, compileall and full pytest `1056 passed,
  2` pre-existing warnings all passed; the clone had no default DB,
  output/cache, stash, private absolute path, or tracked secret.
- Final CI run `30866296153` at exact head `1cb5b776`: Ubuntu job
  `91858789432` and Windows job `91858789449` both passed.

## Final Stage 2J report

```text
M2 Stage 2J: CONDITIONAL PASS
North-Star decision: M2_CONDITIONAL_CLOSEOUT_ALLOWED
Milestone 2 status: CONDITIONALLY CLOSED WITH EXPLICIT EVIDENCE GAPS
M2 completion matrix: TRUSTED
Canonical M2 gap ledger: TRUSTED
ROIC decision: ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT
ROIC numeric value: NOT PRODUCED
ROIC shadow: NOT RUN
Production ROIC Metric/Result: NOT CREATED
Scoring: DEFERRED_BY_DESIGN
PetroChina value profile: UPDATED WITH EXPLICIT ROIC STATUS
Stage 2F evidence gaps: PRESERVED
Stage 2H evidence gaps: PRESERVED
Stage 2I evidence gaps: PRESERVED
Market mechanism: NOT STARTED
M3 next step: NORTH-STAR PREFLIGHT ALLOWED
Next-stage implementation: NOT STARTED
```
