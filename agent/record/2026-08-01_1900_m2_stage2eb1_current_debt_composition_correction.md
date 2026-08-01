# 工作记录：M2 Stage 2E-B.1 财务安全债务口径纠正与验收重跑

## 基本信息

- 日期：2026-08-01
- Agent：Codex
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`7581c537255197534cade09a4b6959000d5f72cc`
- 任务来源：goal objective `M2 Stage 2E-B.1`
- 对应模块：价值评估 / 数据底座 / 工程治理

## 任务目标

纠正上一阶段把资产负债表整行“一年内到期的非流动负债”当作有息 current
portion 的口径。依据 2021—2025 年报附注双官方证据，只有能证明完整、互斥的有息组成年度才计算 gross debt、cash coverage 和 net debt；缺口年度显式 missing，不填零、不估算、不制造假 Fact 或假版本。资产负债率、Stage 2D-F 基线、默认数据库和治理边界必须保持不变。

## 范围与非目标

- 允许修改：financial-safety evidence/restatement、current-debt component Concept、专用派生规则、financial-safety engine/runner/tests、报告、验收文件和本阶段记录。
- 不修改：Fact Schema/Identity/PIT、Stage 2D-F 201 Fact/77 Result、ROE/ROA、Rule 001—005、默认 DB、stash、main、Tag/Release。
- 非目标：interest coverage、ROIC、scoring、阈值、评级、投资建议。

## 开始前状态与冻结

- HEAD 为 `7581c537255197534cade09a4b6959000d5f72cc`，分支为 `feat/m2-value-assessment-mvp`，worktree clean。
- stash 未修改：`protect pre-existing Stage 1B.4 record edit before Stage 1C`。
- Stage 2D-F foundation 需重建并验证 201 Fact / 77 Metric Result；Stage 2E-B 的 318 Fact / 102 Result 不作为不可变整体，只作为纠正前比较基线。
- 默认 DB、protected source hashes 和远端一致性在实施前后复核。

## 已读取的合同与实现

- `agent/agent.md`、`agent/record/README.md`、North Star review、`financial_safety_v1` machine contract/input contract、Stage 2E-A/B acceptance/report/record。
- 五份已提交 financial-safety 年度 evidence 与四份 restatement JSON；Rule006 additive contract；financial-safety definitions/engine/runner/tests；Fact/Metric repository、Identity、AsOfQuery 和 Stage 2D-F runner。
- 开始时实现仍把 statement aggregate 直接建成 `current_portion...` eligible Fact，`_debt_exclusivity()` 仍硬编码 `mutually_exclusive=true`；这些风险已在本记录后续章节纠正并保留为审计前态。

## 实施计划

1. 检查每年附注构成，区分可证明 direct/derived/missing，并保留原错误审计说明。
2. 新增最小 component Concept 与 `DERIVE_INTEREST_BEARING_CURRENT_PORTION_001 v1`，只由双源直接组件求和；不完整则不生成 eligible derived Fact。
3. 重建 evidence、restatement、runner、exclusivity/coverage/PIT/差异输出和测试。
4. 更新报告、验收文件和本记录；执行 targeted/full pytest、ruff、compileall、污染及保护门禁。
5. 按三次提交逐个 push，最终复核 local/origin/remote 与 clean worktree。

## 纠正决策记录

- statement aggregate 一律不再视为 canonical current portion；即使数值相同，也必须有附注组件或明确有息合计证明。
- B 方案的 derived Fact 必须保留每个组件的 input Fact lineage；缺一项即 missing，不能用零代替。
- exclusivity 结论必须由 committed evidence 计算，输出组件来源、页码、分类、租赁/债券/借款边界、排除项和 proof status；不能由布尔常量或自比较 sum 证明。
- 局部年度缺口不阻断资产负债率及其他有完整输入年度；官方冲突、重复计算或治理破坏才硬停止。

## 实际操作与验证

- 五个年度附注均证明三项有息 component（current long-term borrowings、current bonds、current lease liabilities）与一项排除项（current long-term payables）；company/exchange 数值一致，aggregate = 三项有息 component + 排除项，五年 proof status 均为 `proven`。
- 新增三项运行时 Concept 与 `DERIVE_INTEREST_BEARING_CURRENT_PORTION_001 v1`；Rule006 只对六项基础安全事实和三项 component 做双源对账。statement aggregate 保留在 evidence/审计输出，但没有 eligible canonical Fact。
- FY2023 的 current lease component comparative 7,773→7,780（人民币百万元）自然生成 current-portion derived v1 `11757400`→v2 `11758100`；FY2022 aggregate 变化不生成 aggregate Fact version。
- 离线 runner preflight 通过：Fact `contexts=11/facts=354/raw=232/reconciled=122/fact_links=58/lineage=354/audit=354`；`R=4`，canonical changed keys 为 FY2022 total liabilities、FY2023 total liabilities/full lease/current lease component。
- 财务安全 Metric counts 保持 `4/25/25/0/5/116/20/20`；组合 counts 保持 `16/102/98/4/22/280/80/76`。PIT latest `0/16/32/48/64/80`，computed `0/12/28/44/60/76`，insufficient `0/4/4/4/4/4`。
- targeted test `tests/test_official_financial_safety_vertical_slice.py -q`：5 passed；无 interest coverage/ROIC/score 输出。正式 runner 仍离线，不访问 network/PDF/cache/default DB。

## 当前状态

- 状态：`completed`
- 口径纠正、正式 run-scoped runner、full pytest、ruff、compileall、diff/pollution、protected blob、default DB、stash 及 local/origin/remote 门禁均已完成。

## 最终交付与门禁

- 正式输出位于 `C:\m2e1\value_assessment\601857.SH\financial_safety_vertical_slice\2021_2025\e1`，manifest=`passed`；重跑同一 run id 仍幂等返回 `passed`。
- 最终 runner：`354/232/122/58` Fact counts；statement aggregate eligible canonical Fact count=`0`；五年 current-portion proof=`proven`；financial-safety `4/25/25/0/5/116/20/20`；combined `16/102/98/4/22/280/80/76`。
- 全量 pytest：`911 passed, 2 warnings`；warning 为既有 `tests/test_quality.py` 日期解析测试，不是本阶段失败。ruff、compileall、git diff --check、污染检查和六项 protected artifact tests 均通过。
- default DB SHA 前后均为 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；stash 原样保留；HEAD、origin、remote 均为 `6c0db0d7bf8f014cb075fa02f435703c3c689498`。
- 已逐个 push 实现/证据、测试、文档及 append-only roadmap guard 提交；未 merge main、未建 Tag/Release，未入库 DB/PDF/PNG。
