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

## 官方后续报告重新核验

- 从 2022—2025 已注册 bundle 的正式 URL 重新下载四组 company /
  exchange PDF；8 份本地文件的 SHA-256、字节数和页数均与已提交
  bundle 一致。
- 公司与交易所副本分别目视核验后续年度合并利润表、合并现金流量表；
  byte-identical 的 2023、2024 双路径另以哈希相同证明内容相同。
- 每个 Concept 均完成两遍读数复核；PDF、截图和临时渲染未进入 Git。
- 实际结论：
  - 2022 年报复核 2021：三项均 unchanged；
  - 2023 年报复核 2022：营业收入、经营现金流 unchanged，归母净利润
    `149,375 → 148,738`；
  - 2024 年报复核 2023：营业收入 `3,011,012 → 3,012,812`、归母净利润
    `161,144 → 161,414`、经营现金流 `456,596 → 456,847`；
  - 2025 年报复核 2024：三项均 unchanged；
  - 2025：`not_yet_reviewable`。
- 2023 年报印刷第 6 页明确披露 2022 比较数据因企业会计准则解释第
  16 号相关递延所得税规定追溯调整；2024 年报印刷第 113 页明确披露
  同一控制下合并中国石油集团电能有限公司。未将未知原因写成会计差错。
- 实际变化的 Concept-Year 数量 `R = 4`。

## 重列证据与离线整合

- 新增四个 `restatement_evidence_v1` 注册文件；原值、后续比较值、
  双来源页面与文档元数据均由证据文件承载。
- 新增薄工具 `official_fact_restatement_integration.py`：
  - 复用 Stage 1D-A preflight、annual builders、Engine、Service、
    Repository、AsOfQuery；
  - 不包含网络或 PDF 依赖；
  - 在内存中验证所有 changed pair matched 后才创建 run-scoped DuckDB；
  - 仅 changed 数据创建 company/exchange/reconciled v2；
  - `source_id` 保持目标年度 v1 逻辑来源身份，后续报告只进入证据字段。
- 真实离线 run：
  `restatement_601857_SH_2021_2025_20260730_110128_441181`，状态
  `passed`，`transaction_committed = true`。
- 动态计数：Contexts 5、company 19、exchange 19、raw 38、
  reconciled 19、facts 57、eligible 19、ineligible 38、version links
  12、Audit 57、Lineage 57。
- 四个 PIT 切换均在较晚的 exchange 公告日发生：
  - 2022 归母净利润：2024-03-25 v1，2024-03-26 v2；
  - 2023 三项：2025-03-30 v1，2025-03-31 v2。
- 四个 `compare_versions.changed = true`；最终 2026-03-30 PIT snapshot
  为 15 个 eligible reconciled facts。

## 当前测试

- Restatement evidence/integration + Service/version-chain targeted：
  `30 passed`。
- Ruff 0.13.2：新增工具与测试通过。

## 待完成

- 正式报告、全量门禁、后续两个提交逐次推送与远程核验。
