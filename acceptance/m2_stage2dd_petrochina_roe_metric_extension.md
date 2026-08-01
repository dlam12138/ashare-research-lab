# M2 Stage 2D-D 验收：2021-2025 ROE 透明 Metric 计算

对应分支：`feat/m2-value-assessment-mvp`
开始提交：`0f48fa0`（Stage 2D-C 收口后）
阶段性质：新增一个 ROE 指标定义与最小三输入 Metric Engine 扩展；透明计算 2021-2025 ROE。
不新增 Fact、不计算 ROA/ROIC/评分、不改 Schema/Identity/PIT。

## 1. 结论（决策矩阵）

| 指标 | 状态 |
|---|---|
| **ROE** `return_on_average_equity_attributable_to_parent` | **TRUSTED**（透明计算，7 版本/2 重述链） |
| ROE metric computation | **ALLOWED**（本阶段已落地） |
| ROA numerator fact coverage | ALLOWED（Stage 2D-C 已确认 `net_profit` 缺口） |
| ROA metric computation | NOT YET（blocked，`net_profit` 无可信事实） |
| ROIC | NOT YET |
| Scoring | STILL NOT YET |

## 2. ROE 定义与公式

- **metric_id：** `return_on_average_equity_attributable_to_parent`，version=1，unit=ratio，`score_eligible=false`。
- **公式：** `net_profit_attributable_to_parent / ((opening_equity_attributable_to_parent + closing_equity_attributable_to_parent) / 2)`
- **input_concepts：** `[net_profit_attributable_to_parent, equity_attributable_to_parent, equity_attributable_to_parent]`
- **input_roles：** `[numerator, opening, closing]`
- 新增独立 `CapitalReturnMetricDefinitionRegistry`（`capital_return_definitions.py`），不把 ROA 加入计算，不修改旧 10 个定义。
- 公式字符串与 `config/value_evaluation_methodology_capital_return_v1.json` 完全一致。

## 3. Metric Engine 三输入扩展

- `compute` 新增可选 `tertiary_fact=None`；缺失分支条件 `tertiary_fact is None and len(input_roles)>=3`，
  仅 3-role 定义触发；旧 2-role 定义从不进入该分支，2 输入计算路径逐字保留。
- 旧 63 Metric Result ID 集合与语义哈希不变（测试证明）。
- ROE 公式分支：`average=(opening+closing)/2` 内联计算（Decimal prec28/ROUND_HALF_EVEN/量化1e-12），
  不把平均余额写成 Fact、不先量化后反算。
- 平均权益=0 -> `undefined_zero_denominator`；<0 -> `not_comparable_negative_denominator`（MetricStatus 枚举增加字符串，不升级 Schema）；缺失 -> `missing_input`。
- `available_at=max(三输入 available_at)`；lineage 角色固定 `numerator/opening/closing`。

## 4. 离线 runner 与 PIT 回放

- `official_roe_metric_extension.py` 调用 Stage 2D-B foundation 重建 180-fact upstream，
  验证 eligible=60、Fact PIT=47、links=39；正式运行不访问网络/PDF/cache。
- 用 `AsOfQuery.get_latest_available()` 按五个年报可用日（2022-04-01/2023-03-30/2024-03-26/2025-03-31/2026-03-30）回放，
  重建并冻结原 10 指标 63 结果，再生成 ROE 版本。
- 2020 `comparison_only_opening_baseline` 仅作 FY2021 opening；每年 opening/closing 必须相邻 12-31、
  同 Concept/单位/CAS/consolidated 且 eligible reconciled。

## 5. 重列传播（自然产生 2 条链）

| FY | v1 available_at | v2 available_at | 原因 |
|---|---|---|---|
| 2022 | 2023-03-30 | 2024-03-26 | 2022 归母净利润（14,937,500->14,873,800）与 closing equity（136,957,600->136,586,600）重列 |
| 2023 | 2024-03-26 | 2025-03-31 | 2023 归母净利润（16,114,400->16,141,400）与 closing equity（144,641,000->145,133,300）重列；opening 已用 2022 equity v2 |

- FY2024 首次生成直接使用 2023 equity v2（无假版本）。
- FY2025 `revision_review_status=not_yet_reviewable`；其余状态从 committed review evidence 推导。

## 6. 验收值（从 Fact 计算，非硬编码）

| FY | latest ROE | 过渡 v1 |
|---|---|---|
| 2021 | 0.074346290551 | - |
| 2022 | 0.113122466185 | 0.113446882745 |
| 2023 | 0.114591833946 | 0.114600416175 |
| 2024 | 0.111016131033 | - |
| 2025 | 0.101438303339 | - |

## 7. 计数

**ROE 自身：** definition=1，result_versions=7，computed=7，version_links=2，lineage=21，final_latest=5。

**组合（旧 10 + ROE）：** definitions=11，results=70，computed=66，insufficient=4，links=15，lineage=143，final_latest=55，final_computed=51。

**Metric PIT 回放：** latest=0/11/22/33/44/55；computed=0/7/18/29/40/51；insufficient=0/4/4/4/4/4。

## 8. 输出产物

run-scoped `metrics.duckdb` 及 `metric_definitions.json`/`metric_result_versions.json`/
`latest_metric_snapshot.json`/`metric_pit_snapshots.json`/`roe_metric_transitions.json`/
`metric_lineage.json`/`run_manifest.json`/`acceptance_summary.md`。upstream 与默认 DB 只读。

## 9. 不变性证明

- 旧 63 Metric Result ID 集合 SHA=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526` 不变；
  旧 63 语义哈希=`e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053` 不变；
  旧 38 Result ID 集=`730484f4…` 不变。
- 上游 180 Fact ID 集合 SHA=`2bd5b2d20ec7992a07b66238fff86ab0fb91f881c5f7cd7f0b5d68b5bde6946c` 不变；
  上游 132 Fact ID 集=`1e5267022b…` 不变。
- 默认 `data/research.duckdb` SHA=`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` 不变；
  upstream DB SHA 不变（只读）；`stash@{0}` 未动。
- Stage 2D-B runner/report/evidence/restatement、Stage 2D-C 方法论 JSON/文档、Rule 001-004 代码
  （engine/validator/version_chain/as_of/identity/service）、Concept Registry、旧 10 定义
  （definitions/earnings_quality_definitions/cashflow_definitions）Git blob 全部不变。
- `models.py`/`engine.py` blob 合法推进（枚举增值 + tertiary_fact 扩展，旧 2 输入行为/ID 不变），
  三处 protected-blob 测试引用同步更新（跨阶段 surgical edit）。

## 10. 工程门禁

- `ruff check src tests`：exit 0；
- `compileall -q src tests`：exit 0；
- targeted + full pytest：全部通过；
- `git diff --check`：exit 0；
- 污染检查：无 DB/PDF/PNG 入库。

## 11. 最终状态

- 3 个提交逐个 push；worktree clean，local/origin/remote 一致；
- 不 merge main，不建 Tag/Release；不进入 Stage 2D-E 或 ROA 计算。

## 12. Stage 2D-D Engine 收口：输入角色绑定加固

本节为 Stage 2D-D 收口，**不新增事实、指标或方法**，仅修复 Engine 输入角色绑定缺陷并审计收口。
原 Section 1-11 的 PASS 历史不重写；下列说明结果不变、接口合同加固。

### 12.1 缺陷

`MetricEngine.compute` 原实现先以列表推导过滤 `None` 再与 `input_roles` zip：

```python
facts = [f for f in (primary, secondary, tertiary) if f is not None]
input_fact_ids = tuple(str(f["fact_id"]) for f in facts)
lineage = [_lineage(role, fact) for role, fact in zip(input_roles, facts)]
```

当中间输入缺失（如 `secondary`(opening) 为 `None`）而后输入存在（`tertiary`(closing) 非 `None`）时，
`facts` 收缩为 `[primary, tertiary]`，`zip` 使 `tertiary` 继承 `input_roles[1]`(opening) 角色——
**closing 被错误标记为 opening**，角色发生移位。既有 70 结果因输入齐全或仅末位缺失而未触发，
故结果 ID/语义不变，但角色绑定合同不成立（latent 缺陷）。两角色定义收到非 `None` 的 `tertiary_fact`
时被静默忽略，亦违反合同。

### 12.2 修复

`engine.py`（blob `0ae662fb…` -> `244f3605…`）改为按声明角色绑定：

- 构造 `role_bindings = [(input_roles[0], primary), (input_roles[1], secondary)]`；
  `len(input_roles) >= 3` 时追加 `(input_roles[2], tertiary)`。
- 仅对非 `None` 的绑定对生成 `input_fact_ids` 与 `lineage`，**原始角色不移位**：
  `present = [(role, fact) for role, fact in role_bindings if fact is not None]`，
  `lineage = [_lineage(role, fact) for role, fact in present]`。
- 两角色定义收到非 `None` `tertiary_fact` 时抛 `MetricInputError`（不静默忽略）。
- `available_at` 仍取非 `None` 绑定输入的 `max(available_at)`；缺全部输入时回退 `as_of_date`。
- 完整 3 输入 ROE 与所有有效 2 输入指标的 result / id / available_at / 语义逐字不变
  （因输入齐全时 `present` 与旧 `facts` 同序同集）。

### 12.3 不变性证明（实跑 run_manifest）

实跑离线 runner（`run_id=roe_metric_extension_601857_SH_2021_2025_20260801_130937_462232`，
`started_at=2026-08-01T13:09:37+08:00`、`completed_at=2026-08-01T13:09:41+08:00`、`status=passed`、
`transaction_committed=true`、`offline=true`、`network_access=pdf_access=cache_access=false`、`downloaded=0`）：

- 组合 70 Result ID 集合 SHA=`bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0`（新增冻结）；
  combined_counts 全匹配（results=70/computed=66/insufficient=4/links=15/lineage=143/final_latest=55/final_computed=51）。
- 旧 63 ID 集=`34edbbc3…` 不变；旧 63 语义=`e988394f…` 不变；旧 38 Result ID 集=`730484f4…` 不变。
- 上游 180 Fact ID 集=`2bd5b2d2…` 不变（eligible=60/PIT=47/links=39，before==after）。
- ROE 7 版本/2 链/21 lineage/5 latest 全匹配；2 条重述链（FY2022@2024-03-26、FY2023@2025-03-31）不变。
- 默认 `data/research.duckdb` SHA=`4a71d3c7…` 不变；ROA `blocked`、scoring `not_implemented`、investment_advice `not_produced`。
- `models.py` blob 不变；`engine.py` blob 合法推进（`0ae662fb…`->`244f3605…`），三处 protected-blob 测试引用同步（跨阶段 surgical edit）。
- 污染检查：无 DB/PDF/PNG 入库；`stash@{0}` 未动。

### 12.4 新增测试

`test_capital_return_metric_definitions.py`：opening 缺失/closing 仍绑 closing、numerator 缺失/opening-closing 不移位、
closing 缺失/两角色正确、两角色定义拒非 None tertiary、input_fact_ids↔lineage 一一对应（完整/缺失/2 输入三场景）。
`test_official_roe_metric_extension.py`：组合 70 Result ID 集冻结（修复后逐字不变）。

### 12.5 提交

1. `fix: preserve metric input role bindings`——engine.py 角色绑定修复 + 新增 6 测试 + 跨阶段 protected-blob 同步。
2. `docs: close Stage 2D-D engine acceptance`——本节验收收口 + 工作记录收口。

不 merge main，不建 Tag/Release；不进入 Stage 2D-E 或 ROA 计算。
