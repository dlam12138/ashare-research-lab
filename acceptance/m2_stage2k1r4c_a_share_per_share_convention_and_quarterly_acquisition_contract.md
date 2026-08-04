# M2 Stage 2K.1R4C — A-Share Per-Share Valuation Convention and Quarterly Denominator Acquisition Contract

Status: `PASS` (CI-backed; final CI run recorded after completion)

## Objective

A single, small, complete governance stage that (1) fixes two small non-blocking
issues, (2) corrects the R4B A/H-share valuation misjudgment by freezing the A-share
per-share convention, and (3) freezes the quarterly denominator fact-acquisition
contract. No quarterly collection, no valuation series, no scoring expansion.

## Phase A — two small governance fixes

- **A1 (R4B work-record status):** the top `Status: in_progress` conflict is fixed to
  `Status: completed` with closeout verdict `PASS`, final head `15c8e28`, final CI
  `30907749043`. The historical starting-state text in the body is preserved.
- **A2 (sensitivity ledger validator):** a single shared pure function
  `recompute_dimension_summary_from_ledger` now drives both `build_sensitivity_v6` and
  `validate_sensitivity_ledger`. The validator compares the FULL per-dimension summary
  (incl. `coverage_gate_sensitivity`, `confidence_gate_sensitivity`,
  `production_readiness_reason`, and all base/band/count/type fields) instead of a
  hand-written partial whitelist. Tampering with any summary field fails even when the
  digest is recomputed. The v6 report is byte-identical (digest `213cdba0…`); scenarios,
  thresholds, and `NOT_STABLE` are unchanged.

## Phase B — A-share per-share valuation convention (ADR-VALUATION-002)

- `A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION` frozen: market = `SSE_A_SHARE`,
  symbol `601857.SH`, price = A-share unadjusted close, currency CNY.
- Core valuation = **A-share price ÷ company-wide per-share fundamental** (total
  ordinary shares). No A/H share-count split required.
- H-share price / FX / dual market cap: **not** in core PE/PB/PS or the score; A/H
  premium is an optional separate reference only.
- R4B route `UNRESOLVED`/`MARKET_CAP` is **superseded** (not erased) → effective
  `route = A_SHARE_PRICE_PER_SHARE`, `route_status = FROZEN`, `a_h_split_required =
  false`, `total_ordinary_share_timeline_required = true`.
- The overall decision **`PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED` is unchanged**
  (the real blocker is the absence of quarterly financial facts).

## Phase C — quarterly denominator acquisition contract (plan only)

- `config/pit_valuation_fact_acquisition_plan_v1.json`,
  `docs/pit_valuation_fact_acquisition_contract.md`,
  `reports/pit_valuation_fact_acquisition_coverage_matrix.json`.
- Facts: `net_profit_attributable_to_parent` (PE-TTM), `revenue` (PS-TTM),
  `equity_attributable_to_parent` (PB-MRQ), plus two share-count roles
  (`total_ordinary_shares_at_period_end`, `weighted_average_total_ordinary_shares`).
- Share-count conventions frozen: PE = weighted-average total ordinary shares; PB and
  PS = period-end total ordinary shares.
- Sources: PetroChina quarterly/half-year/annual reports + SSE announcements + share
  change/corporate-action announcements only. No commercial-terminal transcription, no
  third-party daily PE/PB/PS, no LLM inference, no current-share backfill, no H-share
  price/FX.
- Time contract: every fact carries `period_start/period_end/filing_date/available_at/
  effective_from/restatement_version/supersedes_fact_id/source_evidence_id`; effective
  from the next trading day after an announcement-only date; restated values never
  backfilled into pre-restatement history.
- **No collection, no download, no injection this round.**

## Phase D — readiness decision

```text
A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED
```

"Allowed" means only that the next round may perform official quarterly denominator
fact collection per the acquisition contract. It does **not** authorize PIT daily
PE/PB/PS construction, historical valuation percentages, valuation score updates, peer
acquisition, production scores, or M3.

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | R4B record top no longer `in_progress` | DONE | `test_r4b_record_status_completed` |
| 2 | R4B closeout metadata + starting state preserved | DONE | `test_r4b_record_closeout_metadata_present`, `test_r4b_record_starting_state_preserved` |
| 3 | Sensitivity full summary recomputable from ledger | DONE | `test_sensitivity_full_summary_recomputable_from_ledger` |
| 4 | Tampered gate summary fails | DONE | `test_sensitivity_tamper_{coverage_gate,confidence_gate,production_readiness_reason}` |
| 5 | Scenario+summary tamper (digest resynced) fails | DONE | `test_sensitivity_tamper_scenario_and_summary_sync_fails` |
| 6 | A-share price registered as the only core price | DONE | `test_a_share_price_is_only_core_price`, `test_adr_002_exists_and_accepted` |
| 7 | H-share price not in core valuation | DONE | `test_h_share_not_in_core_valuation` |
| 8 | A/H split no longer a core blocker | DONE | `test_a_h_split_not_core_blocker`, `test_r4b_decision_blocks_updated` |
| 9 | Total ordinary share timeline still required | DONE | `test_total_ordinary_share_timeline_required` |
| 10 | PE uses weighted-average total ordinary shares | DONE | `test_pe_uses_weighted_average_shares` |
| 11 | PB uses period-end total ordinary shares | DONE | `test_pb_uses_period_end_shares` |
| 12 | PS share-count convention clear and unique | DONE | `test_ps_share_count_convention_unique` |
| 13 | Quarterly profit and revenue are TTM-required | DONE | `test_quarterly_profit_and_revenue_ttm_required` |
| 14 | Quarterly equity is MRQ-required | DONE | `test_quarterly_equity_mrq_required` |
| 15 | available_at and restatement rules exist | DONE | `test_available_at_and_restatement_rules_exist` |
| 16 | close percentile still not a valuation percentile | DONE | `test_close_percentile_not_valuation_percentile` |
| 17 | No historical PE/PB/PS series generated | DONE | `test_no_historical_series_generated` |
| 18 | Valuation shadow not modified | DONE | `test_valuation_shadow_not_modified` |
| 19 | Scoring weights/thresholds unchanged | DONE | `test_scoring_weights_thresholds_unchanged` |
| 20 | No peer acquisition | DONE | `test_no_peer_acquisition_started` |
| 21 | No M3 | DONE | `test_no_m3_started` |
| 22 | R4B decision PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED unchanged | DONE | `test_r4b_decision_pit_unchanged` |
| 23 | R4C decision A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED | DONE | `test_r4c_decision_allowed` |

## Validation

Covered in the work record's verification section (full suite + static checks + CI).

## Final project state

```text
Two small governance issues:   CLOSED
Core valuation market:         SSE A SHARE
Core valuation convention:     A SHARE PRICE / COMPANY-WIDE PER-SHARE FUNDAMENTALS
H-shares:                      OPTIONAL SEPARATE REFERENCE
PIT quarterly denominators:    ACQUISITION REQUIRED
Historical PE/PB/PS:           NOT IMPLEMENTED
Valuation scoring:             NON_PRODUCTION_AND_NOT_INTERPRETABLE
Production scoring:            NOT ALLOWED
Peer acquisition:              NOT ALLOWED
M3:                            NOT STARTED
```

## Git state

- Branch: `feat/m2-value-assessment-mvp`; pushed to `origin`; CI run (to be recorded) PASS
  on ubuntu + windows.
- Protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash) untouched.
- No force push, no reset --hard, no git clean.