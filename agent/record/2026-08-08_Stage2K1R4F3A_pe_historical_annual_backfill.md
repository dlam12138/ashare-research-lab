# 工作记录：M2 Stage 2K.1R4F.3A — Historical Annual Fact Backfill for 3Y Normalized-Earnings Validation

Status: completed（closeout：committed + pushed + CI PASS）

## 基本信息

- 日期：2026-08-08
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`7e1a9c9`（R4F.3 closeout，final tip CI PASS）
- 任务来源：用户指令 M2 Stage 2K.1R4F.3A（EXECUTION AUTHORIZED，2026-08-08）
- 对应模块：价值评估（historical annual fact backfill / PIT lineage / readiness recheck）

## 任务目标

1. 补齐 R4F.3 gap plan 的 MINIMUM_3Y_BACKFILL（5 个 target logical cells）：
   - 2017-12-31 equity_attributable_to_parent（opening equity for ROE 2018）
   - 2018-12-31 equity + net_profit_attributable_to_parent
   - 2019-12-31 equity + net_profit_attributable_to_parent
2. 扩展历史交易日历（baostock，不动 calendar v1），使 2018/2019/2020 年报公告
   date 可映射到 next trading day（announcement-date-to-next-trading-day-v1）。
3. SSE exchange_official 年报 PDF 联网获取（external content-addressed cache，
   不提交 PDF）；离线提取；restatement lineage；FactIdentity；PIT；overlay；
   用同一 R4F.3 readiness 引擎复跑 before/after；3Y gate。
4. 独立手工 5-cell evidence 复核 + Decimal-only 重算 ROE 2018/2019/2020。
5. 本地完成全部验证后 STOP 并报告（不 commit、不 push）。

## 范围

- 新增：contract v1、R4F3A calendar registry v1（复用既有 schema，不动 v1）、
  source evidence / cache registry（R4F3A 独立）、extraction spec、纯函数模块
  `pe_historical_annual_backfill.py`、薄 CLI、tests、docs、acceptance、decision、
  9+ reports。
- 下载：SSE exchange_official 年报 PDF（2018/2019/2020 相关 + restatement 扫描
  所需的最小 official filings；issuer official 仅作 alias/cross-check）。
- 日历：baostock 历史交易日历（新 content-addressed object + R4F3A registry pin）。

## 非目标

- 不 commit / 不 push / 不开始 R4F.4 / 不采 5Y financial facts / 不修改 scoring。
- 不修改 calendar v1、R4D frozen CALENDAR_COVERAGE_START、R4D/R4E facts 的
  calendar provenance / effective_from / Fact identity。
- 不修改 registry v2 / policy v2 / shadow v6 / sensitivity v8 / capsule v5。
- 不恢复 PE numeric score；不产生 valuation dimension score；不生成 normalized
  PE percentile；不做 empirical cycle-guard validation；不采 peer；不开始 M3。
- 不写默认 DB；不建第二套 readiness 算法（复用 R4F.3 resolver）。
- 不改 artifact_manifest.py；R4B/R4C/R4A manifest debt 不处理。
- 不把 disclosed ROE 作为 formal input（仅 cross-check diagnostic）。
- 不更换日历 provider（保持 baostock；若无法覆盖则 STOP 报告
  CALENDAR_PROVIDER_HISTORICAL_COVERAGE_GAP）。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `7e1a9c9`；local == origin；
  R4F.3 两笔提交已推送，final tip CI（run 31229287797）三作业全绿。
- R4F.3 decision = `PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN`
  （CONDITIONAL PASS）；gap plan：MINIMUM_3Y_BACKFILL=5 facts，MINIMUM_5Y=9 facts。
- 日历 v1 registry：first 2020-01-02 / last 2026-08-05 / row_count 1597 /
  object_sha256 77021dce… / provider baostock / evidence_cutoff 2026-08-02。
- R4D source evidence：50 entries（2020..2026 各 8 + 2026 Q1 2 笔），
  announcement 2020-04-30..2026-04-30；cache registry 25 objects。
- 已提交 reported bundle 127 facts / reconciled 38；2020 之前无 annual facts。
- 保护项：`acceptance/m2_stage2i2r_*.md`（既有 1 行修改）、`AGENTS.md`、
  `agent/goals/`、`agent/record/2026-08-08_01_*.md`（核验记录，未提交）、
  stash@{0}、默认 DB SHA `4a71d3c7b88c0b16…`。
- 外部缓存：官方 PDF 缓存、market cache 均 gitignored 外部根（需显式路径）。

## 实施计划

1. 建工作记录（本文件）。
2. 日历扩展：识别 evidence 文档集合 → 推导 required_start/end → baostock 拉取
   历史日历 → 新 content-addressed object → R4F3A registry → overlap 校验 →
   reconciliation 报告。
3. 合同 + source evidence + cache registry + extraction spec（config）。
4. acquire（联网，SSE official）→ 缓存校验（A/B）。
5. formal（离线）：extraction → restatement lineage → FactIdentity → PIT →
   reported bundle。
6. overlay + readiness 复跑（before/after，同一 resolver）+ 3Y gate + 5Y
   diagnostic。
7. 独立 5-cell 复核 + ROE 重算。
8. decision + docs + acceptance + tests；Section 二十六 全量验证；本地 STOP。

## 决策记录

- **日历扩展（A-Q 指令）**：新增 `config/pit_valuation_market_calendar_registry_r4f3a_v1.json`
  （复用 v1 schema），新 content-addressed 对象 `6a3cf1a0…`（baostock
  2017-01-03..2026-08-07，2330 交易日）；overlap 与 v1 完全一致（1597/1597，
  missing=0, extra=0）；calendar v1 与 R4D CALENDAR_COVERAGE_START 未动。
- **required_start 由 evidence 推导**：5 cells 链所需最早公告 = 2017 AR
  （2018-03-22），故 required_start=2018-03-22；registry 记录该值。
- **source evidence 集合**：2017 AR（A 的 original，2018-03-22）、2018 AR
  （B/C original，2019-03-21）、2019 AR（D/E original + restated_1 来源，
  2020-03-26）、2020 AR（comparative 扫描，R4D 同对象 7aac267c…）。
  2021/2022 AR 由窗口分析排除（比较列只覆盖上一年）。
- **restatement 机制**：2019 AR note 6(2) 大连西太同一控制合并 → 追溯重报
  2017/2018 比较值；original + restated_1 双版本保留，supersedes 链完整。
- **FactIdentity context 修正**：restated fact 的 context fiscal_year 必须用
  cell period_end 年份（2017/2018），不能用 evidence filing 年份（2019），
  否则 2017/2018 两个 restated equity 会撞同一个 fact_id。
- **2020 AR 下载校验**：sha256 与 R4D registry 完全一致 → 同一内容对象，
  不产生第二条经济事实（byte-identical alias 规则）。

## 实际操作

### 起点核验（2026-08-08）

- 分支 `feat/m2-value-assessment-mvp`；HEAD `7e1a9c9`；local == origin；
  R4F.3 final tip CI PASS。
- 保护项：`m2_stage2i2r`（1 行修改）、`AGENTS.md`、`agent/goals/`、
  `2026-08-08_01_*.md`（核验记录）；stash=1；默认 DB SHA `4a71d3c7…`。

### 日历扩展（任务 2）

1. baostock 探测 2017/2018 覆盖：2017-01-03 起有数据。
2. 拉取 601857 日线 2017-01-01..2026-08-10（adjustflag='3'，tradestatus 映射
   is_trading）→ 2330 交易日；sha256 `6a3cf1a0f920…`。
3. 新对象写入 `tmp/market_cache/baostock/`；新增 R4F3A registry。
4. overlap 校验：2020-01-02..2026-08-05 新旧 1597/1597 完全一致（missing/extra=0）；
   旧日历全部日期在新日历中。
5. 生成 `petrochina_pe_3y_historical_calendar_reconciliation_v1.json`
   （overlap PASS、coverage PASS、earliest_required_announcement_covered=true）。

### 合同 + 源证据（任务 3）

6. `config/pe_3y_historical_backfill_contract_v1.json`（5 cells、PIT 规则、
   source policy、scoring boundary）。
7. `config/pe_3y_historical_backfill_source_evidence_v1.json`（4 份 evidence）。
8. `config/pe_3y_historical_backfill_cache_registry_v1.json`（acquire 后填充）。
9. `config/pe_3y_historical_backfill_extraction_specs_v1.json`（最小 spec）。

### 联网获取（任务 4，用户已授权）

10. SSE query API 确认公告记录与 URL（2017/2018/2019 AR 旧式 URL）。
11. `fetch_official_pdf`（复用 R4D acw solver）下载 2018/2019 AR →
    sha256 5c205cc1…（292 页）/ d5fc4658…（306 页）。
12. 探明 2017-12-31 equity original 需 2017 AR（2018 AR 只有 comparative）→
    补下载 2017 AR（c1a6fbff…，274 页）。
13. 下载 2020 AR（7aac267c…，301 页），**sha256 与 R4D registry 完全一致**。

### 提取（任务 5）

14. 探针确认各 PDF 关键页（2017 AR p122 资产负债表、2018 AR p113/p114、
    2019 AR p114/p115），行模式带 `\s*` 桥接跨行。
15. 5 cells 全部提取成功并写入 extraction 报告。

### lineage + FactIdentity + PIT（任务 6）

16. 2019 AR p117/p118 权益变动表发现大连西太重报（equity 2017 -948、
    equity 2018 -503、NP 2018 +445）。
17. `build_fact` 构建 8 条事实（5 original + 3 restated_1），PIT 用 R4F3A
    日历（2018-03-22→03-23、2019-03-21→03-22、2020-03-26→03-27）。
18. **修复 context fiscal_year bug**（restated 用 period year 而非 filing
    year），8 个 fact_id 唯一。
19. 2020 AR comparative 扫描确认 2019 值无 restatement。

### bundles + overlay + readiness（任务 7）

20. reported bundle（8 facts）、overlay（165+8=173，三 digest）、
    after-readiness（before==committed R4F.3 逐字段一致；after 808 ready，
    3y blocked 0 → THREE_YEAR_HISTORICAL_VALIDATION_READY；5y 仍 BLOCKED，
    gap plan 保留 9 facts）。

### 独立 ROE 验算（任务 8）

21. Decimal-only 重算 ROE 2018/2019/2020，与 resolver 逐值一致（见报告）。

### tests + 全量验证（任务 9）

22. 写 46 项测试；修复 reconciliation 报告 status 字段。
23. ruff 修复（E501/N817/未用 import）→ All checks passed。
24. A/B byte-identical（7/7）；secret/path/pollution 扫描 clean。
25. 写 docs + acceptance + decision；更新本记录。

## 验证

- R4F3A 测试：**46 passed**（1.0s）。
- R4F3 回归：45 passed；R4F2：35 passed；R4F1：19 passed。
- Full pytest：**1835 passed, 2 warnings**（4m13s）。
- ruff：All checks passed；compileall：pass；git diff --check：pass。
- A/B byte-identical：**7/7 True**（含 lint 修复后重跑）。
- before-state 复现：earliest 2026-03-31、ready 84、blocked 1267、
  gap_reason 仅 insufficient_roe_history —— 与 committed R4F.3 一致。
- after-state：earliest 2023-03-31、ready 808、blocked 543、3y blocked 0。
- ROE 独立验算：三个 Decimal 值与 resolver 逐值相同。
- 默认 DB SHA `4a71d3c7…` 未变；stash 未动；保护项未动；calendar v1 未动。
- secret/path/pollution 扫描：clean（无 secret、无绝对路径、无 build-time ref）。

## 结果

- 已完成：日历扩展（R4F3A registry + overlap PASS）、4 份官方 PDF（external
  cache）、8 条事实（5 original + 3 restated_1）、overlay、readiness 复跑
  （3Y READY / 5Y BLOCKED）、docs、acceptance、46 项测试、decision。
- 决策：**PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED**（PASS）。
- 3Y gate：THREE_YEAR_HISTORICAL_VALIDATION_READY（728/728，blocked=0）。
- 5Y 仍 BLOCKED（403 天）。remaining 5Y gap = 程序化减法：baseline 9 −
  resolved 5 = **4**（2015-12-31 equity、2016-12-31 equity+NP、
  2017-12-31 NP）。
- full_cycle_proven = false（未变）。
- PE numeric scoring BLOCKED_UNCHANGED；valuation dimension 无数值分。
- closeout（2026-08-08）：commit `2da7b4a` / `63d874c` / `b13de6d` /
  `067b3cc` 已 push（`7e1a9c9..067b3cc`）；CI run 31234294698
  （head 067b3cc）三作业全绿。

## 遗留问题

- 5Y historical validation 仍 BLOCKED（403 天）。remaining 5Y gap =
  程序化减法：baseline 9 − resolved 5 = **4**（2015-12-31 equity、
  2016-12-31 equity+NP、2017-12-31 NP），留待后续阶段。
- full_cycle NOT_PROVEN（无独立周期证据）。
- 2021/2022 AR 未纳入 comparative 扫描（窗口分析排除），如需复核可补。
- manifest：R4F3A 产出为 report-only 隔离产物，未注册新 schema；
  R4B/R4C/R4A manifest debt 继承不处理。
- 首次 CI（b13de6d）曾在 clean-clone 因真实 parquet 缺失失败（gitignored
  cache），已由 `067b3cc` 合成内容寻址对象修复，后续 CI 全绿。

## 下一步建议

- R4F.4（3Y Historical Normalized-PE Cycle-Guard Validation）——仅验证，
  不授权 PE scoring；需用户另行授权。
- 5Y backfill 需另行授权（本阶段严格禁止顺手采集 2015/2016）。

## 最终文件变更

新增：
- `config/pe_3y_historical_backfill_contract_v1.json`
- `config/pit_valuation_market_calendar_registry_r4f3a_v1.json`
- `config/pe_3y_historical_backfill_source_evidence_v1.json`
- `config/pe_3y_historical_backfill_cache_registry_v1.json`
- `config/pe_3y_historical_backfill_extraction_specs_v1.json`
- `src/ashare_research/pit_valuation/pe_historical_annual_backfill.py`
- `src/ashare_research/tools/r4f3a_build.py`（orchestration）
- `src/ashare_research/tools/r4f3a_extraction_probe.py`（提取探针）
- `reports/petrochina_pe_3y_historical_backfill_extraction_v1.json`
- `reports/petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json`
- `reports/petrochina_pe_3y_historical_backfill_version_lineage_v1.json`
- `reports/petrochina_pe_3y_historical_backfill_overlay_v1.json`
- `reports/petrochina_pe_normalized_earnings_3y_readiness_after_backfill_v1.json`
- `reports/petrochina_pe_3y_historical_calendar_reconciliation_v1.json`
- `reports/petrochina_pe_3y_historical_backfill_reconciliation_v1.json`
- `reports/m2_stage2k1r4f3a_decision.json`
- `tests/test_m2_stage2k1r4f3a_pe_historical_annual_backfill.py`
- `docs/pe_3y_historical_annual_fact_backfill.md`
- `acceptance/m2_stage2k1r4f3a_pe_historical_annual_backfill.md`
- 本工作记录

修改：无（calendar v1、R4D/R4F3 contracts、scoring、既有 artifacts 未动）。

外部（gitignored，不交付）：`tmp/r4f3a_official_cache/`（4 份 PDF）、
`tmp/market_cache/baostock/6a3cf1a0….parquet`、`tmp/r4f3a_calendar_full.parquet`、
`tmp/r4f3a_hashes_a.json`。

## 最终 Git 状态

- 当前分支：`feat/m2-value-assessment-mvp`；HEAD `067b3cc`（R4F3A 实现 tip，
  CI PASS）；local == origin。
- 4 笔提交已推送：`2da7b4a`（backfill 核心）、`63d874c`（readiness +
  decision）、`b13de6d`（acceptance + work record）、`067b3cc`（clean-clone
  测试修复）。
- CI：run 31234294698（head 067b3cc）三作业全绿；run 31234032606
  （b13de6d）曾在 clean-clone 失败（真实 parquet 缺失），已由 067b3cc 修复。
- 保护项未动；stash 未动；默认 DB SHA 未变。
