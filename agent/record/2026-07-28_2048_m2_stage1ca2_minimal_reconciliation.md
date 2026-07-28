# 工作记录：M2 Stage 1C-A.2 - 修正来源语义并实现最小双源 Reconciliation

## 基本信息

- 日期：2026-07-28 20:48
- Agent：Claude Code
- 当前分支：feat/m2-value-assessment-mvp
- 开始提交：95b25d4（`95b25d42246e3d4a1c37e4b87af6eb62df1190f0`）
- 任务来源：Stage 1C-A.2 指令（修正来源语义 + 最小双源 Reconciliation Engine）
- 对应模块：价值评估（数据层治理 / 工程治理）

## 任务目标

1. 修正中国石油 AKShare 数据被错误标记为官方来源的问题（`official_sources/petrochina.py` 标 `company_official`/`petrochina_official::`）；
2. 实现面向中国石油三个关键财务概念的最小双官方来源核验闭环：company_official + exchange_official -> comparison -> reconciled canonical fact。

本轮结束得到一个可离线验证的最小 Reconciliation Engine，不下载、不解析、不录入真实报告。

## 北极星对齐

直接服务于：价值评估 -> 关键财务事实可追溯 -> 手工核验示范公司 -> 缺失和冲突不被掩盖。
不得滑向：通用财务核验平台 / 全市场多源融合 / 自动裁决 / 模糊匹配 / 评分或荐股。

只支持三个 Concept（以 facts/concepts.py 已注册名称为准）：
- `revenue`（营业收入）
- `net_profit_attributable_to_parent`（归属于母公司股东的净利润，指令称 attributable_net_profit）
- `operating_cash_flow`（经营活动现金流净额）

## 范围

允许修改/新增：

- `src/ashare_research/facts/models.py`（SourceTier 新增 `reconciled_derived`）
- 删除 `src/ashare_research/official_sources/petrochina.py`
- 新增 `src/ashare_research/reconciliation/__init__.py`、`models.py`、`engine.py`、`service.py`
- `tests/test_official_provider_identity.py`（移除已删 provider 的 Layer 1a 测试）
- `tests/test_fact_reconciliation.py`（修正 source_tier 语义）
- 新增 `tests/test_minimal_official_reconciliation.py`

## 非目标

- 不修复已失效的 AKShare API（仅记录 candidate source runtime unavailable）；
- 不添加新数据源 / 下载报告 / 解析 PDF / 录入真实数值；
- 不增加超过三个 Concept / 模糊匹配 / 容差配置 / 人工裁决 UI / 全市场支持；
- 不修改估值或评分；
- 不动 stash@{0}；不合并 main；不创建 Tag/Release；
- 不重构整个 FactService；
- 不删除 official_sources/base.py、registry.py（未明确授权，标记为后续 dead-code 清理）。

## 开始前状态

- 分支 feat/m2-value-assessment-mvp，HEAD=`95b25d4`，与远程一致；
- 工作区干净，`stash@{0}` 保持不动；
- Stage 1C-A 第一项已推送（`1aed47b` 实现 + `95b25d4` 记录）。

## 调研结论

### 来源语义问题根因

- `official_sources/petrochina.py`（PetroChinaProvider）使用 AKShare 取数，但生成 `source_tier="company_official"`、`source_id="petrochina_official::..."`、`provider_name="petrochina"`；
- 与 `fact_sources/candidates/akshare_financial.py`（AKShareFinancialCandidateProvider，`candidate_aggregator`）功能完全重复（相同 AKShare API、相同报表类型、都有 get_dividends）；
- PetroChinaProvider 未接入 Service/CLI/config（config 引用的是 PetroChinaOfficialFilingProvider）；
- 适用 Preferred path：删除 petrochina.py，无独特能力需合并。

### SourceTier 现状

- 现有：candidate_aggregator、company_official、exchange_official；
- 需新增：reconciled_derived。

### 现有 reconciliation 测试的 bug

- `tests/test_fact_reconciliation.py` 中 company 与 exchange 事实都用 `source_tier="company_official"`；
- reconciled 事实用 `source_tier="company_official"`（应为 reconciled_derived）。

### Concept canonical 名称

- 指令 `attributable_net_profit` -> concepts.py 注册名 `net_profit_attributable_to_parent`。

### UnitRegistry

- 用 float 转换；reconciliation 用 `Decimal(str(...))` 精确比较，避免二进制 float 回写。

## 实施计划

1. SourceTier 新增 `reconciled_derived`（models.py）。
2. 删除 `official_sources/petrochina.py`。
3. 更新 `tests/test_official_provider_identity.py`：移除 Layer 1a（PetroChinaProvider 已删）。
4. 新增 reconciliation/models.py（ReconciliationStatus、ReconciliationResult）。
5. 新增 reconciliation/engine.py（纯 Engine：reconcile_pair，硬门禁 + Decimal 比较 + 生成 reconciled fact）。
6. 新增 reconciliation/service.py（OfficialFactReconciliationService：加载/调用 engine/校验 canonical/事务写入/lineage）。
7. 修正 tests/test_fact_reconciliation.py source_tier 语义。
8. 新增 tests/test_minimal_official_reconciliation.py（完整 engine + 语义测试）。
9. 验证 ruff/compileall/pytest/CLI import/diff-check。
10. 提交并推送独立检查点。

## 决策记录

### D1: 删除 petrochina.py（Preferred path），不保留 legacy

- 决策：删除 official_sources/petrochina.py，不移动为 legacy candidate。
- 原因：与 akshare_financial.py 功能完全重复，且 AKShare API 已失效；保留 legacy 会增加维护负担且仍需修 source_tier。
- 替代：Compatibility path 移动为 PetroChinaAKShareCandidateProvider。未采用，重复且 API 失效，不值得保留。
- 风险：tests/test_official_provider_identity.py 的 Layer 1a 依赖 PetroChinaProvider，需同步移除。

### D2: output_fact 用 dict 而非 Fact dataclass

- 决策：ReconciliationResult.output_fact 类型为 `dict | None`。
- 原因：整个代码库（Repository.store_facts、build_fact_id、lineage、make_test_fact）统一使用 dict；返回 Fact dataclass 需额外转换，与持久化层不一致。
- 替代：返回 Fact dataclass。未采用，与代码库惯例不符。
- 风险：与指令字面 `Fact | None` 偏离，已在记录说明。

### D3: reconciliation_id 确定性，created_at 由 service 注入

- 决策：engine 纯函数，reconciliation_id = 确定性 hash(sorted input fact_ids + rule_id)；output_fact.created_at 由 service 传入 now。
- 原因：保持 engine 纯粹与可复现；created_at 不参与 fact_id 与语义相等性，不影响幂等。
- 替代：engine 内 datetime.now。未采用，破坏纯度与确定性。

### D4: 可比身份字段中 scope/statement_type 经查表/解析

- 决策：consolidation_scope 经 parse_context_id 解析；statement_type 经 ConceptRegistry 查 concept_id；currency 用 unit 字段。
- 原因：spec 列出这些字段，但 Fact 不直接含 scope/statement_type；context_id 已编码 scope（冗余但保留以符 spec），concept_id 决定 statement_type。
- 风险：context_id 相等时 scope 必然相等，检查冗余但不冲突。

### D5: reconciliation service 不存 context，由测试 seed

- 决策：OfficialFactReconciliationService 只事务写入 reconciled fact + 输入事实 + lineage，不写 fact_contexts。
- 原因：spec 明确 service 职责仅为 reconcile+持久化 rec fact+lineage；context 属 FactService 范畴。get_latest_available JOIN fact_contexts，故 PIT 查询测试需 seed context（与 test_fact_reconciliation.py 一致）。
- 风险：调用方若未 seed context，PIT 查询返回空；属调用方职责。

### D6: AKShare candidate 测试 stub 整个 ak 对象

- 决策：测试用 `patch.object(mod, "ak", _FakeAk())` stub akshare_financial 模块的 ak，不依赖具体 API 名。
- 原因：AKShare API 已失效（Stage 1C-A.1 遗留），stub 任意属性返回假 DataFrame，验证 source_tier=candidate_aggregator。
- 实现修正：初版用 `__import__("unittest.mock").patch` 失败（返回 unittest 而非 unittest.mock），改为 `from unittest.mock import patch`。

## 实际操作

1. **models.py**：SourceTier 新增 `reconciled_derived`。
2. **删除 official_sources/petrochina.py**（`rm` + git 记录删除）。
3. **test_official_provider_identity.py**：移除 Layer 1a（TestPetroChinaProviderCanonical）与 petrochina 导入，保留 Layer 1b/2/3（9 用例）。
4. **reconciliation/models.py**：ReconciliationStatus（matched/mismatch/not_comparable/insufficient_evidence）、ReconciliationResult（Decimal 字段串序列化，output_fact: dict|None）。
5. **reconciliation/engine.py**：纯 ReconciliationEngine.reconcile_pair。7 步硬门禁（source tier -> verification -> evidence -> comparable identity -> concept support -> unit/currency -> Decimal 比较）；matched 生成 reconciled fact（source_tier=reconciled_derived、source_id=reconciled:petrochina_company_sse、input_fact_ids 稳定排序、available_at/announcement_date 取 max、fact_id=build_fact_id）；reconciliation_id 确定性。
6. **reconciliation/service.py**：OfficialFactReconciliationService.reconcile_official_pair（存输入+rec fact+lineage，事务，canonical 校验）。
7. **test_fact_reconciliation.py**：_source_fact 加 source_tier 参数，company=company_official、exchange=exchange_official；_reconciled_fact 改 reconciled_derived + 新 source_id/provider/derivation_id；断言对齐。
8. **test_minimal_official_reconciliation.py**（25 用例）：6 组测试覆盖 AKShare 语义、matched、retention/query、gates、Decimal、idempotency/conflict/lineage。
9. **修复**：_company/_exchange source_id override（setdefault）；PIT 测试 seed context；unittest.mock 正确导入；ruff SIM103/I001/F401。
10. **验证**：ruff + compileall + pytest + CLI import + diff-check。

## 验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| Ruff | `ruff check src tests` | All checks passed（exit 0） |
| compileall | `python -m compileall -q src tests` | exit 0 |
| CLI import | `import ashare_research.cli` + engine/service | OK |
| 针对性测试 | `pytest test_official_provider_identity.py test_fact_reconciliation.py test_minimal_official_reconciliation.py -q` | 40 passed |
| 全量 pytest | `pytest -q` | 261 passed, 2 baseline warnings（exit 0） |
| 空白 | `git diff --check` | 无空白错误 |
| output 跟踪 | `git ls-files "output/**"` | 无输出 |

全量 261 = 基线 240 + 净增 21（新增 test_minimal 25 - 移除 Layer 1a 4）。2 warnings 为 test_quality.py 既有 pandas 日期解析，与本次无关。无 DuckDB/PDF/缓存/output 产物。

## 结果

- AKShare 不再被标为 official：petrochina.py 已删除，AKShareFinancialCandidateProvider 为唯一 AKShare 路径（candidate_aggregator）；
- company 与 exchange 来源真正分离（company_official + exchange_official）；
- reconciled fact 不伪装为原始官方来源（source_tier=reconciled_derived）；
- 只接受两个 verified 官方事实（verification + eligible_for_metrics=False 门禁）；
- 三个 Concept 精确 Decimal 核验（revenue/net_profit_attributable_to_parent/operating_cash_flow）；
- matched 生成 canonical reconciled fact；mismatch 不生成事实；
- 原始事实完整保留（verified + eligible=False）；
- 默认 PIT 只返回 reconciled；审计查询返回全部三条；
- 重复核验幂等；lineage 完整引用两输入；
- 全部门禁通过，无网络和运行产物污染。
- 与原计划一致，无偏离；当前可用。

## 遗留问题

1. AKShare API 失效（Stage 1C-A.1 遗留）：测试用 stub 验证语义，但真实 candidate 源运行时不可用，记录为「candidate source runtime unavailable」，未修复（符合约束）。
2. 三 Concept 之外的核验（如总资产、净资产等）未实现，需 Stage 1C-B 后按需扩展；当前刻意保持最小集。
3. 真实 PetroChina 年报事实尚未录入（Stage 1C-B 任务），现 reconciled 仅由测试 fixture 触发；真实双源需 Stage 1C-B 注册 SSE+公司官网路径后录入。
4. reconciliation engine 当前为「无容差」第一版；未来若需容差，须另设 rule version + 容差配置，且不得改变 v1 语义。
5. service 不写 fact_contexts；调用方负责 seed context（PIT 查询依赖）。
6. stash@{0}（Stage 1B.4 旧记录编辑）保持原状未 pop。

## 下一步建议

- M2 Stage 1C-B：注册一份真实 PetroChina 年报的公司官网 + SSE 路径，保存 URL / announcement_date / SHA-256；手工录入并核验 3 个关键财务事实（revenue、net_profit_attributable_to_parent、operating_cash_flow），跑通真实双源 Reconciliation。
- 仅与核心目标相关，不扩展超出 Stage 1C-B 范围。

## 最终文件变更

新增：
- `src/ashare_research/reconciliation/__init__.py`
- `src/ashare_research/reconciliation/models.py`
- `src/ashare_research/reconciliation/engine.py`
- `src/ashare_research/reconciliation/service.py`
- `tests/test_minimal_official_reconciliation.py`
- `agent/record/2026-07-28_2048_m2_stage1ca2_minimal_reconciliation.md`

修改：
- `src/ashare_research/facts/models.py`（SourceTier 新增 reconciled_derived）
- `tests/test_fact_reconciliation.py`（source_tier 分离 + reconciled_derived 断言）
- `tests/test_official_provider_identity.py`（移除 Layer 1a 与 petrochina 导入）

删除：
- `src/ashare_research/official_sources/petrochina.py`

## 最终Git状态

- 当前分支：feat/m2-value-assessment-mvp
- 当前提交：__FINAL_HASH__（待填）
- 未提交修改：工作记录待记录最终哈希后单独 docs 提交
- 是否创建提交：是
- 是否创建 Tag/Release：否
- 是否推送：是（见 Final Report）
