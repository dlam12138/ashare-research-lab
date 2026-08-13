# 工作记录：M2 Stage 2K.1R4E.3 — Alternative Secondary Market Provider Preflight

Status: completed
Verdict: PASS
Decision: ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED
Selected provider: tencent_via_akshare

## 基本信息

- 日期：2026-08-06
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`43234e1`（== 预期起点）
- 任务来源：用户指令 M2 Stage 2K.1R4E.3
- 对应模块：价值评估（alternative secondary provider preflight）

## 任务目标

对免费、独立于 Eastmoney 的 A 股日线来源做有限、可审计的 provider preflight，
从候选来源中选出可进入下一阶段正式集成的 secondary provider。本轮只做 preflight：
不修改 registry v3、不发布 candidate v2、不计算历史分位、不更新评分、不采集同行、不启动 M3。

## 范围

- 新增 `config/pit_valuation_secondary_provider_preflight_v1.json`（冻结候选范围）。
- 新增 `docs/alternative_secondary_market_provider_preflight.md`（参考设计记录）。
- 新增 `src/ashare_research/pit_valuation/secondary_provider_preflight.py`（独立 preflight 包）。
- 新增薄 CLI `src/ashare_research/tools/m2_stage2k1r4e3_secondary_provider_preflight.py`
  （verify-contracts / probe / acquire / compare / fixtures）。
- 真实 probe + 采集可达候选 → 与钉住 Baostock `c6771aa5…` 逐日比较 → 输出 preflight 结果与决策。
- 新增测试、acceptance、本工作记录。
- 修改 `src/ashare_research/scoring/artifact_manifest.py`（注册 R4E.3 manifest schema）并重生成 R4C1 manifest。

## 非目标

- 不修改 registry v3；不创建 registry v4；不发布 candidate v2；不计算 percentile。
- 不更新评分；不写默认 DB；不采集同行；不启动 M3；不开始 R4E.4。
- 不注册新账户、不充值、不把 token 写入任何文件。
- 不使用 Yahoo / 雪球页面 / 随机 CSV；不用 Eastmoney 另一层包装冒充独立来源。
- 未经明确授权不提交、不推送、不创建 PR/tag/release。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `43234e1`；local == origin（0 ahead / 0 behind）。
- R4E.2 decision = `PIT_VALUATION_SERIES_GAPS_REMAIN`；AKShare/eastmoney 次要源
  `BLOCKED_EXTERNAL_PROVIDER_ACCESS`；formal candidate v2 `NOT PUBLISHED`；percentile `NOT ALLOWED`。
- 默认 DB `data/research.duckdb` SHA-256 `4a71d3c7b88c0b16…`（未变；financial_facts=0）。
- registry v3 `events/market_data_snapshot_registry_v3.json`：baostock `c6771aa5…`（1351 行，
  2021-01-04..2026-07-31，adjustment=none），AKShare provider_gap，`reconciliation_status=pending_real_reconciliation`。
- Baostock 钉住对象存在于 `tmp/market_cache/baostock/c6771aa5….parquet`。
- 受保护项：`AGENTS.md`、`agent/goals/`（untracked）、`acceptance/m2_stage2i2r_*.md` 既有 1 行编辑、
  `stash@{0}`、默认 DB。
- 环境：Python 3.13.9；akshare 1.18.79；baostock 0.9.3；pandas 2.3.3；pyarrow 21.0.0；duckdb 1.5.5。
  pytdx 未安装；tushare 未安装（无 token）。
- 网络（2026-08-06 实测 probe）：**Tencent**（`ak.stock_zh_a_hist_tx`）可达；
  **Sina**（`ak.stock_zh_a_daily`）可达；Eastmoney（`push2his.eastmoney.com`）仍不可达（R4E.2 已记录）。

## 实施计划

1. 建工作记录（本文件）。
2. 新增 preflight 合同 config（候选范围冻结：tencent/sina/pytdx/tushare）。
3. 新增参考设计文档。
4. 新增 `secondary_provider_preflight.py`（合同校验/规范化/独立判断/A-B/比较/公司行动/分类/选择/决策）。
5. 新增薄 CLI。
6. 真实 probe → 对可达候选采集 A/B → 与 Baostock 比较 → 生成 reports + 决策 + manifest。
7. 新增测试。
8. 全量验证（pytest/ruff/compileall/git diff --check/manifest/pollution scan/受保护项）。
9. 写 acceptance 与本记录结果。

## 决策记录

| 决策 | 采用原因 | 考虑过的替代方案 | 未采用原因 | 潜在风险 |
| --- | --- | --- | --- | --- |
| 候选范围冻结为 tencent/sina/pytdx/tushare，transport 与 underlying 分离 | 每个候选可统一规范化、可独立判断、可逐日比较 | 合并为"akshare 一个源" | 掩盖 underlying 独立性 | 无 |
| 统一 14 列规范行（symbol/trade_date/OHLC/volume/amount/is_trading/adjustment/transport/underlying/version/endpoint） | 每个候选与 Baostock 主源及彼此可比 | 各 provider 各自 schema | 无法统一比较 | 无 |
| close/trade_date/adjustment 为硬门禁，volume/amount 单位显式登记或 not_comparable | 与本项目既有 Decimal 合同一致；volume 差异非阻断 | 把所有字段都当硬门禁 | 过度耦合 | 需在报告中登记单位 |
| 与钉住 Baostock `c6771aa5…` 逐日精确比较（0.01 CNY/share 容差） | 复用 R4E.2 已确认真实主源 | 新建第二个主源 | 增加不必要复杂度 | 无 |
| pytdx 未装库 → 尝试安装并真实 probe；服务器不可达 → BLOCKED | 诚实报告真实访问结果 | 直接把 pytdx 标 BLOCKED"库未装" | 未反映真实网络阻塞 | 无 |
| tushare 无 token → `credential_not_available`（not_a_failure）→ BLOCKED | 符合冻结合同；不注册/不充值 | 静默跳过 | 隐藏状态 | 无 |
| 确定性非加权选择规则，顺序无关 | 可复现、可解释 | 加权总分 | 会掩盖严重风险 | 无 |
| R4E.3 manifest schema 注册到 artifact_manifest.py ALLOWED + V2_SCHEMAS，并重生成 R4C1 manifest | 让 R4E.3 manifest 通过 verifier；R4C1 保护 | 绕过 verifier | 破坏 R4C1 保护 | 需同步重生成 R4C1 manifest |

## 实际操作

1. 阅读 `agent/agent.md`、`agent/record/README.md`、最近三份记录（R4E.2/R4E.1/R4E）、R4E.2 acceptance。
2. 核对开始状态：分支 `feat/m2-value-assessment-mvp` HEAD `43234e1`，0 ahead/0 behind，stash 存在，
   默认 DB `4a71d3c7b88c0b16…`，registry v3 `c6771aa5…`，受保护项未动。实测 Tencent/Sina 可达。
3. 新增 `config/pit_valuation_secondary_provider_preflight_v1.json`：冻结 4 候选、窗口
   （2021-01-04..2026-07-31、1351 日）、adjustment=none、close 容差 0.01 CNY/share、决策枚举、
   禁止的 eastmoney 主机/underlying、规范化合同、product boundary。
4. 新增 `docs/alternative_secondary_market_provider_preflight.md`。
5. 新增 `src/ashare_research/pit_valuation/secondary_provider_preflight.py`：
   `validate_preflight_contract` / `check_independence`（拒绝 eastmoney 主机与 underlying）/
   `normalize_candidate_rows`（14 列规范行、ISO 严格升序、无重复/空日期、Decimal(str)、无 float repr）/
   `ab_stability` / `validate_pytdx_pages`（overlap/gap/ordering）/
   `compare_to_baostock`（逐日 close/OHLC 比较 + mismatch ledger + comparison digest）/
   `check_adjustment_semantics`（公司行动窗口校验）/
   `classify_candidate`（QUALIFIED/PARTIAL/REJECTED/BLOCKED）/
   `select_provider`（确定性非加权、顺序无关）/ `decide` / `decision_to_exit_code`。
6. 新增薄 CLI `src/ashare_research/tools/m2_stage2k1r4e3_secondary_provider_preflight.py`：
   `verify-contracts`（离线）、`probe`（网络最小可达测试）、`acquire`（网络 A/B 写入外部内容寻址缓存）、
   `compare`（离线，含公司行动窗口与分类/选择/决策，写 comparison matrix + mismatch ledger + decision + manifest）、
   `fixtures`（CI 合成 SYNTHETIC_ENGINEERING_ONLY）。
7. 修改 `src/ashare_research/scoring/artifact_manifest.py`：ALLOWED_MANIFEST_SCHEMAS + V2_SCHEMAS
   注册 `m2_stage2k1r4e3_artifact_manifest`；运行 `tmp/regenerate_r4c1_manifest.py` 重生成 R4C1 manifest。
8. 新增测试 `tests/test_m2_stage2k1r4e3_secondary_provider_preflight.py`（53 项，全离线/确定性，mock 网络）。
9. **真实 preflight**（网络）：`probe` → Tencent 可达 1351 行、Sina 可达 1351 行、Pytdx 不可达
   （安装 pytdx 1.72 后实测 4 个 TongdaXin 服务器全部拒绝连接 → BLOCKED_PROVIDER_ACCESS）、
   Tushare `credential_not_available`。`acquire` → Tencent/Sina 各 A/B STABLE 1351 行。
   `compare` → Tencent/Sina 均 QUALIFIED：common=1351，max close diff=0，over-tolerance=0，
   nonzero=0，changed-OHLC=0，primary-only=0，candidate-only=0，adjustment TRUSTED
   （3 个除息窗口 + 1 个控制窗口）。Pytdx BLOCKED，Tushare BLOCKED。
   决策 `ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED`，selected=tencent_via_akshare。
10. **增强轮（应验收要求）**：
    - pytdx 作为**非核心、函数内延迟导入**的可选依赖：`try: from pytdx.hq import TdxHq_API
      except ModuleNotFoundError`；未安装 pytdx 时模块仍可导入、Tencent/Sina 路径正常、
      `_probe_candidate` 对 pytdx 返回 `dependency_not_available`（reason
      `optional_dependency_not_available`）、`_acquire_pytdx_candidate` 抛
      `PreflightAcquisitionError`。新增 `_pytdx_runtime_version()`（importlib.metadata，缺包返回 None）、
      `pytdx_core_dependency()`（恒 False）、`_akshare_runtime_version()`。**不把 pytdx 加入
      pyproject.toml**。
    - 报告写入 provider 独立性证据：`transport_library` / `underlying_provider` / `endpoint_host` /
      `function_name` / `request_parameters` / `provider_version`（akshare 1.18.79），并显式
      `endpoint_host_not_push2his_eastmoney_com` 与 `underlying_provider_not_eastmoney`。
    - 决策绑定真实对象身份：`selected_provider` / `selected_transport` /
      `selected_underlying_provider` / `selected_provider_dependency` / `selected_object_sha256` /
      `selected_table_digest` / `selected_row_count=1351` / `selected_first_trade_date=2021-01-04` /
      `selected_last_trade_date=2026-07-31` / `selected_comparison_digest` /
      `selected_mismatch_ledger_digest`；probe 报告增加 `pytdx_probe_runtime_version=1.72`、
      `pytdx_core_dependency=false`。
    - 运行 `tmp/regenerate_r4c1_manifest.py` 重生成 R4C1 manifest（仅 artifact_manifest.py SHA/长度变化）。
11. **重跑真实 preflight**（网络 probe + acquire，离线 compare）：对象 SHA 与首轮一致（确定性、内容寻址），
    compare 重新产出 comparison matrix（含独立性证据）、mismatch ledger、decision（含对象身份绑定）、manifest。
12. 全量验证（见「验证」节）。
13. 写 acceptance 与本记录结果。

## 数据与方法说明

- 数据来源：Tencent（ak.stock_zh_a_hist_tx，sh601857，20210101..20260731，adjust=""）；
  Sina（ak.stock_zh_a_daily，sh601857，20210101..20260731，adjust=""）；
  Pytdx（TongdaXin 日 K，服务器不可达）；Tushare（无 token）。
- 基准对象：baostock `c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67`
  （1351 行，2021-01-04..2026-07-31，adjustment=none）。
- 下载时间：2026-08-06（本轮真实采集）。
- 数据日期范围：requested 2021-01-01..2026-07-31；required first=2021-01-04、last=2026-07-31、1351 日。
- 复权方式：不复权（adjust=""）。
- 单位：close 为 CNY/share；volume 为 share、amount 为 CNY（config 显式登记，已与 Baostock 抽查一致）；
  volume 非硬门禁，close/trade_date/adjustment 为硬门禁。
- 缺失值处理：is_trading 标记；缺失日期保留为真实 provider gap，不 reindex 补齐。
- 是否未来数据泄漏：无。快照仅按交易日期组织。
- 统计阈值：A/B 以 canonical table digest 全等为准；与 Baostock 比较 close 容差 0.01 CNY/share；
  公司行动窗口：3 个除息日 + 1 个控制窗口，窗口前后各 2 个交易日。
- 证据等级：Tencent/Sina 为真实外部数据（A/B 稳定、1351 日、close 与 Baostock 完全一致）；
  Pytdx/Tushare 为 BLOCKED（服务器不可达 / 无凭据）。preflight 为真实证据，PASS。

## 验证

- `pytest tests/test_m2_stage2k1r4e3_secondary_provider_preflight.py`：通过（**59** passed，含增强轮 +6 测试）。
- `pytest`（R4E.3 + R4E.2 + R4E.1 + R4C1）：通过（**174** passed）。
- 全量离线 `pytest`：通过（**1599** passed，2 个既有 warning；R4E.3 +59 测试；基线 1540 +59）。
- `ruff check`（所有改动文件）：全部通过。
- `compileall`：通过。
- `git diff --check`：通过。
- manifest verifier：R4E.3 manifest `status: pass`（4 文件）；R4C1 manifest 重生成后 `status: pass`（17 文件）。
- R4C1 manifest diff：仅 `src/ashare_research/scoring/artifact_manifest.py` SHA/长度变化（注册 R4E.3 schema），
  无其他文件变化——符合增强轮验收第 3 项。
- 受保护项检查：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 1 行编辑、
  `stash@{0}`、默认 DB 全部未改动。
- pollution/secret/path：新模块/CLI/config/reports 无绝对路径、无代理、无 token、无 tmp/ 泄漏；
  pytdx 未加入 pyproject.toml（非核心依赖）。

## 结果

- 已完成：preflight 合同、参考设计、独立 preflight 包、薄 CLI、manifest schema 注册 + R4C1 重生成、
  R4E.3 报告（probe/comparison matrix/mismatch ledger/decision/manifest）、59 项新测试、acceptance、本记录。
- 增强轮完成：pytdx 非核心延迟导入（未装仍可导入/运行 Tencent/Sina、probe 报 dependency_not_available）、
  provider 独立性证据写入 comparison matrix、决策绑定真实对象身份（object sha/row count/首末交易日期/
  comparison digest/mismatch ledger digest、pytdx 运行版本、核心依赖标志）。
- 真实 preflight：Tencent QUALIFIED、Sina QUALIFIED、Pytdx BLOCKED、Tushare BLOCKED；
  决策 `ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED`，selected=tencent_via_akshare；
  增强轮重跑对象 SHA 与首轮完全一致（内容寻址、确定性）。
- 未完成（正确留出，非失败）：registry v3 不修改、candidate v2 不发布、percentile 不计算、R4E.4 不启动。
- 当前可用：preflight 全链路可用；selected provider = tencent_via_akshare 可进入 R4E.4 正式集成。

## 遗留问题

- Pytdx/TongdaXin 服务器在本环境不可达（BLOCKED）；如需作为附加一致证据，可在可达网络重试。
- Tushare 无 token（credential_not_available）；如需启用，需在环境预置合法 token 且不新增付费。
- 本阶段未计算历史分位、未发布 candidate v2（应在 R4E.4 之后进入 percentile preflight）。

## 下一步建议

- R4E.4 — Selected Secondary Provider Integration and Registry v4 Release：以
  tencent_via_akshare 为 secondary market provider 做正式双源集成、发布 candidate v2、
  进入历史估值分位 preflight。

## 最终文件变更

- 新增：`config/pit_valuation_secondary_provider_preflight_v1.json`、
  `docs/alternative_secondary_market_provider_preflight.md`、
  `src/ashare_research/pit_valuation/secondary_provider_preflight.py`、
  `src/ashare_research/tools/m2_stage2k1r4e3_secondary_provider_preflight.py`、
  `reports/petrochina_secondary_provider_probe_v1.json`、
  `reports/petrochina_secondary_provider_comparison_matrix_v1.json`、
  `reports/petrochina_secondary_provider_mismatch_ledger_v1.json`、
  `reports/m2_stage2k1r4e3_decision.json`、
  `reports/m2_stage2k1r4e3_artifact_manifest.json`、
  `tests/test_m2_stage2k1r4e3_secondary_provider_preflight.py`、
  `acceptance/m2_stage2k1r4e3_alternative_secondary_provider_preflight.md`、
  `agent/record/2026-08-06_Stage2K1R4E3_alternative_secondary_provider_preflight.md`。
- 修改：`src/ashare_research/scoring/artifact_manifest.py`（注册 R4E.3 manifest schema）、
  `reports/m2_stage2k1r4c1_artifact_manifest.json`（重生成）。
- 未改动：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`（仅保留既有 1 行编辑）、默认 DB。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`。
- 当前提交：`43234e1`（本阶段提交前起点）。
- 用户已明确授权：按两笔提交（`feat: preflight alternative secondary market providers` →
  `docs: record R4E.3 provider selection`）提交后再普通 push，并等待 CI 门禁。
- 受保护项 `AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 1 行编辑保留在工作区，
  未 stage/未提交；默认 DB 未改动。
- 是否创建提交或 Tag：按授权创建两笔提交；不创建 Tag。
- 是否推送：按授权普通 push；不 force push。
- 未执行：force push、reset --hard、git clean、merge main、创建 PR、tag/release、删除 stash。