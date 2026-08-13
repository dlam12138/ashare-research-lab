# 工作记录：M2 Stage 1C-A.2.1 Blocker Fix Checkpoint

## 基本信息

- 日期：2026-07-29
- 分支：`feat/m2-value-assessment-mvp`
- 起始提交：`e3888a3`
- 范围：Schema 2.1 迁移、Reconciliation 证据绑定、StrEnum 与对应测试
- Stage 1C-B：未开始

## 修复内容

1. `financial_facts` Schema 版本由 2.0 升为 2.1。
2. `ensure_schema()` 对真实旧 2.0 `fact_lineage` 执行事务化增量迁移：
   - 增加 `role VARCHAR DEFAULT ''`；
   - 增加 `reconciliation_rule_id VARCHAR DEFAULT ''`；
   - 增加 `reconciliation_rule_version VARCHAR DEFAULT ''`；
   - 三列成功且结构复核通过后，才将 `fact_schema_meta` 更新为 2.1；
   - 任一步异常均回滚整个迁移。
3. 已有 2.1 数据库会核验上述物理列；重复调用 `ensure_schema()` 不重复迁移。
4. Reconciliation 写入前严格校验：
   - `output_fact.input_fact_ids` 必须恰好等于实际 company/exchange 输入 ID；
   - `derived_from` 必须与 `input_fact_ids` 一致；
   - Engine result 的 company/exchange ID 必须与实际来源角色一致；
   - 三条 lineage 的 role/fact_id 必须对应实际 company、exchange、output；
   - output lineage parents 必须与 output `input_fact_ids` 一致。
5. 任一证据链错误产生 `FACT_RECON_INPUT_001` 和
   `ReconciliationValidationError`，并在事务开启前终止。
6. `ReconciliationStatus` 改用 Python 3.11 `enum.StrEnum`，枚举值和业务语义不变。
7. `FactService` 与 lineage manifest 的事实 Schema 版本同步为 2.1。

## 测试设计

- 旧库 fixture 直接复制 `86696b8` 的相关 2.0 DuckDB DDL，不调用当前建表 SQL，
  预置 1 条 `financial_facts`、1 条 `fact_contexts`、1 条旧结构
  `fact_lineage`，以及 `fact_schema_meta = 2.0`。
- 迁移测试覆盖新列、安全默认值、旧事实/Context/lineage 保留、幂等执行，以及
  metadata 写入失败后 DDL 与版本元数据整体回滚。
- 恶意 Engine/lineage 测试覆盖错误输入 ID、`derived_from` 不一致、错误 parents、
  role 对调、缺少输入和额外第三输入；均断言事务未进入且事实/lineage 零写入。
- StrEnum 测试覆盖 `str()`、字符串相等和 JSON 序列化。

## 范围约束

- 未下载或录入真实报告与财务数据；
- 未修改 AKShare；
- 未开始 Stage 1C-B；
- 未 pop 或修改 stash；
- 未增加新的通用基础设施。

## 提交前门禁

- `ruff check src tests`：All checks passed，exit 0；
- `python -m compileall -q src tests`：exit 0；
- CLI / reconciliation models / reconciliation service import：OK，exit 0；
- `pytest -q`：322 passed，2 个既有 pandas 日期解析 warning，exit 0；
- `git diff --check`：exit 0。
