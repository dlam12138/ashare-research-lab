# 工作记录：M2 Stage 1B.4.1 - 补交核心模块、强制事实身份、真实版本链与干净检出验收

## 基本信息

- 日期：2026-07-28
- Agent：Claude Code
- 当前分支：feat/m2-value-assessment-mvp
- 开始提交：043197d
- 任务来源：Stage 1B.4.1 最终补交与干净检出闭环指令
- 对应模块：价值评估（数据层治理 / 工程治理）

## 任务目标

让远程分支在全新 clone 中可以独立导入、测试和运行，并让事实身份、版本链、PIT、CLI、Manifest 五条链路真正闭环。

具体子目标：

1. 补交漏提交的 `src/ashare_research/facts/identity.py`（043197d 漏文件根因）；
2. 全链路强制 canonical fact ID（Service + Repository 双边界）；
3. 完整语义 payload 比对，来源字段变化触发冲突；
4. Repository-aware 版本链校验（旧事实存在性、版本递增、稳定身份一致、日期不倒退、防循环）；
5. 真实 PIT 重述版本切换测试；
6. 真实 CLI 调用级测试（candidate=2, official=1 不回退, verify 指定 run）；
7. 修复 Manifest finalized 时机（写入成功后才置 True，失败抛 LineagePersistenceError）；
8. 远程干净 clone 验收。

## 范围

允许修改：

- `src/ashare_research/facts/identity.py`
- `src/ashare_research/exceptions.py`
- `src/ashare_research/derivations/engine.py`
- `src/ashare_research/facts/repository.py`
- `src/ashare_research/facts/service.py`
- `src/ashare_research/validation/version_chain.py`（新增）
- `src/ashare_research/validation/rule_registry.py`
- `src/ashare_research/cli.py`
- `tests/fact_test_helpers.py`（新增）
- `tests/test_m2_integration.py`、`tests/test_m2_idempotency.py`（fixture 改 canonical）
- `tests/test_fact_identity.py`、`tests/test_fact_version_chain.py`、`tests/test_fact_cli.py`、`tests/test_fact_manifest_finalization.py`（新增）

## 非目标

- 不接入中国石油真实官方数据；
- 不开始 2021-2025 财务事实录入；
- 不新增估值、评分、ROE、ROIC；
- 不引入 PDF OCR；
- 不合并到 main；
- 不创建 Tag 或 Release。

## 开始前状态

- 当前分支：feat/m2-value-assessment-mvp，HEAD=043197d；
- `git status` 显示 3 个未跟踪文件：
  - `agent/record/2026-07-28_10_m2_stage1b4_final_closure.md`
  - `agent/record/2026-07-28_1100_top_level_exception_guard_service.md`
  - `src/ashare_research/facts/identity.py`
- `git ls-files src/ashare_research/facts/identity.py` 为空 -> identity.py 未被 Git 跟踪（漏提交根因）；
- 043197d 提交了 11 个文件（repository.py、service.py、akshare_financial.py 等都 import identity），但漏掉 identity.py 本身；
- 干净 clone 会因 `import ashare_research.facts.identity` 失败而无法运行；
- 基线测试（本地有 identity.py）：`pytest -q` -> 164 passed；
- `output/` 已在 .gitignore，`git ls-files "output/**"` 为空；
- ruff 配置：E/F/W/I/N/UP/B/SIM，line-length=100，py311。

## 已发现的关键问题（调研结论）

1. **identity.py 漏提交**：根因确认，akshare_financial.py 和 repository.py 均 import identity，但 identity.py 未进 043197d。
2. **canonical ID 仅 Provider 用**：akshare_financial.py 用 `build_fact_id`，但 service 和 repository 不强制；测试 fixture 用随机 UUID / 硬编码字符串。
3. **derivation engine 私有 ID**：engine.py 有私有 `_make_fact_id`（16 字符截断），非 canonical；`_make_single_q_fact_dict` 硬编码 `symbol="601857.SH"`。
4. **FACT_VERSION_001 只查字段**：不查旧事实存在性、版本递增、身份一致、日期、循环。
5. **get_latest_available**：PARTITION BY 已不含 fact_version（正确），但 ORDER BY 缺 `restatement_version DESC`。
6. **Manifest finalized 时机**：service.py 第 830 行在 `write_manifest`（867）之前置 `finalized=True`，写失败已置 True；用 RuntimeError 而非 LineagePersistenceError。
7. **CLI official 模式**：提前返回 1，不写失败 Manifest，不输出 "no fallback"；verify 只输出验证 run id，不输出 build run id。
8. **语义 payload**：identity.py 含 `period_start`，但 Fact 模型与 financial_facts 表均无此列（应移除以保持三者一致）。

## 实施计划

按依赖顺序：

1. identity.py：补 `normalize_identity_text`/`fact_identity_from_fact`/`build_fact_identity_key`/`validate_canonical_fact_ids`；移除 payload 中 `period_start`。
2. exceptions.py：加 `FactIdentityError`、`LineagePersistenceError`、`VersionChainCycleError`。
3. engine.py：改用 `build_fact_id`，删 `_make_fact_id`，修 symbol 硬编码，补 concept_version/source_id。
4. repository.py：store_facts 加 canonical 校验；get_latest_available ORDER BY 加 restatement_version DESC；冲突消息列 sorted diff。
5. validation/version_chain.py：新增 VersionChainValidator。
6. rule_registry.py：加 FACT_VERSIONCHAIN_001。
7. service.py：加 canonical 校验（reported+derived）；加版本链校验；修 manifest finalized 时机 + LineagePersistenceError。
8. cli.py：加 create_fact_service 工厂；official 走 service 写失败 Manifest + no fallback；verify 输出 build+validation run id；main 支持 factory 注入。
9. tests：fact_test_helpers.py；重构两个 fixture 文件为 canonical；新增 4 个测试文件。
10. 验证：ruff + pytest + compileall；干净 clone 验收。

## 决策记录

### D1: Repository 硬性拒绝非 canonical fact_id（FactIdentityError）

- 决策：store_facts 对每条事实校验 `fact_id == build_fact_id(fact)`，不符即抛 FactIdentityError。
- 原因：spec 5.3 要求持久化边界最终保证身份契约；Repository 不是 Service 唯一调用者。
- 替代：仅 Service 校验。未采用，因手工脚本/迁移可能直连 Repository。
- 风险：现有测试 fixture 用随机 UUID 会全部失败 -> 必须同步重构 fixture（spec 5.4）。

### D2: 测试 fixture 统一改 canonical ID

- 决策：新建 `tests/fact_test_helpers.py::make_test_fact`，内部 `fact["fact_id"] = build_fact_id(fact)`，忽略显式 fact_id 覆盖。
- 原因：spec 5.4 明确禁止为让旧 fixture 运行而允许非 canonical ID。
- 风险：需要逐个更新断言硬编码 fact_id 的测试，改为读取 `fact["fact_id"]`。

### D3: 版本链校验用 store 单例连接读已提交数据

- 决策：VersionChainValidator.validate(facts, *, conn) 在 Service 事务前调用，conn 由 `repo.store.connect()` 提供（单例）。
- 原因：DuckDBStore.connect 返回缓存连接，校验阶段读已提交数据，后续事务用同一连接，不打开第二连接（spec 7.2）。
- 替代：在校验阶段开新连接。未采用，违反 spec 7.2。

### D4: semantic payload 移除 period_start

- 决策：从 `_SEMANTIC_PAYLOAD_FIELDS` 移除 `period_start`。
- 原因：Fact 模型与 financial_facts 表均无 period_start（在 FactContext 上）；spec 6.1 要求三者一致，不存在的字段不硬加。
- 风险：低，实践中 fact dict 从不含 period_start。

（实施中持续补充）

## 实际操作

按计划顺序执行：

1. **identity.py（补全接口）**：新增 `normalize_identity_text`、`fact_identity_from_fact`、`build_fact_identity_key`、`validate_canonical_fact_ids`、`_safe_get`；`fact_identity_from_dict` 改为兼容别名。从 `_SEMANTIC_PAYLOAD_FIELDS` 移除 `period_start`（Fact 模型与 financial_facts 表均无此列）。`_normalize_list_field` 增加逗号分隔字符串处理；`_normalize_for_comparison` 与 `diff_fact_semantic_payloads` 增加 NaN==None 处理（DuckDB DOUBLE NULL 读回 NaN）。

2. **exceptions.py**：新增 `FactIdentityError(FactPersistenceError)`、`LineagePersistenceError(AshareDataError)`、`VersionChainCycleError(FactValidationError)`。

3. **engine.py**：删除私有 `_make_fact_id`（16 字符截断），`_make_single_q_fact`/`_make_single_q_fact_dict` 改用 `build_fact_id`；修复 `_make_single_q_fact_dict` 硬编码 `symbol="601857.SH"`（改为必填关键字参数，由调用方从源行传入）；补 `concept_version`/`source_id`/`fact_version`/`restatement_version` 身份字段；`_make_single_q_fact_dict` 新增 `period_end` 参数（继承源事实报告期，修复派生事实 period_end 空导致 FACT_PERIOD_001 失败）。

4. **repository.py**：`store_facts` 每条事实加 canonical 校验（`build_fact_id(fact) != fact_id` -> `FactIdentityError`，标注 persistence boundary）；冲突消息列 `sorted(diff.keys())`；`get_latest_available` ORDER BY 增加 `restatement_version DESC`。

5. **validation/version_chain.py（新增）**：`VersionChainValidator(repository)`，`validate(facts, *, conn, now)` 返回 `FactValidationResult` 列表。检查项：E 早检自取代与循环遍历（`_assert_no_cycle` 沿 supersedes_fact_id 向上，visited 集合，超过 `_MAX_CHAIN_DEPTH=1000` 防御）；A 旧事实存在性（batch_by_id + repo._get_fact_by_id）；B 严格 +1（`fv == old_fv + 1`）；C 稳定身份字段一致（7 个字段）；D available_at/announcement_date 不倒退。

6. **rule_registry.py**：新增 `FACT_VERSIONCHAIN_001` 规则描述。

7. **service.py**：`__init__` 初始化 `self.version_chain_validator`；阶段 2b（reported）和 6b（derived）插入 `validate_canonical_fact_ids`（失败写 failed manifest + 返回）；阶段 4b（reported）和 6b（derived）插入 `VersionChainValidator.validate`（VersionChainCycleError 写 failed manifest + 返回；error 计入 reported/derived_error_count）；`all_validation` 改为阶段 4b 初始化并累积（移除阶段 10 重复赋值）；`_finalize_and_write_manifest` 修正 finalized 时机（`write_manifest` 成功后才置 `finalized=True` 并记录 `manifest_path`，失败抛 `LineagePersistenceError` 而非 RuntimeError）；新增 `_safe_finalize_manifest`（错误处理器中调用，写失败 manifest 自身失败时不掩盖原错误、不递归，run 保持 unfinalized）；通用 except 中 `LineagePersistenceError` 直接 re-raise（不包装 RuntimeError）。

8. **cli.py**：新增 `create_fact_service(config, *, registry, output_root, symbol, source_mode, raw_dir)` 工厂；`cmd_build_value_facts` 改用工厂，official 失败时输出 "official source unavailable" + "no fallback" 并走 service 写 failed manifest；`cmd_verify_value_facts` 支持注入工厂（复用测试 db_path），输出同时显示 Build Run 和 Verification Run；`main` 新增 `service_factory` 参数（仅注入 registry/DuckDB/output_root，不替换 validator/transaction/manifest/退出码）。

9. **tests/fact_test_helpers.py（新增）**：`make_test_fact`（内部 `fact_id = build_fact_id(fact)`，忽略显式 fact_id 覆盖）、`make_verified_fact`、`make_canonical_fact`、`now_iso`。

10. **tests/test_m2_integration.py / test_m2_idempotency.py**：`_make_fact` 改为基于 `make_test_fact` 重建（canonical ID），`_SingleFactProvider`/MockFactProvider/SimpleProvider 改用 `build_fact_id`；所有硬编码 fact_id 断言改为读取 `f["fact_id"]`，不同事实用不同 `source_id` 区分 identity。

11. **新增四个测试文件**（共 51 用例）：test_fact_identity.py、test_fact_version_chain.py、test_fact_cli.py、test_fact_manifest_finalization.py。

## 验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| Ruff | `ruff check src tests` | All checks passed（16->0 错误，已全部修复） |
| compileall | `python -m compileall -q src tests` | OK |
| identity 导入 | `python -c "import ashare_research.facts.identity"` | OK |
| CLI 导入 | `python -c "import ashare_research.cli"` | OK |
| 全量测试 | `pytest -q` | 215 passed, 0 failed（原 164 + 新增 51） |
| 新增四文件 | `pytest test_fact_identity.py test_fact_version_chain.py test_fact_cli.py test_fact_manifest_finalization.py` | 51 passed |
| git diff --check | `git diff --check` | 仅 CRLF 警告，无空白错误 |
| output 跟踪 | `git ls-files "output/**"` | 空（output/ 未被跟踪） |

## 结果

- identity.py 已补全接口并待提交；
- Service + Repository 双边界强制 canonical fact_id；
- semantic payload 完整字段，source_hash/source_url/source_document/raw_unit/normalization_rule/verification_note 变化触发冲突，NaN==None 处理避免假冲突；
- VersionChainValidator 实现 5 项检查；
- PIT 重述切换测试通过（旧版本保留，重述日前返回 v1、重述日返回 v2）；
- CLI candidate 返回 2、official 返回 1 不回退、verify 按指定 run 复验；
- Manifest finalized 仅在写入成功后置 True，失败抛 LineagePersistenceError 且 run 保持 unfinalized；
- 派生事实改用 canonical ID，修复 symbol 硬编码与 period_end 缺失。

## 遗留问题

- 远程干净 clone 验收待提交并推送后执行（下一步）。

## 下一步建议

- 提交并推送后执行远程干净 clone 验收（compileall/identity import/CLI import/pytest/ruff/diff-check）。


## 最终文件变更

（待填）

## 最终Git状态

（待填）
