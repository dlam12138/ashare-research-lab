# 工作记录：M2 Stage 1C-A 第一项 - 官方 Provider canonical 身份规范化

## 基本信息

- 日期：2026-07-28 20:14
- Agent：Claude Code
- 当前分支：feat/m2-value-assessment-mvp
- 开始提交：f1b7f87（`f1b7f87a492c0b38c1722ca51859303630c18186`）
- 任务来源：Stage 1C-A 第一项指令（官方来源身份规范化，单独完成，不实现 reconciliation engine）
- 对应模块：价值评估（数据层治理 / 工程治理）

## 任务目标

让官方来源 Provider 全面使用 canonical `FactIdentity` / `build_fact_id()`，消除私有 ID 拼接逻辑，使 reported/derived/manual official facts 均无法绕过身份契约。本轮只做身份契约规范化，为 Stage 1C-A 第二项（reconciliation engine）扫清第一个硬阻塞。

## 范围

经审查，代码库有两个名字相近、现状不同的官方 provider，用户确认"两者都做"：

### 文件 1：`src/ashare_research/official_sources/petrochina.py`（PetroChinaProvider）

- 含私有 `_make_fact_id`（16 字符截断 SHA-256，`petrochina.py:235-240`）；
- 用 AKShare 取数、访问网络；
- 未被 Service/CLI 接入（Service 用 `fact_sources` 体系），但属官方 provider 体系，是 Preflight 遗留问题 #1 的字面对象。

### 文件 2：`src/ashare_research/fact_sources/official/petrochina_filings.py`（PetroChinaOfficialFilingProvider）

- 被 Service/CLI 接入的官方入口（`config/official_sources/601857.SH.yaml` 引用）；
- 当前空骨架，所有方法 `raise SourceDocumentError`，无 ID 生成路径；
- 将来消费"官网报告、上交所公告、已注册官方手工事实文件"。

允许修改：

- `src/ashare_research/official_sources/petrochina.py`（删 `_make_fact_id`，改 `build_fact_id`，补全 canonical 身份字段）
- `src/ashare_research/fact_sources/official/petrochina_filings.py`（增加 manual official fact 加载入口，出口强制 canonical）
- 新增 `tests/test_official_provider_identity.py`（Provider/Service/Repository 三层测试）

## 非目标

- 不实现 reconciliation engine（Stage 1C-A 第二项）；
- 不下载、解析真实官方报告（PDF 等）；
- 不录入 2021-2025 真实事实；
- 不接入真实网络数据；
- 不为 `fact_contexts.restatement_version` 开数据库迁移；
- 不合并到 main，不创建 Tag 或 Release；
- 不自动推送；
- 不动 `stash@{0}`。

## 开始前状态

- 分支：feat/m2-value-assessment-mvp，HEAD=`f1b7f87`，与远程一致；
- 工作区干净，`stash@{0}`（Stage 1B.4 记录旧修改）保持不动；
- Preflight 检查点已推送（`26f6702` 实现 + `f1b7f87` 记录）；
- `official_facts/` 目录不存在，手工事实文件机制尚未建立；
- `PetroChinaOfficialFilingProvider` 全 raise，不生成 fact。

## 调研结论

### 架构现状

- 存在两套并行 provider 体系：
  1. `fact_sources/`（`FactSourceProvider` + `FactSourceRegistry`）--被 Service/CLI 实际使用，`SourceTier` 区分 candidate/company_official/exchange_official；
  2. `official_sources/`（`OfficialSourceProvider` + `OfficialSourceRegistry`）--独立、未接入 Service，`PetroChinaProvider` 用 AKShare。
- `PetroChinaOfficialFilingProvider`（`fact_sources/official/`）是 Service 真正入口，空骨架。
- `PetroChinaProvider`（`official_sources/`）未接入 Service，含非 canonical `_make_fact_id`。

### 身份契约现状

- `build_fact_id` / `validate_canonical_fact_ids`（identity.py）已是 canonical 单一入口，Service + Repository 双边界已强制（Preflight 实现）；
- `PetroChinaProvider._make_fact_id` 是最后一个私有 ID 拼接逻辑，输出 16 字符截断 SHA-256，与 canonical（完整 64 字符）不一致；
- `PetroChinaOfficialFilingProvider` 无 ID 生成，但缺少 manual fact 加载入口。

## 实施计划

1. 文件 1：删 `_make_fact_id`；`_fetch_report_facts` 与 `get_dividends` 改 `build_fact_id`；补全 canonical 身份字段（concept_version、source_id、fact_version、restatement_version、supersedes_fact_id、eligible_for_metrics、verification_status、source_tier 等）；context_id 已用 build_context_id（Preflight 已改）。
2. 文件 2：增加 manual official fact 加载入口（构造注入 fact 列表）；`get_financial_statements` 读取并强制 `build_fact_id` + `validate_canonical_fact_ids`；未提供手工事实时仍 raise `SourceDocumentError`（保持占位语义，不静默返回空）。
3. 新建 `tests/test_official_provider_identity.py`：
   - Provider 层：PetroChinaProvider（monkeypatch stub AKShare，不访问网络）产出 canonical fact_id；PetroChinaOfficialFilingProvider manual 加载产出 canonical 且拒绝非 canonical 注入；
   - Service 层：official 路径拒绝非 canonical（补充）；
   - Repository 层：store_facts 拒绝非 canonical official fact（补充）。
4. 验证：ruff + compileall + pytest + diff-check。
5. 提交并推送独立检查点。

## 决策记录

### D1: 两个 provider 同时处理，但职责不同

- 决策：文件 1 清理私有 ID（消除隐患），文件 2 建立 canonical 加载入口（纵深防御第一层）。
- 原因：用户确认"两者都做"。文件 1 的 `_make_fact_id` 是明确的身份契约隐患（遗留 #1）；文件 2 是 Service 真正入口，需保证将来 manual official facts 无法绕过 canonical。
- 替代：只改文件 1。未采用，文件 2 作为 Service 入口缺少 canonical 强制点，manual facts 仍可绕过。
- 替代：只改文件 2。未采用，文件 1 的私有 ID 拼接仍是代码库隐患。
- 风险：文件 1 未接入 Service，改它对主链路无影响，但消除隐患；文件 2 增加 manual 加载入口，需确保不滑入真实录入（仅入口机制，不下载/解析真实报告）。

### D2: Provider 层 canonical 校验是纵深防御第一层，不与 Service/Repository 重复

- 决策：`PetroChinaOfficialFilingProvider.get_financial_statements` 出口强制 `validate_canonical_fact_ids`。
- 原因：通过标准要求"reported/derived/manual official facts 均无法绕过身份契约"且"增加 Provider 三层测试"。provider 是数据进入第一站，Service/Repository 是第二三层。
- 替代：仅靠 Service/Repository 校验。未采用，不满足"Provider 层测试"与"无法绕过"要求。

### D3: manual fact 加载入口用构造注入，不访问网络/文件系统

- 决策：`PetroChinaOfficialFilingProvider` 构造接受可选 `manual_facts: list[dict]`；测试直接注入，不读真实文件、不访问网络。
- 原因：非目标禁止真实录入与网络；构造注入使测试确定且不访问网络。
- 替代：从 official_facts/ 目录读取真实文件。未采用，超出非目标（真实录入），且目录尚不存在。
- 风险：manual_facts 由调用方提供 fact_id 时，provider 出口会重算并拒绝不匹配--这正是"无法绕过"的体现。

### D4: PetroChinaProvider 测试 patch 整个 ak 对象，不依赖具体 API 名

- 决策：测试用 stub 整个 `petrochina.ak` 对象（任意属性返回返回假 DataFrame 的 callable），而非逐个 patch `akshare.stock_financial_*_by_report_em`。
- 原因：petrochina.py 用的旧 AKShare API 名（`stock_financial_profit_by_report_em` 等）在当前安装的 akshare 版本里不存在，`patch("akshare.stock_financial_...")` 因 `AttributeError: does not have the attribute` 失败。stub 整个 ak 不依赖具体 API 名，测试稳定且不访问网络。
- 替代：改用当前 akshare 的新 API 名。未采用，那是数据源适配问题，超出本轮"身份规范化"范围；且 petrochina.py 是将被废弃的旧实现，不值得修 API 适配。
- 风险：petrochina.py 在当前 akshare 版本下实际取数已失效（getattr 拿不到 API -> EmptyResultError），但这是既有数据源问题，非本轮身份契约问题；身份契约本身已被测试覆盖。

### D5: AKShare API 失效的工程结论（记录，不在本轮修）

- 发现：petrochina.py 调用的 `stock_financial_profit_by_report_em` / `balance_sheet` / `cash_flow` 三个 API 在当前 akshare 版本不存在，实际取数链路已断。
- 处理：本轮不修（超出身份规范化范围）。记录为遗留，提示 Stage 1C 真实数据录入时若复用 AKShare 候选路径需先做 API 适配。
- 注：candidate provider（akshare_financial.py）用的也是同类 API，可能同样失效，待 Stage 1C 验证。

## 实际操作

1. **调研**：审查发现两个官方 provider--`official_sources/petrochina.py`（PetroChinaProvider，含 `_make_fact_id`，未接入 Service）与 `fact_sources/official/petrochina_filings.py`（PetroChinaOfficialFilingProvider，空骨架，被 Service 接入）。用户确认两者都做。
2. **文件 1（official_sources/petrochina.py）**：删 `import hashlib`、加 `from ashare_research.facts.identity import build_fact_id`；`_fetch_report_facts` 删 `_make_fact_id` 调用，改 `build_fact_id`，补全 canonical 身份字段（concept_version/source_id/source_tier/fact_version/restatement_version/supersedes_fact_id/source_url/source_hash/source_page/source_table/source_label 等）；`get_dividends` 同样改 `build_fact_id` + 补全字段；删除文件末尾 `_make_fact_id` 私有函数。
3. **文件 2（fact_sources/official/petrochina_filings.py）**：重写为 canonical 加载入口。构造接受 `manual_facts`；`get_financial_statements` 读取并经 `_enforce_canonical`（重算 `build_fact_id` + `validate_canonical_fact_ids`）；未注入时仍 raise `SourceDocumentError`。`get_dividends/get_buybacks/...` 同样在未注入时 raise。
4. **新增 tests/test_official_provider_identity.py（13 用例）**：
   - Layer 1a PetroChinaProvider：无 `_make_fact_id` 残留、facts canonical（64 字符）、相同身份稳定相同 id、value 变化不改 id（stub ak，不访问网络）；
   - Layer 1b PetroChinaOfficialFilingProvider：未注入 raise、manual facts 强制 canonical、错误 fact_id 被重算覆盖、fact_version/source_id 变化改 id；
   - Layer 2 Service：official 路径接受 canonical、拒绝篡改 fact_id 的 provider；
   - Layer 3 Repository：store_facts 拒绝非 canonical official fact、接受 canonical。
5. **修复**：初版 Provider 层测试逐个 patch `akshare.stock_financial_*_by_report_em`，因当前 akshare 版本无此 API 失败；改用 stub 整个 `petrochina.ak` 对象（D4）；修复 ruff SIM117（嵌套 with 合并）与 I001（导入顺序）。
6. **验证**：ruff + compileall + 全量 pytest + CLI import + diff-check。

## 验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| Ruff | `ruff check src tests` | All checks passed（exit 0） |
| compileall | `python -m compileall -q src tests` | exit 0 |
| 三层身份测试 | `pytest tests/test_official_provider_identity.py -q` | 13 passed |
| 全量 pytest | `pytest -q` | 240 passed, 2 baseline warnings（exit 0） |
| CLI import | `import ashare_research.cli` + 两个 provider | OK |
| 空白 | `git diff --check` | 无空白错误 |

全量 240 = 基线 227 + 新增 13。2 warnings 为 test_quality.py 既有 pandas 日期解析，与本次无关。

## 结果

- 官方 Provider 不再存在私有 ID 拼接逻辑（`_make_fact_id` 已删除）；
- 相同身份生成稳定相同 `fact_id`；`value`/公告日期/来源哈希变化不改变 ID（由 canonical 语义保证），同版本内容冲突由 Repository 触发；
- `fact_version`/`context_id`/`source_id` 变化会改变 ID（canonical 身份字段）；
- Service 与 Repository 均拒绝非 canonical official fact（三层测试覆盖）；
- 官方 Provider 测试不访问网络（stub ak + manual facts 注入）；
- 与原计划一致，无偏离；当前可用。

## 遗留问题

1. **AKShare 财务 API 失效**（D5）：petrochina.py 与 candidate provider 用的 `stock_financial_*_by_report_em` 在当前 akshare 版本不存在，实际取数链路已断；本轮不修（超出身份规范化范围），Stage 1C 真实数据录入前需做 API 适配或换源。
2. **reconciliation engine 尚未实现**（Stage 1C-A 第二项硬阻塞）。
3. **中国石油官网和上交所报告尚未注册**，真实官方事实未录入。
4. `fact_contexts.restatement_version` 仍为兼容名义字段，不单独迁移。
5. 未提交、未推送（待用户确认检查点提交方式）。

## 下一步建议

（待填）

## 最终文件变更

（待填）

## 最终Git状态

（待填）
