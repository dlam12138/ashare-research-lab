# 工作记录：M2 Stage 2D-F ROA 透明 Metric（2026-08-01）

## 目标与边界

从 `feat/m2-value-assessment-mvp@ac4b3af` 执行 Stage 2D-F，完成 2021—2025
中国石油 consolidated ROA 的透明计算、PIT 回放和重列传播。不开启 ROIC、评分、投资建议，
不 merge main，不建 Tag/Release。

## 启动冻结

- 分支：`feat/m2-value-assessment-mvp`；起始 HEAD：`ac4b3af6bc4d1493ebedf8533d88a6c567ef0e43`。
- 启动时 worktree clean，local/origin 一致；stash 只有既有
  `protect pre-existing Stage 1B.4 record edit before Stage 1C`，未动。
- 未发现仓库内 `AGENTS.md`；按北极星、`agent/agent.md`、Stage 2D-C 合同与既有记录执行。
- 冻结默认 `data/research.duckdb` SHA-256：
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。
- Stage 2D-D 70 Result ID 集：
  `bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0`；
  旧 63 ID 集：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
  旧 63 语义：`e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053`。
- Stage 2D-B 180 Fact ID 集：
  `2bd5b2d20ec7992a07b66238fff86ab0fb91f881c5f7cd7f0b5d68b5bde6946c`；
  Stage 2C 132 Fact ID 集：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`。

## 实施

1. 读取北极星、Stage 2D-B/C/D/E 报告与 runner、Fact/Metric Engine、Identity、Repository、
   AsOfQuery 和既有测试；确认方法论 JSON 保持冻结。
2. 在 `CapitalReturnMetricDefinitionRegistry` 增加唯一 ROA 定义；ROE 定义、ID、文本和既有
   Stage 2D-D runner view 保持兼容。ROA view 通过显式 `include_roa=True` 进入新 runner。
3. 在 Metric Engine 复用现有角色绑定和 Decimal 分支，加入 average-assets 公式及零/负分母状态；
   对旧公式路径不做重构。
4. 新增 `official_roa_metric_extension.py`：调用 Stage 2D-E foundation，验证 201 Fact，
   重新构建并冻结 Stage 2D-D 70 Result，再通过 `AsOfQuery.get_latest_available()` 回放 ROA。
5. 新增边界与集成测试；生产代码不硬编码验收 ROA 数值，验收从 foundation Fact 计算。

## 实测证据

- Stage 2D-F runner status=`passed`：201 Fact / 67 eligible / PIT 52 / 45 links。
- ROA counts=`1/7/7/2/21/5`（definition/result_versions/computed/links/lineage/latest）。
- Combined counts=`12/77/73/4/17/164/60/56`。
- Metric PIT latest=`0/12/24/36/48/60`，computed=`0/8/20/32/44/56`，
  insufficient=`0/4/4/4/4/4`。
- 最新 ROA：2021 `0.045958140492`、2022 `0.063149706787`、2023 `0.066506160423`、
  2024 `0.066668674318`、2025 `0.061639226063`。
- 两条 Metric 重列链和 FY2024 直接使用 2023 assets v2 均通过；FY2025 状态通过。
- targeted `tests/test_official_roa_metric_extension.py`：13 passed。
- `ruff check src tests`：通过；`compileall -q src tests`：通过；`git diff --check`：通过。
- targeted ROA/ROE/net-profit/protected tests：通过；full pytest：`899 passed, 2 warnings`。
- 两个 warning 为既有 `test_quality.py` 日期解析 warning，与本阶段无关。

## 最终门禁记录

最终全量 pytest、污染检查、diff check、stash/default DB/保护文件哈希均通过；
run-scoped 产物未进入仓库，随后按三提交计划逐个 push。
