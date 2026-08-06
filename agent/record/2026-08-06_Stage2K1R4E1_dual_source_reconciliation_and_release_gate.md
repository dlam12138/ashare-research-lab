# 工作记录：M2 Stage 2K.1R4E.1 — 双源行情重验、PB 血缘与 Release Gate 收口

Status: `completed`
Closeout verdict: `CONDITIONAL PASS`
Pinned AKShare object: `AKSHARE_PINNED_OBJECT_RECOVERY = NOT_FOUND`
R4E.1 decision: `PIT_VALUATION_SERIES_GAPS_REMAIN`（formal exit 1）

## 基本信息

- 日期：2026-08-06
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`a487c6f96fae19eb2bb8c3b067388afced5b9805`（== 预期基线）
- 任务来源：用户指令 M2 Stage 2K.1R4E.1
- 对应模块：价值评估（双源行情重验 / PB 血缘 / Release Gate）

## 任务目标

收紧 R4E 候选序列的市场双源证明、PB 输入血缘、CLI 退出码与 artifact manifest；
竣工后判断是否允许进入历史分位预检。不计算分位、不更新评分、不重做 R4D、不启动 M3。

## 范围

- 新增 `market_reconciliation.py`；修改 `financial_state.py`、CLI、
  `valuation_series.py`、`series_contract.py`、`fixtures.py`、`artifact_manifest.py`。
- 配置：formula registry 增加 `market_reconciliation_contract`（close_tolerance=0.01）。
- 新增测试文件；新增 reports（decision / manifest v2）；候选 v2 系列仅在 fixtures 合成路径演示。
- 维护性再生成本轮副作用：`reports/m2_stage2k1r4c1_artifact_manifest.json`（见 决策记录 D4）。

## 非目标

- 不计算/不发布历史分位；不更新 shadow/sensitivity；不创建生产 Metric Result。
- 不重做 R4D；不启动 M3；不采集 peer；不写默认 DB。
- 不在本阶段网络刷新或新建一套 market registry。
- 不覆盖 R4E v1 工件；不删除 v1 manifest。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `a487c6f`；本地 == origin (0 ahead / 262 behind)。
- 受保护项：`acceptance/m2_stage2i2r_*.md` 编辑、`AGENTS.md`、`agent/goals/`、
  `stash@{0}`、默认 DB `data/research.duckdb`（SHA-256 `4a71d3c7…`）。
- market registry（events/market_data_snapshot_registry.json）：
  - baostock `defd0b95…` 本地存在（tmp/market_cache/baostock/）；
  - akshare `203ddfd7…` 本地**缺失**（全库搜索无匹配 SHA，含 data/ 、runs/、tmp/、
    clean-clone、外部候选目录）。
- 基线：354 Fact / 102 Metric Result / 16 definitions；R4E 42 测试；全量 1475 passed。

## 实施计划

1. 建工作记录。
2. 配置：formula registry 增加 market_reconciliation_contract（close_tolerance=0.01）。
3. series_contract.py：暴露 reconciliation 合同加载与 close_tolerance。
4. 新增 market_reconciliation.py。
5. 修改 financial_state.py（PB 完整输入血缘 + 确定性股本选择 + fail-closed）。
6. 修改 valuation_series.py（observation 绑定 market_reconciliation_digest）。
7. 重写 CLI（exit codes + formal A/B/C + 结构化错误 + manifest v2）。
8. artifact_manifest.py：允许 m2_stage2k1r4e1_artifact_manifest_v2。
9. fixtures：增加 load_fixture_dual_market 与 market_reconciliation_digest。
10. 新增测试文件。
11. 全量测试 + ruff + compileall + git diff --check。
12. fixtures CLI → ALLOWED / exit 0；formal CLI（真实缓存）→ GAPS_REMAIN / exit 1。
13. 写 acceptance 与本记录结果。

## 决策记录

### D1：close 容差放入版本化 formula-registry 合同，不散落硬编码

- 决策内容：在 `config/pit_valuation_series_formula_registry_v1.json` 中新增
  `market_reconciliation_contract`，冻结 `close_tolerance = "0.01"`（CNY/share）、
  providers、required_columns、fail_closed_status。`series_contract.py` 暴露
  `load_market_reconciliation_contract()` 与 `close_tolerance_decimal()`。
- 采用原因：容差必须来自版本化合同（任务要求），且 formula registry 已是冻结的
  数值/时间/身份合同宿主，新增一节为纯增量，不改既有键。
- 替代方案：新建独立 config 文件。
- 未采用原因：会导致 contract 验证多一个来源，且 formula registry 已是自然宿主。
- 潜在风险：改动 formula registry 会改变其 digest（无测试硬编码该 digest，安全）。

### D2：两对象逐日 Decimal 对账 + 独立 digest，绝不信任 registry 预写的 pass

- 决策内容：`market_reconciliation.py` 独立读每个对象做全字段校验，再按 trade_date
  exact align 逐日比较 close（canonical Decimal），并验证实际结果与 registry 声明
  （common_trade_days / close_max_abs_difference / within-tolerance）一致。
  `reconciliation_digest` 绑定两个 SHA、行数、日期范围、容差、日期集摘要、逐日
  比较摘要、ledger digest、合同版本。
- 采用原因：任务指出的根缺陷是"只查 SHA/存在即 pass"；digest 必须覆盖全部关键字段。
- 替代方案：仅对 registry 预写字段做摘要。
- 未采用原因：`reconciliation_digest` 需随重验结果变化，不能只绑定预写字段。
- 潜在风险：无（纯增量模块）。

### D3：AKShare 对象按精确 SHA 恢复，缺失则保持 GAPS_REMAIN

- 决策内容：全库（tmp/market_cache、Stage 2G/2G.2/R4E run 目录、data/、runs/、
  clean-clone、外部候选目录）搜索 `203ddfd7…` 内容对象，重算 SHA 仅允许完全相等
  的恢复。结果 NOT_FOUND → formal 决策保持 GAPS_REMAIN、exit 1、不发布候选 v2。
- 采用原因：fail-closed 合同；不得用相似文件改名、不得用新下载数据冒充、不得改 registry。
- 替代方案：网络重抓 akshare；仅用 baostock 单源并宣称 pass。
- 未采用原因：respect fail-closed；本阶段禁止网络刷新与新建 registry。
- 潜在风险：正式 dual-source 重验与真实候选 v2 被阻塞，需后续独立恢复快照。

### D4：再生 R4C1 manifest（副作用）

- 决策内容：R4C1 v2 manifest 将 `src/ashare_research/scoring/artifact_manifest.py`
  列为被钉文件；本轮为支持 R4E.1 对该文件做了增量修改，故再生该 manifest 的
  sha256/byte_size（仅 2 行改动，其余文件与元数据不变，indent=2 + LF 保持原格式）。
- 采用原因：R4C1 manifest 是功能性校验合同，必须保持可验证；不更新会导致
  R4C/R4C1/R4A 保护测试失败。
- 替代方案：不改 artifact_manifest.py（不可行，R4E.1 需要新 schema）。
- 未采用原因：R4E.1 必须新增 schema。
- 潜在风险：无（最小 2 行 diff，历史文件列表与元数据保留）。

## 实际操作

1. 核验 Git（HEAD `a487c6f`，受保护项未动）；读 R4E 记录、series_contract、
   financial_state、valuation_series、CLI、temporal_join、series_validation、
   fixtures、scoring/artifact_manifest + content_digest、formula_registry、ttm、
   market registry。
2. 全库搜索 akshare `203ddfd7…` 内容对象 → NOT_FOUND（无任何文件 SHA 匹配）。
3. 建工作记录。
4. 配置 formula registry 增加 market_reconciliation_contract（JSON 校验 OK）。
5. series_contract.py 增加 close_tolerance_decimal()。
6. 新增 market_reconciliation.py（对象校验 / 逐日对账 / ledger / digest / report）。
7. financial_state.py 重写 PB 血缘（_select_period_end_share + 完整 input_fact 绑定）。
8. valuation_series.py 绑定 market_reconciliation_digest。
9. fixtures.py 增加 market_reconciliation_digest 与 load_fixture_dual_market。
10. 重写 CLI（decision_to_exit_code + formal A/B/C + 结构化错误 + manifest v2）。
11. artifact_manifest.py 增加 r4e1 schema。
12. 新增测试文件（34 测试）。
13. ruff --fix 后手工修复剩余（N814/E501/SIM102/SIM108），All checks passed。
14. 修复 _validate_against_registry 的 Decimal 字符串比较 bug（"0" vs "0.0"）。
15. 修复 CLI formal ALLOWED 未写 mismatch_ledger 文件（manifest 列出缺失文件）。
16. 再生 R4C1 manifest（2 行 diff，修复 3 个 R4C/R4C1/R4A 保护测试）。
17. 全量测试 1509 passed；ruff/compileall/git diff --check 通过。
18. fixtures CLI → ALLOWED/exit 0；formal CLI（真实缓存）→ GAPS_REMAIN/exit 1。
19. 写 real decision 到 reports/ + manifest v2 验证 pass。
20. 写 acceptance 与本记录。

## 数据与方法说明

- 市场：events/market_data_snapshot_registry.json（baostock `defd0b95…` 本地存在；
  akshare `203ddfd7…` 本地缺失）。close 不复权、A 股、CNY/share。
- 容差：formula registry `market_reconciliation_contract` close_tolerance=0.01 CNY/share。
- Decimal：`Decimal(str(source))`；`float(close)` 与 `Decimal(binary_float)` 禁止；
  中间值不提前 quantize；ratio 无量纲。
- PB 股本选择：同 period_end 可见版本中取 effective_from 最新；同 effective_from 用
  supersession（supersedes_fact_id 指向兄弟可见版本）消歧；无法唯一选择 fail-closed。
- 未来数据泄漏：无——股本仅在 equity effective_from 时点可见才参与，否则 PB 不提前生效。
- 身份：PB state_id 与 observation_id 因完整血缘/reconciliation digest 变化（预期）。

## 验证

- R4E 42 tests：passed。
- R4E.1 34 tests：passed。
- R4D/R4D.1/R4D.1a/R4D.1b 保护测试 106：passed。
- 全量离线套件：**1509 passed, 2 既有 warning**。
- ruff check（全部改动文件）：All checks passed。
- compileall：pass；git diff --check：pass。
- fixtures CLI：decision ALLOWED，exit 0，manifest v2 pass（9 files），dual oracle
  identical，工程覆盖 READY/READY（合成双源，仅 CI 证据），identity migration
  （PB/obs id 变、ratio/status 不变）。fixture ALLOWED 结果仅作合成工程证据，
  不替代真实数据门禁。
- formal CLI（真实缓存，akshare 缺失）：decision GAPS_REMAIN，exit 1，结构化 gap 错误，
  不发布候选 v2 → 正式候选覆盖 **NOT RELEASED / BLOCKED BY SECONDARY MARKET OBJECT**。
- real reports/m2_stage2k1r4e1_decision.json + manifest v2 验证 pass。
- 默认 DB SHA-256 不变（`4a71d3c7…`）；stash 保留；受保护项未动。

## 结果

- 完成：market_reconciliation 模块；PB 完整输入血缘；CLI fail-closed 退出码 +
  结构化错误 + formal A/B/C；manifest v2 schema；fixtures 双源合成路径（ALLOWED）；34 测试。
- 条件通过：真实候选 v2 / reconciliation / identity 报告因 akshare 缺失而 BLOCKED；
  gate 诚实保持 `PIT_VALUATION_SERIES_GAPS_REMAIN`（formal exit 1）。
- 未生成分位；未改 shadow/sensitivity；未创建生产 Metric Result；未写默认 DB；
  未采集 peer；未启动 M3。

## 遗留问题

- akshare 精确内容对象 `203ddfd7…` 本地缺失 → 正式双源重验无法本地完成；需单独
  恢复该快照后重跑 formal 才能升级 gate。
- real candidate v2 / reconciliation / identity migration 报告待 akshare 恢复后生成。

## 下一步建议

- 独立数据阶段恢复/重采双源市场快照（含 akshare `203ddfd7…`），之后重跑 formal；
  若逐日重验通过，gate 升级为 `..._ALLOWED`，进入历史估值分位预检。

## 最终文件变更

新增：
- `src/ashare_research/pit_valuation/market_reconciliation.py`
- `tests/test_m2_stage2k1r4e1_market_reconciliation_and_release_gate.py`
- `reports/m2_stage2k1r4e1_decision.json`
- `reports/m2_stage2k1r4e1_artifact_manifest.json`
- `acceptance/m2_stage2k1r4e1_dual_source_reconciliation_and_release_gate.md`
- `agent/record/2026-08-06_Stage2K1R4E1_dual_source_reconciliation_and_release_gate.md`

修改：
- `config/pit_valuation_series_formula_registry_v1.json`（market_reconciliation_contract）
- `src/ashare_research/pit_valuation/financial_state.py`
- `src/ashare_research/pit_valuation/valuation_series.py`
- `src/ashare_research/pit_valuation/series_contract.py`
- `src/ashare_research/pit_valuation/fixtures.py`
- `src/ashare_research/scoring/artifact_manifest.py`
- `src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py`
- `reports/m2_stage2k1r4c1_artifact_manifest.json`（再生 2 行，见 D4）

未改动：v1 methodology、market_observation_set.py、旧 close-percentile 工件、默认 DB。
受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
`stash@{0}`。

## 最终 Git 状态

- 分支 `feat/m2-value-assessment-mvp`；开始 HEAD `a487c6f`。
- 未提交（本轮产出）；未推送（遵循"未经明确要求不得推送"）。
- 受保护项未纳入提交；tmp/r4e1-* / tmp/r4e1-test-* 演示目录在 gitignore 内。