# M2 Stage 2K.1R4E.5 — Historical Valuation Percentile Preflight & Non-Production Percentile Profile

## Verdict: PASS — LOCAL CANDIDATE

M2 Stage 2K.1R4E.5: **PASS — LOCAL CANDIDATE**
Remote CI: **PENDING**
decision: `PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED`

The frozen `MIDRANK_EMPIRICAL_PERCENTILE` method contract was released
(`config/pit_valuation_percentile_contract_v1.json`,
`docs/historical_valuation_percentile_methodology.md`), the six non-production
historical valuation percentile observations were computed from the trusted
candidate v2 (the **only** valuation input, no re-fetch, no PE/PB/PS
recomputation), a fully independent in-memory DuckDB oracle agreed with the
Python core on all six records (`all_identical = true`), and the PIT /
future-leakage / tie / invalid-status / minimum-sample / boundary audit passed.
The PE interpretation guard is present on every PE record
(`cycle_warning_required = true`). The profile is **non-production** and
**descriptive-only**: it is not mapped to a score, a cheap/expensive label, a
buy/sell recommendation, a target price, or a margin-of-safety conclusion. No
production Metric Result, no default-DB write, no scoring change, no M3.

Per explicit instruction, local validation is complete and work **stops here**:
nothing is committed and nothing is pushed.

## 0. Final report card

```
M2 Stage 2K.1R4E.5:                                          PASS — LOCAL CANDIDATE
Method contract frozen:                                      config + docs
Rank method:                                                  MIDRANK_EMPIRICAL_PERCENTILE
As-of trade date:                                             2026-07-31
Metrics:                                                      PE_A_TTM / PB_A_MRQ / PS_A_TTM
Windows:                                                      3y (eff 2023-07-31) / 5y (eff 2021-08-02)
Records:                                                      6 (PE/PB/PS x 3y/5y)
Sample counts:                                                3y N=728 / 5y N=1211 (all metrics)
Current observation:                                          exactly 1 computed per metric at as-of
DuckDB independent oracle == Python:                          all_identical
Future-leakage gate:                                          pass (max sample date <= as_of)
Tie handling:                                                 midrank (E counted, +1 in numerator)
Invalid-status / non-positive exclusion:                      fail-closed, excluded from N
Minimum-sample gates (3y>=500 / 5y>=900):                    all READY
PE cycle interpretation guard:                               present (cycle_warning_required=true)
Production boundary:                                          non_production=true, score_eligible=false
Decision:   PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED
Scoring integration:                                          NOT STARTED (requires North-Star review)
Default DB:                                                   UNCHANGED
Scoring integration:                                          NOT AUTHORIZED / NOT STARTED
Git:                                                          COMMITTED + PUSHED (LOCAL CANDIDATE); CI PENDING
```

## 1. 6 percentile observations (non-production)

| metric | window | N | L/E/G | rank | midrank | strict | weak |
|--------|--------|---|-------|------|---------|--------|------|
| PE_A_TTM | 3y | 728 | 668/2/58 | 1339/1456 | 91.964286 | 91.758242 | 92.032967 |
| PE_A_TTM | 5y | 1211 | 1128/2/81 | 2259/2422 | 93.270025 | 93.146160 | 93.311313 |
| PB_A_MRQ | 3y | 728 | 617/2/109 | 1237/1456 | 84.958791 | 84.752747 | 85.027473 |
| PB_A_MRQ | 5y | 1211 | 1100/2/109 | 2203/2422 | 90.957886 | 90.834021 | 90.999174 |
| PS_A_TTM | 3y | 728 | 668/2/58 | 1339/1456 | 91.964286 | 91.758242 | 92.032967 |
| PS_A_TTM | 5y | 1211 | 1151/2/58 | 2305/2422 | 95.169282 | 95.045417 | 95.210570 |

For every record `0 <= strict <= midrank <= weak <= 100` and
`N == L + E + G`. The exact rational identity `rank_numerator /
rank_denominator` (e.g. `1339/1456`) is what the `percentile_record_id`
binds — display rounding never affects identity.

## 2. Method

- `MIDRANK_EMPIRICAL_PERCENTILE`: `midrank = 100 * (2L + E + 1) / (2N)`,
  `strict = 100*L/N`, `weak = 100*(L+E)/N`. Ties are averaged via the midrank
  convention.
- **Decimal-only** ranking and comparison (`Decimal(str(...))`), never float.
- Sample eligibility is **fail-closed**: only `status == "computed"` with a
  strictly-positive `ratio_decimal` within the window enters `N`. Non-positive
  PE is never ranked as cheap. All exclusions are recorded in the sample ledger.
- The as-of observation is included (`include_current = true`) and must be found
  exactly once per metric.
- Windows are calendar-year windows mapped to actual trade days. The 5y
  calendar start `2021-07-31` is a non-trading day; the effective first trade
  date is `2021-08-02`.

## 3. Independent DuckDB oracle

`percentile_oracle.py` loads candidate v2 into an isolated in-memory DuckDB,
stores ratios as exact `DECIMAL(38,28)`, and recomputes `N/L/E/G` and
`rank_numerator/rank_denominator` per metric/window with exact `DECIMAL`
comparisons. It deliberately does **not** use `percent_rank()` or `cume_dist()`.
The Python core and the DuckDB oracle agree on all six records
(`all_identical = true`); any mismatch would make the profile NOT_TRUSTED.

## 4. PIT / future-leakage / tie / invalid-status / boundary audit

- `max(sample.trade_date) <= 2026-07-31` for all six windows (future-leakage gate
  pass).
- Tie handling is midrank; `E` enters the rank fraction via `+1` in the
  numerator.
- Invalid status (`missing_ttm_input`, etc.) and non-positive ratios stay in the
  exclusion ledger and never enter `N`.
- Window boundary is `effective_first <= trade_date <= as_of`; the 5y effective
  first `2021-08-02` is asserted in the frozen config.

## 5. PE interpretation guard

Every PE_A_TTM record carries
`interpretation_guard_id = low_pe_not_automatic_undervaluation_v1` with
`interpretation = DESCRIPTIVE_RELATIVE_VALUATION_ONLY` and
`cycle_warning_required = true`. A low PE percentile is **not** treated as
automatic evidence of undervaluation.

## 6. Decision

`reports/m2_stage2k1r4e5_decision.json`:
`PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED` (exit 0),
`oracle_identical = true`, `all_windows_ready = true`, `record_count = 6`,
`north_star_review_required = true`. This authorises a downstream independent
North-Star review of scoring integration; it does **not** itself integrate
scoring or start M3.

## 7. Artifact manifest

`reports/m2_stage2k1r4e5_artifact_manifest.json`, schema
`m2_stage2k1r4e5_artifact_manifest_v2` (registered in `artifact_manifest.py`
ALLOWED + V2_SCHEMAS). Verified `status: pass` (all files present, 0 hash
mismatches), covering config, docs, code, tests, all six percentile reports,
the decision, and the acceptance doc.

## 8. Product boundary

- No historical percentile mapped to a valuation score; no cheap/fair/expensive
  bucket; no buy/sell/target price/margin-of-safety conclusion.
- No scoring weight/threshold/sensitivity change; no production Metric Result;
  no default-DB write (SHA unchanged).
- No candidate v2 / registry v4 / R4E.4 decision modification; no market
  re-fetch; no PE/PB/PS recomputation; no peer percentile; no rolling percentile
  series.
- No M3 started.

## 9. Validation

- R4E.5 tests: **29 passed** (offline).
- Full offline pytest: **1668 passed, 2 pre-existing warnings**.
- `ruff check` on all changed files: All checks passed.
- `git diff --check`: pass.
- Manifest verifier: R4E.5 manifest `status: pass`.
- Protected files (`AGENTS.md`, `agent/goals/`, `acceptance/m2_stage2i2r_*`,
  stash, default DB, registry v4, R4E.4 decision) untouched.

## 10. Deliverables

- `config/pit_valuation_percentile_contract_v1.json`
- `docs/historical_valuation_percentile_methodology.md`
- `src/ashare_research/pit_valuation/historical_percentile.py`
- `src/ashare_research/pit_valuation/percentile_oracle.py`
- `src/ashare_research/tools/m2_stage2k1r4e5_historical_percentile.py`
- `src/ashare_research/scoring/artifact_manifest.py` (schema registered)
- `reports/petrochina_pit_valuation_percentile_profile_v1.json`
- `reports/petrochina_pit_valuation_percentile_sample_ledger_v1.json`
- `reports/petrochina_pit_valuation_percentile_dual_oracle_v1.json`
- `reports/petrochina_pit_valuation_percentile_method_audit_v1.json`
- `reports/petrochina_pit_valuation_percentile_audit_samples_v1.json`
- `reports/m2_stage2k1r4e5_decision.json`
- `reports/m2_stage2k1r4e5_artifact_manifest.json`
- `tests/test_m2_stage2k1r4e5_historical_percentile.py`
- `acceptance/m2_stage2k1r4e5_historical_valuation_percentile.md`
- `agent/record/2026-08-07_Stage2K1R4E5_historical_valuation_percentile.md`

## 11. Next steps

Scoring integration requires an independent North-Star review of the
non-production percentile profile before any scoring change; entry to scoring
is **not** authorised by this stage (`Scoring integration: NOT AUTHORIZED`,
`Next-stage implementation: NOT STARTED`). R4E.5 is committed and pushed as a
**LOCAL CANDIDATE**; remote CI is pending.