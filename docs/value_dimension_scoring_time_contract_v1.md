# M2 Stage 2K.1R2 — Dual-clock score timing contract

Contract file: `config/value_dimension_scoring_time_contract_v1.json`
Version: `1.0` · Timezone: `Asia/Shanghai` · Frozen: 2026-08-04

## Purpose

The single ambiguous `score_date` is replaced by four distinct, explicit time
points. A scorecard is a research snapshot **formed** at one point using market
data **as of** an earlier cutoff and research evidence **as of** a later cutoff.

## The three time points (and the legacy field)

| Field | Value | Meaning |
|---|---|---|
| `market_data_as_of_date` | `2026-07-31` | Latest allowed market trade date for valuation observations |
| `research_evidence_as_of` | `2026-08-02` | Official risk-research cross-section date |
| `scorecard_formed_at` | `2026-08-02` | The moment the scorecard is formed; must be ≥ max included `available_at` |
| `score_date` (legacy) | — | `legacy`, `deprecated`, `do_not_use_for_pit_validation`; kept only for compatibility |

`market_data_as_of_date` and `scorecard_formed_at` are **not** the same field and
must not be conflated.

## Rules

1. **Market / valuation observations**: `trade_date <= market_data_as_of_date`;
   `available_at <= scorecard_formed_at`.
2. **Financial, dividend, event facts**: `available_at <= scorecard_formed_at`;
   fiscal year, event period and method version must be explicit.
3. **Risk observations**: `evaluation_as_of_date <= research_evidence_as_of`;
   `conclusion_available_at <= scorecard_formed_at`. A 2026-08-02 risk conclusion
   must never be described as "known as of 2026-07-31".
4. **Any input `available_at > scorecard_formed_at`** → validation error (not a
   mere confidence finding); no formal shadow scorecard is produced.
5. **Any market `trade_date > market_data_as_of_date`** → failure.
6. **Strict single-point 2026-07-31 historical scoring**: 2026-08-02 risk
   observations must be invisible; `risk_veto_status` must be
   `not_available_at_cutoff`; `clear` output is prohibited.
7. **Dual-clock risk status**: `risk_veto_status` must not be a permanent `clear`.
   It is reported as `no_trigger_observed_within_bounded_evidence` with
   `research_evidence_as_of`, `missing_evidence_risk_ids`,
   `complete_absence_claim=false`, `non_compensatory=true`.
8. `scorecard_formed_at` is derived from / verified against the maximum included
   input `available_at`, not manually hardcoded.
9. Time contract, input identity, scorecard identity and artifact digest all embed
   `market_data_as_of_date`, `research_evidence_as_of`, `scorecard_formed_at`,
   `timezone` and the time-contract version.
10. Any legacy `score_date` field is marked `legacy`/`deprecated`/
    `do_not_use_for_pit_validation` and is not the sole time semantics.