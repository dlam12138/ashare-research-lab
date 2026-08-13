# M2 Stage 2K.1R — scoring-input lineage, confidence, and sensitivity decision

Status: `accepted`

## Decision

`SCORING_CONTRACT_GAPS_REMAIN`

The Stage 2K.1R scoring-input capsule is deterministic, artifact-bound, and
PIT-safe; confidence is separated from score; and the risk dimension is
reassessed into non-compensatory veto status + evidence integrity. The complete
frozen sensitivity is, however, **NOT_STABLE** under the frozen
`stability_tolerance=1.0`: per-dimension max_score_delta is 3.16–9.54 under
±25% single-component weight perturbation and leave-one-out, beyond the 1.0
tolerance, and the 0.95 coverage gate exceeds the achieved 0.90/0.80 coverage.
The scoring contract therefore still has gaps and is not yet production-trusted.
Peer acquisition is not yet allowed.

## What this decision permits

- A later, separately authorized production scoring stage, after the scoring
  contract's stability gaps are resolved (weight/threshold calibration, coverage
  gate policy, or a peer-benchmark calibration).
- It does **not** create production scores now.
- It does **not** authorize a composite score, ranking, recommendation, or
  target price.
- It does **not** authorize peer benchmark acquisition now.

## What was decided and why

- **Deterministic capsule**: score inputs are built by `m2_stage2k1r_capsule.py`
  from committed canonical artifacts only; every component binds to upstream
  artifact SHA-256, contract, record, value, unit, date, and available_at.
  Missing upstream identity is a coverage gap, never zero.
- **Confidence separation**: a versioned confidence contract
  (`config/value_dimension_scoring_confidence_v1.json`) produces a per-dimension
  grade (high/medium/low/not_trusted) separate from score/coverage. All four
  dimensions are `medium`. ROIC absence lowers enterprise confidence but is never
  a zero or a poor-capital-return claim.
- **Risk reassessment**: `risk_and_evidence_integrity` is retained but emits
  separate `risk_veto_status` (clear, non-compensatory) and `evidence_integrity`
  (medium) outputs with `no_merged_numeric_score: true`. A merged risk score could
  mask a serious veto.
- **Stability honesty**: `stability_tolerance=1.0` is frozen and was **not**
  relaxed to force a pass. `NOT_STABLE` is the machine-derived result and is the
  concrete basis for this decision.

## Alternatives considered

- `PEER_BENCHMARK_ACQUISITION_ALLOWED`: rejected because the frozen sensitivity
  is NOT_STABLE and the confidence contract is not yet production-trusted, so the
  precondition "lineage, percentile PIT, confidence, and sensitivity are trusted"
  is not met.
- `SCORING_NOT_TRUSTED`: rejected because lineage, percentile PIT protection,
  confidence separation, and the non-compensatory veto contract are all trusted
  and deterministic; the residual gaps are stability/calibration, not lineage or
  integrity.

## Reopen conditions

- Resolve the scoring-contract stability gaps (weight/tolerance calibration, or
  a finite peer-benchmark calibration) so the frozen sensitivity is STABLE.
- A separately authorized production scoring stage may then proceed.

## Boundary

- Production value profile: unchanged and score-free.
- No production score, table, Metric Result, or registry entry was created.
- Market mechanism: not started.
- No main merge, PR, tag, release, force push, or hard reset.