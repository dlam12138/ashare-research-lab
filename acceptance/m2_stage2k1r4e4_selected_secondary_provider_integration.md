# M2 Stage 2K.1R4E.4 — Selected Secondary Provider Integration & Registry v4 Release

## Verdict: PASS — LOCAL CANDIDATE

M2 Stage 2K.1R4E.4: **PASS — LOCAL CANDIDATE**
Remote CI: **PENDING**
decision: `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`

The R4E.3-selected secondary provider `tencent_via_akshare` (underlying Tencent,
endpoint `web.ifzq.gtimg.cn`, object `d760923a…`) is **formally integrated**:
a new immutable registry v4 (`events/market_data_snapshot_registry_v4.json`)
resolves the two market providers by **role** (primary/secondary) instead of by
provider name, the R4E.3 Tencent object was **promoted byte-identical** into the
formal content-addressed cache (no re-request, no Sina fallback), a real
dual-source reconciliation **v2** bound the role identity and passed on all 1351
common trade days (max close diff 0, over-tolerance 0), and the **non-production**
PIT PE/PB/PS candidate v2 was published (4053 observations, ALLOWED). The
economic identity migration from candidate v1 → v2 left ratio/status/market-close
**unchanged** (0/0/0) with only the expected lineage-identity bindings changed.
No percentile, no scoring, no peer, no production Metric Result, no default-DB
write, no M3. Local validation is complete; **nothing was committed or pushed**.

## 0. Final report card

```
M2 Stage 2K.1R4E.4:                                     PASS
Provider-role abstraction:                              TRUSTED
Registry v4 (immutable):                                COMPLETE / pass
R4E.3 object promotion (byte-identical):                d760923a… ✓
Formal reconciliation v2 (1351 days):                   pass
  max abs close difference:                             0
  differences over tolerance:                           0
Reconciliation digest:                                  4fb3382b25e5…
Candidate v2 (non-production):                          ALLOWED
  observation count:                                    4053
Economic migration v1 → v2:                             TRUSTED
  ratio / status / market-close changed:                0 / 0 / 0
Dual oracle (Python == DuckDB ASOF):                    all_identical
Coverage gate (PE/PB/PS 3y+5y):                         READY
Decision:               PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED
Historical percentiles:                                 NOT COMPUTED
Valuation scoring:                                      UNCHANGED_NON_PRODUCTION
Default DB:                                             UNCHANGED
Peer acquisition:                                       NOT ALLOWED
M3:                                                     NOT STARTED
Git:                                                    NOT COMMITTED / NOT PUSHED
```

## 1. Scope

This stage formally integrated the R4E.3-selected secondary provider
`tencent_via_akshare` into the market-data release path, replaced the hard-coded
`primary=baostock / secondary=akshare` business contract with a role-based
provider abstraction, created the immutable registry v4, ran the real formal
Baostock+Tencent dual-source reconciliation under the v2 contract, published the
non-production PIT PE/PB/PS candidate v2, and verified the economic identity
migration and the dual oracle. It did **not** compute percentiles, update scoring,
acquire peers, write a production Metric Result, or start M3.

## 2. Provider-role abstraction

`src/ashare_research/pit_valuation/provider_roles.py`:

- Registry v4 entries carry `provider_id`, `provider_role`, `transport_library`,
  `underlying_provider`, `object_key`, `sha256`, `table_digest`, row/date fields.
- Legacy v2/v3 registries carry a `provider` name; a read-only compatibility
  adapter maps `baostock -> primary` and `akshare -> secondary`. Old registries are
  never modified and historical artifact digests never change.
- Fail-closed: exactly one `primary` and exactly one `secondary` are required;
  0 or >1 of either role raises `ProviderRoleError` (NOT_TRUSTED), never a silent
  fallback.
- The formal release path never calls `load(..., "akshare")`; it resolves by role.

## 3. Registry v4 (staged)

`events/market_data_snapshot_registry_v4.json`:

- `contract = market_data_snapshot_registry_v4`, `schema_version = 4.0`,
  `supersedes_registry = events/market_data_snapshot_registry_v3.json`,
  `supersession_reason = selected_alternative_secondary_provider_formally_integrated`.
- Written first as a draft (`integration_status = PENDING_REAL_RECONCILIATION`,
  `reconciliation_status = pending`) and frozen to `COMPLETE` / `pass` **only after**
  the real formal v2 reconciliation passed.
- Binds `r4e3_decision_digest`, `r4e3_comparison_digest` (`21a1ad83…`),
  `r4e3_mismatch_ledger_digest` (`d1dba16c…`), and the formal `reconciliation`
  block with `formal_reconciliation_digest`.
- Providers: `baostock_primary` (primary, `c6771aa5…`, 1351 rows,
  2021-01-04..2026-07-31) and `tencent_via_akshare` (secondary, transport akshare,
  underlying tencent, endpoint `web.ifzq.gtimg.cn`, `d760923a…`, 1351 rows).

## 4. Object promotion (byte-identical, no re-request)

`reports/petrochina_tencent_snapshot_promotion_receipt_v1.json`:

- The R4E.3 selected object `d760923a…` was located in the R4E.3 cache,
  identity-verified (sha `d760923a…`, table digest `e6cbee88…`, 1351 rows,
  2021-01-04..2026-07-31, endpoint `web.ifzq.gtimg.cn`), and copied byte-identical
  into the formal cache at `r4e4/tencent_via_akshare/d760923a…parquet`.
- `promotion_mode = byte_identical_content_addressed_copy`,
  `byte_identity_preserved = true`. No re-request, no Sina fallback, no Baostock
  backfill of candidate gaps.

## 5. Formal reconciliation v2

`reports/petrochina_market_close_reconciliation_v2.json` +
`reports/petrochina_market_close_mismatch_ledger_v2.json`:

- Contract `pit_valuation_market_double_source_reconciliation_v2` binds the
  primary/secondary **role identity** into the digest.
- Real run: `common_trade_days = 1351`, `max_abs_close_difference = 0`,
  `differences_over_tolerance_count = 0`, `primary_only_dates = 0`,
  `secondary_only_dates = 0`, `reconciliation_status = pass`.
- `reconciliation_digest = 4fb3382b25e5889e…` (independently recomputable).

## 6. Candidate v2 (non-production)

`reports/petrochina_pit_valuation_series_candidate_v2.json`:

- `observation_count = 4053` (PE_A_TTM + PB_A_MRQ + PS_A_TTM × 1351 trade days).
- Every observation binds the primary object sha `c6771aa5…`, the secondary object
  sha `d760923a…`, and the v2 reconciliation digest `4fb3382b25e5…`.
- `non_production = true`, `percentile_computed = false`, `score_eligible = false`,
  `production_eligible = false`.

## 7. Economic identity migration v2

`reports/petrochina_pit_valuation_series_identity_migration_v2.json`:

- From candidate v1 → v2: `ratio_changed_count = 0`, `status_changed_count = 0`,
  `market_close_changed_count = 0` (Decimal-normalized; `"6.0" == "6"`).
- Only the expected lineage bindings changed: `financial_state_changed_count = 1351`
  (PB lineage identity), `observation_id_changed_count = 4053`. These are the
  intended v2 identity contract changes, not economic changes.
- `_economic_migration_trusted = true`; any unexplained ratio/status change would
  have made the series NOT_TRUSTED.

## 8. Dual oracle

`reports/petrochina_pit_valuation_series_dual_oracle_validation_v2.json`:

- Pure-Python backward sweep == DuckDB ASOF LEFT JOIN on every metric
  (PE_A_TTM, PB_A_MRQ, PS_A_TTM), `row_count = 1351`, `mismatch_count = 0`,
  `all_identical = true`, `trusted = true`. The join is backward-only
  (`effective_from <= trade_date`); no forward/nearest ASOF join.

## 9. Coverage gate

`reports/petrochina_pit_valuation_series_coverage_v2.json`:

- PE_A_TTM, PB_A_MRQ, PS_A_TTM all `3y_ready = true` and `5y_ready = true`
  (effective sample counts ≥ 3y 500 / 5y 900 thresholds).

## 10. Decision

`reports/m2_stage2k1r4e4_decision.json`:

- `decision = PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`
  (exit 0). This authorises entry to the historical percentile preflight; it does
  **not** itself compute percentile, update scoring, or start M3.

## 11. Artifact manifest

`reports/m2_stage2k1r4e4_artifact_manifest.json`, schema
`m2_stage2k1r4e4_artifact_manifest_v2` (registered in `artifact_manifest.py`
ALLOWED + V2_SCHEMAS). Verified `status: pass` (all files present, 0 hash
mismatches), covering registry v4, promotion receipt, reconciliation v2, ledger
v2, candidate v2, timeline, coverage, audit, dual, migration, decision, plus the
acceptance doc, config, docs, code and tests that define this release.

## 12. Product boundary

- No historical percentile computed; no percentile JSON written.
- No valuation scoring weight/threshold/sensitivity change; no production Metric
  Result; no default-DB write (SHA unchanged).
- No peer acquisition; no M3 started.
- Registry v3 not modified; R4E.3 decision not overwritten; no Sina fallback.
- No Parquet / raw response / DuckDB / token / proxy config / absolute path
  committed.

## 13. Validation

- New R4E.4 tests: **40 passed** (offline; provider roles, promotion, registry v4
  draft→final, v2 reconciliation, candidate v2, identity migration, dual oracle,
  manifest, product-boundary invariants).
- Full offline pytest: **1639 passed, 2 pre-existing warnings**.
- `ruff check` on all changed files: All checks passed.
- `git diff --check`: pass.
- Manifest verifier: R4E.4 manifest `status: pass`; R4C1 manifest re-verified
  `status: pass` (only the `artifact_manifest.py` SHA/length change).
- Protected files (`AGENTS.md`, `agent/goals/`, `acceptance/m2_stage2i2r_*`,
  stash, default DB) untouched.
- Pollution/secret scan: no absolute path, no proxy, no token in new code/config.

## 14. Deliverables

- `events/market_data_snapshot_registry_v4.json`
- `config/pit_valuation_secondary_provider_preflight_v1.json` (from R4E.3)
- `docs/selected_secondary_provider_integration_contract.md`
- `src/ashare_research/pit_valuation/provider_roles.py`
- `src/ashare_research/tools/m2_stage2k1r4e4_secondary_provider_integration.py`
- `src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py` (modified)
- `src/ashare_research/pit_valuation/market_reconciliation.py` (modified)
- `src/ashare_research/scoring/artifact_manifest.py` (modified)
- `reports/petrochina_tencent_snapshot_promotion_receipt_v1.json`
- `reports/petrochina_market_close_reconciliation_v2.json`
- `reports/petrochina_market_close_mismatch_ledger_v2.json`
- `reports/petrochina_pit_financial_state_timeline_v2.json`
- `reports/petrochina_pit_valuation_series_candidate_v2.json`
- `reports/petrochina_pit_valuation_series_coverage_v2.json`
- `reports/petrochina_pit_valuation_series_audit_samples_v2.json`
- `reports/petrochina_pit_valuation_series_dual_oracle_validation_v2.json`
- `reports/petrochina_pit_valuation_series_identity_migration_v2.json`
- `reports/m2_stage2k1r4e4_decision.json`
- `reports/m2_stage2k1r4e4_artifact_manifest.json`
- `tests/test_m2_stage2k1r4e4_selected_provider_integration.py`
- `acceptance/m2_stage2k1r4e4_selected_secondary_provider_integration.md`
- `agent/record/2026-08-07_Stage2K1R4E4_selected_secondary_provider_integration.md`

## 15. Next steps

Historical PIT percentile preflight (the authorised next stage): compute the PIT
PE/PB/PS historical percentiles, then the valuation scoring preflight. Local
validation is complete; commit/push and percentile entry await explicit
authorisation.