# M2 Stage 2K.1R4E.2 — Versioned Dual-Source Market Snapshot Reacquisition and Formal Candidate Release

## Verdict: CONDITIONAL PASS

M2 Stage 2K.1R4E.2: CONDITIONAL PASS
decision: `PIT_VALUATION_SERIES_GAPS_REMAIN`

- Engineering implementation: **TRUSTED**
- Baostock reacquisition: **TRUSTED**
- AKShare reacquisition: **BLOCKED_EXTERNAL_PROVIDER_ACCESS**
- Real dual-source reconciliation: **NOT RUN**
- Formal candidate v2: **NOT PUBLISHED**
- Percentile preflight: **NOT ALLOWED**

The versioned dual-source reacquisition pipeline is **implemented and fully
tested**, Baostock was **re-acquired successfully (A/B stable) with
NO_HISTORICAL_DATA_CHANGE versus the old pinned object**, and the new registry
v3 was created with the correct supersession contract. However, the **AKShare
secondary source is unreachable from this environment** (eastmoney
`push2his.eastmoney.com` returns a persistent `ProxyError` through the local
proxy and a `RemoteDisconnected` when bypassing it; Baidu and Baostock both
remain reachable). Per the fail-closed contract, "one provider unable to
acquire" → `GAPS_REMAIN` (formal exit 1). No real dual-source reconciliation and
no formal candidate v2 were published.

- Dual-source acquisition: **INCOMPLETE** (Baostock stable, AKShare provider gap).
- Registry v3: **CREATED** with `supersedes v2`, `reconciliation_status =
  pending_real_reconciliation`, `ab_stability = ACQUISITION_INCOMPLETE`.
- Real market-close reconciliation: **NOT RUN** (blocked by missing AKShare object).
- Formal candidate v2: **NOT PUBLISHED** (blocked by missing secondary market object).
- Percentile computation: **NOT STARTED** (correctly stays out of this stage).

## 1. Scope

This stage froze a versioned dual-source daily market snapshot acquisition
contract, implemented a content-addressed reacquisition module + thin CLI,
attempted a real dual-source acquisition, built registry v3, and (were the
secondary source reachable) would have run the real reconciliation and released
the R4E.1 formal candidate v2. It did **not** compute historical percentiles,
update scoring, acquire peers, or start M3.

## 2. Deliverables

### 2.1 New config — `config/pit_valuation_market_snapshot_acquisition_v1.json`

Frozen acquisition contract for `601857.SH`:

- `requested_start = 2021-01-01`, `required_first_trade_date = 2021-01-04`,
  `requested_end = 2026-07-31`, `required_last_trade_date = 2026-07-31`.
- `frequency = daily`, `adjustment = none`, `currency = CNY`, `close_unit = CNY/share`.
- AKShare: `function = ak.stock_zh_a_hist`, `symbol = 601857`, `start = 20210101`,
  `end = 20260731`, `adjust = ""`.
- Baostock: `function = bs.query_history_k_data_plus`, `code = sh.601857`,
  `frequency = d`, `start = 2021-01-01`, `end = 2026-07-31`, `adjustflag = 3`.
- `provider_versions` (`baostock 0.9.3`, `akshare 1.18.79`) and `runtime_versions`
  (python 3.13.9, pandas 2.3.3, pyarrow 21.0.0).
- Bounded retry policy: at most 3 attempts per provider, 2 A/B runs required,
  no silent interface switch, no third-party backfill.

### 2.2 New module — `src/ashare_research/pit_valuation/market_snapshot_acquisition.py`

- `acquire_baostock_snapshot` / `acquire_akshare_snapshot` — network-only,
  bounded (≤3) retries, no silent interface switch, no web backfill.
- `normalize_market_snapshot` — canonical row contract (`symbol`, `trade_date`,
  `open/high/low/close`, `volume`, `amount`, `is_trading`, `adjustment`,
  `provider`, `provider_version`), strict ascending `trade_date`, no duplicates,
  canonical `Decimal` strings (no float repr for identity), normalized integer
  volume in shares (AKShare 手→shares ×100), no DataFrame index, no absolute path.
- `write_content_addressed_snapshot` — deterministic Parquet (`index=False`,
  pyarrow) to `<cache-root>/<provider>/<sha256>.parquet`; SHA-256 from the final
  normalized file's raw bytes; atomic write.
- `canonical_table_digest` / `build_acquisition_batch_id` /
  `build_acquisition_receipt` / `validate_acquisition_receipt` — deterministic
  receipt whose batch identity is derived only from a canonical payload (never a
  wall-clock timestamp, never an absolute path). Cross-platform digest of the
  normalized table is recomputable.

### 2.3 New CLI — `src/ashare_research/tools/m2_stage2k1r4e2_reacquire_market_snapshots.py`

- Modes: `acquire` (network only), `verify` / `reconcile` / `formal` (offline),
  `fixtures` (CI synthetic).
- `acquire` performs two independent bounded acquisitions (run A / run B) per
  provider into isolated directories, normalizes independently, compares the
  canonical table digest → `ACQUISITION_STABLE` or (after 3 bounded pairs)
  `ACQUISITION_UNSTABLE`. A provider that cannot be acquired is recorded as a
  `provider_gap`; the decision is honestly `GAPS_REMAIN`.
- `reconcile` reuses R4E.1 `market_reconciliation` (no third reconciliation) and
  writes the v2 reconciliation report + mismatch ledger and the old/new Baostock
  revision diff, promoting registry v3 to `pass` only on a real pass.
- `formal` runs the R4E.1 formal with the explicit `--market-registry` into an
  isolated dir (so the committed R4E.1 decision is never overwritten), copies the
  six candidate v2 reports, and writes the R4E.2 decision + manifest.

### 2.4 R4E.1 CLI — explicit `--market-registry`

`m2_stage2k1r4e_series_preflight.py` formal now accepts `--market-registry` so
the caller supplies the registry explicitly (never an implicit "latest").

### 2.5 New registry — `events/market_data_snapshot_registry_v3.json`

- `supersedes_registry = events/market_data_snapshot_registry.json`.
- `supersession_reason = pinned_secondary_object_unrecoverable_versioned_reacquisition`.
- `contract = market_data_snapshot_registry_v3`, `data_class = external_real_data_cache`.
- Acquired provider records carry `object_key`, `sha256`, `row_count`,
  `first/last_trade_date`, `schema_digest`, `table_digest`, `ab_stability`,
  `provider_version`, `function`, `params`.
- `reconciliation_status = pending_real_reconciliation` (never pre-written as pass).
- Old registry v2, old Baostock object `defd0b95…`, and the old R4E/R4E.1
  decision are all preserved untouched.

### 2.6 New reports (real acquisition)

- `reports/petrochina_market_snapshot_acquisition_receipt_v1.json` — records the
  real Baostock acquisition (A/B stable, 1351 rows, 2021-01-04..2026-07-31,
  object `c6771aa5…`), runtime versions, acquisition code commit, and the explicit
  AKShare `provider_gap`.
- `reports/m2_stage2k1r4e2_decision.json` — decision `GAPS_REMAIN`, exit 1,
  `candidate_v2_published = false`, `percentile_computed = false`.
- `reports/petrochina_baostock_snapshot_revision_diff_v1.json` — real old/new
  Baostock object comparison (`defd0b95…` → `c6771aa5…`), independently
  recomputable: same date set (0 old_only / 0 new_only), 0 changed close and OHLC
  dates, `max_close_difference = 0`, classification **NO_HISTORICAL_DATA_CHANGE**.

### 2.7 New tests

`tests/test_m2_stage2k1r4e2_versioned_market_reacquisition.py` — 31 tests, all
offline/deterministic (network mocked), covering: AKShare/Baostock param freeze,
`adjust=""`/`adjustflag=3` registered as unadjusted, provider version in receipt,
A/B same passes, A/B different blocks, canonical table digest recomputable,
object SHA == filename, old registry v2 unmodified, v3 supersedes v2, registry
does not pre-write pass, old/new Baostock diff recomputable, date-set mismatch
fails, close over-tolerance fails, explicit registry to formal, candidate
observation binds both new SHAs, fixture cannot masquerade as formal, no
percentile/score/DB/peer/M3.

## 3. Real acquisition evidence

- Baostock: acquired successfully (A/B stable). New object
  `c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67.parquet`,
  `row_count = 1351`, `2021-01-04..2026-07-31`. Old/new Baostock comparison:
  **NO_HISTORICAL_DATA_CHANGE** (0 changed close dates, max close diff 0.00).
- AKShare: **provider gap** — `stock_zh_a_hist` (eastmoney) unreachable.
  `ProxyError` through local proxy `127.0.0.1:10808`; `RemoteDisconnected` when
  bypassing the proxy. Verified Baidu (proxy + direct) and Baostock remain
  reachable, so this is an eastmoney-specific block, not a total network outage.
  **Retry re-confirmed failure on 2026-08-06**: `tmp/ak_retry.py` (5 attempts, 6s
  backoff) all returned `ProxyError` on `push2his.eastmoney.com` — the gap is
  persistent, so the `GAPS_REMAIN` outcome stands.
- Registry v3 `acquisition_batch_id = c4c3239a…` (canonical, no wall-clock).

## 4. Decision gate

Final decision: `PIT_VALUATION_SERIES_GAPS_REMAIN` (exit 1). One provider
(AKShare) could not be acquired; therefore no real dual-source reconciliation,
no candidate v2, and no percentile. This is the honest fail-closed outcome and
does not fabricate a dual-source pass.

## 5. Product boundary

- No histogram/percentile computed.
- No scoring updated; no production Metric Result.
- No default database modified (SHA unchanged).
- No peer acquisition; no M3 started.
- No Parquet / raw response / DuckDB / network log committed.

## 6. Validation

- New R4E.2 tests: 31 passed.
- R4E.1 tests: 34 passed (after adding `--market-registry`).
- Full offline pytest: **1540 passed, 2 pre-existing warnings** (was 1509 before
  this stage; +31 new tests).
- `ruff check` on all changed files: All checks passed.
- `compileall`: pass.
- `git diff --check`: pass.
- `git status` / protected files checked: `AGENTS.md`, `agent/goals/`,
  `acceptance/m2_stage2i2r_*` edit, `stash@{0}`, default DB all untouched.
- Commits: `d641899` (implementation) + `8586193` (conditinal closeout docs),
  pushed as `9e69409..8586193` (no force push / reset / merge / PR / tag).
- CI Stage 2G reproducibility (`31095863441`, head `8586193`): **success** —
  clean-clone Ubuntu `92597606233`, clean-clone Windows `92597606313`,
  identity-compare `92598869716` (Ubuntu/Windows identity identical). CI ran the
  full pytest (incl. 31 R4E.2 contract tests, R4E.1 protection, R4C1 manifest
  verifier) and performed no real network acquisition.

## 7. CI evidence

- Implementation commit: `d641899` (`feat: add versioned dual-source market reacquisition`).
- Evidence commit: `8586193` (`docs: record R4E.2 conditional closeout`).
- CI run ID: `31095863441` — Ubuntu success (`92597606233`),
  Windows success (`92597606313`), identity-compare success (`92598869716`).
- Full pytest count: 1540 passed, 2 warnings.
- Manifest verification: R4C1 manifest `status: pass`; R4E.2 schema registered
  in ALLOWED + V2_SCHEMAS (no real R4E.2 manifest committed — no real candidate v2).
- Final decision: `PIT_VALUATION_SERIES_GAPS_REMAIN`.

## 7. Next steps

Re-run `acquire` when the AKShare/eastmoney source is reachable; then `reconcile`
(real dual-source) and `formal` (candidate v2) to upgrade the gate to
`..._ALLOWED` and enter the historical valuation percentile preflight.