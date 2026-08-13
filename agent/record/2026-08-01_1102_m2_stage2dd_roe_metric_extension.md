# 工作记录：M2 Stage 2D-D 2021-2025 ROE 透明 Metric 计算

## 基本信息

- 日期：2026-08-01
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`0f48fa0`（Stage 2D-C 收口 push 落地后的 HEAD）
- 任务来源：`/goal` 指令（M2 Stage 2D-D：2021-2025 ROE 透明 Metric 计算）
- 对应模块：价值评估（资本回报 ROE 透明指标）

## 任务目标

基于 Stage 2D-C 冻结的 ROE 方法论合同与 Stage 2D-B 的平均归母权益输入对，
透明计算 2021-2025 ROE Metric Result。新增一个 ROE 指标定义、最小三输入 Metric Engine
扩展、离线 runner 及 Definition/Engine/Integration 测试。不新增 Fact、不计算 ROA/ROIC/评分、
不改 Schema/Identity/PIT。

## 范围

- 新增 `src/ashare_research/metrics/capital_return_definitions.py`（`CapitalReturnMetricDefinitionRegistry`，仅 ROE）；
- 修改 `src/ashare_research/metrics/models.py`（MetricStatus 枚举增加 `not_comparable_negative_denominator`）；
- 修改 `src/ashare_research/metrics/engine.py`（可选 `tertiary_fact`，旧调用行为/ID 不变，ROE 公式分支）；
- 新增 `src/ashare_research/tools/official_roe_metric_extension.py`（离线 runner）；
- 新增 `tests/test_capital_return_metric_definitions.py`、`tests/test_roe_metric_engine.py`、`tests/test_official_roe_metric_extension.py`；
- 新增 `acceptance/m2_stage2dd_petrochina_roe_metric_extension.md`；
- 同步更新受 protected-blob 测试引用（models.py/engine.py blob 推进，跨阶段 surgical edit）；
- 新增本工作记录。

## 非目标

- 不新增 Fact、不计算 ROA/ROIC/评分、不访问网络/PDF/cache；
- 不改 Fact Schema / Metric Schema（DuckDB DDL 不变）/ FactIdentity / AsOfQuery / VersionChain；
- 不修改 Rule 001-004 代码、validator、service、definitions/earnings_quality_definitions/cashflow_definitions；
- 不修改 Stage 2D-B runner/evidence/restatement/report、Stage 2D-C 方法论 JSON/文档/报告正文；
- 不补录 `net_profit`，不计算 ROA；不进入 Stage 2D-E；
- 不 merge main，不建 Tag/Release。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`，HEAD `0f48fa0`，worktree clean，`stash@{0}` 未动；
- 默认 `data/research.duckdb` SHA=`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；
- Stage 2D-B 产物 blob 不变（runner `959fee57…`、报告 `52c87458…`）；
- Metric 代码基线 blob：models.py `16e36169…`、engine.py `7505cccc…`、identity.py `2073a297…`、
  repository.py `02cc128e…`、definitions.py `bb06f1e5…`、earnings_quality_definitions.py `1bd9a75e…`；
- 旧 63 Metric Result ID 集合 SHA=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
  旧 38 Result ID 集=`730484f4…`、语义=`f665e337…`；上游 132 Fact ID 集=`1e5267022b…`。

关键事实核查（已从 180-fact 2D-B foundation 实测）：
- 5 个 distinct available_at（eligible reconciled）= {2022-04-01, 2023-03-30, 2024-03-26, 2025-03-31, 2026-03-30}，
  duration 与 instant 完全对齐（同一组年报可用日）。
- net_profit_attributable_to_parent（duration, reconciled）：2021 v1=9,216,100（2022-04-01）；
  2022 v1=14,937,500（2023-03-30）/v2=14,873,800（2024-03-26）；
  2023 v1=16,114,400（2024-03-26）/v2=16,141,400（2025-03-31）；2024 v1=16,467,600；2025 v1=15,730,200。
- equity_attributable_to_parent（instant, reconciled）：2020=121,542,100；2021=126,381,500；
  2022 v1=136,957,600/v2=136,586,600；2023 v1=144,641,000/v2=145,133,300；2024=151,537,100；2025=158,606,100。
- ROE 验收值已从上述事实精确复核（万元口径）：
  2021=0.074346290551（avg 123,961,800）；2022 v1=0.113446882745/v2=0.113122466185；
  2023 v1=0.114600416175/v2=0.114591833946；2024=0.111016131033；2025=0.101438303339。全部吻合。
- 版本链自然产生：FY2022 v1@2023-03-30 -> v2@2024-03-26（NP2022+EQ2022 重列）；
  FY2023 v1@2024-03-26（opening 已用 EQ2022 v2）-> v2@2025-03-31（NP2023+EQ2023 重列）；
  FY2024 v1@2025-03-31 直接用 EQ2023 v2（无假版本）；FY2025 not_yet_reviewable。

## 实施计划

1. 创建本工作记录。
2. 新增 `capital_return_definitions.py`（ROE 定义，formula 与 2D-C JSON 完全一致）。
3. models.py：MetricStatus 增加 `not_comparable_negative_denominator`。
4. engine.py：加 `tertiary_fact=None`；3-role 缺失分支；ROE 公式分支（avg=(opening+closing)/2 内联，
   不写 Fact、不先量化）；旧 2 输入路径逐字不变。
5. 新增 runner：重建 180-fact 2D-B upstream，验证 eligible=60/PIT=47/links=39；回放 5 日重建冻结旧 63 结果；
   PIT 回放生成 ROE 7 结果/2 链/21 lineage/5 latest；输出 run-scoped metrics.duckdb + JSON。
6. 新增 Definition/Engine/Integration 测试 + 验收报告。
7. 同步 protected-blob 引用（models.py/engine.py 新 blob）。
8. 门禁：ruff、compileall、targeted/full pytest、git diff --check、污染；证明不变性。
9. 3 个提交逐个 push。

## 决策记录

### 决策 1：tertiary_fact 用 len(input_roles)>=3 守卫，旧路径逐字不变

- 内容：engine `compute` 新增 `tertiary_fact=None`；缺失分支条件 `tertiary_fact is None and len(input_roles)>=3`，
  仅 3-role 定义触发；旧 2-role 定义从不进入该分支，2 输入计算路径逐字保留。
- 原因：`/goal` 要求"旧调用默认 None、行为和 ID 必须完全不变"；用 role 数守卫保证旧指标走原路径。
- 风险：无；旧 63 结果 ID/语义将由测试证明不变。

### 决策 2：ROE formula 字符串与 2D-C JSON 完全一致

- 内容：code MetricDefinition.formula = JSON contract formula（概念名长串），engine 分支精确匹配该串。
- 原因：保持 JSON==code 一致（沿用 earnings-quality 先例），可追溯。
- 风险：串较长但仅作 dispatch key，无性能影响。

### 决策 3：models.py/engine.py blob 推进，跨阶段同步 protected-blob 引用

- 内容：2D-D 合法扩展 models.py（枚举）与 engine.py（tertiary），二者 blob 变化；
  2D-C 测试 `test_capital_return_methodology.py` 的 PROTECTED_BLOBS 中 models.py/engine.py 引用
  同步推进为新 blob（surgical edit + 注释），不修改 2D-C 方法论 JSON/文档/报告正文。
- 原因：与 2D-C 推进 roadmap blob 同一跨阶段模式；`/goal` 明确要求枚举增加与 engine 扩展。
- 风险：2D-C 测试需同步；不构成对 2D-C 方法论语义的改动（枚举增值不改旧状态语义）。

## 实际操作

### Stage 2D-D 主体（已完成，3 提交已 push：`72b8e22`/`80cbd4b`/`9501251`）

1. 确认起点：分支/HEAD `0f48fa0`/worktree clean/stash 未动；记录基线哈希。
2. 实测 2D-B foundation：确认 5 available_at 对齐、net_profit v1/v2、equity v1/v2、ROE 验收值精确复核。
3. 读取 Metric Engine/Identity/Repository/definitions/earnings_quality_definitions/2C-D runner/2D-B runner/2D-C 合同。
4. 新增 `capital_return_definitions.py`（ROE 定义）、`models.py` 枚举增值、`engine.py` 三输入扩展、runner、测试、验收报告。
5. 同步三处 protected-blob 引用；门禁全过；3 提交逐个 push。

### Stage 2D-D Engine 收口（本次，从 `9501251` 起，不新增事实/指标/方法）

6. 确认起点：HEAD `9501251`、worktree clean、`stash@{0}` 未动。
7. 定位 `engine.py` 角色绑定缺陷：`facts=[f for f in (primary,secondary,tertiary) if f is not None]` 再 `zip(input_roles, facts)`，
   中间输入缺失时末位输入继承前序角色（closing 被标记为 opening）；两角色定义收到非 None `tertiary_fact` 被静默忽略。
8. 修复 `engine.py`（blob `0ae662fb…`->`244f3605…`）：按声明角色构造 `role_bindings`，仅对非 None 绑定对生成
   `input_fact_ids`/`lineage`，角色不移位；两角色定义收到非 None `tertiary_fact` 抛 `MetricInputError`。
9. 新增 6 测试（5 单元 + 1 集成）：opening 缺失/closing 仍绑 closing、numerator 缺失/opening-closing 不移位、
   closing 缺失/两角色正确、两角色定义拒非 None tertiary、input_fact_ids↔lineage 一一对应、组合 70 Result ID 集冻结。
10. 跨阶段 protected-blob 同步：`engine.py` 新 blob 引用更新于 `test_capital_return_methodology.py`、
    `test_value_evaluation_methodology.py`；后者自身 blob变化级联更新 `test_official_earnings_quality_2025_acceptance.py`。
11. 实跑离线 runner 取真实 run_id 与不变性证据（见下"收口验证"）。
12. 更新验收报告 Section 12（不重写原 PASS 历史）与本记录；2 提交逐个 push。

## 验证

实际执行（全部通过）：

1. `ruff check src tests`：exit 0（All checks passed）。
2. `compileall -q src tests`：exit 0。
3. targeted pytest（Definition 10 + Integration 17 + 2D-C/2C-D protected-blob 等）：58 passed。
4. full pytest：789 passed（2 warnings，均为既有 `test_quality.py`，与本任务无关）。
5. `git diff --check`：exit 0。
6. 污染检查：无 .duckdb/.wal/.pdf/.png 入库；默认 DB SHA 不变；`stash@{0}` 未动。
7. ROE runner 实跑通过：combined 计数全匹配（definitions=11/results=70/computed=66/insufficient=4/links=15/lineage=143/final_latest=55/final_computed=51）；
   ROE 计数全匹配（definition=1/result_versions=7/computed=7/version_links=2/lineage=21/final_latest=5）；
   PIT latest=0/11/22/33/44/55、computed=0/7/18/29/40/51、insufficient=0/4/4/4/4/4；
   ROE 验收值与过渡值全部精确复核；2 条重述链（FY2022@2024-03-26、FY2023@2025-03-31）自然成立；
   FY2024 直接用 2023 equity v2；FY2025 not_yet_reviewable。

不变性证明：
- 旧 63 Metric Result ID 集合 SHA=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526` 不变；
  旧 63 语义哈希=`e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053` 不变；
  旧 38 Result ID 集=`730484f4…` 不变。
- 上游 180 Fact ID 集=`2bd5b2d2…` 不变；上游 132 Fact ID 集=`1e5267022b…` 不变。
- 默认 DB SHA 不变；upstream DB 只读不变；stash 未动。
- Stage 2D-B/C 产物、Rule 001-004 代码、Concept Registry、旧 10 定义 blob 不变。
- models.py（`16e36169…`->`9c979146…`）与 engine.py（`7505cccc…`->`0ae662fb…`）blob 合法推进；
  三处 protected-blob 测试引用同步更新（2D-C `test_capital_return_methodology.py`、2C-D `test_official_earnings_quality_2025_acceptance.py`、`test_value_evaluation_methodology.py`）。

## 收口验证（Stage 2D-D Engine 输入角色绑定，从 `9501251` 起）

实际执行（全部通过）：

1. `ruff check`（engine + 5 测试）：exit 0（All checks passed）。
2. `compileall -q`（engine + 2 新测试）：exit 0。
3. targeted pytest（capital_return_metric_definitions 15 + official_roe_metric_extension 18）：33 passed。
4. full pytest：795 passed（2 warnings，均为既有 `test_quality.py`，与本任务无关；789 旧 + 6 新）。
5. `git diff --check`：exit 0（仅 LF->CRLF 提示，非错误）。
6. 污染检查：无 .duckdb/.wal/.pdf/.png 入库；默认 DB SHA 不变；`stash@{0}` 未动。

实跑离线 runner（真实 run_manifest.json）：

- `run_id=roe_metric_extension_601857_SH_2021_2025_20260801_130937_462232`；
  `started_at=2026-08-01T13:09:37+08:00`、`completed_at=2026-08-01T13:09:41+08:00`、`status=passed`、
  `transaction_committed=true`、`offline=true`、`network_access=pdf_access=cache_access=false`、`downloaded=0`。
- 组合 70 Result ID 集合 SHA=`bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0`（新增冻结，证明修复后 70 ID 逐字不变）；
  combined_counts 全匹配（results=70/computed=66/insufficient=4/links=15/lineage=143/final_latest=55/final_computed=51）。
- 旧 63 ID 集=`34edbbc3…` 不变；旧 63 语义=`e988394f…` 不变；旧 38 Result ID 集=`730484f4…` 不变。
- 上游 180 Fact ID 集=`2bd5b2d2…` 不变（eligible=60/PIT=47/links=39，before==after）。
- ROE 7 版本/2 链/21 lineage/5 latest 全匹配；PIT latest=0/11/22/33/44/55、computed=0/7/18/29/40/51、insufficient=0/4/4/4/4/4。
- 默认 `data/research.duckdb` SHA=`4a71d3c7…` before==after 不变；ROA `blocked`、scoring `not_implemented`、investment_advice `not_produced`。

收口不变性证明：
- 完整 3 输入 ROE 与所有有效 2 输入指标的 result/id/available_at/语义逐字不变（输入齐全时 `present` 与旧 `facts` 同序同集）。
- 每个 input_fact_id 恰好一条 lineage、每条 lineage 恰好对应一个 input_fact_id（新单元测试覆盖完整/缺失/2 输入三场景）。
- 既有 70 Result ID（63 旧 + 7 ROE）全部不变（70 ID 集冻结哈希证明）。
- `models.py` blob 不变；`engine.py` blob 合法推进（`0ae662fb…`->`244f3605…`），三处 protected-blob 测试引用同步（跨阶段 surgical edit）。
- Stage 2D-B/C 产物、Rule 001-004 代码、Concept Registry、旧 10 定义 blob 不变；`stash@{0}` 未动。

## 结果

- ROE 透明 Metric 计算落地：2021-2025 ROE 全部 computed，7 版本/2 重述链/21 lineage/5 latest。
- Metric Engine 最小三输入扩展（tertiary_fact 可选），旧 63 结果 ID/语义逐字不变。
- 新增独立 ROE 定义 registry，不把 ROA 加入计算；ROA 仍 blocked。
- 全部门禁通过；不新增 Fact、不计算 ROA/ROIC/评分、不访问网络/PDF/cache、不改 Schema/Identity/PIT。

### 收口结果（Stage 2D-D Engine 输入角色绑定）

- Engine 输入按声明角色绑定修复落地；中间输入缺失不再导致末位输入角色移位；
  两角色定义收到非 None `tertiary_fact` 抛 `MetricInputError`。
- 接口合同加固：每个 input_fact_id 恰好一条 lineage、角色与声明槽位一一对应。
- 既有 70 Result ID（63 旧 + 7 ROE）全部不变（70 ID 集冻结哈希证明）；result/available_at/语义不变。
- 新增 6 测试（5 单元 + 1 集成）全过；全量 795 passed。
- 不新增事实、指标或方法；不进入 Stage 2D-E 或 ROA 计算。

## 遗留问题

- 无硬阻塞。
- ROA 仍 NOT YET（`net_profit` 无可信事实，待 Stage 2D-E）。
- ROIC / scoring 仍 NOT YET / STILL NOT YET。

## 下一步建议

- Stage 2D-E：2021-2025 consolidated `net_profit` 官方事实与重列（解除 ROA 分子阻塞）。
- 之后才允许 ROA 计算。

## 最终文件变更

新增（6 个文件）：
1. `src/ashare_research/metrics/capital_return_definitions.py`
2. `src/ashare_research/tools/official_roe_metric_extension.py`
3. `tests/test_capital_return_metric_definitions.py`
4. `tests/test_official_roe_metric_extension.py`
5. `acceptance/m2_stage2dd_petrochina_roe_metric_extension.md`
6. `agent/record/2026-08-01_1102_m2_stage2dd_roe_metric_extension.md`（本记录）

修改（5 处 surgical edit，2 处合法扩展 + 3 处 protected-blob 引用同步）：
1. `src/ashare_research/metrics/models.py`（MetricStatus 增加 `not_comparable_negative_denominator`）；
2. `src/ashare_research/metrics/engine.py`（可选 `tertiary_fact` + ROE 公式分支）；
3. `tests/test_capital_return_methodology.py`（models/engine blob 引用同步）；
4. `tests/test_official_earnings_quality_2025_acceptance.py`（test_value_evaluation blob 引用同步）；
5. `tests/test_value_evaluation_methodology.py`（models/engine blob 引用同步）。

### 收口文件变更（Stage 2D-D Engine role-binding，6 处）

修改（1 处核心修复 + 5 处测试/审计）：
1. `src/ashare_research/metrics/engine.py`（输入按声明角色绑定；两角色定义拒非 None tertiary；blob `0ae662fb…`->`244f3605…`）；
2. `tests/test_capital_return_metric_definitions.py`（新增 5 单元测试：角色绑定/拒绝/一一对应）；
3. `tests/test_official_roe_metric_extension.py`（新增组合 70 Result ID 集冻结测试 + 常量）；
4. `tests/test_capital_return_methodology.py`（engine.py blob 引用同步 `0ae662fb…`->`244f3605…`）；
5. `tests/test_value_evaluation_methodology.py`（engine.py blob 引用同步；自身 blob `7ef8fdb5…`->`6f4c3efd…`）；
6. `tests/test_official_earnings_quality_2025_acceptance.py`（级联：test_value_evaluation blob `7ef8fdb5…`->`6f4c3efd…`）；
7. `acceptance/m2_stage2dd_petrochina_roe_metric_extension.md`（Section 12 收口：缺陷/修复/实跑 run_id/不变性）；
8. `agent/record/2026-08-01_1102_m2_stage2dd_roe_metric_extension.md`（本记录收口）。

## 最终Git状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`0f48fa0`
- Stage 2D-D 主体三个提交（逐个 push）：
  1. `72b8e22` `feat: add average-equity ROE metric`--ROE 定义 + Engine 三输入扩展 + 枚举
  2. `80cbd4b` `test: add PetroChina PIT ROE integration`--离线 runner + Definition/Integration 测试 + protected-blob 引用同步
  3. `9501251` `docs: finalize PetroChina ROE metric acceptance`--验收报告 + 本工作记录
- Stage 2D-D Engine 收口两个提交（逐个 push，从 `9501251` 起）：
  1. `fix: preserve metric input role bindings`--engine.py 角色绑定修复 + 新增 6 测试 + 跨阶段 protected-blob 同步
  2. `docs: close Stage 2D-D engine acceptance`--验收报告 Section 12 + 本记录收口
- `stash@{0}` 未动；默认 `data/research.duckdb` SHA 不变；最终 worktree clean。
- 不 merge main，不建 Tag/Release；不进入 Stage 2D-E 或 ROA 计算。
