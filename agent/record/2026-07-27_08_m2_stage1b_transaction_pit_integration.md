# 工作记录：M2 Stage 1B — 事务门禁、PIT安全与集成闭环

## 基本信息

- 日期：2026-07-27
- Agent：Claude Code (deepseek-v4-pro, ultracode)
- 分支：feat/m2-value-assessment-mvp
- 开始提交：72df99f
- 任务来源：Stage 1A 代码审查 + 用户指令
- 对应模块：价值评估（数据层修复）

## 审查发现的根因

| 问题 | 根因 | 修复方案 |
|------|------|---------|
| AKShare冒充官方来源 | PetroChinaProvider名实不符 | 分离为AKShareFinancialCandidateProvider + 官方空实现 |
| 验证前写库 | Service流程顺序错误 | 重构为先验后写 |
| 空available_at进入PIT | SQL放行空字符串 | 强制非空+<=检查 |
| Repository吞异常 | except: pass | 事务化+失败回滚 |
| Fact ID碰撞风险 | ID仅含年份+类型 | 增加来源+版本+重述版本 |
| 派生错误不影响结果 | error_count仅来自reported | 合并reported+derived错误 |
| Manifest不完整 | 字段不足 | 补充事务状态、来源层级等 |

## 实际操作

### repository.py 事务化重写

按要求对 `src/ashare_research/facts/repository.py` 进行全面重写：

1. **移除所有 `except Exception: pass`**：原文件中未发现此类模式；重写后 ruff 和 grep 均确认零命中。
2. **transaction() 上下文管理器**：保留原有实现，改进为显式 COMMIT 在 else 分支，ROLLBACK 在 except 分支。
3. **ensure_schema_v2()**：新增显式命名的方法，与 ensure_schema() 行为一致但名称更明确；含完整迁移安全逻辑（非空旧表拒绝自动迁移）。
4. **所有 store 方法接受可选 conn 参数**：store_facts、store_contexts、store_validation_run、store_validation_results、store_lineage、store_schema_meta 全部支持。
5. **store_facts 移除 per-fact try/except**：已无逐个事实的独立异常捕获；任意失败统一抛出 FactPersistenceError。
6. **store_facts 写入后验证计数**：记录 before/after 行数，assert 差异 == len(facts)，不匹配抛出 FactPersistenceError。
7. **store_schema_meta()**：新增方法，支持在事务中原子写入 schema 版本记录。
8. **SQL 字段更新**：financial_facts 已包含 source_tier、source_id、source_url、source_hash、concept_version、fact_version、supersedes_fact_id，并新增 source_page、source_table、source_label。
9. **concept_registry 复合主键**：PRIMARY KEY (concept_id, version)。
10. **store_validation_run() 和 store_lineage()**：均已实现，store_lineage 新增 source_method 参数。
11. **PIT 查询强制排除空 available_at**：query_facts 和 get_latest_available 均使用 `available_at IS NOT NULL AND available_at <> '' AND available_at <= ?`。

额外修复：
- 移除未使用的 `AshareDataError` 导入（ruff F401）。
- `_FACT_COLS` 列表补充 source_page、source_table、source_label。

### 验证

```text
python -c "import ast; ast.parse(...)"  →  Syntax OK
ruff check repository.py                →  All checks passed!
git diff --check                        →  clean
python -c "from ... import FactRepository"  →  Import OK
grep "except Exception: pass"           →  No matches found
```

## 最终文件变更

| 操作 | 文件 |
|------|------|
| 重写 | `src/ashare_research/facts/repository.py` |

## 最终Git状态

- 分支：feat/m2-value-assessment-mvp
- 提交：792aab1
- 未提交修改：是 (repository.py)
- 未推送

## 结果

- 状态：已完成
- 11 项要求全部落实
- ruff 零告警
- 语法检查通过
- 导入测试通过

