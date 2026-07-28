# 工作记录：M2 Stage 1B.4 — 最终身份契约、版本链、CLI与门禁收口

## 基本信息

- 日期：2026-07-28
- Agent：Claude Code
- 分支：feat/m2-value-assessment-mvp
- 开始提交：f578629
- 对应模块：价值评估（数据层最终收口）

## 任务目标

1. 新建 `src/ashare_research/facts/identity.py`：
   - FactIdentity 冻结 dataclass
   - canonical_payload / canonical_key / fact_id 方法
   - build_fact_id / fact_identity_from_dict 辅助函数
   - fact_semantic_payload / facts_semantically_equal / diff_fact_semantic_payloads 语义比较函数
2. 更新 repository.py：导入并使用 facts_semantically_equal 替代内联比较
3. 更新 akshare_financial.py：删除 _make_fact_id，改用 build_fact_id；先构建 dict 再计算 ID

## 实际操作

### 1. 创建 identity.py

新建 `src/ashare_research/facts/identity.py`，包含：

- **FactIdentity** 冻结 dataclass（9 个字段）：symbol, concept_id, concept_version, context_id, source_id, fact_version (int), restatement_version, derivation_definition_id, derivation_version。全部有合理默认值。
- **canonical_payload()** → dict with sorted keys
- **canonical_key()** → JSON string with sort_keys=True, separators=(',', ':')
- **fact_id()** → SHA-256 hex of canonical_key（完整 64 字符）
- **build_fact_id(fact)** → 从 dict 或 dataclass 提取身份字段，构建 FactIdentity，返回 fact_id()
- **fact_identity_from_dict(d)** → 从 dict 提取 FactIdentity
- **_identity_from_fact(fact)** → 内部辅助：同时支持 dict 和对象属性访问
- **fact_semantic_payload(fact)** → 返回所有持久化业务字段（排除 fact_id, created_at, run_id, validation_run_id, updated_at, ingested_at）
- **facts_semantically_equal(existing, incoming)** → 比较语义 payload 的排序 JSON，input_fact_ids 列表规范化
- **diff_fact_semantic_payloads(existing, incoming)** → 返回变更字段字典

### 2. 更新 repository.py

- 删除模块级 `_FACT_SEMANTIC_FIELDS` 列表
- 删除 `_facts_semantically_equal` 静态方法
- 从 identity 导入 `facts_semantically_equal`
- 将 `self._facts_semantically_equal(existing, fact)` 改为 `facts_semantically_equal(existing, fact)`
- 移除无用的 `import json`（不再有内联 JSON 比较）

### 3. 更新 akshare_financial.py

- 删除 `import hashlib`（不再直接使用）
- 删除私有函数 `_make_fact_id`
- 添加 `from ashare_research.facts.identity import build_fact_id`
- `_fetch_report_facts`：先构建 fact dict 全部字段，然后 `fact["fact_id"] = build_fact_id(fact)` 赋值
- `get_dividends`：同样先构建 dict，再计算 ID
- 移除末尾多余空行

## 决策记录

1. **fact_id 从 16 字符截断改为完整 64 字符 SHA-256 hex**：任务明确要求 sha256 hex，不再截断。这是开发分支，不影响生产数据。
2. **事实比较字段集扩大**：原 `_FACT_SEMANTIC_FIELDS` 仅比较 15 个字段，新 `fact_semantic_payload` 含 35+ 个字段。更严格的语义比较意味着以前被当作"相同"但字段不同的记录现在会正确触发冲突。
3. **build_fact_id 支持 dict 和 dataclass**：通过 `_identity_from_fact` 统一处理。

## 验证

| 命令 | 结果 |
|------|------|
| `ruff check identity.py repository.py akshare_financial.py` | 首次 3 错误（SIM108, E731, F401），修复后全部通过 |
| `pytest tests/test_m2_integration.py -v` | 30 通过，0 失败 |
| `python -c "import identity"` | 全部导入正常 |
| 功能烟测：canonical_payload 排序、fact_id 确定性、语义比较忽略元数据、diff 正确 | 全部通过 |
| `git diff --check` | 无空白问题 |

## 结果

- 已完成：identity.py 新建、repository.py 重构、akshare_financial.py 重构
- 部分完成：无
- 条件通过：无

## 最终文件变更

| 文件 | 操作 |
|------|------|
| `src/ashare_research/facts/identity.py` | 新增 |
| `src/ashare_research/facts/repository.py` | 修改（删除内联比较，导入外部函数） |
| `src/ashare_research/fact_sources/candidates/akshare_financial.py` | 修改（删除 _make_fact_id，使用 build_fact_id） |

## 最终Git状态

- 当前分支：feat/m2-value-assessment-mvp
- 当前提交：f578629
- 未提交修改：是（3 文件）
- 未推送：是

## 下一步建议

- 考虑在 repository.py 中实际使用 build_fact_id 进行 ID 生成（当前无此需求，ID 由调用方生成）
- 考虑将 identity.py 中的语义比较集成到验证管线
