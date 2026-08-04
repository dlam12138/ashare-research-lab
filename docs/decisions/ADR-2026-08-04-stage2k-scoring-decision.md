# M2 Stage 2K — explainable dimension scoring decision

Status: `accepted`

## Decision

`PEER_BENCHMARK_ACQUISITION_REQUIRED`

The four-dimension independent scoring method is trusted and a non-production
PetroChina shadow was computed and validated. However, at least one dimension
(`enterprise_quality`) cannot be responsibly productionized without a finite
peer benchmark dataset, because its absolute-contract thresholds have no peer
or statistical calibration. The `risk_and_evidence_integrity` band is also
unstable at its A/B boundary. A responsible production dimension score
therefore requires a finite peer benchmark dataset.

## What this decision permits

- A later, separately authorized Stage 2K.1 production scoring stage, after the
  smallest peer benchmark acquisition batch is completed and the risk band
  stability is resolved.
- It does **not** create production scores now.
- It does **not** authorize a composite score, ranking, recommendation, or
  target price.

## What was decided and why

- North-Star decision: `M2_SCORING_ADDENDUM_REOPENED`. Only the scoring module
  is reopened; Stage 2J remains an immutable historical conditional closeout.
- Four independent dimensions, no fifth overall score.
- Missing is never zero; ROIC is a coverage gap; dividend yield is a coverage gap.
- Risk vetoes are non-compensatory.
- The non-production shadow is computed and deterministic.

## Alternatives considered

- `DIMENSION_SCORING_MVP_ALLOWED`: rejected because the enterprise-quality
  absolute thresholds are not statistically calibrated and the risk band is
  unstable; a bounded production representation is not yet supported.
- `SCORING_NOT_TRUSTED`: rejected because the method is traceable, PIT-safe,
  deterministic, and its missingness/coverage/confidence and risk-veto contracts
  are trusted.

## Reopen conditions

- Acquire the smallest finite peer benchmark batch (see
  `docs/value_dimension_scoring_peer_preflight.md`) and recalibrate the
  enterprise-quality thresholds.
- Resolve the risk-dimension band instability.
- A separately authorized production scoring stage may then proceed.

## Boundary

- Production value profile: unchanged and score-free.
- No production score, table, Metric Result, or registry entry was created.
- Market mechanism: not started.
- No main merge, PR, tag, release, force push, or hard reset.