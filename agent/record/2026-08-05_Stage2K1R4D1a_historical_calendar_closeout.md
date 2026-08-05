# 工作记录：M2 Stage 2K.1R4D.1a — Historical Calendar and Remote Evidence Closeout

Status: `in_progress`

## 基本信息

- 日期：2026-08-05
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`9057494`（R4D.1 closeout）
- 任务来源：用户指令（R4D.1a——历史日历与远端证据收口）
- 对应模块：价值评估（PIT 估值分母事实的日历/PIT 时间契约）

## 任务目标

很小范围的收口，不重做 R4D.1，不开始 PE/PB/PS 序列：

1. 补齐交易日历：`calendar_start <= 2020-01-01`，`calendar_end >= evidence_cutoff (2026-08-02)`。
2. 重新计算所有 2020 facts 的 `effective_from`、`effective_from_derivation`、calendar object ID、calendar digest。
3. 禁止 fallback：公告日期早于日历首日 → 使用日历第一个交易日。正确行为：日历覆盖不足 → `explicit calendar_coverage_gap` → fail-closed。
4. 至少测试：2020 Q1 公告→真实下一交易日；周末公告→下一交易日；节假日公告跨休市；日历首日晚于公告→失败；不允许统一回填 2021-01-04；2020 facts 的 available_at 不变、仅修正 effective_from；Fact ID 迁移由当前身份合同决定并生成 old→new 报告；3y/5y readiness 独立重算。
5. 更新 gap 定义：当前不能写 0 gaps。日历修复前至少应有 `historical_market_calendar_coverage_gap`。分类：`economic_fact_gaps = 0`，`pit_time_contract_gaps = 1`。
6. 修复完成后推送本地提交（4d28d11、9057494、calendar fix、acceptance/CI evidence），并运行最终双平台 CI。

边界：日频 PE/PB/PS preflight NOT YET；估值分位 NOT ALLOWED；估值 shadow NOT ALLOWED；同行采集 NOT ALLOWED；M3 NOT STARTED。最终 gate 在日历修复推送 + reviewer 实物复核后才升为 READY。

## 范围

- market cache 重建（601857 baostock 2020-01-01..2026-08-10）。
- `fact_builder.py`：`load_market_calendar` 前缀更新；`next_trading_day` fail-closed（CalendarCoverageGapError）。
- `contracts.py`：新增 `calendar_coverage_gap` 状态 + gap 分类（economic/pit_time）。
- `readiness.py`：gap 分类输出 `economic_fact_gaps`/`pit_time_contract_gaps`；PIT time gap fail-closed。
- CLI：catch CalendarCoverageGapError → 单元标 calendar_coverage_gap。
- 2020 facts 重算（effective_from、calendar object/digest）。
- 迁移报告（日历修复不迁 Fact ID）。
- 测试 + acceptance + work record + 推送。

## 非目标

- 不重做 R4D.1 任何已接受工程。
- 不生成日频 PE/PB/PS、TTM、分位、评分。
- 不采集 peer。
- 不启动 M3。
- 不写默认 DuckDB。
- 不合并 main、不创建 PR/Tag/Release、不强制推送、不重写已有提交、不删除 stash。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `9057494`；本地 == origin（R4D.1 未推送）。
- 受保护项：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、`stash@{0}`、默认 DB。
- R4D.1 决策 `PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT`；reported 127、reconciled 38、0 gaps。
- 市场日历 `tmp/market_cache/baostock/defd0b9507c0d87c*.parquet` 覆盖 2021-01-04..2026-07-31（1351 交易日本）。
- 已验证：baostock 可登录并获取 601857 2020 日线（2020-01-02..2020-12-31，243 行）。
- 默认 DB `data/research.duckdb` SHA-256 = `4a71d3c7…`（基线）。

## 实施计划

1. 建工作记录（本文件）。
2. 重建市场日历（baostock 601857，2020-01-01..2026-08-10），写入 tmp/market_cache/baostock/，更新 market registry。
3. `next_trading_day` fail-closed（CalendarCoverageGapError）；`load_market_calendar` 前缀更新。
4. gap 分类：`calendar_coverage_gap` 状态 + `economic_fact_gaps`/`pit_time_contract_gaps`。
5. CLI catch gap → 单元标记；readiness fail-closed。
6. 重算 2020 facts；重跑管线。
7. 测试（8 项）+ 全量 pytest + ruff + compileall。
8. 迁移报告（0 变更）+ acceptance + manifest。
9. 本地验证序列；提交（calendar fix + evidence）；推送 4 个 commit；CI 记录。

## 实际操作

按执行顺序记录（2026-08-05）：

1. 核验 Git 状态（HEAD `9057494`，受保护项未动）；读 R4D.1a 指令与 R4D.1 源码
   （contracts、fact_builder、readiness、CLI、identity）。
2. 重建市场日历：用 baostock 单次查询 601857 日线 2020-01-01..2026-08-10
   （`adjustflag='3'` 不复权），写入
   `tmp/market_cache/baostock/77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d.parquet`，
   1597 行完整交易日（2020-01-02..2026-08-05），覆盖证据截止 2026-08-02。
3. `contracts.py`：新增 `CalendarCoverageGapError`、`CALENDAR_COVERAGE_START=2020-01-01`、
   `CALENDAR_COVERAGE_END=2026-08-02`、`GAP_CLASS_ECONOMIC_FACT`/`GAP_CLASS_PIT_TIME_CONTRACT`、
   `"calendar_coverage_gap"` 状态。
4. `fact_builder.load_market_calendar`：前缀更新为 `77021dce…`；`required_start` 语义
   改为“必须能解析的最早公告日”（CLI 传入最早公告 2020-04-30），`required_end`=证据截止；
   首/末交易日不覆盖边界即抛 `CalendarCoverageGapError`（fail-closed）。
5. `fact_builder.next_trading_day`：fail-closed——日历首日晚于公告日、或空日历、或无后续
   交易日即抛 `CalendarCoverageGapError`，永不回填首个可用交易日。
6. `fact_builder._pit_time_from_calendar`：新增 helper，捕获 gap 返回
   `("", "calendar_coverage_gap", {})`；`build_reported_fact`/`build_share_capital_fact`
   接入，并给每个 fact 写入 `effective_from_derivation`、`calendar_object_id`、
   `calendar_sha256`（非身份字段，fact_id 不变）。
7. `readiness.py`：gap 分类（`calendar_coverage_gap`→`pit_time_contract`，其余→`economic_fact`）；
   `build_readiness` 输出 `economic_fact_gaps`/`pit_time_contract_gaps`；
   `decide_from_readiness` 对 `pit_time_contract_gaps>0` fail-closed（layers 不 trusted）。
8. CLI `_cmd_formal`：传入最早公告日作为 `required_start`；`_build_derived_fact` 捕获
   `CalendarCoverageGapError` 写 `pit_time_contract_gap`；带 gap 的 fact 移出 reported bundle，
   其单元标记 `calendar_coverage_gap`。
9. 新增 `tests/test_m2_stage2k1r4d1a_historical_calendar.py`（12 测试，覆盖指令 8 项要求）。
10. 更新既有 `test_m2_stage2k1r4d_restatement_and_readiness.py` 的合成日历 fixture
    （加入公告前交易日，符合 fail-closed 契约）。
11. 重跑正式管线（真实缓存 + 新日历）：
    gate=READY，reported=127，reconciled=38，gaps=0，binding_ok=true；
    2020 facts `effective_from` 解析为真实下一交易日（2020-04-30→05-06 等），无 2021-01-04 回填。
12. 迁移报告：127 条 / changed=0（日历非身份字段，fact_id 不变）。
13. 更新 market registry（`tmp/market_registry_baostock_only.json`）指向扩展日历对象。
14. ruff / compileall 通过；全量 pytest 1421 passed（后台完成）。

## 验证

- ruff check src/ tests/：All checks passed。
- compileall：pass。
- 全量离线测试套件：**1421 passed, 2 warnings**（1409 R4D.1 基线 + 12 新 R4D.1a 测试）。
- 新测试 12 passed；R4D.1a 相关既有测试（fact_identity / context_restatement /
  restatement_and_readiness）61 passed。
- 正式管线：gate=READY，reported=127，reconciled=38，gaps=0，binding_ok=true；
  2020 facts `effective_from` 解析为真实下一交易日（2020-04-30→05-06、2020-08-28→08-31、
  2020-10-30→11-02、2021-03-26→03-29），无 2021-01-04 回填；available_at 不变。
- 迁移报告：127 条 / changed=0（日历非身份字段，fact_id 不变）。
- git diff --check：pass。
- 默认 DB SHA-256 不变（4a71d3c7…）；stash 保留；受保护项未动。

## 结果

- R4D.1a 收口完成：日历扩展至 2020-01-02..2026-08-05，覆盖证据截止 2026-08-02。
- 2020 facts 的 effective_from / effective_from_derivation / calendar object ID /
  calendar digest 全部重算并写入 fact。
- 禁止 fallback 落地：`CalendarCoverageGapError` fail-closed，永不回填首个/末个交易日。
- gap 定义更新：修复后 `economic_fact_gaps=0`、`pit_time_contract_gaps=0`；修复前
  至少应有 `historical_market_calendar_coverage_gap`（分类 `pit_time_contract`）。
- 迁移报告 changed=0；3y/5y readiness 独立重算（READY）。
- 决策：**PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT**（日历修复推送 + 实物复核后）。

## 遗留问题

- 日历为 baostock 单源（601857 日线）；扩展历史窗口完整性受数据源覆盖约束。
- A+H 总股本假设与 SSE 归档完整性仍为 constancy 派生的 residual risks（继承 R4D.1）。
- 日频 PE/PB/PS preflight、估值分位、估值 shadow、同行采集、M3 均未开始（边界保持）。

## 下一步建议

- 推送本地提交（9057494、calendar fix、acceptance/CI evidence）并运行最终双平台 CI；
  推送 + reviewer 实物复核后 gate 升为 READY。

## 最终文件变更

新增：
- `tests/test_m2_stage2k1r4d1a_historical_calendar.py`
- `agent/record/2026-08-05_Stage2K1R4D1a_historical_calendar_closeout.md`

修改：
- `src/ashare_research/pit_valuation/fact_builder.py`（load_market_calendar 前缀与
  required_start 语义、next_trading_day fail-closed、_pit_time_from_calendar、
  effective_from_derivation/calendar object/digest 写入 fact）
- `src/ashare_research/pit_valuation/readiness.py`（gap 分类、economic/pit_time 计数、
  pit_time fail-closed）
- `src/ashare_research/pit_valuation/contracts.py`（CalendarCoverageGapError、
  CALENDAR_COVERAGE_*、GAP_CLASS_*、calendar_coverage_gap 状态）
- `src/ashare_research/tools/m2_stage2k1r4d_acquire_denominators.py`（最早公告日、
  derived fact pit gap、gap 单元标记）
- `tests/test_m2_stage2k1r4d_restatement_and_readiness.py`（合成日历 fixture 对齐
  fail-closed 契约）
- `reports/petrochina_pit_denominator_*.json`（reported/reconciled/readiness/
  migration 等 9 份覆写）
- `tmp/market_registry_baostock_only.json`（指向扩展日历对象）

受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
默认 DB、`stash@{0}`。

## 最终 Git 状态

- 分支 `feat/m2-value-assessment-mvp`；推送 4 个提交：`4d28d11`（R4D.1 closeout）、
  `9057494`（R4D.1 工作记录完成）、`4b34fea`（calendar fix）、以及本 acceptance/CI
  evidence 提交。
- 推送：`a399a17..4b34fea` 已推送 origin；第 4 个 evidence 提交随后推送。
- 最终双平台 CI（`Stage 2G reproducibility`，run 30999204443，headSha `4b34fea`）：**success**，
  windows + ubuntu clean-clone 与 identity-compare 全部通过。
- 受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
  默认 DB、`stash@{0}`。