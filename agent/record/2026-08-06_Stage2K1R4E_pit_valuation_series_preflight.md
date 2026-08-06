# 工作记录：M2 Stage 2K.1R4E — PIT Valuation Series Preflight and Candidate Build

Status: `completed`
Closeout verdict: `CONDITIONAL PASS` (decision `PIT_VALUATION_SERIES_GAPS_REMAIN`)

## 基本信息

- 日期：2026-08-06
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`8760858`（== origin，R4D.1b closeout）
- 任务来源：用户指令（R4E——PIT 估值序列 preflight + 候选序列构建）
- 对应模块：价值评估（PE/PB/PS 候选序列与时间连接合同）

## 任务目标

基于已验收的官方季度分母 Facts（reported 127 / reconciled 38）与双源市场日线，
生成非生产、可审计、可逐日复算的 PE-A-TTM、PB-A-MRQ、PS-A-TTM 候选序列，
判断是否允许进入历史估值分位预检。

## 范围

- 新增 `src/ashare_research/pit_valuation/`：series_contract、financial_state、ttm、
  temporal_join、valuation_series、series_validation。
- 新增薄 CLI：`src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py`。
- 新增 config：`pit_valuation_series_formula_registry_v1.json`、
  `value_evaluation_methodology_valuation_pit_v2.json`（supersedes v1）。
- 新增 docs：`pit_valuation_series_contract.md`。
- 新增 reports：financial_state_timeline、valuation_series_candidate、coverage、
  audit_samples、dual_oracle_validation、decision、artifact_manifest。
- 新增 acceptance：`m2_stage2k1r4e_pit_valuation_series_preflight.md`。
- 新增 tests：series_contract、financial_state、temporal_join、valuation_series、
  series_preflight。

## 非目标

- 不计算/不发布 3y/5y 估值分位值。
- 不更新 valuation-attractiveness shadow；不改评分权重/阈值/transform/sensitivity。
- 不创建生产 Metric Result；不改 canonical value profile。
- 不用 close percentile 代替估值 percentile；不采集同行；不输出评级/目标价/买卖结论。
- 不启动 M3；不写默认 DuckDB。
- 不合并 main、不创建 PR/Tag/Release、不强制推送、不重写已有提交、不删除 stash。
- 不删除/改写 v1 methodology；不动 `market_observation_set.py`；不删旧 close-percentile 工件。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `8760858`；本地 == origin。
- 受保护项：`acceptance/m2_stage2i2r_*.md` 编辑（1 行状态措辞）、`AGENTS.md`、
  `agent/goals/`、`stash@{0}`、默认 DB `data/research.duckdb`（SHA-256 基线 `4a71d3c7…`）。
- 基线计数：354 Fact（roic_canonical_fact_inventory_v2）、102 Metric Result、
  16 definitions（output/ 既有基线，未改动）。
- R4D/R4D.1/R4D.1a/R4D.1b 均已验收：decision `PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT`；
  reported 127 / reconciled 38 / coverage 150 cells / gaps 0。
- market snapshot registry（events/market_data_snapshot_registry.json）两个 1351 行对象：
  baostock（defd0b95…）、akshare（203ddfd7…）。
- market calendar registry：1597 交易日对象（77021dce…）。
- **关键缺口**：akshare 二级市场缓存对象本地缺失（tmp/market_cache/akshare/ 不存在）；
  baostock 主对象存在。→ 双源市场 reconciliation 无法本地重验 → 预期 gate = GAPS_REMAIN。

## 实施计划

1. 建工作记录（本文件）。
2. 新增 config：formula registry v1 + methodology v2（supersedes v1）。
3. 新增 docs：pit_valuation_series_contract.md。
4. 新增模块：series_contract → financial_state → ttm → temporal_join → valuation_series
   → series_validation。
5. 新增薄 CLI。
6. 新增测试（contract/financial_state/temporal_join/valuation_series/preflight）。
7. 运行测试、ruff、compileall。
8. 用 baostock 主对象 + 已提交 bundles 构建候选序列（akshare 缺失 → 记录 BLOCKED
   market reconciliation gap）。
9. 生成 reports（timeline/candidate/coverage/audit/dual_oracle/decision/manifest）。
10. 写 acceptance 与本记录结果；最终报告。

## 决策记录

### D1：TTM 状态按"当前报告期窗口"构建，restatement 折叠进下一期主状态

- 决策内容：每个报告期 (Y,P) 只在其当前窗口 `[primary_start, next_start)` 内
  发射 TTM 状态；输入（current_cum / prior_cum / prior_annual）的重述在窗口内
  触发重算，与下一期公告同日生效的重述被自然折叠进下一期主状态（不回填）。
- 采用原因：本项目所有重述（如 2022-Q1 净利在 2023-Q1 重述，生效 2023-05-04）
  都与下一报告期公告同日生效；窗口法无需为旧期发射“幽灵”重述状态，保证状态
  时间线 effective_from 严格递增，双 oracle 一致。
- 替代方案：1) 为每个 (Y,P) 枚举所有版本组合并发射全部候选状态；2) 用
  “latest effective_from <= t” 直接选。
- 未采用原因：1) 产生与下一期同 effective_from 的旧期重述状态，需额外 tie-break；
  2) 忽略了 fiscal year/period 检查（违反合同规则 7）。
- 潜在风险：若未来某重述在窗口中部生效，窗口法会发射额外状态（已实现该路径，
  测试覆盖）。

### D2：双 oracle 共用 dedup 后的统一状态时间线

- 决策内容：状态时间线先按 effective_from 去重（保留最新报告期），再分别喂给
  Python 与 DuckDB oracle；两者在相同状态列表上连接，避免 ASOF tie 歧义。
- 采用原因：dedup 是状态构造的一部分（合同要求 effective_from 严格递增），
  不是把一种 oracle 的输出作为另一种的输入。
- 替代方案：让 DuckDB 处理同 effective_from tie。
- 未采用原因：ASOF 对 tie 的实现依赖输入顺序，跨平台不可控。

### D3：正式候选用 baostock 主对象，akshare 缺失记为 BLOCKED gap

- 决策内容：baostock 主对象本地存在（1351 行，已校验），用它计算候选 PE/PB/PS；
  akshare 二级对象本地缺失 → `market_reconciliation_status =
  BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE` → 最终 gate = GAPS_REMAIN。
- 采用原因：市场数据合同要求两个对象都存在并重验；任一缺失即 fail-closed，
  不得网络刷新、不得切换 provider、不得用 committed close percentile。
- 替代方案：网络重抓 akshare；只用 baostock 并宣称 reconciliation pass。
- 未采用原因：respect fail-closed 合同；不伪造双源一致性。
- 潜在风险：formal 候选序列在 akshare 恢复前不可用于 percentile preflight。

## 实际操作

按执行顺序记录（2026-08-06）：

1. 核验 Git 状态（HEAD `8760858`，受保护项未动）；读 R4D.1b/R4D.1a/R4D.1 记录、
   contracts.py、fact_builder.py、reconciliation.py、readiness.py、share_continuity.py、
   scoring/market_observation_set.py、docs/ADR-VALUATION-002、v1 methodology、
   percentile/time contracts、market snapshot registry。
2. 核对数据：reported 127（net_profit 34 / revenue 31 / equity 25 / basic_eps 25 /
   period-end shares 12）；reconciled 38（13 Q1/Q3 期末股本 + 25 加权股本派生，
   均 = 183,020,977,818）；股本恒定。
3. 确认市场缓存：baostock 主对象（defd0b95…）存在且内容 SHA 匹配、1351 行、
   2021-01-04..2026-07-31；**akshare 二级对象（203ddfd7…）本地缺失**。
4. 建工作记录（本文件）。
5. 新增 config：formula registry v1、methodology v2（supersedes v1）。
6. 新增 docs：pit_valuation_series_contract.md。
7. 新增模块：series_contract → ttm → financial_state → temporal_join →
   valuation_series → series_validation → fixtures。
8. 新增薄 CLI：m2_stage2k1r4e_series_preflight.py（verify-contracts/formal/fixtures）。
9. 新增 5 个测试文件（42 测试）。
10. 跑正式管线（baostock 主缓存 + committed bundles）：decision=GAPS_REMAIN，
    market reconciliation=BLOCKED（akshare 缺失）。
11. 跑 fixtures（CI 合成）管线：decision=ALLOWED（合成已 reconciliation 市场）。
12. 全量离线测试套件 1475 passed + ruff + compileall + git diff --check。
13. 生成 reports（timeline/candidate/coverage/audit/dual_oracle/decision/manifest）。
14. 写 acceptance 与本记录结果。

## 数据与方法说明

- 财务 Facts：reported 127 / reconciled 38（来自 reports/ 已提交 bundles，R4D/R4D.1
  已验收）。单位：净利/收入/权益 CNY；股本 SHARE。
- 市场：events/market_data_snapshot_registry.json（两个 1351 行外部内容对象）。
  baostock 主对象 defd0b95… 本地存在；akshare 二级对象 203ddfd7… 本地缺失。
  close 不复权、A 股、CNY/share。
- 时间合同：价格 exact trade_date；财务状态 latest effective_from <= trade_date
  （backward only；禁止 forward/nearest）。
- TTM：annual = annual(Y)；Q1/H1/Q3 = annual(Y-1)+cum(Y,P)-cum(Y-1,P)。
- 股本：恒定 183,020,977,818，绑 share_continuity_proof_id。
- 数值：全程 Decimal(str(value))；禁止 Decimal(binary_float)；ROUND_HALF_EVEN，
  中间值不提前 quantize；ratio 无量纲。
- 未来数据泄漏：无——状态只选 effective_from 当日已可见版本；重述不回填。
- 窗口：3y >= 2023-07-31（交易日当日）；5y >= 2021-07-31（周六，首个真实交易日
  2021-08-02）。

## 验证

- R4E 新测试：**42 passed**。
- 全量离线测试套件：**1475 passed, 2 warnings**（1433 基线 + 42 新）。
- ruff check src/ tests/：All checks passed。
- compileall：pass。
- git diff --check：pass。
- verify-contracts：4 契约摘要全部校验通过。
- 正式 CLI：decision=GAPS_REMAIN，market_reconciliation=BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE。
- fixtures（CI）CLI：decision=ALLOWED（合成 reconciliation 市场）。
- 双 oracle：4053 行逐行一致（1351 交易日 × PE/PB/PS）。
- 交叉目录身份：committed observation ids 与独立重建逐字节一致。
- PE 抽查（2023-07-31）：close=7.92，TTM 净利=154,107,000,000（Q1-2023 用重述
  Q1-2022），EPS=0.842，PE=9.406，与手工复算一致。
- 默认 DB SHA-256 不变；stash 保留；受保护项未动。

## 结果

- 完成：methodology v2 supersede v1；formula registry；series contract doc；
  6 模块 + fixtures + 薄 CLI；候选 PE/PB/PS 序列（4053 观测）；coverage/audit/
  dual_oracle/decision/manifest；5 测试文件；acceptance。
- coverage：PE/PB/PS 各 3y=728（>=500）、5y=1211（>=900）→ READY/READY。
- 未完成 / 条件通过：正式候选序列因 akshare 二级市场缓存对象缺失而
  **BLOCKED**（market reconciliation）；gate = **PIT_VALUATION_SERIES_GAPS_REMAIN**。
- 未生成分位；未改 shadow/sensitivity；未创建生产 Metric Result；未写默认 DB；
  未采集 peer；未启动 M3。

## 遗留问题

- akshare 二级市场缓存对象本地缺失 —— 正式候选的双源 reconciliation 无法本地重验；
  需恢复该对象后重跑 formal 才能升级 gate。
- 正式管线的端到端双平台 CI 未运行（需推送 + 二级缓存）。
- 2021-01-04..2021-03-27 的 PE/PS 观测为 missing_ttm_input（缺 2019 数据），
  位于 5y 窗口之外，不影响覆盖。

## 下一步建议

- 恢复 akshare 二级市场缓存对象后重跑 formal，重验双源 reconciliation，将 gate
  升级为 `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`。
- 之后才允许进入历史估值分位预检（当前 NOT YET）。

## 最终文件变更

新增：
- `config/pit_valuation_series_formula_registry_v1.json`
- `config/value_evaluation_methodology_valuation_pit_v2.json`
- `docs/pit_valuation_series_contract.md`
- `src/ashare_research/pit_valuation/series_contract.py`
- `src/ashare_research/pit_valuation/ttm.py`
- `src/ashare_research/pit_valuation/financial_state.py`
- `src/ashare_research/pit_valuation/temporal_join.py`
- `src/ashare_research/pit_valuation/valuation_series.py`
- `src/ashare_research/pit_valuation/series_validation.py`
- `src/ashare_research/pit_valuation/fixtures.py`
- `src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py`
- `tests/test_m2_stage2k1r4e_series_contract.py`
- `tests/test_m2_stage2k1r4e_financial_state.py`
- `tests/test_m2_stage2k1r4e_temporal_join.py`
- `tests/test_m2_stage2k1r4e_valuation_series.py`
- `tests/test_m2_stage2k1r4e_series_preflight.py`
- `reports/petrochina_pit_financial_state_timeline_v1.json`
- `reports/petrochina_pit_valuation_series_candidate_v1.json`
- `reports/petrochina_pit_valuation_series_coverage_v1.json`
- `reports/petrochina_pit_valuation_series_audit_samples_v1.json`
- `reports/petrochina_pit_valuation_series_dual_oracle_validation_v1.json`
- `reports/m2_stage2k1r4e_decision.json`
- `reports/m2_stage2k1r4e_artifact_manifest.json`
- `acceptance/m2_stage2k1r4e_pit_valuation_series_preflight.md`
- `agent/record/2026-08-06_Stage2K1R4E_pit_valuation_series_preflight.md`

未修改：v1 methodology、market_observation_set.py、旧 close-percentile 工件。
受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
默认 DB、`stash@{0}`。

## 最终 Git 状态

- 分支 `feat/m2-value-assessment-mvp`；开始 HEAD `8760858`。
- 未提交（本轮产出）；未推送（遵循"未经明确要求不得推送"）。
- 受保护项未纳入提交。