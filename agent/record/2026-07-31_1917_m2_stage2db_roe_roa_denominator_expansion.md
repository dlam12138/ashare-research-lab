# 工作记录：M2 Stage 2D-B 2020-2025 ROE/ROA instant 分母事实扩展

## 基本信息

- 日期：2026-07-31
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`f9b749a`（Stage 2D-A 工程门禁收口后的 HEAD）
- 任务来源：`/goal` 指令（M2 Stage 2D-B：2020-2025 ROE/ROA instant 分母事实扩展）
- 对应模块：价值评估（ROE/ROA 分母事实底座）

## 任务目标

在 Stage 2D-A 冻结的 2024/2025 instant 分母事实基础上，补齐 2020-2023 的
`total_assets`、`equity_attributable_to_parent` 两个 instant Concept-Date：
- 2020-12-31 仅作为 2021 平均余额的 opening baseline，取自 2021 年报经审计合并
  资产负债表的 2020 比较列，`available_at` = 2021 年报两官方路径较晚公告日
  （2022-04-01），证据标记 `comparison_only_opening_baseline`；
- 2021、2022、2023 年末同两项 instant 事实，取各自年报当期合并列；
- 用下一年度报告比较列复核 2021→2022、2022→2023、2023→2024。
- 不计算平均余额、ROE、ROA、ROIC 或评分。

## 范围

- 新增 5 份 evidence（2020 opening、2021、2022、2023）+ 3 份 restatement
  （2021←2022、2022←2023、2023←2024）；
- 新增 4 个 instant Context（2020-2023）；
- 新增离线 runner `src/ashare_research/tools/official_roe_roa_denominator_foundation.py`；
- 新增 evidence/restatement/integration 测试与正式报告；
- 新增本工作记录。

## 非目标

- 不修改 Rule 001-004 语义、engine.py、validator.py、Fact Schema、FactIdentity、
  AsOfQuery、VersionChainValidator、Metric 代码或既有事实/指标；
- 不修改 2024/2025 evidence 与 2024 reviewed-by-2025 restatement；
- 不下载 2020 年报，不为 2020 制造 review/v2；
- 不计算平均余额/ROE/ROA/ROIC/评分，不扩展其他科目；
- 不 merge main，不创建 Tag/Release。

## 开始前状态

- 当前分支 `feat/m2-value-assessment-mvp`，HEAD `f9b749a`，worktree clean；
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，未动；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（与基线一致）；
- Stage 2D-A 已落地：Rule 004（`ROE_ROA_DENOMINATOR_RECONCILIATION_RULE`）、
  `FACT_INSTANT_001` 收窄、2024/2025 evidence、2024←2025 restatement（R=0）、
  runner `official_roe_roa_denominator_2025_acceptance.py`、正式报告；
- Stage 2D-A 计数基线：contexts=7 / facts=144 / raw_ineligible=96 /
  reconciled_eligible=48 / links=27 / audit=lineage=144 / final PIT=39；
- 上游 132 Fact ID 集合 SHA：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`；
- 63 Metric Result ID 集合 SHA：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
- 2024 已知原值：total_assets=2,753,007（275,300,700 万元）、
  equity=1,515,371（151,537,100 万元）；2025：2,828,017 / 1,586,061；
- 工具：pdftotext 4.00、PyMuPDF 1.28.0、Python 3.13.9、ruff 0.12.0；
- 共享缓存 `D:\量化分析-cache\official-pdfs` 中 2021-2024 公司/交易所 PDF 全部在位且以 SHA 命名。

受保护 Git blob（本次不得变更，已与 Stage 2D-A 测试 PROTECTED_BLOBS 核对一致）：
engine.py `459adfc7…`、validator.py `4f90195f…`、version_chain.py `292442c3…`、
as_of.py `d707ec3a…`、identity.py `85c84b4e…`、service.py `62837ed1…`、
Stage 2D-A runner `8d3ab73a…`、Stage 2D-A 报告 `2b9b06d4…`、
2024/2025 evidence/restatement `a3ac5483…/62250878…/868fac35…`。

## 实施计划

1. 证据准备（PDF 文本层提取，非 runner）：核验 8 份 PDF 头/大小/页数/SHA；
   定位经审计合并资产负债表，目视核验“资产总计”“归属于母公司股东权益合计”，
   取合并列，做三重会计恒等式交叉验证；确定 R。
2. Commit 1 `test: register PetroChina historical ROE ROA denominator evidence`：
   5 份 evidence + 3 份 restatement + evidence/restatement/Context 测试。
3. Commit 2 `feat: add multi-year ROE ROA denominator foundation`：
   runner + integration 测试。
4. Commit 3 `test: finalize PetroChina denominator expansion`：
   正式报告 + 本记录 + 收尾测试。
5. 门禁：全量 Ruff、compileall/import、targeted + full pytest、`git diff --check`、
   污染检查；证明不变性；逐个 push 3 个提交。

## 决策记录

### 决策 1：2020 opening baseline 取 2021 年报比较列，available_at=2022-04-01

- 内容：2020 两项 instant 事实直接取 2021 年报经审计合并资产负债表的 2020 比较列；
  `available_at` = 2021 年报两官方路径较晚公告日（max(2022-03-31, 2022-04-01)=2022-04-01）；
  evidence 标记 `comparison_only_opening_baseline`，不下载 2020 年报，不为其建 review/v2。
- 原因：`/goal` 明确要求；2020 仅作 2021 平均余额 opening，不需要 2020 年报原始披露。
- 风险：2020 事实的 `available_at` 晚于其 `period_end`（2020-12-31），符合 PIT 语义
  （事实在 2021 年报公告时才对市场可用），AsOfQuery 以 `available_at` 为准。

### 决策 2：v2 raw 事实保持 source_id 稳定（修正 Stage 2D-A 隐性缺陷）

- 内容：2D-B runner 的 v2 raw 事实（company/exchange）保持与 v1 相同的 `source_id`
  与 `source_tier`，仅更新 `source_document/source_url/source_hash/announcement_date/
  available_at` 为下一年报，`fact_version=2`、`restatement_version="restated_1"`、
  `supersedes_fact_id` 指向 v1 raw 事实。
- 原因：`VersionChainValidator` 约束 C 要求 `source_id` 跨版本一致；
  `service._check_input_source_tier_chains` 要求 `source_tier` 稳定；
  raw 输入事实会被持久化并对版本链做完整校验（service 步骤 4）。
  Stage 2D-A 的 v2 代码将 `source_id` 改为下一年报的 `source_id`
  （`official_roe_roa_denominator_2025_acceptance.py:879`），但因 R=0 从未实跑，
  属未被触发的隐性缺陷。2D-B 若 R>0 将首次触发该路径，必须修正。
  采信 earnings-quality foundation v2 的既有成功范式（保持 source_id 稳定）。
- 风险：与 2D-A v2 代码不一致；但 2D-A v2 路径未实跑、未被任何测试以 R>0 覆盖，
  故不构成对既有通过测试的回归。reconciled 输出事实的 `source_id` 为
  `reconciled:{symbol}:company_exchange:{rule_id}:v{version}`，仅由 symbol+rule 决定，
  天然跨版本稳定，不受此决策影响。

## 实际操作

（进行中，按执行顺序持续记录）

1. 读取 `agent/record/README.md`、最近两份 Stage 2D-A 记录、Stage 2D-A runner 与
   evidence/restatement、as_of.py、contexts.py、version_chain.py、engine.py、service.py、
   earnings_quality foundation、2021-2024 annual bundles；确认缓存 PDF 在位。
2. 记录基线：HEAD `f9b749a`、worktree clean、默认 DB SHA、stash、受保护 blob。
3. PDF 文本层提取（`output/extract_denominators.py`，仅文本层，无 OCR/无 PNG 渲染）：
   - 8 份 PDF 头/大小/页数/SHA-256 全部与 2021-2024 annual bundle 一致（`cache_miss=0`）。
   - 2021 公司 audited statements（badab8f2，95 页）为**扫描影像 PDF**（CCITTFaxDecode，文本层为空）；
     改用已登记的 2021 业绩公告 `555a24ed...`（44 页，文本层）作为 2021/2020 公司来源——
     其 p40-41 完整复现经审计合并资产负债表，数值与交易所版完全一致，三重会计恒等式成立。
   - 2022 公司/交易所 p111（资产侧）、p112（续）均确认 `资产总计` 行，公司=交易所。
   - 2023（b845502e）p112-113、2024（15a2de01）p113-114 确认。

4. 目视核验经审计合并资产负债表“资产总计”“归属于母公司股东权益合计”（合并列），三重会计恒等式
   （流动+非流动=资产总计；归母+少数=股东权益合计；负债+权益=负债及股东权益总计=资产总计）
   对 2020/2021/2022/2023 当期列与比较列全部精确成立。

5. 编写 `output/verify_555_and_2022.py`（系统 `python` 带 PyMuPDF 1.28，仅文本层）复核
   555a24ed（size=1195800/pages=44/SHA OK）、939de04e（282 页）、fea19e90/da64c67d（285 页）、
   b845502e（293 页）、15a2de01（280 页）头/大小/页数/SHA；补齐 2022 v1 资产侧拆分
   （流动 613,867 + 非流动 2,059,884 = 2,673,751）；确认 555a24ed printed page=PDF page
   （p40/p41 顶部 "40"/"41"），年报 printed = PDF-2（如 939de04e p112->"-110-"）。
   939de04e 与 555a24ed 的 2020/2021 合并列逐行精确一致（company==exchange）。

6. 编写 `output/author_denominator_evidence.py` 生成 5 份 evidence + 3 份 restatement：
   - `supplemental/2020_opening_roe_roa_denominators_from_2021.json`（comparison_only_opening_baseline，
     base_bundle=2021_annual，company=555a24ed override，available_at=2022-04-01）
   - `supplemental/2021|2022|2023_roe_roa_denominators.json`（reviewed_unchanged/changed/changed）
   - `roe_roa_denominators_2021|2022|2023_reviewed_by_*.json`（R=0/R=2/R=2；
     2022 原因 "Interpretation 16 / IAS 12 revisions"，2023 原因 "Common-control business combination (中油电能)"）
   生成器内置三重会计恒等式断言与 company==exchange 断言，全部通过。
   修正：2020 evidence `source_table` 用报告年 2021（非数据年 2020），column_label 用 2020 比较列。

7. 编写 `src/ashare_research/tools/official_roe_roa_denominator_foundation.py`，泛化 2D-A runner
   至 2020-2025：6 份 evidence + 4 份 restatement；2020/2021 company 用 evidence-level
   `documents` override（555a24ed），2020 base_bundle=2021_annual 允许 fiscal_year 不等；
   v2 用 `_build_v2_raw_fact`（deepcopy 前驱，**不更新 source_id**，仅更新 value/source_document/
   source_hash/source_url/available_at + V2_SOURCE_PAGES 页码），修正 2D-A v2 source_id 隐性缺陷。
   首跑两处隐性缺陷（均为 2D-A R=0 未触发路径）：
   (a) 版本切换断言 `get_latest_available([concept])` 返回多年多行，应按 period_end 过滤；
   (b) `compare_versions` 返回全部 period_end，应只校验目标年条目。修正后通过。

8. 实跑 runner（run_id `roe_roa_denominator_601857_SH_2020_2025_20260731_201740_244689`）通过：
   counts={contexts:11, financial_facts:180, raw_ineligible:120, reconciled_eligible:60,
   version_chain_links:39, audit:180, lineage:180}；R=4；
   年度 PIT 2021=11/2022=20/2023=29/2024=38/2025=47；final PIT=47；
   average_balance_input_pairs=10（5 年×2），全部 ready_for_average=True；
   2021 pair 起点用 2020 开仓基线 2,488,400，2022/2023 pair 用 v2 重述值 2,670,666/2,759,237；
   offline=True, network/pdf/cache=False, downloaded=0；
   上游 DB 与默认 DB SHA 不变；upstream fact_id_set_sha256=`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`。

## 数据与方法说明

合并口径 instant 原值（人民币百万元；×100=万元）：

| Concept | 2020 | 2021 | 2022 v1/v2 | 2023 v1/v2 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| total_assets | 2,488,400 | 2,502,533 | 2,673,751 / 2,670,666 | 2,752,710 / 2,759,237 | 2,753,007 | 2,828,017 |
| equity_attributable_to_parent | 1,215,421 | 1,263,815 | 1,369,576 / 1,365,866 | 1,446,410 / 1,451,333 | 1,515,371 | 1,586,061 |

来源与页码（PDF page / printed page）：
- 2020/2021（取自 2021 年报）：公司=业绩公告 555a24ed p40(资产总计)/p41(归母)，交易所=939de04e p112/p110、p113/p111；
  available_at=max(2022-03-31,2022-04-01)=2022-04-01。
- 2022（取自 2022 年报）：公司=fea19e90、交易所=da64c67d，p111/p109、p112/p110；available_at=2023-03-30。
- 2023（取自 2023 年报 b845502e）：p112/p110、p113/p111；available_at=2024-03-26。
- 2022 v2（2023 年报比较列，b845502e p112/p113）：available_at=2024-03-26。
- 2023 v2（2024 年报比较列，15a2de01 p113/p114）：available_at=2025-03-31。

R（2021-2023 比较复核中 changed 的 Concept-Year 数）：
- 2021←2022：资产总计 2,502,533=2,502,533（未变）；归母 1,263,815=1,263,815（未变）→ 0。
- 2022←2023：资产总计 2,673,751→2,670,666（变）；归母 1,369,576→1,365,866（变）→ 2。
- 2023←2024：资产总计 2,752,710→2,759,237（变）；归母 1,446,410→1,451,333（变）→ 2。
- **R = 4**（2022 两项 + 2023 两项）。2021/2024 未变（2024 R=0 沿用 Stage 2D-A）。

计数核验（R=4）：contexts=11；facts=168+12=180；raw/ineligible=112+8=120；
reconciled/eligible=56+4=60；version links=27+12=39；audit=lineage=180；final PIT=47；
年度 PIT 11/20/29/38/47。全部自洽。

## 结果

- 2020-2025 ROE/ROA instant 分母事实底座落地；R=4（2022 两项 + 2023 两项 changed）。
- 动态计数（R=4，自洽）：contexts=11；financial_facts=180；raw/ineligible=120；
  reconciled/eligible=60；version_chain_links=39；audit=lineage=180；final PIT=47；
  年度 PIT 2021=11 / 2022=20 / 2023=29 / 2024=38 / 2025=47。
- 12 v1 + 4 v2 = 16 条 Rule 004 reconciliation，全部 `matched`；reconciled 输出
  `source_tier=reconciled_derived`、`eligible_for_metrics=True`、Fact ID canonical。
- 平均余额输入对 10 条（5 年×2），全部 `ready_for_average=True`，同 unit(万元)/同
  consolidated 口径/相邻 12-31；FY2021 起点用 2020 开仓基线 2,488,400；
  FY2022/FY2023 终点用 v2 重述值 2,670,666 / 2,759,237（百万元）。
- runner offline=True，network/pdf/cache=False，downloaded=0；不计算平均余额/ROE/ROA/ROIC/评分。
- 修正 Stage 2D-A v2 `source_id` 隐性缺陷（2D-B `_build_v2_raw_fact` deepcopy 前驱、
  不更新 source_id）；R=4 首次实跑该路径，VersionChainValidator check C 通过。
- 工程门禁（实际执行）：
  - `ruff check src tests`：exit 0（All checks passed）；
  - `compileall -q src tests`：exit 0；
  - targeted pytest（2D-B foundation + 2D-A acceptance）：23 passed；
  - full pytest：740 passed（2 warnings，均为既有 `test_quality.py` 日期解析，与本任务无关）；
  - `git diff --check`：exit 0；
  - 污染检查：`output/` 被 `.gitignore:34` 忽略（3 个辅助脚本不入库）；无 .duckdb/.wal/.pdf/.png 入库；
    默认 `data/research.duckdb` SHA=`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（与基线一致）；
    `stash@{0}` 未动；`git status` 显示零既有文件被修改（仅 12 个新文件）。
- 不变性证明（全部通过）：
  - 上游 132 Fact ID 集合 SHA=`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d` 不变；
  - 63 Metric Result ID 集合 SHA=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526` 不变；
  - 38 original Result ID 集合 SHA=`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa` 不变；
  - Stage 2D-A runner/report/2024+2025 evidence/2024 restatement Git blob 不变；
  - Rule 001-004 代码（engine/validator/version_chain/as_of/identity/service）blob 不变；
  - Stage 2C 报告与 runner blob 不变；docs 三份方法学文件 blob 不变。

## 遗留问题

- 无硬阻塞。Stage 2D-B 全部门禁通过，2020-2025 instant 分母事实可信任。
- 2020 事实的 `available_at`（2022-04-01）晚于 `period_end`（2020-12-31），符合 PIT 语义
  （2020 比较值仅在 2021 年报公告时对市场可用），非缺陷，已记录于决策 1。
- ROIC 仍 NOT YET（分母侧仅 total_assets/equity_attributable_to_parent 两项 instant 事实，
  ROIC 尚需投入资本构成与营业利润口径，不在本阶段范围）。
- 评分仍 STILL NOT YET（价值评估评分门禁未触发）。

## 下一步建议

- 仅在价值评估核心目标内：基于已就绪的 2021-2025 平均余额输入对，构建 ROE/ROA
  average-balance 计算（需明确分子净利润的 duration 事实与公告日 PIT），并补充稳健性检验。
- ROIC 投入资本口径研究（仅价值评估模块需要时启动）。

## 最终文件变更

新增（12 个文件，零既有文件修改）：

1. `acceptance/fixtures/official_facts/601857.SH/supplemental/2020_opening_roe_roa_denominators_from_2021.json`
2. `acceptance/fixtures/official_facts/601857.SH/supplemental/2021_roe_roa_denominators.json`
3. `acceptance/fixtures/official_facts/601857.SH/supplemental/2022_roe_roa_denominators.json`
4. `acceptance/fixtures/official_facts/601857.SH/supplemental/2023_roe_roa_denominators.json`
5. `acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2021_reviewed_by_2022.json`
6. `acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2022_reviewed_by_2023.json`
7. `acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2023_reviewed_by_2024.json`
8. `src/ashare_research/tools/official_roe_roa_denominator_foundation.py`
9. `tests/test_registered_roe_roa_denominator_foundation_evidence.py`
10. `tests/test_official_roe_roa_denominator_foundation.py`
11. `acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md`
12. `agent/record/2026-07-31_1917_m2_stage2db_roe_roa_denominator_expansion.md`（本记录）

辅助脚本（不入库，gitignored）：`output/extract_denominators.py`、
`output/verify_555_and_2022.py`、`output/author_denominator_evidence.py`。

## 最终Git状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`f9b749a`
- 本任务三个提交（按 /goal 指令，逐个 push）：
  1. `0c19599` `test: register PetroChina historical ROE ROA denominator evidence`
     （4 evidence + 3 restatement + evidence/restatement/Context 注册测试）
  2. `ded8290` `feat: add multi-year ROE ROA denominator foundation`
     （offline runner + 12 项 integration 契约测试）
  3. 本提交 `test: finalize PetroChina denominator expansion`
     （正式报告 + 本工作记录）
- 不 merge main；不创建 Tag/Release；不重写既有提交；不强制推送。
- `stash@{0}` 保留未动；默认 `data/research.duckdb` SHA 不变；worktree clean。
- 推送后 local / origin / remote 一致性以 `git status` 与远端 ref 核验。
