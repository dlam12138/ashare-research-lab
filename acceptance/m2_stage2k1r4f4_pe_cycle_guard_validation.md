# M2 Stage 2K.1R4F.4 — 3Y Historical Normalized-PE Cycle-Guard Validation

## Verdict: CONDITIONAL PASS — LOCAL CANDIDATE

Status: completed (local validation only; not committed/pushed)

Decision: `PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_INDEPENDENT_CYCLE_VALIDATION_REQUIRED`

Next-stage implementation: **NOT STARTED** (`R4F.4A — Independent
Cycle-Context Validation Preflight`; PE scoring stays blocked)

Reviewer correction applied: engineering and mechanical-guard validation
PASS, but independent cycle-context validation is **NOT ESTABLISHED** —
the direction relation is algebraically implied by the PE formulas and
cannot alone serve as empirical cycle evidence.

This stage validates the PIT-safe Average-ROE × Current-BVPS normalized
earnings denominator as a repeatable historical guard against the
mechanical compression of raw PE when current TTM earnings rise above the
normalized proxy, across the full frozen 3Y PIT window.

## 0. Final report card

```
M2 Stage 2K.1R4F.4:                                   CONDITIONAL PASS
R4F3A upstream:                                       TRUSTED
3Y historical series:                                728/728 TRUSTED
PIT/restatement:                                      PASS
Mechanical inversion property:                        PASS
Mechanical direction consistency:                     PASS
Condition observed across distinct raw states:        11
Independent protective episodes:                      NOT_ESTABLISHED (one contiguous segment)
Direction violations:                                 0
Normalized denominator orphan transitions:            0
Raw TTM denominator orphan transitions:               0
Raw TTM denominator states:                           13
Normalized denominator states:                        13
Paired denominator states:                            13
Current raw PE 3Y percentile:                         91.964286
Current normalized PE 3Y percentile:                  22.321429
Percentile comparison:                                DESCRIPTIVE_ONLY
Cycle stage identified:                               NO
Cycle guard empirical validation:                     NOT_ESTABLISHED
Normalized earnings as valid cycle proxy:             NOT_YET_VALIDATED
Mechanical denominator guard:                         CONFIRMED
Full-cycle coverage:                                  NOT_PROVEN
5Y historical validation:                             BLOCKED
5Y remaining facts:                                   DEFERRED_PENDING_IDENTIFICATION_REVIEW
PE numeric scoring:                                   BLOCKED_UNCHANGED
Valuation dimension score:                            NONE
Registry/policy v2:                                   UNCHANGED
Shadow v6:                                            UNCHANGED
Sensitivity v8:                                       UNCHANGED
Production scoring:                                   NOT AUTHORIZED
Overall score:                                        PROHIBITED
Decision:                                             PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_INDEPENDENT_CYCLE_VALIDATION_REQUIRED
Next stage:                                           R4F.4A INDEPENDENT_CYCLE_CONTEXT_VALIDATION_PREFLIGHT NOT STARTED
```

## 1. What was built

- `config/pe_3y_cycle_guard_validation_contract_v1.json` — frozen
  contract (window 2023-07-31..2026-07-31, 728 days; method
  AVERAGE_ROE_X_CURRENT_BVPS; protective-direction definition; recurrence
  gate ≥ 2 distinct raw states, frozen before results; daily rows are not
  independent samples; cycle-stage classification PROHIBITED; scoring
  authorization false).
- `docs/pe_3y_normalized_pe_cycle_guard_validation.md` — method references
  (CFA normalized earnings, walk-forward principle, MIDRANK percentile
  semantics) and repository-specific cuts.
- `src/ashare_research/pit_valuation/pe_cycle_guard_validation.py` —
  pure functions: 3Y series, denominator-state identities (normalized +
  raw), run-length segmentation, direction audit, recurrence audit,
  transition audit, divergence diagnostic, midrank percentile, decision.
  Reuses the R4F.3 resolver unchanged (no second ROE/BVPS/normalized-EPS
  implementation).
- Thin CLI `m2_stage2k1r4f4_pe_cycle_guard_validation.py`
  (build / verify / oracle / fixtures).
- 7 artifacts: series, state ledger, direction audit, transition audit,
  divergence, percentile profile, decision.

## 2. Series (728 days, trusted)

Every day reconstructs, from the R4F3A overlay facts and the R4E.4
PE_A_TTM observation: close, current TTM EPS (official
`per_share_denominator_decimal`, never close/PE back-derived), raw PE
(matches the R4E.4 `ratio_decimal` exactly), selected five ROE years,
average ROE, current BVPS, normalized EPS, normalized PE, and the two
exact rational ratios (`normalized_pe/raw_pe == ttm_eps/normalized_eps`).

- 728/728 days; 0 gaps; all dates unique within the frozen window.
- Current TTM EPS identity: `financial_state_id` bound from R4E.4; 13
  distinct raw TTM denominator states (21-101 days each) — **728 daily
  rows are not 728 independent samples**.
- R4F.3 `normalized_earnings_state_id` unchanged (byte-identical); the new
  `normalized_denominator_state_id` (R4F4) excludes date/price/PE and
  yields 13 episode-level states.

## 3. Direction and recurrence (corrected semantics)

- 644 trade days with current TTM EPS > normalized EPS (protective
  direction), 84 below, 0 equal; **0 direction violations** across all
  three cases (A: EPS above → normalized PE > raw PE; B: below → <;
  C: equal → equal).
- **Identification note**: the relation is algebraically implied by
  `raw_pe = price/current_eps` and `normalized_pe = price/normalized_eps`
  for positive operands.  Zero violations therefore verify implementation
  correctness (`mechanical_direction_consistency = PASS`), **not**
  independent empirical cycle evidence.
- Protective direction spans **11 distinct raw TTM denominator states**
  but forms **1 contiguous segment** → interpreted strictly as
  `CONDITION_OBSERVED_ACROSS_MULTIPLE_DENOMINATOR_STATES`, not
  "independently replicated cycle mechanism"; `independent_protective_episodes =
  NOT_ESTABLISHED`.
- Terminology: `PROTECTIVE_DIRECTION_OBSERVED` only — never PEAK/TROUGH/
  BOOM/RECESSION; ratio > 1 is not a cycle-top threshold.

## 4. Transitions and PIT

- 12 normalized + 12 raw TTM state transitions; **0 orphan transitions**.
- A pure market-price day never transitions a denominator state.
- Restatement perturbation: a synthetic later restatement (effective
  2025-06-02) leaves every historical series row byte-identical.

## 5. Percentile (descriptive only)

- Current normalized PE 3Y percentile: **22.321429** (MIDRANK, N=728,
  L=161 E=2 G=565, rank 325/1456) — Python and independent DuckDB oracle
  match exactly.
- Bound raw PE 3Y percentile (R4E.5): 91.964286.  Comparison labeled
  `DESCRIPTIVE_DENOMINATOR_NORMALIZATION_COMPARISON` — the percentile
  shift proves only that the denominator choice materially changes the
  historical valuation position; it is **not** evidence of normalization
  correctness.  No buy/sell/cheap/expensive interpretation; never a
  scoring input.

## 6. Validation performed (local)

- R4F4 tests: **49 passed** (upstream gate, series exactness, identity
  exclusion/change tests, direction cases + algebraic-identity regression,
  recurrence gate pre-registration, identification gates, transition
  orphans, restatement perturbation, array order, percentile
  Python/DuckDB oracle, no-prohibited-terms, no-future-return, scoring
  zero-change, DB SHA).
- R4F3A: 48 passed; R4F3: 45 passed; R4F2: 35 passed; R4F1: 19 passed.
- Full offline suite: **1883 passed, 2 warnings**.
- ruff: All checks passed; compileall: pass; git diff --check: pass.
- A/B builds byte-identical (7/7); secret/path/pollution scan clean.
- Default DB SHA unchanged (`4a71d3c7…`); stash preserved; protected
  files untouched; R4F3/R4F3A committed artifacts untouched.

## 7. Boundary preserved

- `pe_numeric_scoring_authorized = false`; `cycle_guard_empirically_validated =
  false`; `normalized_earnings_mid_cycle_validated = false`; no PE score;
  no valuation score; no percentile in scoring registry; no 5Y percentile;
  no future-return/backtest; no peer; no network; no default-DB write; no M3.
- Mechanical denominator guard **CONFIRMED**; normalized earnings as a
  valid cycle proxy **NOT_YET_VALIDATED**; independent cycle-context
  validation **NOT_ESTABLISHED** — full_cycle remains NOT_PROVEN, 5Y
  remains BLOCKED, single issuer only.
- Next stage R4F.4A is an **Independent Cycle-Context Validation
  Preflight** (freeze a falsifiable contract not defined by the
  raw/normalized PE arithmetic); the remaining 5Y 4 facts are
  `DEFERRED_PENDING_IDENTIFICATION_REVIEW`.
