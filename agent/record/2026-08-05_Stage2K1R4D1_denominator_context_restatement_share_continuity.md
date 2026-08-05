# 工作记录：M2 Stage 2K.1R4D.1 — Denominator Fact Context, Restatement Metadata and Share-Continuity Closeout

Status: `in_progress`

## 基本信息

- 日期：2026-08-05
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`a399a17`（R4D CI 证据 commit）
- 任务来源：用户治理复核（R4D 官方采集与命名捕获工程可接受，但 Fact/PIT 层收口条件未满足）+ R4D.1 指令
- 对应模块：价值评估（PIT 估值分母事实收口）

## 任务目标

修复用户复核提出的 10 项 R4D 缺陷，才允许进入估值序列预检：

1. 为 instant Fact 建立能区分 Q1/H1/Q3/年度的 Context v2，输出 old→new Fact ID 迁移报告。
2. 重述 Fact 必须从后续 filing 的比较列重新构造全部来源字段，不能浅复制原始来源元数据。
3. 按重述公告日期重新计算 `effective_from`。
4. 将 PDF 内容对象摘要与 excerpt 摘要分离（source_object_sha256 / excerpt_hash）。
5. 给每个 acquired cell 写入真实 `fact_id`，给每个缺口写入真实 `gap_id`，增加双向一致性校验。
6. 建立 2020 Q1—2026 Q1 的官方股本变动/公司行动 bounded-search register。
7. 只有在精确股本边界相同、期间内无股本变化且官方搜索完整时，才允许派生 Q1/Q3 期末股本。
8. 加权平均股本只有在整个 duration 内股数恒定且会计口径可证明一致时才能派生；否则继续保留明确缺口。
9. 重新计算 PE、PB、PS readiness。
10. 仍不生成 TTM、每股指标、日频估值、历史分位或评分结果。

最终 gate 仍为三态：READY / GAPS_REMAIN / NOT_TRUSTED。

## 范围

- 修改 `src/ashare_research/pit_valuation/`（fact_builder、reconciliation、readiness、contracts、新增 share_continuity 模块）。
- 修改 CLI `m2_stage2k1r4d_acquire_denominators.py`。
- 新增 `config/pit_valuation_share_continuity_register_v1.json`。
- 重写 report artifacts（reported/reconciled bundles、coverage、gap ledger、readiness、version lineage、新增 fact_id_migration、coverage_binding_validation、share_continuity）。
- 更新/新增测试。
- 更新 acceptance 与工作记录。

## 非目标

- 不生成日频 PE/PB/PS、TTM/MRQ/单季 Metric Result、历史估值分位。
- 不改变估值评分权重/阈值/影子。
- 不采集 peer。
- 不启动 M3。
- 不写默认 DuckDB。
- 不合并 main、不创建 PR/Tag/Release、不强制推送、不重写已有提交、不删除 stash。
- 不扩大 data 采集范围到非官方源。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `a399a17`；本地 == origin。
- 受保护项：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、`stash@{0}`、默认 DB。
- R4D 现状：decision `PIT_DENOMINATOR_FACT_GAPS_REMAIN`；reported 127 facts；weighted-average 25 期歧义缺口；PB/PS 3y/5y READY（但依赖受限 grid）；PE BLOCKED。
- 用户复核把 RESTATED 相关层、instant Context、Coverage Fact/Gap 双向映射标为 NOT TRUSTED/PARTIAL；PB/PS readiness 降为 PARTIAL。
- 默认 DB `data/research.duckdb` SHA-256 = `4a71d3c7…`（基线）。

## 数据现状（已验证）

- 12 个精确股本事实（2020 H1..2025 AR，从 AR/H1 股息基数声明提取）全部 = `183,020,977,818`。
- SSE 官方公告查询归档 `tmp/sse_archive_utf8.json`（553 条，2020-01-01..2026-08-02）扫描全部公司行动类标题：仅有现金分红类（权益分派实施/利润分配方案/独立意见），**无任何股本变动类**（无转增/送股/增发/配股/回购注销/股权激励/可转债/增资）。
- 结论：股本在 2020 Q1—2026 Q1 恒定 = `183,020,977,818`（强证据：12 份官方股息基数 + 公司行动 bounded search）。
- 现 instant Context 缺陷确认：`601857.SH|2020|instant|consolidated` 同时绑定 4 个 period_end（03-31/06-30/09-30/12-31）。

## 实施计划

1. 冻结股本连续性 register（config + 生成脚本）。
2. Context v2：instant context_id 含 period_end；duration 不变；输出 fact_id 迁移报告。
3. source_object_sha256 / excerpt_hash 分离（thread object sha 进 fact 构造）。
4. 重述 Fact 全源重建 + effective_from 重算。
5. Coverage 双向绑定（真实 fact_id/gap_id + 一致性校验）。
6. Q1/Q3 期末股本与加权平均股本 constancy 派生（register trusted 时）。
7. 重算 PB/PS/PE readiness + gate。
8. 测试更新 + 全量 pytest + ruff + compileall。
9. CI 更新（合成 fixture）+ acceptance + manifest。
10. 本地验证序列；提交；最终报告。

## 实际操作

按执行顺序记录（2026-08-05）：

1. 核验 Git 状态（HEAD `a399a17`，受保护项未动）；读 R4D 源码（fact_builder、
   reconciliation、readiness、contracts、CLI、facts/contexts、facts/identity）。
2. 确认 R4D 缺陷：12 个精确股本事实全部 = 183,020,977,818；instant Context
   `601857.SH|2020|instant|consolidated` 同时绑定 4 个 period_end。
3. 扫描 SSE 归档 `tmp/sse_archive_utf8.json`（553 条，2020-01-01..2026-08-02）：
   全部公司行动类公告均为现金分红（权益分派/利润分配/独立意见），无任何股本
   变动类（无转增/送股/增发/配股/回购注销/股权激励/可转债/增资）。归档中文标题
   码点正确（终端显示乱码仅为控制台编码问题）。
4. 建立股本连续性 register：`config/pit_valuation_share_continuity_register_v1.json`
   （trust=trusted，constant=True，constant_value=183020977818，24 个候选公告，
   0 个股本变动行动）。
5. `fact_builder.py`：新增 `build_context_v2`（instant context_id 含 period_end，
   duration 不变）；`build_reported_fact`/`build_share_capital_fact` 改用 v2 并新增
   `source_object_sha256`+`excerpt_hash` 分离（`source_hash`=官方 PDF 内容对象摘要）；
   新增 `migrate_fact_to_context_v2` + `build_fact_id_migration_report`。
6. `reconciliation.py`：`detect_restatements` 增 `market_calendar` +
   `object_sha_by_evidence` 参数；重述 Fact 经 `_build_restated_from_comparative`
   全源重建（source_url/label/page/hash/object/excerpt/filing_date/effective_from
   均从后续 filing 重算）。
7. 新增 `share_continuity.py`：`classify_share_change`、
   `build_share_continuity_register`、`constancy_derivation_available`、
   `derive_period_end_shares_from_constancy`、`derive_weighted_average_shares_from_constancy`。
8. `contracts.py`：新增 `SHARE_CONTINUITY_REGISTER_PATH`、`load_share_continuity_register`、
   `validate_share_continuity_register`，并入 `validate_all_contracts`（第 6 个契约）。
9. `readiness.py`：Q1/Q3 期末股本单元入 grid（derived-eligible，expected_direct=
   False）；`apply_extraction_statuses` 透传 `gap_ids`；`gap_ledger_from_grid` 回写
   `cell['gap_ids']`；新增 `validate_coverage_fact_gap_binding`。
10. CLI `_cmd_formal` 重写：thread object_sha；constancy 派生 Q1/Q3 期末股本与
    加权股本（进 reconciled bundle）；重述事实映射到被取代原始事实所在 cell；
    写 fact_id_migration、coverage_binding_validation、share_continuity 报告。
11. 运行正式管线（真实缓存 + 验证日历）：
    gate=READY，reported=127，reconciled=38（13 Q1/Q3 派生 + 25 加权派生），
    gaps=0，constancy=true，binding_ok=true。
12. 修复 `readiness.build_expected_grid` 中 `role` 未定义即使用的错误。
13. 更新 `test_m2_stage2k1r4d_restatement_and_readiness.py`（Q1 期末股本入 grid 断言）；
    新增 `tests/test_m2_stage2k1r4d1_context_restatement_share_continuity.py`（15 测试）。
14. 修复 ruff（E501/SIM103/W292）；`verify-contracts` 返回 6 契约摘要。
15. 将 R4D.1 输出报告拷入 `reports/`（覆写 v1 同名报告 + 新增 migration/binding/
    share_continuity）。
16. 撰写 R4D.1 验收文档。
17. 完整离线测试套件运行中（后台）。

## 验证

- 完整离线测试套件：**1409 passed, 2 warnings**（含 82 个 R4D/R4D.1 测试）。
- ruff check src/ tests/：All checks passed。
- compileall：pass。
- verify-contracts：6 契约摘要全部校验通过。
- git diff --check：pass。
- 正式管线：READY，binding ok=true，0 gaps。
- 默认 DB SHA-256 不变（4a71d3c7…）；stash 保留；受保护项未动。

## 结果

- Decision：**PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT**。
- 缓解用户复核全部 10 项：
  - instant Context v2（period_end 入 context_id），迁移报告 127 条/37 变更；
  - 重述全源重建 + effective_from 重算（如 2023-04-29 公告 → 2023-05-04 生效）；
  - source_object_sha256 / excerpt_hash 分离；
  - 150 单元全部真实 fact_id、0 gap、binding ok；
  - 股本 continuity register trusted + constancy 派生 13 Q1/Q3 期末股本 + 25 加权股本；
  - PE/PB/PS 全部 3y/5y READY。
- 未生成 TTM/每股/日频估值/历史分位/评分；未写默认 DB；未采集 peer；未启动 M3。

## 遗留问题

- 市场日历自 2021-01-04 起；2020 年事实 effective_from 解析为首个可用交易日
  （2021-01-04），为既有日历覆盖限制，非回归。
- constancy 派生受 SSE 归档完整性 + A+H 总股本假设约束（residual risks 已记录）。
- CI 证据待推送后补记。

## 下一步建议

- 进入 PE/PB/PS 估值序列预检须单独授权；本阶段只完成分母事实收口。

## 最终文件变更

新增：
- `src/ashare_research/pit_valuation/share_continuity.py`
- `config/pit_valuation_share_continuity_register_v1.json`
- `reports/petrochina_pit_denominator_fact_id_migration_v1.json`
- `reports/petrochina_pit_denominator_coverage_binding_validation_v1.json`
- `reports/petrochina_pit_denominator_share_continuity_v1.json`
- `acceptance/m2_stage2k1r4d1_denominator_fact_context_restatement_share_continuity.md`
- `agent/record/2026-08-05_Stage2K1R4D1_denominator_context_restatement_share_continuity.md`
- `tests/test_m2_stage2k1r4d1_context_restatement_share_continuity.py`

修改：
- `src/ashare_research/pit_valuation/fact_builder.py`（Context v2、object_sha 分离、迁移报告）
- `src/ashare_research/pit_valuation/reconciliation.py`（重述全源重建）
- `src/ashare_research/pit_valuation/readiness.py`（Q1/Q3 股本入 grid、binding 校验）
- `src/ashare_research/pit_valuation/contracts.py`（share continuity 契约）
- `src/ashare_research/tools/m2_stage2k1r4d_acquire_denominators.py`（formal 重写）
- `tests/test_m2_stage2k1r4d_restatement_and_readiness.py`（Q1 股本 grid 断言）
- `reports/petrochina_pit_denominator_reported_fact_bundle_v1.json` 等 6 份报告（覆写）

受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
默认 DB、`stash@{0}`。

## 最终 Git 状态

（待提交）