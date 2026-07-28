# 工作记录：M2 Stage 1C Preflight - context_id 跨重述稳定、真实重述版本链、双源 reconciliation 规则冻结、verify 隔离强化

## 基本信息

- 日期：2026-07-28 17:01
- Agent：Claude Code
- 当前分支：feat/m2-value-assessment-mvp
- 开始提交：cf75e20
- 任务来源：Stage 1B.4.1 Conditional Pass 审查结论 —— 进入真实数据录入前的 Stage 1C Preflight（四项）
- 对应模块：价值评估（数据层治理 / 工程治理）

## 任务目标

完成审查结论中要求的 Stage 1C Preflight 四项，使版本链与重述机制真正闭环，并冻结双官方来源 reconciliation 语义，为后续中国石油 2021-2025 官方报告注册与事实录入扫清前置阻塞。不开启 Stage 1B.5，不扩大 Stage 1B 范围。

四项：

1. 决定 `context_id` 是否跨重述保持稳定，并落实代码；
2. 增加真正 `original -> restated_1` 的版本链与 PIT 测试；
3. 冻结公司官网与上交所双源生成 `reconciled canonical fact` 的规则；
4. 用不同事实集合强化 `verify --run-id` 隔离测试。

## 范围

允许修改：

- `src/ashare_research/facts/contexts.py`（build_context_id / parse_context_id / create_context / docstring）
- `src/ashare_research/facts/models.py`（FactContext docstring）
- `src/ashare_research/fact_sources/candidates/akshare_financial.py`（context_id 生成）
- `src/ashare_research/official_sources/petrochina.py`（context_id 生成）
- `src/ashare_research/derivations/engine.py`（单季度派生事实 context_id 生成）
- `tests/fact_test_helpers.py`、`tests/test_m2_facts.py`、`tests/test_fact_identity.py`、`tests/test_fact_cli.py`、`tests/test_fact_version_chain.py`、`tests/test_m2_idempotency.py`、`tests/test_fact_manifest_finalization.py`、`tests/test_m2_integration.py`（5 段 context_id 字面量改 4 段 + 新测试）
- 新增 `tests/test_fact_reconciliation.py`

## 非目标

- 不接入中国石油真实官方数据；
- 不开始 2021-2025 财务事实录入；
- 不实现 reconciliation 引擎本身（仅冻结规则并用测试锁定，引擎留待 Stage 1C）；
- 不修复 petrochina.py 的非 canonical `_make_fact_id`（Stage 1C 前置项，记录为遗留）；
- 不改变 fact_contexts 表 schema（restatement_version 列保留为名义字段）；
- 不合并到 main，不创建 Tag 或 Release；
- 不自动推送。

## 开始前状态

- 当前分支：feat/m2-value-assessment-mvp，HEAD=cf75e20；
- 工作区有 1 个已修改文件：`agent/record/2026-07-28_11_m2_stage1b4_clean_checkout_closure.md`（上一任务记录，含遗留 `（待填）` 模板残块）。按 Git 规则保护该修改，不混入本次任务、不擅自清理；
- 远程 cf75e20 已包含 identity.py、version_chain.py、CLI/Manifest 测试与记录，干净 clone 可运行（215 passed）。

## 调研结论（关键问题确认）

### 问题 1：context_id 与版本链稳定身份冲突

- `contexts.py:build_context_id` 把 `restatement_version` 作为第 5 段拼进 `context_id`：
  `SYMBOL|FY|PERIOD_TYPE|SCOPE|RESTATEMENT`；
- `version_chain.py:_STABLE_IDENTITY_FIELDS` 包含 `context_id`，要求跨版本完全一致；同时又允许 `restatement_version` 变化；
- 真实重述（`original -> restated_1`）会改变 `context_id` 第 5 段，触发 `FACT_VERSIONCHAIN_001` 检查 C 失败；
- 现有 PIT 测试 v1/v2 都用 `...|original`，只改 `fact_version/value/available_at`，未真正测试重述。

### 问题 2：service._build_contexts 不传 restatement_version

- `service.py:_build_contexts` 调 `create_context` 时未传 `restatement_version`，恒为默认 `"original"`；
- 若 provider 把事实 `context_id` 设成 `...|restated_1`，会与 service 构建的 `...|original` context 不匹配，`get_latest_available` JOIN 失败。

### 问题 3：get_latest_available 查询语义

- PARTITION BY `symbol, concept_id, period_end, consolidation_scope`，ORDER BY `available_at DESC, fact_version DESC, restatement_version DESC, created_at DESC`；
- WHERE 已含 `verification_status IN ('verified','reconciled') AND eligible_for_metrics = TRUE`；
- 即查询侧已支持“只有 eligible 的 reconciled 事实进指标”，双源 reconciliation 规则可在现有查询上冻结，无需把 source_id 加入分区。

### 问题 4：verify --run-id 隔离测试偏弱

- `cli.py:cmd_verify_value_facts` 按 `SELECT fact_id FROM fact_lineage WHERE run_id=?` 加载，实现正确；
- 但测试两次构建同年同概念，fact_id 集合相同，即使错误实现加载全部事实，count 也可能相同，无法证伪。

## 实施计划

1. Item 1：`build_context_id` 去掉 `restatement_version`（4 段）；`parse_context_id` 改 4 键；`create_context` 保留 `restatement_version` 形参（存入 FactContext 名义字段）但不再拼入 context_id；更新 models.py / contexts.py docstring；provider 与 engine 改用 `build_context_id`；tests 字面量去 `|original` 后缀。
2. Item 2：`test_fact_version_chain.py` 新增 `TestRealRestatementChain`，v1(original,fv1) 与 v2(restated_1,fv2,supersedes v1) 同 context_id，验证链路通过 + PIT 切换。
3. Item 3：新增 `tests/test_fact_reconciliation.py` 锁定 reconciliation 规则。
4. Item 4：`test_fact_cli.py` 第二次构建改 2024 年，断言两 run fact_id 集合不相交。
5. 验证：ruff + compileall + pytest。
6. 更新记录与 Git 状态。

## 决策记录

### D1: context_id 跨重述保持稳定（Model A）

- 决策：`context_id = SYMBOL|FY|PERIOD_TYPE|SCOPE`（4 段），不再包含 `restatement_version`。`restatement_version` 退为事实级属性，沿版本链允许变化。
- 原因：`VersionChainValidator` 检查 C 要求 `context_id` 跨版本稳定，而 Item 2 要求 `original -> restated_1` 进入同一版本链；二者同时成立的唯一自洽解是 context_id 不含 restatement_version。语义上 context 代表“哪家公司+哪个期间+什么口径”这一经济现实，重述是对同一 context 的重新报告。
- 替代方案：保留 5 段、从 `_STABLE_IDENTITY_FIELDS` 移除 `context_id`。未采用，因会失去“v2 必须与 v1 同一期间/口径”的保护，允许跨期 supersede。
- 替代方案：保留 5 段、为重述新增 context 级后继链。未采用，需新增 schema 与机制，超出“很小 Preflight”范围，且与 Item 2“同一版本链”诉求不符。
- 风险：`fact_contexts.restatement_version` 列变为名义字段（service 恒填 `original`），不参与 context_id 与查询分区；已在记录中标注，不改 schema。

### D2: 双源 reconciliation 规则冻结（reconciled canonical fact）

- 决策：公司官网事实 + 上交所事实各自以独立身份（不同 `source_id`）入库，`verification_status='verified'`、`eligible_for_metrics=False`；交叉核验通过后生成一个独立 `reconciled canonical fact`，`verification_status='reconciled'`、`eligible_for_metrics=True`、`input_fact_ids` 引用两源、`source_id` 形如 `reconciled:<src_a>+<src_b>`。指标查询只取 reconciled，两源保留为审计轨迹。
- 原因：`get_latest_available` 与 `query_facts` 默认已过滤 `eligible_for_metrics=True`，天然只返回 reconciled；无需把 `source_id` 加入业务快照分区，完整审计来源保留在 `input_fact_ids` 与事实行。
- 替代方案：把 `source_id` 加入 `get_latest_available` 分区，两源都进指标。未采用，会导致同一指标双行、依赖 `created_at` 兜底选行，语义不稳。
- 范围边界：本 Preflight 仅冻结规则并用测试锁定数据模型与查询语义；真正“取数-比对-生成 reconciled”的引擎留待 Stage 1C。
- 风险：reconciled 事实与两源 `source_id` 不同，因 `source_id` 是稳定身份字段，reconciled 不进入两源的版本链，而是独立身份（符合“派生/核对”语义）。

### D3: provider / engine 改用 build_context_id 单一入口

- 决策：akshare_financial.py、petrochina.py、engine.py 的 context_id 由硬编码字符串改为调用 `build_context_id`，保证与 `create_context` 输出一致。
- 原因：service._build_contexts 用 create_context 重建 context 行，provider 事实 context_id 必须与之精确匹配，否则 JOIN 失败；单一入口消除漂移。
- 风险：低，period_type 透传不变。

### D4: verify 隔离测试改用不同年份

- 决策：第二次构建改 2024 年（与第一次 2025 年 fact_id 集合不相交），并断言两 run fact_id 集合 `isdisjoint`。
- 原因：同年同概念幂等构建 fact_id 相同，无法证伪“加载全部事实”的错误实现；不同年份使 fact_id 集合真正不同。
- 替代方案：改用不同 concept（run_a=revenue, run_b=net_profit）。未采用，需参数化 provider，改动更大；不同年份同样达成目的且最小。

（实施中持续补充）

## 实际操作

按计划顺序执行：

1. **contexts.py**：`build_context_id` 去掉 `restatement_version` 形参与第 5 段，输出 4 段 `SYMBOL|FY|PERIOD_TYPE|SCOPE`，并补 docstring 说明“跨重述稳定”；`parse_context_id` 改 4 键（不再返回 restatement_version）；`create_context` 仍接受 `restatement_version` 形参（存入 FactContext 名义字段）但调用 `build_context_id` 时不再传入。
2. **models.py**：FactContext docstring 改为 4 段格式说明（首行因编码差异保留原样，实质性格式/示例行已更新）。
3. **provider/engine 改用 build_context_id 单一入口**：akshare_financial.py、petrochina.py 各 1 处；engine.py 两处单季度派生事实（`single_quarter_q{quarter}`）。均新增 `from ashare_research.facts.contexts import build_context_id`。
4. **tests 5 段字面量去 `|original` 后缀**：fact_test_helpers.py、test_fact_identity.py、test_fact_cli.py(StubProvider)、test_m2_facts.py、test_m2_idempotency.py(3 处)、test_fact_manifest_finalization.py、test_m2_integration.py(4 处)。
5. **test_m2_facts.py 新增 2 用例**：`test_build_context_id_stable_across_restatements`（create_context 传 restated_1 仍得相同 context_id）、`test_parse_context_id_four_parts`（4 键、无 restatement_version）。
6. **test_fact_version_chain.py**：`_versioned_fact`/`_seed_context` 改用 `build_context_id`；新增 `TestRealRestatementChain`（4 用例：链路校验通过 / PIT 重述日前返回 original / 重述日返回 restated_1 / 双版本保留）。
7. **新建 tests/test_fact_reconciliation.py（6 用例）**：冻结双源规则——两源 verified+eligible=False、reconciled eligible=True+input_fact_ids；验证 get_latest_available 与 query_facts 默认仅返回 reconciled、审计查询见三事实、源事实不可进指标、reconciled 记录两源 ID。
8. **test_fact_cli.py**：`test_cli_verify_uses_requested_run_only` 第二次构建改 2024 年，新增两 run fact_id 集合 `isdisjoint` 断言。
9. **验证**：ruff + compileall + 分项 pytest + 全量 pytest + git diff --check。

## 验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| Ruff | `ruff check src tests` | All checks passed |
| compileall | `python -m compileall -q src tests` | OK |
| context 烟测 | `build_context_id` / `parse_context_id` / `create_context(restated_1)` | 4 段；restated_1 与 original 产生相同 context_id |
| 版本链+context | `pytest tests/test_fact_version_chain.py tests/test_m2_facts.py -q` | 51 passed |
| reconciliation | `pytest tests/test_fact_reconciliation.py -q` | 6 passed |
| CLI | `pytest tests/test_fact_cli.py -q` | 6 passed |
| 全量 | `pytest -q` | 227 passed, 2 warnings |
| 空白 | `git diff --check` | 仅 LF->CRLF 警告，无空白错误 |

全量 227 = 基线 215 + 新增 12（Item1 ×2、Item2 ×4、Item3 ×6）。2 个 warnings 位于 `tests/test_quality.py` 的 pandas 日期解析，为既有警告，与本次改动无关。

## 结果

- 四项 Preflight 全部完成并通过验证；
- Item 1：context_id 跨重述稳定（Model A），真实重述 `original -> restated_1` 可进入同一版本链；
- Item 2：新增真实重述版本链 + PIT 测试，覆盖此前缺失的“restatement_version 变化、context_id 不变”场景；
- Item 3：双源 reconciliation 规则已冻结，并用 6 个测试锁定数据模型与查询语义（仅 reconciled 进指标、两源留审计）；
- Item 4：verify `--run-id` 隔离测试改用不相交 fact_id 集合，真正可证伪“加载全部事实”的错误实现；
- 与原计划一致，无偏离；当前可用。

## 遗留问题

1. **petrochina.py 仍用非 canonical `_make_fact_id`**（16 字符截断 SHA-256），是 Stage 1C 真实官方源接入前的硬阻塞；本次仅改其 context_id，未动 ID 生成（超出 Preflight 范围）。
2. **fact_contexts.restatement_version 列现为名义字段**（service 恒填 `original`），不参与 context_id 与查询分区；未改 schema，未来若需 context 级重述语义可再评估。
3. **reconciliation 引擎本身未实现**（取数-比对-生成 reconciled）；本 Preflight 仅冻结规则与数据模型/查询语义，留待 Stage 1C。
4. 工作区开始时已有 `agent/record/2026-07-28_11_m2_stage1b4_clean_checkout_closure.md` 的未提交修改（上一任务记录含 `（待填）` 残块），按 Git 规则保护，未混入本次、未清理。
5. 未提交、未推送（用户未要求 commit）。

## 下一步建议

- Stage 1C：修复 petrochina.py canonical ID（改用 `build_fact_id`）并接入真实官方源（公司官网 + 上交所），按已冻结 reconciliation 规则生成 `reconciled canonical fact`；
- 中国石油 2021-2025 年度 + 8 个单季度官方事实注册与录入；
- 录入后跑 PIT 与审计查询验证。

## 最终文件变更

新增：

- `tests/test_fact_reconciliation.py`
- `agent/record/2026-07-28_1701_m2_stage1c_preflight.md`

修改：

- `src/ashare_research/facts/contexts.py`
- `src/ashare_research/facts/models.py`
- `src/ashare_research/fact_sources/candidates/akshare_financial.py`
- `src/ashare_research/official_sources/petrochina.py`
- `src/ashare_research/derivations/engine.py`
- `tests/fact_test_helpers.py`
- `tests/test_fact_cli.py`
- `tests/test_fact_identity.py`
- `tests/test_fact_manifest_finalization.py`
- `tests/test_fact_version_chain.py`
- `tests/test_m2_facts.py`
- `tests/test_m2_idempotency.py`
- `tests/test_m2_integration.py`

## 最终Git状态

- 当前分支：feat/m2-value-assessment-mvp
- 当前提交：cf75e20（未变）
- 工作区：本次 12 个已修改 + 2 个未跟踪；另含 1 个会话开始前已存在的前次修改（`2026-07-28_11_m2_stage1b4_clean_checkout_closure.md`，未触碰、未混入）
- 是否提交：否
- 是否推送：否
- 未创建 Tag 或 Release
