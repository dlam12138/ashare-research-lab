# Core company financial analysis

<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-09 -->
<!-- AI provenance: action=modified; model=GPT-5; agent=Codex; date=2026-10-10 -->

Goal: agent/goals/2026-10-09_core_financial_analysis.md.
Root works directly without DSH or delegation.
Before implementation inspected actual root/base HEAD and worktree status,
worktree registrations, stash, local/origin/live main, database hash,
root north-star v2, governance, latest three work records, README, metric
registries/engine, public PIT gate/repository, and unified research entry.
Fetched origin; main unchanged. Created isolated codex/core-financial-analysis
from ce76502. Captured protection baseline before implementation.

The user asks for core functionality. Existing financial replay is tied to
a fixed company/five-concept snapshot. This task enables the existing
financial model to analyze any eligible company in an explicitly selected
read-only fact database, across years and PIT dates, including earnings
quality and ROA that the fixed replay cannot supply.
New analytical capability reuses approved formulas and the public PIT gate;
historical M2/M3/M4 research dispositions remain frozen.

## 2026-10-10 实施与验证（同一任务续作）

实现：新增 `src/ashare_research/financial_analysis.py`（显式只读数据库核心）与
`src/ashare_research/tools/financial_analysis.py`（CLI）；`tools/research_entry.py`
注册 `financial` 命令；新增 `tests/test_financial_analysis.py` 与
`docs/core_financial_analysis_guide_v1.md`。无新增公式、评分、排名或建议；
只复用既有 12 个指标定义与公开 PIT 门禁。

边界落实：选择器在任何数据库访问前校验；数据库只读打开、单事务读取两个 PIT 视图；
只绑定年末年度流量与年末时点余额；精度边界为 2^53−1 以内有限整数、单位 `万元`、
`source_tier=reconciled_derived`，不兼容输入逐条显式排除；报告确定性、无绝对路径与
当前时间戳；`--output` 先渲染后独占创建，已存在目录以 `OUTPUT_PATH_EXISTS` 拒绝。

验证（工作树 `D:\量化分析-worktrees\量化分析-core-financial-analysis`，
Python `D:/量化分析-m4a2i/.venv/Scripts/python.exe`，`PYTHONPATH=src`）：

- `pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py
  tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py
  tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py
  tests/test_research_entry.py` → 166 passed in 70.19s（其中新测试 30 个）。
- `ruff check`（核心、CLI、research_entry、新测试）→ All checks passed。
- `git diff --check` → 退出码 0。
- `python tmp/core-financial-analysis/verify_protections.py` → PASS：64 个外部工作树、
  207 个保护文件哈希、stash 与本地/origin/live main 未变。
- 独立交叉验证：提交的 stage2g 快照临时库上，12 指标 × 3 年逐条与公开 `MetricEngine`
  独立 PIT 选择结果一致；PetroChina 快照 2023 年如实计算既有 7 个指标，其余 5 个
  以 `missing_input` 如实报告（扩展概念无覆盖面）。

限制与未决：调用者数据库来源与独立性不被本工具验证；父事实只在数据库保留范围内解析；
相邻年度差值与两时点重述对比分离，均为描述性；不授权发布、评分或研究执行。
任务结束后按合同创建单个本地提交；不推送、不合并、不自动进入下一阶段。
