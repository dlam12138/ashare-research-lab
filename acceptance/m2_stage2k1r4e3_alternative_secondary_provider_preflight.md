# M2 Stage 2K.1R4E.3 — Alternative Secondary Market Provider Preflight

## Verdict: PASS

M2 Stage 2K.1R4E.3: **PASS**
decision: `ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED`

The bounded, auditable preflight of free, Eastmoney-independent A-share daily
sources is **implemented and fully tested**, and a real preflight was run against
live Tencent and Sina endpoints. Both `tencent_via_akshare` and `sina_via_akshare`
were acquired in two independent A/B runs (stable, 1351 rows each) and matched the
pinned Baostock primary `c6771aa5…` exactly on every one of the 1351 required trade
days (max close difference 0, over-tolerance 0), with trustworthy unadjusted
adjustment semantics across 3 ex-dividend windows + 1 control window. The
deterministic non-weighted selection rule chose **`tencent_via_akshare`** as the
secondary provider to enter the next-stage formal integration. No registry v3
change, no candidate v2, no percentile, no scoring, no default-DB write, no peer,
no M3.

## 0. Final report card

```
M2 Stage 2K.1R4E.3:                                     PASS
Tencent via AKShare:                                    QUALIFIED
Sina via AKShare:                                       QUALIFIED
Pytdx / TongdaXin:                                      BLOCKED
Tushare Pro:                                            BLOCKED
Selected provider:                                      tencent_via_akshare
Provider independence:                                  TRUSTED
A/B stability:                                          TRUSTED
Required trade days:                                    1351
Maximum close difference:                               0
Differences over tolerance:                             0
Adjustment semantics:                                   TRUSTED
Artifact manifest:                                      TRUSTED
Registry v3:                                            UNCHANGED
Formal candidate v2:                                    NOT PUBLISHED
Historical percentiles:                                 NOT COMPUTED
Valuation scoring:                                      UNCHANGED_NON_PRODUCTION
Default DB:                                             UNCHANGED
Peer acquisition:                                       NOT ALLOWED
M3:                                                     NOT STARTED
Decision:                            ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED
Next-stage implementation:                              NOT STARTED (R4E.4)
```

## 1. Scope

This stage froze a bounded candidate list of free, Eastmoney-independent A-share
daily sources, implemented an independent preflight package + thin CLI
(verify-contracts / probe / acquire / compare / fixtures), ran a real preflight
against the reachable Tencent and Sina endpoints, compared each candidate against
the pinned Baostock primary `c6771aa5…`, classified each candidate
(QUALIFIED/PARTIAL/REJECTED/BLOCKED), applied a deterministic non-weighted
selection rule, and produced the frozen decision. It did **not** modify registry
v3, publish candidate v2, compute percentiles, update scoring, acquire peers, or
start M3 (R4E.4 is the next stage).

## 2. Frozen candidate list

`config/pit_valuation_secondary_provider_preflight_v1.json`:

| candidate | transport_library | underlying_provider | function / params | adjust |
| --- | --- | --- | --- | --- |
| `tencent_via_akshare` | akshare | tencent | `stock_zh_a_hist_tx` sh601857 20210101..20260731 | `""` |
| `sina_via_akshare` | akshare | sina | `stock_zh_a_daily` sh601857 20210101..20260731 | `""` |
| `pytdx_tongdaxin` | pytdx | tongdaxin_quote_server | SH 601857 daily, explicit pagination | n/a |
| `tushare_pro_optional` | tushare | tushare_pro | only if an existing legal token is present | n/a |

`transport_library` and `underlying_provider` are kept **separate**: AKShare is
only a calling tool; Tencent/Sina are the actual underlying providers. Independence
is judged on the underlying provider and endpoint host, never on a function name.

## 3. Independence

- `tencent_via_akshare` → `web.ifzq.gtimg.cn` (Tencent), underlying `tencent`.
- `sina_via_akshare` → `finance.sina.com.cn` (Sina), underlying `sina`.
- The forbidden host `push2his.eastmoney.com` and the forbidden underlying provider
  `eastmoney` are rejected by `check_independence` (→ `rejected_not_independent`).
- A different AKShare function name alone does **not** make a source independent.
- No candidate reads from registry v2/v3 pre-written digests, no committed
  candidate/close-percentile artifact, no Baostock backfill of candidate gaps.

## 4. A/B stability

For each reachable candidate, two independent acquisitions (run A / run B) are
performed, normalized independently, and their canonical table digests compared.
Both reachable candidates were **ACQUISITION_STABLE** (row count A == B == 1351,
date set A == B, table digest A == B). No manual picking between A and B.

## 5. Real preflight evidence

- **probe** (network): Tencent reachable (1351 rows), Sina reachable (1351 rows),
  Pytdx unreachable (all TongdaXin servers refused the connection → BLOCKED), Tushare
  `credential_not_available` (no token; not a failure).
- **acquire** (network): Tencent and Sina each acquired A/B stable, 1351 rows,
  2021-01-04..2026-07-31, adjustment none.
- **compare** (offline): each candidate aligned to the pinned Baostock primary
  `c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67` by exact
  `trade_date`:
  - Tencent: common=1351, max close diff=**0**, over-tolerance=**0**, nonzero=0,
    changed-OHLC=0, primary-only=0, candidate-only=0, adjustment **TRUSTED**.
  - Sina: common=1351, max close diff=**0**, over-tolerance=**0**, nonzero=0,
    changed-OHLC=0, primary-only=0, candidate-only=0, adjustment **TRUSTED**.
- **company-action / adjustment**: 3 ex-dividend windows (2021-09-17, 2022-06-28,
  2022-09-20) + 1 non-event control window (2024-01-15), 2 trade days before/after
  each. Both candidates track the Baostock raw close exactly across every window →
  no pre-adjustment back-write, no post-adjustment accumulation → `TRUSTED`.
- **volume/amount units**: both candidates report volume in shares and amount in
  CNY, registered in the config and confirmed comparable to Baostock (spot-checked
  2026-07-01: Baostock volume 124659910 ≈ Tencent 124659900, close 8.73 identical).
  Volume is not a hard gate; close / trade_date / adjustment are.

## 6. Classification + selection + decision

- `tencent_via_akshare`: **QUALIFIED**
- `sina_via_akshare`: **QUALIFIED**
- `pytdx_tongdaxin`: **BLOCKED** (TongdaXin quote servers unreachable from this
  environment; the pytdx transport library was installed and probed, all four
  public servers refused the connection).
- `tushare_pro_optional`: **BLOCKED** (`credential_not_available`, no token; not a
  failure).

The deterministic non-weighted selection rule (no credential, clear independent
underlying provider, complete single date range, A/B stable, fully satisfies
Baostock date+close contract, maintained interface, lower ban risk, simpler
adapter) chose **`tencent_via_akshare`** (transport akshare, underlying tencent,
endpoint `web.ifzq.gtimg.cn`, 1351 rows). The rule is order-independent: both
Tencent and Sina are QUALIFIED and equally valid; the tie is broken deterministically
by the frozen recommended adoption order. The choice is reproducible (not
hard-coded).

Decision: **`ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED`** (exit 0). This
only authorises entry to the next-stage formal integration (R4E.4); it does **not**
itself modify registry v3, publish candidate v2, or compute percentiles.

## 7. Network boundary

Network is allowed only in `probe` and `acquire`. `verify-contracts`, `compare` and
`fixtures` are fully offline. CI runs only synthetic fixtures
(`evidence_class = SYNTHETIC_ENGINEERING_ONLY`); a real provider selection can only
come from a real local preflight.

## 8. Product boundary

- No registry v3 change; no registry v4 created.
- No candidate v2 published; no percentile computed; no scoring updated.
- No default database modified (SHA `4a71d3c7b88c0b16…` unchanged).
- No peer acquisition; no M3 started (R4E.4 is the next stage).
- No Parquet / raw response / DuckDB / token / proxy config / absolute path / local
  path committed.

## 8a. pytdx is a non-core, function-local optional dependency

- pytdx is **not** added to `pyproject.toml`; `selected_provider_dependency = akshare`.
- The only `from pytdx.hq import TdxHq_API` is inside a function, guarded by
  `try/except ModuleNotFoundError`. A clean clone without pytdx still imports the
  module and runs the Tencent/Sina paths; pytdx is not imported at module top level.
- Without pytdx, probe reports `status = dependency_not_available`,
  `reason = optional_dependency_not_available` (→ BLOCKED); acquisition raises
  `PreflightAcquisitionError("… optional_dependency_not_available …")`. Neither is
  a total-preflight failure, and the selected provider (Tencent) is unaffected.
- Reports record `pytdx_probe_runtime_version = "1.72"` (this environment),
  `pytdx_core_dependency = false`, `selected_provider_dependency = "akshare"`.

## 8b. Provider-independence evidence (reported)

For each reachable candidate the comparison matrix records an
`independence_evidence` block with `transport_library`, `underlying_provider`,
`endpoint_host`, `function_name`, `request_parameters`, `provider_version`
(akshare `1.18.79`), plus the explicit checks
`endpoint_host_not_push2his_eastmoney_com: true` and
`underlying_provider_not_eastmoney: true`.

## 8c. Decision binds real object identity

`reports/m2_stage2k1r4e3_decision.json` binds the frozen decision to the real
selected object: `selected_provider`, `selected_transport`,
`selected_underlying_provider`, `selected_provider_dependency`,
`selected_object_sha256` (`d760923a…`), `selected_table_digest`,
`selected_endpoint_identity`, `selected_row_count = 1351`,
`selected_first_trade_date = 2021-01-04`,
`selected_last_trade_date = 2026-07-31`, `selected_comparison_digest`,
`selected_mismatch_ledger_digest`, `pytdx_probe_runtime_version`, and
`pytdx_core_dependency`.

## 9. Validation

- New R4E.3 tests: **59 passed** (offline, network mocked; includes 6 new tests
  for pytdx optional dependency, decision object-identity binding, and
  independence evidence).
- R4E.2 + R4E.1 + R4C1 combined with R4E.3: **174 passed**.
- Full offline pytest: **1599 passed, 2 pre-existing warnings** (was 1540 before
  this stage; +59 R4E.3 tests).
- `ruff check` on all changed files: All checks passed.
- `compileall`: pass.
- `git diff --check`: pass.
- Manifest verifier: R4E.3 manifest `status: pass` (4 files); R4C1 manifest
  re-verified `status: pass` (17 files) after registering the R4E.3 schema in
  `artifact_manifest.py` (ALLOWED + V2_SCHEMAS) and regenerating it. The R4C1
  manifest diff contains **only** the `artifact_manifest.py` SHA/length change.
- Protected files: `AGENTS.md`, `agent/goals/`, `acceptance/m2_stage2i2r_*` edit,
  `stash@{0}`, default DB all untouched.
- Pollution/secret scan across new module/CLI/config/reports: no absolute path, no
  proxy, no token, no `tmp/` leakage; pytdx left out of `pyproject.toml`.

## 10. Deliverables

- `config/pit_valuation_secondary_provider_preflight_v1.json`
- `docs/alternative_secondary_market_provider_preflight.md`
- `src/ashare_research/pit_valuation/secondary_provider_preflight.py`
- `src/ashare_research/tools/m2_stage2k1r4e3_secondary_provider_preflight.py`
- `reports/petrochina_secondary_provider_probe_v1.json`
- `reports/petrochina_secondary_provider_comparison_matrix_v1.json`
- `reports/petrochina_secondary_provider_mismatch_ledger_v1.json`
- `reports/m2_stage2k1r4e3_decision.json`
- `reports/m2_stage2k1r4e3_artifact_manifest.json`
- `tests/test_m2_stage2k1r4e3_secondary_provider_preflight.py`
- `acceptance/m2_stage2k1r4e3_alternative_secondary_provider_preflight.md`
- `agent/record/2026-08-06_Stage2K1R4E3_alternative_secondary_provider_preflight.md`
- Modified: `src/ashare_research/scoring/artifact_manifest.py` (register R4E.3
  manifest schema), `reports/m2_stage2k1r4c1_artifact_manifest.json` (regenerated).

## 11. Next steps

R4E.4 — Selected Secondary Provider Integration and Registry v4 Release: integrate
`tencent_via_akshare` as the secondary market provider, build the formal candidate
v2 against the dual-source series, enter the historical valuation percentile
preflight.