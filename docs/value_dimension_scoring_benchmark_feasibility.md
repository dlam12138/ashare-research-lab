# M2 Stage 2K — Benchmark and Normalization Feasibility

Contract: `value_dimension_scoring_benchmark_feasibility_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose

Evaluate the four benchmark modes separately for the PetroChina non-production
shadow. Modes are not blended without an explicit transform and rationale.

## 2. Benchmark modes

### 2.1 `absolute_contract`

Used for enterprise-quality and value-realization metrics where no peer or
long history exists. A frozen, sourced piecewise band on the raw value. The
thresholds are documented in the registry and selected from industry-informed
levels; they are frozen before the shadow is viewed. They are theory-informed,
not peer-calibrated, and therefore **not** a sufficient basis for a production
score without a peer benchmark.

### 2.2 `self_history_percentile`

Used for the valuation dimension. The value profile already computes PIT-safe
3y/5y/expanding percentiles with exact sample counts (3y = 727, 5y = 1050,
expanding = 1050). Only observations visible as of the score date are used, so
no future observation leaks into a historical percentile. Minimum-sample gates
(3y 500, 5y 900, expanding 120) are enforced. The two dividend-yield
observations fail the 3y/5y sample gate and are therefore not eligible for a
self-history percentile; they remain coverage gaps.

### 2.3 `peer_percentile`

Not available in this stage. Only one issuer vertical slice exists. No peer
universe is registered and no peer data is acquired. A peer percentile is a
bounded future enhancement; it is never fabricated or substituted.

### 2.4 `binary_or_categorical_evidence`

Used for the risk-and-evidence dimension and the repurchase component. Values
are deterministic flags from evidence slots (risk-veto status, PIT/lineage
status, gap counts). Missing evidence is represented as `missing_evidence`, not
as a negative conclusion.

## 3. Self-history audit

- Exact sample counts: 3y 727, 5y 1050, expanding 1050 (computed PE/PB/PS/FCF
  yield). Dividend-yield windows have 242/410/410 and 244/418/418 samples but
  fail the 3y/5y minimum gates, so they are not eligible.
- PIT-safe: verified; historical percentiles use only observations visible at
  the score date.
- Percentile direction checked: PE/PB/PS are `lower_better`; FCF yield is
  `higher_better`.
- Minimum-sample gate: enforced per window.
- No look-ahead: the percentile for a historical score uses only data visible
  at that score date.
- Cycle limitation: disclosed; a low PE at a possible cycle peak is not
  auto-cheap.

## 4. Peer-benchmark preflight

No broad peer dataset is acquired in this stage. A candidate peer-selection
contract is defined for the future production stage:

- official industry classification (CSRC / SSE integrated-industry);
- integrated oil/gas business mix;
- A-share listing and accounting comparability (CAS consolidated);
- size and state-ownership considerations where analytically relevant;
- historical fact coverage across the same metric set;
- exclusions and conflicts (no issuer where facts are not reconcilable).

Estimated issuer count for a bounded integrated-oil/gas peer universe: a small
finite set (single-digit). Required facts/metrics: the same ROE/ROA/margin/
safety/valuation set. Current repository coverage: only PetroChina. Minimal
acquisition batch if needed: the finite peer universe described above.

The peer-selection contract is not hardcoded to make PetroChina look better or
worse. Peer scoring is a future enhancement and is not required to compute the
non-production shadow.

## 5. Transform comparison

Three representations are compared for each dimension:

- **percentile 0–100**: a numeric score in [0,100]. Used internally for
  sensitivity; communicates false precision if presented as the primary output.
- **transparent piecewise bands**: an ordinal band A–E from frozen thresholds.
  Used as the primary output for the quality, valuation, and realization
  dimensions.
- **A–E grade**: equivalent to the ordinal band; used as the primary output.
- **descriptive no-score status**: used when coverage is below the gate or a
  veto blocks the dimension.

The free-standing representations are ordinal bands (A–E) and descriptive
status. The numeric 0–100 is disclosed as an internal sensitivity value. The
difference between numeric and ordinal output is explicit in the output
contract.

## 6. Decision

- `enterprise_quality`, `valuation_attractiveness`, `value_realization_capacity`:
  ordinal band A–E (primary) with numeric 0–100 (internal sensitivity).
- `risk_and_evidence_integrity`: ordinal band A–E with categorical veto flags.
- Diminishing below-gate dimensions emit `insufficient_evidence` and no band.

No threshold is selected after viewing the PetroChina result.