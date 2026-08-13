# M2 Stage 2K — Peer-Universe Preflight

Contract: `value_dimension_scoring_peer_preflight_v1`
Version: `1.0`
Date: `2026-08-04`
Status: `frozen`

## 1. Purpose

Define a candidate peer-selection contract and a bounded peer-universe
feasibility assessment. This stage does **not** acquire a broad peer dataset.
The peer benchmark is a future production enhancement, not a requirement for
the non-production shadow.

## 2. Candidate peer-selection contract

A peer must satisfy all of the following:

- **Official industry classification**: CSRC / SSE integrated-industry or
  upstream-integrated oil/gas classification.
- **Integrated oil/gas business mix**: meaningful upstream plus downstream
  (refining/chemicals) mix, comparable to PetroChina's integrated model.
- **A-share listing and accounting comparability**: listed on the A-share market
  with CAS consolidated financial statements and a comparable fiscal period.
- **Size and state-ownership considerations**: where analytically relevant, size
  and state-ownership are recorded as covariates, not used as a hidden exclusion.
- **Historical fact coverage**: the same metric set (ROE, ROA, margins, cash
  conversion, safety, valuation) must be reconcilable across the peer.
- **Exclusions and conflicts**: no issuer whose facts cannot be reconciled to
  the same contracts; no issuer selected to make PetroChina look better or worse.

## 3. Feasibility assessment

- **Candidate universe definition**: a small, finite set of integrated oil/gas
  A-share majors and comparable integrated peers.
- **Estimated issuer count**: single-digit (a bounded set; the exact membership
  is registered in the future production stage, not hardcoded here).
- **Required facts/metrics**: the same ROE/ROA/margin/safety/valuation metric set
  used by the four dimensions.
- **Current repository coverage**: only PetroChina (`601857.SH`). No peer facts
  are stored.
- **Minimal acquisition batch if needed**: the finite peer universe described
  above, with the same dual-source evidence contract already used for PetroChina.
- **Whether peer scoring is required for production**: yes, for a responsible
  productionized `enterprise_quality` (threshold calibration) and as a
  cross-check for the valuation reading. It is **not** required to compute the
  non-production shadow.

## 4. Boundary

No peer is acquired, hardcoded, or used to substitute for evidence in this
stage. The peer universe is not selected to favor or disfavor PetroChina. The
peer benchmark remains a bounded future enhancement whose acquisition is
triggered by a separately authorized production stage.