# M2 Stage 2A 工作记录：最小透明指标底座

## 启动基线

- Branch：`feat/m2-value-assessment-mvp`
- HEAD：`5b79028e6cbfff2c9540dd852aa75b0b084ce4c2`
- Worktree：clean
- `stash@{0}` 保持不动。
- Stage 1D-B：PASS；57 facts、最终 PIT 15、重列版本链可信。
- 默认数据库启动 SHA-256：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 开始前审查

- 仓库不存在 `AGENTS.md`。
- 既有 DerivationEngine 明确不实现 YoY、CAGR 或评分指标。
- 2022 归母净利润与 2023 三项 reconciled facts 存在 v2；2025 为
  `not_yet_reviewable`。
- 本阶段无需且不得修改 Fact Schema、FactIdentity、AsOfQuery、
  VersionChainValidator、Reconciliation、Derivation 或重列工具。

## 第一部分：独立 Metric 层

- 新建独立 `metrics` 包，包含版本化定义、Decimal-only 引擎、canonical
  SHA-256 身份和事务化 MetricRepository。
- 四个 canonical value 均以 ratio 表示，Decimal precision 28，
  量化 `0.000000000001`，ROUND_HALF_EVEN。
- Metric Schema 1.0 独立于 Fact Schema，value 使用
  `DECIMAL(38,12)`。
- Repository 支持 canonical 校验、语义冲突、幂等、严格版本链和批量
  事务回滚。
