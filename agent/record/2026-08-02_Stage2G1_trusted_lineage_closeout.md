# Stage 2G.1 Trusted-Lineage Closeout

## 任务

在 `feat/m2-value-assessment-mvp` 上从 `61e4f5e` 继续，按 `agent/goals/2026-08-01_m2_stage2g_dividend_correction_and_valuation_profile.md` 收口 Stage 2G 可信血缘。仅处理 Rule007、canonical Fact/PIT、证据股本时间线和风险语义；不启动 ROIC、评分、Web、市场机制、目标价或推荐。

## 实现记录

1. `petrochina_valuation_and_value_profile.py`
   - Rule007 raw Fact 从各自 source `extracted_values` 取值，event 仅交叉检查。
   - reconciled Fact 只在两个 raw Fact 的数值、币种、scope 一致时生成，并保留精确 `input_fact_ids`。
   - formal runner 要求显式 `fact_db`，只读使用 `FactRepository`、`AsOfQuery`、`FactService.query_as_of` 和现有 version chain；移除 fixture、手工可得日期和股本常量路径。
   - 估值事实保留 canonical ID、context、source、available_at、版本和 lineage；缺失概念不 fallback。
   - 股本 ledger/timeline 来自 source evidence；A/H 拆分缺失作为显式 gap，total ordinary shares 仍以证据为准。
   - 风险检查改为四态 `risk_veto_checks`，Identity/PIT 控制不再冒充 observed risk。
2. `tests/test_stage2g_dividend_correction_and_valuation.py`
   - 新增 source payload mutation、event/raw 分离、Rule007 精确双 raw 输入、share timeline mutation/removal/inconsistency、missing canonical input 检查；定向套件 13 passed。
3. `README.md`、Stage 2G.1 acceptance、reports
   - 标明 Milestone 1 已完成、Milestone 2 进行中、单一 PetroChina PIT value profile、9 个交易所证据缺口及明确未启动边界。

## Formal 输入/输出

- run：`stage2g_valuation_pit_20260801`
- canonical DB logical name：`net_profit.duckdb`
- DB SHA-256：`47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`
- schema `2.1`；Facts `201`；eligible `67`；used canonical IDs `33`
- market rows `1,351`；observations `8,106`
- Stage status：`pass_with_explicit_gaps`
- 两次 formal offline 输出逐文件 hash 一致
- 全仓 pytest：933 tests collected，分片全部通过
- 全仓 Ruff、compileall、import：PASS

## 保护项

默认 DB、stash、历史提交、Stage 1B.4/Stage 1 foundation baseline 未修改。正式输出没有将本地输入绝对路径写入 manifest；market registry 的缓存路径在 manifest 中只保留逻辑文件名。
