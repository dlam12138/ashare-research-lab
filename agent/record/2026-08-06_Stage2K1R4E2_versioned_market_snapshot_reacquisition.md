# 工作记录：M2 Stage 2K.1R4E.2 — Versioned Dual-Source Market Snapshot Reacquisition and Formal Candidate Release

Status: completed
Closeout verdict: CONDITIONAL PASS
Decision: PIT_VALUATION_SERIES_GAPS_REMAIN
Formal candidate v2: NOT PUBLISHED
Historical percentile eligibility: BLOCKED

## 基本信息

- 日期：2026-08-06
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`9e69409c5fde8a498bd9f7b6f2b99cb822f1102c`（== 预期基线）
- 任务来源：用户指令 M2 Stage 2K.1R4E.2
- 对应模块：价值评估（双源行情快照重采 / 真实对账 / formal candidate v2）

## 任务目标

本轮只重新采集并冻结双源日线快照，执行真实行情对账，然后用已完成的 R4E.1 formal 路径
发布非生产 candidate v2。不计算历史分位、不更新估值评分、不采集同行、不启动 M3。

## 范围

- 新增 `config/pit_valuation_market_snapshot_acquisition_v1.json`（冻结采集合同）。
- 新增 `src/ashare_research/pit_valuation/market_snapshot_acquisition.py`（采集/规范化/写对象/receipt）。
- 新增薄 CLI `src/ashare_research/tools/m2_stage2k1r4e2_reacquire_market_snapshots.py`：
  acquire / verify / reconcile / formal / fixtures。
- 新增 registry v3 `events/market_data_snapshot_registry_v3.json`（supersedes v2）。
- 真实采集双源 → 真实对账 → formal candidate v2 发布。
- 新增测试、acceptance、本工作记录。

## 非目标

- 不计算 percentile；不更新评分；不启动 peer/M3；不写默认 DB。
- 不覆盖旧 registry v2；不修改旧 Baostock 对象 SHA；不把新下载结果写入旧 object_key。
- 不把单源 Baostock 当正式双源；不用 committed close-percentile 工件代替行情对象。
- 不提交/推送（未经明确授权）。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `9e69409`；local == origin (0 ahead / 0 behind)。
- CI run 31083945305（Stage 2G reproducibility）为 success（Ubuntu 92558913654 / Windows 92558913574 / identity-compare 92559998622）。
- 默认 DB `data/research.duckdb` SHA-256 `4a71d3c7b88c0b16…`。
- 基线：354 Fact / 102 Metric Result / 16 definitions；R4E.1 decision = `PIT_VALUATION_SERIES_GAPS_REMAIN`。
- 旧 market registry v2（events/market_data_snapshot_registry.json）：baostock `defd0b95…` 本地存在；
  akshare `203ddfd7…` 本地缺失（全范围搜索未找到）。
- 钉住 PIT 市场日历 `config/pit_valuation_market_calendar_registry_v1.json` → baostock
  `77021dced…`（tmp/market_cache/baostock/，1597 行 2020-01-02..2026-08-05；窗口 2021-01-04..2026-07-31 = 1351 行）。
- 受保护项：`acceptance/m2_stage2i2r_*.md` 既有编辑（1 行 status 措辞）、`AGENTS.md`、
  `agent/goals/`、`stash@{0}`、默认 DB。
- 环境：Python 3.13.9；akshare 1.18.79；baostock 0.9.3；pandas 2.3.3；pyarrow 21.0.0；duckdb 1.5.5。
- 网络：Baostock 登录 + query_history_k_data_plus 可用；AKShare stock_zh_a_hist 可用（实测 2021-01-04..15）。

## 实施计划

1. 建工作记录（本文件）。
2. 新增采集合同 config。
3. 新增 market_snapshot_acquisition.py（acquire/normalize/write_content_addressed/build_receipt/validate_receipt）。
4. 新增薄 CLI。
5. R4E.1 CLI formal 增加显式 `--market-registry`。
6. 真实采集双源 A/B → 写外部缓存 → 生成 registry v3 + receipt。
7. 真实对账 + 新旧 Baostock diff → v2 reports。
8. formal candidate v2（用 registry v3）。
9. 新增测试。
10. 全量验证（pytest/ruff/compileall/git diff --check/manifest/pollution scan）。
11. 写 acceptance 与本记录结果。

## 决策记录

| 决策 | 采用原因 | 考虑过的替代方案 | 未采用原因 | 潜在风险 |
| --- | --- | --- | --- | --- |
| 内容寻址对象：`<cache-root>/<provider>/<sha256>.parquet`，SHA 取自最终规范化文件的原始字节 | 对象身份可复现、可审计、A/B 可对比 | 用时间戳/序号命名 | 破坏可复现性 | 无 |
| OHLC/amount 用规范 Decimal 字符串（`Decimal(str).normalize()` 格式化 `f`），不用 float repr | 业务身份稳定，避免浮点尾差导致 A/B 误判 | 直接存 float | 不可靠 | 无 |
| A/B 双跑：每 provider 独立采集两次，比较 canoncal table digest | 捕获采集/规范化非确定性 | 单跑 | 无法发现不稳定 | 两倍网络开销 |
| AKShare 不可达 → 记为 `provider_gap`，决策 `GAPS_REMAIN`（fail-closed） | 不伪造双源通过；符合合同 | 用 Baostock 单源冒充双源 | 违反诚实与合同 | 本轮无法发布 candidate v2 |
| registry v3 `reconciliation_status` 初始为 `pending_real_reconciliation`，不预写 pass | 真实对账后才升级 | 预写 pass | 伪造证据 | 无 |
| R4E.1 formal 增加显式 `--market-registry`，绝不用隐式 "latest" | 调用方显式指定 registry | 默认取最新 | 隐式可能选错对象 | 无 |
| R4E.2 manifest schema 注册到 artifact_manifest ALLOWED + V2_SCHEMAS，并重新生成 R4C1 manifest | 让 R4E.2 manifest 通过 verifier；R4C1 钉住 artifact_manifest.py | 绕过 verifier | 破坏 R4C1 保护 | 需同步更新 R4C1 的 sha256/byte_size |

## 实际操作

1. 阅读 `agent/agent.md`、`agent/record/README.md`、最近三份记录、相关历史记录（R4E.1、R4D.1b、R4C1）。
2. 确认开始状态：`feat/m2-value-assessment-mvp` HEAD `9e69409`，受保护项未动。
3. 新增 `config/pit_valuation_market_snapshot_acquisition_v1.json`：冻结 symbol=601857.SH、
   requested_start=2021-01-01、required_first_trade_date=2021-01-04、requested_end=2026-07-31、
   required_last_trade_date=2026-07-31、frequency=daily、adjustment=none、currency=CNY、close_unit=CNY/share。
   AKShare: stock_zh_a_hist symbol=601857 period=daily start=20210101 end=20260731 adjust=""。
   Baostock: query_history_k_data_plus code=sh.601857 frequency=d start=2021-01-01 end=2026-07-31 adjustflag=3。
   provider_versions（baostock 0.9.3 / akshare 1.18.79）与 runtime_versions（python 3.13.9 / pandas 2.3.3 / pyarrow 21.0.0）。
   重试策略：每 provider ≤3 次、A/B 双跑、不静默换接口、不第三方回填。
4. 新增 `src/ashare_research/pit_valuation/market_snapshot_acquisition.py`：
   `acquire_baostock_snapshot` / `acquire_akshare_snapshot`（仅网络、有界重试）、
   `normalize_market_snapshot`（12 列规范行、严格升序 trade_date、无重复、规范 Decimal 字符串、volume 转为股）、
   `write_content_addressed_snapshot`（原子写 parquet）、`canonical_table_digest` / `column_schema_digest`、
   `build_acquisition_batch_id` / `build_acquisition_receipt` / `validate_acquisition_receipt`。
5. 新增薄 CLI `src/ashare_research/tools/m2_stage2k1r4e2_reacquire_market_snapshots.py`：
   `acquire`（仅网络，A/B，provider_gap 记录，写 registry v3 + receipt + GAPS 决策）、
   `verify` / `reconcile`（复用 R4E.1 market_reconciliation，写 v2 对账报告 + 新旧 Baostock diff，通过才升级 registry 为 pass）、
   `formal`（调 R4E.1 formal 带 --market-registry 进隔离目录，复制 candidate 报告，写 R4E.2 决策 + manifest）、
   `fixtures`（CI 合成）。
6. 修改 R4E.1 CLI `m2_stage2k1r4e_series_preflight.py`：formal 增加 `--market-registry` 参数。
7. 真实采集：Baostock 成功（A/B 稳定，1351 行，2021-01-04..2026-07-31，对象 `c6771aa5…`）；
   新旧 Baostock 对比 NO_HISTORICAL_DATA_CHANGE（0 个变动 close 日期，max close diff 0.00）。
   AKShare/eastmoney `push2his.eastmoney.com` 不可达（经代理 `127.0.0.1:10808` ProxyError；
   绕过代理 RemoteDisconnected）；Baidu、Baostock 可达 → 判定为 eastmoney 专属阻塞，记录 `provider_gap`。
8. 生成 `events/market_data_snapshot_registry_v3.json`（supersedes v2，ACQUISITION_INCOMPLETE，
   reconciliation_status=pending_real_reconciliation，batch_id=`c4c3239a…`）、
   `reports/petrochina_market_snapshot_acquisition_receipt_v1.json`、
   `reports/m2_stage2k1r4e2_decision.json`（GAPS_REMAIN，candidate_v2_published=false，percentile_computed=false）。
9. 新增测试 `tests/test_m2_stage2k1r4e2_versioned_market_reacquisition.py`（31 项，全离线/确定性，mock 网络）。
10. 离线验证 reconcile + formal 的 ALLOWED 路径（tmp/e2e_r4e2.py 合成双源）：reconcile exit 0、
    registry 升级 pass、NO_HISTORICAL_DATA_CHANGE；formal exit 0、4053 观测（1351×3）、观测同时绑定两个新 SHA、manifest 写出。
11. 修复 manifest 校验失败：把 `m2_stage2k1r4e2_artifact_manifest` 注册进
    `artifact_manifest.py` 的 ALLOWED_MANIFEST_SCHEMAS 与 V2_SCHEMAS，并重新生成
    `reports/m2_stage2k1r4c1_artifact_manifest.json` 中 artifact_manifest.py 的 sha256/byte_size。
12. 全量验证（见「验证」节）。
13. **AKShare 重试（2026-08-06）**：运行 `python tmp/ak_retry.py`（5 次尝试、6s 退避），
    全部返回 `ProxyError`（`push2his.eastmoney.com`）→ FINAL_OK False，exit 1。确认
    eastmoney 阻塞为持久性，`GAPS_REMAIN` 结论成立，不执行 ALLOWED 双源 pipeline。

## 数据与方法说明

- 数据来源：Baostock `query_history_k_data_plus`（sh.601857，adjustflag=3 不复权）；AKShare
  `stock_zh_a_hist`（601857，adjust="" 不复权）。
- 下载时间：2026-08-06（本轮真实采集）。
- 数据日期范围：requested 2021-01-01..2026-07-31；required first=2021-01-04、last=2026-07-31；
  Baostock 实际 1351 行 2021-01-04..2026-07-31。
- 复权方式：不复权（Baostock adjustflag=3；AKShare adjust=""）。
- 单位：close 为 CNY/share；AKShare volume 以手返回，已 ×100 转为股；Baostock volume 为股。
- 缺失值处理：`is_trading` 标记非交易日；规范行 strict 升序、无重复；不把缺失当 0。
- 是否未来数据泄漏：无。所有快照仅按交易日期组织，不含未来信息。
- 统计阈值：A/B 稳定性以规范表 digest 全等为准；对账 close 容差、日期集合一致为准（复用 R4E.1 合同）。
- 证据等级：双源采集为真实外部数据；因 AKShare 缺失，双源对账与 candidate v2 未形成，
  仅 Baostock 单源证据，属 fail-closed 条件通过。

## 验证

- `pytest tests/test_m2_stage2k1r4e2_versioned_market_reacquisition.py`：通过（31 passed）。
- `pytest tests/test_m2_stage2k1r4c1_cross_platform_identity.py`：通过（R4C1 保护，manifest 重生成后仍校验）。
- `pytest tests/test_m2_stage2k1r4e_series_preflight.py`：通过（9 passed，R4E.1）。
- 全量离线 `pytest`：通过（1540 passed，2 个既有 warning；R4E.2 +31 测试）。
- `ruff check`（所有改动文件）：全部通过。
- `compileall`：通过。
- `git diff --check`：通过。
- 受保护项检查：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 1 行编辑、
  `stash@{0}`、默认 DB 全部未改动。
- 提交：两笔（`feat: add versioned dual-source market reacquisition` = `d641899`；
  `docs: record R4E.2 conditional closeout` = `8586193`），已推送 origin。未 force push / reset / merge。
- CI Stage 2G reproducibility（run `31095863441`，head `8586193`）：**success**。
  - clean-clone (ubuntu) `92597606233` success；
  - clean-clone (windows) `92597606313` success；
  - identity-compare `92598869716` success（Ubuntu/Windows 身份指纹一致）。
  CI 全量 pytest（含 31 项 R4E.2 合同测试、R4E.1 保护、R4C1 manifest verifier）通过；CI 不进行真实网络采集。

## 结果

- 已完成：采集合同、采集模块、薄 CLI、R4E.1 `--market-registry`、registry v3、receipt、
  R4E.2 决策（GAPS_REMAIN）、单源 Baostock 真实采集（A/B 稳定，NO_HISTORICAL_DATA_CHANGE）、
  31 项新测试、acceptance、本工作记录、manifest schema 注册 + R4C1 重生成。
- 未完成：AKShare 采集（provider_gap）、双源真实对账、candidate v2 发布、percentile 计算（均被 AKShare 阻塞，正确留出）。
- 与原计划差异：因 eastmoney 不可达，本轮为**条件通过（GAPS_REMAIN）**，未发布 candidate v2。
- 当前可用：单源 Baostock registry v3 已建立；AKShare 恢复后可续跑 reconcile+formal 升级 gate。

## 遗留问题

- AKShare/eastmoney 源不可达（ProxyError / RemoteDisconnected），需在源可达时重跑 `acquire`。
- 无双源真实对账与 candidate v2，gate 仍为 `GAPS_REMAIN`。
- 未计算历史分位、未更新评分（应在双源 gate 升级后进入 percentile preflight）。

## 下一步建议

- 在 AKShare/eastmoney 源可达后重跑 R4E.2 `acquire`，随后 `reconcile` + `formal` 生成 candidate v2，
  将 gate 升级为 `..._ALLOWED`，再进入历史估值分位 preflight。

## 最终文件变更

- 新增：`config/pit_valuation_market_snapshot_acquisition_v1.json`、
  `src/ashare_research/pit_valuation/market_snapshot_acquisition.py`、
  `src/ashare_research/tools/m2_stage2k1r4e2_reacquire_market_snapshots.py`、
  `events/market_data_snapshot_registry_v3.json`、
  `reports/petrochina_market_snapshot_acquisition_receipt_v1.json`、
  `reports/m2_stage2k1r4e2_decision.json`、
  `tests/test_m2_stage2k1r4e2_versioned_market_reacquisition.py`、
  `acceptance/m2_stage2k1r4e2_versioned_market_snapshot_reacquisition.md`、
  `agent/record/2026-08-06_Stage2K1R4E2_versioned_market_snapshot_reacquisition.md`。
- 修改：`src/ashare_research/scoring/artifact_manifest.py`（注册 R4E.2 manifest schema）、
  `reports/m2_stage2k1r4c1_artifact_manifest.json`（重生成 artifact_manifest.py 记录）、
  `src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py`（formal 增加 --market-registry）。
- 未改动：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`（仅保留既有 1 行编辑）、默认 DB。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`。
- 当前提交：`8586193`（docs closeout）；前序实现提交 `d641899`。
- 未提交修改：受保护项仍在工作区（`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 1 行编辑），未 stage/未提交。
- 是否创建提交或 Tag：已创建两笔提交；未创建 Tag。
- 是否推送：已普通推送 `9e69409..8586193`（origin/feat/m2-value-assessment-mvp，0 ahead / 0 behind）。
- 未执行：force push、reset --hard、git clean、merge main、创建 PR、tag/release、删除 stash。