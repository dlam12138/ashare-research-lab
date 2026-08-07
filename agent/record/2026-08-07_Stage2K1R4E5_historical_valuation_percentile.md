# 工作记录：M2 Stage 2K.1R4E.5 — Historical Valuation Percentile Preflight and Non-Production Percentile Profile

Status: completed
Closeout verdict: PASS — CI CONFIRMED
Remote CI: GREEN (run 31151600368 on push 6a088e7)
Decision:
PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED
Scoring integration: NOT AUTHORIZED
Next-stage implementation: NOT STARTED

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`4e4caeb`（R4E.4 CI 全绿后的 tip）
- 任务来源：用户指令 M2 Stage 2K.1R4E.5
- 对应模块：价值评估（historical valuation percentile preflight）

## 任务目标

对 PE_A_TTM / PB_A_MRQ / PS_A_TTM 三指标，截至 as-of=2026-07-31，计算 3-year 与
5-year 的正式非生产历史估值 percentile（MIDRANK_EMPIRICAL_PERCENTILE），共 6 个
observations。冻结 percentile 方法合同、构建 3y/5y eligible samples、Python/DuckDB
独立 oracle、PIT/identity/tie/boundary audit，发布 non-production percentile profile。
本轮不接 scoring、不改 valuation shadow、不创建生产 Metric Result、不做同行、不启动 M3。

## 范围

- 新增 `config/pit_valuation_percentile_contract_v1.json`（方法合同）。
- 新增 `docs/historical_valuation_percentile_methodology.md`（方法学）。
- 新增 `src/ashare_research/pit_valuation/historical_percentile.py`（核心）。
- 新增 `src/ashare_research/pit_valuation/percentile_oracle.py`（DuckDB 独立 oracle）。
- 新增 `src/ashare_research/tools/m2_stage2k1r4e5_historical_percentile.py`（薄 CLI）。
- `artifact_manifest.py` 注册 `m2_stage2k1r4e5_artifact_manifest_v2`。
- 发布 6 个 percentile profile + sample ledger + method audit + dual oracle + audit samples
  + decision + R4E.5 manifest。
- 新增测试、acceptance、本工作记录。

## 非目标

- 不修改 candidate v2 / registry v4 / R4E.4 decision / default DB / scoring weights /
  sensitivity / valuation shadow。
- 不重取行情、不重算 PE/PB/PS、不做同行 percentile、不建 cheap/expensive bucket。
- 不输出 buy/sell / target price / margin-of-safety 结论。
- 不创建生产 Metric Result；不启动 M3；不自动进入下一阶段。
- 不做 1351d×3m×2w 的 rolling percentile series（只做 as-of 单点）。
- 未经明确授权不提交、不推送。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `4e4caeb`；local == origin（0/0）。
- R4E.4 final CI（run 31148682678）success。
- 默认 DB SHA `4a71d3c7b88c0b16…`（financial_facts=0，受保护基线）。
- registry v4 COMPLETE/pass；providers baostock_primary / tencent_via_akshare。
- R4E.4 decision = `PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED`；
  reconciliation_digest=`4fb3382b25e5889e…`；observation_count=4053。
- candidate v2：schema `petrochina_pit_valuation_series_candidate_v1`，4053 obs，
  metrics PE/PB/PS，non_production=True，dual oracle all_identical。
- coverage v2：3y_effective=728 / 5y_effective=1211（R4E.5 必须独立重算，不复用）。
- R4E.4 manifest 22 文件 PASS。
- 受保护项：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 M、`stash@{0}`、
  默认 DB、registry v3/v4、R4E.4 decision、candidate v2。
- 环境：Python 3.13.9；pandas 2.3.3；duckdb 1.5.5。

## 实施计划

1. 建工作记录（本文件）。
2. 新增 percentile contract config + methodology doc。
3. 新增 `historical_percentile.py` 核心（load_trusted_candidate / build_percentile_sample /
   compute_midrank_percentile / build_percentile_record / build_percentile_profile /
   validate_percentile_profile）。
4. 新增 `percentile_oracle.py`（DuckDB 独立实现，不用 percent_rank）。
5. 新增 R4E.5 CLI（verify-contracts / build / verify / fixtures）。
6. `artifact_manifest.py` 注册 R4E.5 manifest schema。
7. 新增测试。
8. 真实执行：build A / build B → A/B byte compare → dual oracle → 6-record 精确比较 →
   future-leakage / tie / invalid-status / boundary audit → method audit →
   cycle guard → decision → manifest。
9. 新增 acceptance。
10. 全量验证（pytest/ruff/compileall/git diff --check/manifest/pollution/protected）。

## 决策记录

- **决策 1：MIDRANK_EMPIRICAL_PERCENTILE 作为正式方法**。采用原因：契约冻结
  strict/weak/midrank 三读，midrank 做正式值，strict/weak 做审计界；
  `0 <= strict <= midrank <= weak <= 100` 恒成立；tie 由 midrank
  （分子 `+1`）平均。已考虑替代方案：`percent_rank()`（排名约定与本契约不同，
  弃用）、`cume_dist()`（非官方 percentile，弃用）。风险：显示截断不影响
  恒等式，恒等式绑定精确有理数 `rank_numerator / rank_denominator`。
- **决策 2：Decimal-only，绝不 float**。采用原因：排名/比较必须精确。
  DuckDB oracle 用 `DECIMAL(38,28)` 精确比较，不用 `percent_rank`。
- **决策 3：样本准入 fail-closed**。仅 `status=="computed"` 且
  `ratio_decimal>0` 且在窗口内进入 N；非正 PE 永不排为 cheap；其余全部进
  exclusion ledger，绝不进入 N。
- **决策 4：5y 窗口 effective_first=2021-08-02**。calendar_start=2021-07-31
  是非交易日，取其后第一个交易日 2021-08-02 为 effective first。
- **决策 5：6 条记录固定顺序** PE/3y, PE/5y, PB/3y, PB/5y, PS/3y, PS/5y，
  `percentile_record_id` 绑定身份字段（schema/version/symbol/metric/window/
  dates/current obs id/current ratio/N/L/E/G/rank/method/guard），不绑定
  path/time/machine/dir。
- **决策 6：PE 解释防护**。PE 记录带
  `low_pe_not_automatic_undervaluation_v1`，`cycle_warning_required=true`，
  `interpretation=DESCRIPTIVE_RELATIVE_VALUATION_ONLY`。
- **决策 7：非生产边界**。profile `non_production=true`、`score_eligible=false`、
  `production_eligible=false`；写 default DB、改 scoring weights、peer 均禁止。
- **决策 8：R4E.5 manifest schema `m2_stage2k1r4e5_artifact_manifest_v2`**
  注册于 `ALLOWED_MANIFEST_SCHEMAS` 和 `V2_SCHEMAS`；用
  `sha256_lf_normalized_bytes_v1` 摘要算法。

## 实际操作

（按执行顺序真实记录）

1. 核对 R4E.5 开始状态：分支 `feat/m2-value-assessment-mvp`，HEAD `4e4caeb`，
   local==origin 0/0，默认 DB SHA `4a71d3c7b88c0b16…`（financial_facts=0），
   stash 完好，registry v4 COMPLETE/pass，R4E.4 decision 存在，candidate v2
   4053 obs / 3 metrics / dual oracle all_identical。
2. 确认 candidate v2 观测状态：computed(3943) + missing_ttm_input(110)；
   ratio_decimal 为 string 或 None；as-of 2026-07-31 每指标恰 1 条 computed。
3. 新增 `config/pit_valuation_percentile_contract_v1.json`（方法契约，schema
   `pit_valuation_historical_percentile_v1` v1.0）。`verify-contracts` 通过。
4. 新增 `src/ashare_research/pit_valuation/historical_percentile.py` 核心
   （load contract/candidate、fail-closed sample、midrank 核心、profile、PE
   guard、validate）。独立验证：midrank [1,2,3,3,4]=70；6 条 READY 记录
   N=728/1211，与 coverage v2 重算一致。
5. 新增 `src/ashare_research/pit_valuation/percentile_oracle.py`（DuckDB 独立
   oracle，DECIMAL(38,28)，不用 percent_rank）。验证 Python==DuckDB
   all_identical=True。
6. 在 `src/ashare_research/scoring/artifact_manifest.py` 注册
   `m2_stage2k1r4e5_artifact_manifest_v2`（ALLOWED + V2_SCHEMAS）。
7. 新增 `docs/historical_valuation_percentile_methodology.md`（方法学）。
8. 新增 CLI `src/ashare_research/tools/m2_stage2k1r4e5_historical_percentile.py`
   （verify-contracts / build / verify / fixtures）。修复 bug：`verify-contracts`
   子命令缺少 `--contract/--candidate` 参数；`_build_audit` 误传
   `oracle_report`（无 `comparisons`）而非 `comparison`，导致 method audit
   `oracle_identical_all=False`——改为传 `comparison` 后为 `True`。
9. 真实 build：6 条非生产 percentile 记录 + profile + sample ledger 6 条 +
   dual oracle（6 条比较 all_identical）+ method audit（全 pass）+ audit
   samples + decision（exit 0 TRUSTED）。记录值与独立重算一致。
10. 新增 `tests/test_m2_stage2k1r4e5_historical_percentile.py`（25 个测试）。
    修复：ROOT 路径 parents 偏移（parents[2]→parents[1]）；ruff E501/N806/E741/
    F841 若干，用 `# noqa: N806`（契约 N/L/E/G 词汇）+ 重构长行修复。
11. 新增 `acceptance/m2_stage2k1r4e5_historical_valuation_percentile.md`。
12. 构建并验证 `reports/m2_stage2k1r4e5_artifact_manifest.json`（15 文件，
    status pass，0 mismatch）。
13. 全量验证：ruff（changed files All checks passed）、compileall、git diff
    --check、pollution/secret 扫描（无输出）、report 交叉一致性检查、manifest
    verifier pass、protected files 未动。

## 数据与方法说明

- 数据来源：`reports/petrochina_pit_valuation_series_candidate_v2.json`
  （R4E.4 发布的候选 v2，schema `petrochina_pit_valuation_series_candidate_v1`，
  4053 obs）。这是本阶段唯一估值输入；不重取行情、不重算 PE/PB/PS。
- As-of 交易日：2026-07-31（include_current=true）。
- 窗口：3y effective_first=2023-07-31（calendar 同）；5y calendar_start=
  2021-07-31、effective_first_trade_date=2021-08-02（非交易日顺延）。
- 最小样本：3y≥500、5y≥900（冻结）。
- 排名方法：MIDRANK_EMPIRICAL_PERCENTILE；严格
  100*L/N、弱 100*(L+E)/N、midrank 100*(2L+E+1)/(2N)；tie 由 midrank 平均。
- 精度：Decimal-only（`Decimal(str(...))`）；DuckDB oracle 用精确
  DECIMAL(38,28) 比较；恒等式绑定精确有理数。
- 未来泄漏：max(sample.trade_date) <= 2026-07-31 门禁；任何 > as_of 失败。
- 缺失/非正处理：仅 status==computed 且 ratio_decimal>0 且在窗口进入 N；
  其余全部进 exclusion ledger（missing_ttm_input、null_ratio、
  nonpositive_ratio、before_window_start、future_trade_date、metric_mismatch）。
- 无 cheap/fair/expensive bucket；无 buy/sell/target price/margin-of-safety
  结论；无 rolling percentile series（仅 as-of 单点）。

## 验证

- `python -m ashare_research.tools.m2_stage2k1r4e5_historical_percentile build`
  → exit 0，decision TRUSTED，oracle_identical=true，all_windows_ready=true，
  record_count=6。
- `python -m pytest tests/test_m2_stage2k1r4e5_historical_percentile.py -q`
  → 29 passed。
- `ruff check`（changed files）→ All checks passed。
- `python -m compileall -q`（changed files）→ pass。
- `git diff --check` → pass。
- R4E.5 manifest verifier → status pass，15 files，0 mismatch。
- Pollution/secret 扫描 → 无绝对路径/代理/token。
- Report 交叉一致性：sample ledger N == profile eligible_sample_count（6 条）；
  dual oracle all_identical；method audit 三 flag 全 True；decision 绑定
  candidate/r4e4/recon digest 与报告一致。
- A/B 复现：两次 build 到不同输出目录，6 个报告字节一致。
- 全量 pytest：**1668 passed, 2 pre-existing warnings**（含夹具 fixtures 测试）。

## 结果

- 已完成：R4E.5 全部交付物；6 条非生产 percentile（PE/PB/PS × 3y/5y）；
  方法契约 + 方法学冻结；Python/DuckDB 独立 oracle all_identical；PIT/tie/
  invalid/boundary/min-sample audit 全 pass；PE cycle guard 存在；decision
  TRUSTED（exit 0，north-star review required）；manifest pass。
- 6 条记录（midrank）：PE/3y=91.964286、PE/5y=93.270025、PB/3y=84.958791、
  PB/5y=90.957886、PS/3y=91.964286、PS/5y=95.169282。
- 未完成：无（本阶段范围内全部完成）。
- 条件通过：无（全绿）。
- 已提交并推送（2 笔：feat + docs closeout），CI 全绿（run 31151600368）；
  **未进入 scoring、未启动下一阶段**。

## 遗留问题

- 无本阶段范围内的遗留问题。
- 说明性边界：percentile 为描述性相对估值，低 PE percentile 不作低估证据
  （PE guard 已记录 cycle_warning_required=true）。

## 下一步建议

- 若获授权，进入 scoring 集成前必须先做独立 North-Star Review（scoring
  集成需独立治理历史），再决定是否接入；本阶段不自动进入。

## 最终文件变更

- 新增：`config/pit_valuation_percentile_contract_v1.json`；
  `docs/historical_valuation_percentile_methodology.md`；
  `src/ashare_research/pit_valuation/historical_percentile.py`；
  `src/ashare_research/pit_valuation/percentile_oracle.py`；
  `src/ashare_research/tools/m2_stage2k1r4e5_historical_percentile.py`；
  `tests/test_m2_stage2k1r4e5_historical_percentile.py`；
  `acceptance/m2_stage2k1r4e5_historical_valuation_percentile.md`；
  `agent/record/2026-08-07_Stage2K1R4E5_historical_valuation_percentile.md`；
  报告：`petrochina_pit_valuation_percentile_profile_v1.json`、
  `petrochina_pit_valuation_percentile_sample_ledger_v1.json`、
  `petrochina_pit_valuation_percentile_dual_oracle_v1.json`、
  `petrochina_pit_valuation_percentile_method_audit_v1.json`、
  `petrochina_pit_valuation_percentile_audit_samples_v1.json`、
  `m2_stage2k1r4e5_decision.json`、`m2_stage2k1r4e5_artifact_manifest.json`。
- 修改：`src/ashare_research/scoring/artifact_manifest.py`（仅注册 R4E.5 schema）。
- 保护文件未动：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*`、
  stash、默认 DB、registry v4、R4E.4 decision、candidate v2。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 提交：`1563a32`（feat: add trusted historical valuation percentile profile）、
  `6a088e7`（docs: record R4E.5 local closeout）、本 CI-evidence 提交。
- 已推送：是（普通 push 至 origin，fast-forward，无 force/reset/merge/PR/tag）。
- 远程 CI：GREEN（run `31151600368`，push `6a088e7`）。
- 存在未提交修改：仅用户保护文件（`AGENTS.md`、`agent/goals/`、
  `acceptance/m2_stage2i2r_*`），未 stage、未提交。