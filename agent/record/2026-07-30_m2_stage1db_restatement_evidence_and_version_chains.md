# M2 Stage 1D-B 工作记录：Restatement Evidence And Version Chains

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`9608e64fd3af5ffdb2012c5ca6b2558a9d75399e`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持不动
- 默认 `data/research.duckdb` 启动 SHA-256：`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 开始前实现审查

- 项目北极星保持“官方事实按真实公告日期生效、保留血缘、不输出买卖建议”的边界。
- 仓库中不存在 `AGENTS.md`。
- `FactIdentity` 实际包含 `source_id`、`fact_version`、`restatement_version`。
- `VersionChainValidator` 实际要求 predecessor 存在、版本严格 `+1`、stable identity 一致、`available_at` / `announcement_date` 不倒退且无循环。
- Validator 的 stable identity 实际为 `symbol`、`concept_id`、`concept_version`、`context_id`、`source_id`、`derivation_definition_id`、`derivation_version`；`source_tier` 不在该列表，因此 Service 需在不修改 Validator 的前提下额外守住官方输入角色稳定性。
- Engine output 实际继承输入的 `fact_version` 与 `restatement_version`，并将 `supersedes_fact_id` 留空。
- Service 启动时只对高版本 output 调用 repository-aware validator，尚未对高版本 company/exchange input 执行该验证。
- Stage 1D-A 的五个 Context、45 facts、PIT `0/3/6/9/12/15` 基线已核对。

## 第一部分合同修正

- 仅修改 `reconciliation/service.py`。
- 高版本 company/exchange inputs 在 Engine 和事务之前通过现有 `VersionChainValidator`。
- Service 额外验证高版本原始事实的 `source_tier` 不跨链改变。
- 新增显式关键字参数 `output_supersedes_fact_id`：
  - output v1 必须为空；
  - output v2+ 必须为完整 64 位小写 Fact ID；
  - 写入 output 后重新计算 canonical Fact ID；
  - 随后执行 FactValidator、VersionChainValidator、provenance 和 lineage 检查。
- Engine、FactIdentity、VersionChainValidator、Schema 与 PIT 均不修改。

## 第一部分测试

- 新增合法 company/exchange v2 input chain、缺失 predecessor、版本非严格 `+1`、stable `source_id` 改变、日期倒退、output supersedes 缺失/不存在/错误 Concept、合法 reconciled v2、canonical output ID、v1 参数拒绝、重复运行事实幂等等测试。
- 任一失败路径均断言事实和 lineage 零新增。
- Service/version-chain + 既有 Reconciliation targeted pytest：`97 passed in 10.20s`。
- Ruff 0.13.2：通过。

## 待完成

- 四组双官方 PDF 重新下载、哈希与目视双遍复核。
- 四个 restatement evidence、整合工具、真实 PIT 切换验收。
- 正式报告、全量门禁、三提交逐次推送与远程核验。
