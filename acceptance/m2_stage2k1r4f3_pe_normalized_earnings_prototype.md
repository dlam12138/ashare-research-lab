# M2 Stage 2K.1R4F.3 — PE Normalized-Earnings Prototype and Historical Cycle-Guard Validation Readiness

## Verdict: CONDITIONAL PASS

Status: completed

Decision: `PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN`

Remote CI: PENDING (local validation only)

PE numeric scoring: **BLOCKED_UNCHANGED**

Next-stage implementation: **NOT STARTED** (`R4F.3A — Historical Annual
Fact Backfill` is the next authorized step; PE numeric scoring stays
blocked)

This stage implements the R4F.2-allowed `AVERAGE_ROE_X_CURRENT_BVPS` method
as a formal **non-scoring** prototype at 2026-07-31, proves via a
deterministic property test that the normalized denominator removes the
direct mechanical dependence of PE on current TTM EPS, and builds the
historical PIT readiness matrix — which reveals real fact gaps for 3y / 5y
historical cycle-guard validation.

## 0. Final report card

```
M2 Stage 2K.1R4F.3:                                    CONDITIONAL PASS
R4F.2 upstream:                                        TRUSTED
Prototype method:                                      AVERAGE_ROE_X_CURRENT_BVPS
Current 5y ROE chain:                                  READY (2021..2025)
Current normalized EPS:                                0.9135206151007635380066173292
Current raw PE:                                        12.81970638132453345471096950 (== R4E.4 candidate)
Current normalized PE:                                 12.12889979366021109951970404
Current EPS / normalized EPS:                          0.9461136965920940114716739512
Current prototype:                                     TRUSTED_NON_SCORING
Direct current-earnings denominator dependence:        REMOVED
Mechanical inversion property:                         PASS
Cycle stage identified:                                NO
Cycle guard empirically validated:                     NO
Earliest historical PIT-ready date:                    2026-03-31
3y historical validation:                              BLOCKED
5y historical validation:                              BLOCKED
Full-cycle coverage:                                   NOT_PROVEN
Historical fact gaps:                                  PRESENT
Minimum 3y backfill:                                   5 facts (2017/2018/2019 equity+NP, see gap plan)
Minimum 5y backfill:                                   9 facts (2015/2016/2017/2018/2019 equity+NP)
PE numeric scoring:                                    BLOCKED_UNCHANGED
Valuation dimension score:                             NONE
Registry/policy v2:                                    UNCHANGED
Shadow v6:                                             UNCHANGED
Sensitivity v8:                                        UNCHANGED
Production scoring:                                    NOT AUTHORIZED
Overall score:                                         PROHIBITED
Decision:                                              PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN
Next-stage implementation:                             NOT STARTED
```

## 1. What was built

- `config/pe_normalized_earnings_prototype_contract_v1.json` — frozen
  contract (contract_id `pe_normalized_earnings_average_roe_v1`,
  `minimum_consecutive_annual_roe = 5`, Decimal-only, PIT / restatement /
  share-scope rules, hard boundary: the 5y window is never shortened).
- `src/ashare_research/pit_valuation/pe_normalized_earnings_prototype.py` —
  pure-function resolver: `resolve_annual_roe_chain_as_of`,
  `resolve_current_bvps_as_of`, `build_normalized_earnings_state`,
  `build_normalized_pe_state`, `build_mechanical_inversion_audit`,
  `build_historical_readiness`, `build_historical_state_ledger`,
  `derive_fact_gap_plan`, `validate_prototype`.
- `src/ashare_research/tools/m2_stage2k1r4f3_pe_normalized_earnings_prototype.py`
  — thin CLI (`build` / `verify` / `fixtures`).
- 7 artifacts: prototype v1, normalized-PE snapshot v1, mechanical
  inversion audit v1, historical readiness v1, historical state ledger v1,
  fact gap plan v1, R4F3 decision.

## 2. Current prototype

Reconstructed from committed facts via the PIT resolver (values identical
to R4F.2, but recomputed — never copied from the R4F.2 strings):

- ROE 2021..2025: `0.07434629055079871379731497929`, `0.1129630958714448405117204395`,
  `0.1146411949491226163766439180`, `0.1112006593330161818176293251`,
  `0.1014383033385868205396732864`
- average ROE: `0.1029179088085938346085963897`
- current BVPS (1,624,532,000,000 / 183,020,977,818): `8.876206538550294436827638346`
- normalized EPS: `0.9135206151007635380066173292`
- prototype status: `TRUSTED_NON_SCORING`

Identity: state digest binds symbol, as_of, contract version, the five
annual ROE observation Fact IDs (NP / beginning equity / ending equity per
year), current equity Fact ID, share Fact ID, and the exact Decimals — no
timestamps, machine names, absolute paths, or output directories.

## 3. Normalized PE snapshot

Same frozen market close as the R4E.4 candidate (11.08, observation
`98d47da1…`, reconciliation digest `4fb3382b…`):

- raw PE = close / TTM EPS = `12.81970638132453345471096950` —
  **exactly** the candidate `ratio_decimal` (recomputed, not read).
- normalized PE = close / normalized EPS = `12.12889979366021109951970404`.
- earnings normalization ratio = `0.9461136965920940114716739512`.
- descriptive only; no cheap/expensive/undervalued/overvalued labels;
  `ratio=1` is a mathematical boundary, **not** a cycle threshold.

## 4. Mechanical inversion property

Fixed price / 5y ROE chain / BVPS / normalized EPS; shocked only current
TTM EPS by 0.5× / 1.0× / 2.0×:

- raw PE moves (25.6394… / 12.8197… / 6.4099…) — `raw_pe_changed = true`
- normalized PE constant (12.1289…) — `normalized_pe_changed = false`
- `direct_current_earnings_denominator_dependence_removed = true`
- `cycle_stage_identified = false`, `cycle_guard_empirically_validated = false`

Property PASS ≠ cycle guard validated.  The audit explicitly separates the
mechanical property from the (future, fact-dependent) empirical validation.

## 5. Historical readiness (real result — fact gaps)

Walk-forward over all 1351 candidate trade days (2021-01-04..2026-07-31):

- prototype-ready: **84 days** (2026-03-31..2026-07-31) — the 2025 annual
  report completes the 5-year ROE chain on 2026-03-31.
- blocked: **1267 days** — all `insufficient_roe_history`.
- `CURRENT_ASOF_READY = true`
- `3Y_HISTORICAL_VALIDATION_READY = false` (0 of 644 days ready in
  2023-07-31..2026-07-31)
- `5Y_HISTORICAL_VALIDATION_READY = false` (0 of 1127 days ready in
  2021-08-02..2026-07-31)
- `FULL_CYCLE_VALIDATION_READY = false` (no independent proof)

State: `CURRENT_PROTOTYPE_TRUSTED, HISTORICAL_VALIDATION_FACT_GAPS_REMAIN`.

## 6. Fact gap plan (exact, computed)

| Backfill | Target trade date | Required ROE years | Missing facts |
|---|---|---|---|
| MINIMUM_3Y_BACKFILL | 2023-07-31 | 2018..2022 | 5: 2017-12-31 equity (opening), 2018/2019 equity + NP |
| MINIMUM_5Y_BACKFILL | 2021-08-02 | 2016..2020 | 9: 2015-12-31 equity (opening), 2016..2019 equity + NP |

All missing facts need source tier `exchange_official` with PIT
announcement/effective dates <= target; values re-verified at R4F.3A.  The
plan never invents provider values.  **Priority: 3y backfill first** —
if the 3y prototype validation fails, the 5y backfill is unnecessary.

## 7. Boundary preserved

- `pe_numeric_scoring_authorized = false`; `va_pe` score null, status
  `coverage_gap_cycle_context_required`; valuation dimension score null,
  status `insufficient_evidence_cycle_context`.
- registry v2 / policy v2 / shadow inputs v2 / capsule v5 / shadow v6 /
  sensitivity v8 unchanged; no registry v3 / policy v3 / shadow v7 /
  sensitivity v9.
- No normalized PE percentile (3y/5y) computed, no score, no overall score,
  no recommendation, no target price, no peer, no M3; no network; no
  default-DB write; margin method stays a diagnostic cross-check (never a
  fallback denominator).
- Manifest: `NOT_REQUIRED_PROTOTYPE_STAGE` — the prototype stage does not
  change formal scoring runtime identity; no new verifier schema registered;
  R4B/R4C/R4A historical manifest debt untouched (final milestone-wide
  integrity closeout).

## 8. Validation performed (local)

- R4F.3 static/regression tests: **45 passed**.
- CLI `build` then `verify`: all 7 artifacts **byte-identical**.
- R4F.2 tests / R4F.1 protected tests / R4F protected tests / full suite /
  ruff / compileall / git diff --check / secret-path scan: see work record.
- Scoring files exact-diff check: zero changes.
- Default DB SHA unchanged; stash preserved; protected files untouched.
