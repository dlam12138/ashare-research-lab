# 工作记录：M2 Stage 2D-E 2021-2025 合并净利润 net_profit 官方事实与重列覆盖

## 基本信息

- 日期：2026-08-01
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`766a20d`
- 任务来源：`/goal` 指令（M2 Stage 2D-E：2021-2025 合并净利润 net_profit 官方事实与重列覆盖）
- 对应模块：价值评估（ROA 分子事实底座）

## 任务目标

补齐 5 个年度 duration Concept `net_profit`（合并净利润，含归母与非控股股东损益）的
2021-2025 官方事实与重列覆盖，解除 Stage 2D-C 冻结的 "ROA numerator fact coverage"
阻塞。正式值必须来自经审计合并利润表"净利润"直接披露行；归母+少数股东损益加总只作
交叉校验。新增 Rule 005（`RECON_OFFICIAL_NUMERIC_005` v1，仅 net_profit）、9 份
committed evidence（5 supplemental + 4 restatement）、离线 runner
`official_net_profit_fact_foundation.py`、测试、验收报告。不计算 ROA/ROIC/评分。

## 范围

- 修改 `src/ashare_research/reconciliation/engine.py`（纯新增 Rule 005 常量与规则对象，
  不改 Rule 001-004 语义/输出/身份）；
- 新增 `acceptance/fixtures/official_facts/601857.SH/supplemental/2021_net_profit.json`
  至 `2025_net_profit.json`（5 份）；
- 新增 `acceptance/fixtures/restatements/601857.SH/net_profit_2021_reviewed_by_2022.json`
  至 `net_profit_2024_reviewed_by_2025.json`（4 份）；
- 新增 `src/ashare_research/tools/official_net_profit_fact_foundation.py`（离线 runner）；
- 新增 `tests/test_official_net_profit_fact_foundation.py`（Rule005/evidence/集成测试）；
- 新增 `acceptance/m2_stage2de_petrochina_net_profit_fact_coverage.md`；
- append-only 更新 `docs/value_fact_coverage_roadmap.md`；
- 同步受 protected-blob 测试对 reconciliation/engine.py 的引用（若有）；
- 新增本工作记录。

## 非目标

- 不新增 Context（复用现有 11 个，其中 5 个 annual duration）；不手写 reconciled Fact；
- 不修改 Rule 001-004 语义、输出和身份；不修改既有 annual、earnings-quality、
  denominator evidence；
- 不修改 Stage 2D-C 方法论 JSON；不修改 Stage 2D-B/2D-D runner/报告；
- 不计算 ROA/ROIC/评分；不进入 ROA Metric；
- 不访问网络/PDF/cache（正式 runner offline；证据准备阶段的 PDF 文本层提取在
  gitignored `output/` 辅助脚本中完成，不属于 runner）；
- 不由归母+少数股东损益相加生成正式 Fact（仅作桥接校验）；
- 不使用归母净利润、扣非净利润、营业利润、利润总额、母公司单体净利润；
- 不 merge main，不建 Tag/Release。

## 开始前状态

- 当前分支 `feat/m2-value-assessment-mvp`，HEAD `766a20d`，worktree clean；
  local == origin（`@{u}`=`766a20d`）；
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，未动；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（实测与基线一致）；
- Stage 2D-B 基线：contexts=11 / facts=180 / raw_ineligible=120 / reconciled_eligible=60 /
  links=39 / audit=lineage=180 / final PIT=47；年度 PIT 11/20/29/38/47；R(denominator)=4；
- 180 Fact ID 集合 SHA：`2bd5b2d2…`（2D-B foundation 冻结）；
  132 上游 Fact ID 集合 SHA：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`；
- Stage 2D-D 基线：70 Metric Result（63 旧 + 7 ROE）ID 集合 SHA：
  `bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0`；
  旧 63 ID 集=`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
  旧 63 语义=`e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053`；
  旧 38 ID 集=`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`；
- 受保护 Git blob（实测 HEAD）：reconciliation/engine.py `459adfc7…`、
  facts/concepts.py `f3a9d425…`、roadmap `04d323dd…`。

## 证据准备（gitignored output/ 辅助脚本，非 runner；仅文本层，无 OCR/PNG/下载）

脚本 `output/verify_and_extract_net_profit.py`（运行输出 `output/net_profit_extraction.txt`、
`output/np_sections_exchange.txt`、`output/np_555_financials.txt`）：

1. PDF 完整性：9 份缓存 PDF（`D:\量化分析-cache\official-pdfs\<sha256>.pdf`）头
   （`%PDF-`）/大小/页数/SHA-256 全部与 annual bundle 登记一致，36/36 OK，cache_miss=0，
   未下载任何文件。
2. 2021 公司来源 badab8f2（经审计财务报表，95 页）PDF p10 文本层 chars=0（扫描影像，
   与 Stage 2D-B 判定一致）→ 2021 公司来源采用已登记的 2021 业绩公告 555a24ed
   （44 页，文本层完好），其共享 `company_ir:601857.SH:2021` source_id，不改变版本链
   稳定身份（沿用 2D-B 决策 2 与 earnings-quality 先例）。
3. 经审计合并利润表"净利润"直接披露行（单位：人民币百万元，×100=万元）：

| FY | v1 原值（当年年报当期合并列） | 来源页（公司 / 交易所） | 下一年报比较列 | 比较页 | changed |
|---|---:|---|---:|---|---|
| 2021 | 114,687 | 555a24ed p42/p42；939de04e p114/p112 | 114,687（2022 年报 fea19e90/da64c67d p113/p111） | p113/p111 | 否 |
| 2022 | 163,977 | fea19e90 p113/p111；da64c67d p113/p111 | 163,343（2023 年报 b845502e p114/p112） | p114/p112 | **是** |
| 2023 | 180,291 | b845502e p114/p112（公司=交易所同字节） | 180,561（2024 年报 15a2de01 p115/p113） | p115/p113 | **是** |
| 2024 | 183,747 | 15a2de01 p115/p113（公司=交易所同字节） | 183,747（2025 年报 0eba96bd/840b15aa p109/p107） | p109/p107 | 否 |
| 2025 | 172,005 | 0eba96bd p109/p107；840b15aa p109/p107 | —（not_yet_reviewable） | — | — |

4. 双来源精确相等（公司==交易所）：2021 年 555a24ed p42 四列（114,687/33,481/84,133/
   62,745）与 939de04e p114 逐值一致；2022 fea19e90==da64c67d p113（163,977/114,687）；
   2023/2024 公司与交易所为同一 SHA PDF；2025 0eba96bd 与 840b15aa p109 逐值一致
   （172,005/157,302/14,703）。
5. 桥接校验（归母+少数股东=净利润，仅交叉校验不作正式值）：
   - 2021：92,161+22,526=114,687 ✓；利润总额−所得税=158,194−43,507=114,687 ✓
   - 2022：149,375+14,602=163,977 ✓；比较列 148,738+14,605=163,343 ✓
   - 2023：161,144+19,147=180,291 ✓；237,458−57,167=180,291 ✓；比较列 161,414+19,147=180,561 ✓
   - 2024：164,676+19,071=183,747 ✓；241,502−57,755=183,747 ✓；比较列同原值 ✓
   - 2025：157,302+14,703=172,005 ✓
6. **R = 2**（changed：2022、2023；与 Stage 2D-B 分母、Stage 2D-D 归母净利润的重列
   格局完全一致：2022=Interpretation 16 / IAS 12 修订，2023=同一控制下企业合并
   （中油电能）；2021、2024 未变，2025 不可复核）。
7. 行标签确认：所有取值行标签为"净利润"（利润表直接行），按所有权归属分类下
   "归属于母公司股东的净利润""少数股东损益"仅作桥接；未使用营业利润、利润总额、
   母公司单体列（公司列值仅作行定位佐证，未入库）。

## 动态计数（R=2，自洽推演）

- contexts = 11（不新增）
- facts = 195+3R = 201（180 基线 + 15 v1 + 6 v2）
- raw/ineligible = 130+2R = 134（120 + 10 v1 raw + 4 v2 raw）
- reconciled/eligible = 65+R = 67（60 + 5 v1 + 2 v2）
- fact version links = 39+3R = 45（39 + 3×2 v2 supersedes）
- Audit = Lineage = 195+3R = 201
- final latest Fact PIT = 52（47 + 5 net_profit latest；v2 替换 v1 不增计数）
- 年报可用时 latest PIT：2021=12 / 2022=22 / 2023=32 / 2024=42 / 2025=52
- v2 PIT 切换：2022 net_profit 于 2024-03-26（2023 年报日）v1→v2；
  2023 net_profit 于 2025-03-31（2024 年报日）v1→v2。

## 实施计划

1. ✅ 启动检查、基线冻结、PDF 证据核验与取值（见上）。
2. 新增 Rule 005（engine.py 纯新增常量/规则对象）+ 9 份 evidence JSON。
3. 新增离线 runner `official_net_profit_fact_foundation.py`：重建并验证 180 Fact
   （调用 2D-B foundation）与 70 Metric Result（调用 2D-D extension）基线；读取
   committed evidence；Rule 005 reconciliation；重列链（仅 changed 建 v2）；PIT/
   Audit/Lineage 验证；写 run-scoped DuckDB + manifest + `net_profit_input_readiness.json`。
4. 新增测试 + 验收报告 + roadmap append-only + protected-blob 引用同步。
5. 门禁：ruff / compileall / import / targeted+full pytest / git diff --check / 污染检查；
   不变性证明（180 Fact、70 Result、ROE 7 版本、Rule 001-004、默认 DB、stash）；
   3 提交逐个 push。

## 决策记录

### 决策 1：2021 公司来源用 555a24ed 业绩公告 override（沿用 2D-B 先例）

- 内容：2021 公司 audited statements badab8f2 为扫描影像（p10 文本层 chars=0，本次
  实测复核确认），改用已登记的 2021 业绩公告 555a24ed（p42 完整复现经审计合并及
  公司利润表，四列与交易所 939de04e p114 逐值一致）。evidence 用 documents override，
  source_id 保持 `company_ir:601857.SH:2021:annual:zh-cn` 不变。
- 原因：`/goal` 要求文本层无法可靠确认时不得猜测；555a24ed 已登记且共享 source_id，
  不改变版本链稳定身份（VersionChainValidator check C）。
- 风险：无；双来源逐值相等由 Rule 005 精确匹配门禁兜底。

### 决策 2：Rule 005 为 engine.py 纯新增，Rule 001-004 逐字不动

- 内容：仅在 reconciliation/engine.py 新增 `NET_PROFIT_RULE_ID/VERSION` 常量与
  `NET_PROFIT_RECONCILIATION_RULE` 对象（`supported_concepts={"net_profit"}`），
  复用既有引擎全部门禁（精确相等、万元、无容差/平均/来源优先）。
- 原因：与 Rule 002-004 的既有扩展模式一致；引擎门禁 1-8 对 net_profit 完全适用。
- 风险：engine.py blob 变化（`459adfc7…`->新值），引用该 blob 的 protected-blob
  测试需同步（跨阶段 surgical edit + 注释）；Rule 001-004 语义/输出/身份不变由
  既有测试与新测试共同证明。

### 决策 3：restatement evidence 命名与 contract 独立于既有 evidence

- 内容：新增 `net_profit_<year>_reviewed_by_<year+1>.json`（4 份）与
  `supplemental/<year>_net_profit.json`（5 份），contract 分别为
  `net_profit_restatement_evidence_v1` / `net_profit_official_facts_v1`；
  不修改任何既有 annual / earnings-quality / denominator / capex_cash evidence。
- 原因：`/goal` 明确文件清单；独立 contract 防止扩展污染冻结证据。
- 风险：无。

## 实际操作

（按执行顺序持续记录）

1. 读取 `agent/record/README.md`、最近三份记录（2D-D/2D-C/2D-B）、北极星目录、
   项目结构；确认 `CLAUDE.md` 与 `agent/agent.md` 已加载。
2. 确认起点：分支 `feat/m2-value-assessment-mvp`、HEAD `766a20d`、worktree clean、
   local==origin、`stash@{0}` 未动；实测默认 DB SHA=`4a71d3c7…` 不变。
3. 读取 2D-B runner（1110 行，runner 模板）、reconciliation/engine.py（Rule 001-004）、
   facts/concepts.py（net_profit 已注册：income_statement/duration/别名"净利润"）、
   facts/contexts.py（duration Context 复用，不新增）、facts/as_of.py
   （get_latest_available / compare_versions / get_all_versions_for_audit API）、
   facts/identity.py（build_fact_id 9 字段）、reconciliation/service.py
   （reconcile_official_pair 15 步契约）、validation/version_chain.py
   （VersionChainValidator A-E 检查）、2D-D runner 结构与常量（Explore 代理结构化
   摘要 + 直接读取核实）、5 份 annual bundle（文档登记与 NPAP 页码）、
   earnings-quality 与 denominator supplemental evidence 样本、restatement 样本。
4. PDF 证据准备（见上节）：36/36 完整性 OK；确认 R=2；全部桥接校验通过。
5. `reconciliation/engine.py` 纯新增 Rule 005（blob `459adfc7…`→`828d7051…`）；
   `output/author_net_profit_evidence.py` 生成 9 份 evidence（LF，内置桥接/
   company==exchange/R 断言全部通过）。
6. 新增 `tests/test_net_profit_reconciliation_rule.py`（Rule 005 契约 13 项）、
   `tests/test_registered_net_profit_evidence.py`（evidence 注册 18 项参数化）；
   4 处 engine.py protected-blob 引用同步（跨阶段 surgical edit + 注释）。
   两文件 + 4 同步套件 targeted pytest 139 passed。
7. 新增 runner `official_net_profit_fact_foundation.py`（约 1000 行）：重建验证
   180 Fact + 70 Result 基线 → Rule 005 v1×5 + v2×2 reconciliation → 动态计数/
   PIT/版本链/readiness 断言 → run-scoped DuckDB + 7 份 JSON + summary。
   Trial run（`run_id=stage2de_trial`）一次通过：status=passed，counts 全匹配。
8. 新增 `tests/test_official_net_profit_fact_foundation.py`（15 项集成测试，
   含 24 项 PROTECTED_BLOBS 与重跑幂等）。修复一处测试缺陷：`financial_facts`
   表不存储 `fiscal_year` 便利字段（identity.py `_SEMANTIC_EXCLUDE` 设计），
   改由 `period_end` 派生年份断言。
9. `docs/value_fact_coverage_roadmap.md` append-only 追加 2D-D/2D-E 状态
   （LF 写入；blob `04d323dd…`→`a9fa3da1…`）；4 处 roadmap protected-blob
   引用同步。
10. 期间处理一次 autocrlf 陷阱：`git checkout -- roadmap` 将工作区转为 CRLF，
    导致 raw `_git_blob` 断言失败；以 CRLF→LF 规范化恢复（repo blob 始终未变），
    所有新文件以 LF 写入避免复发。
11. 新增验收报告与本记录；门禁全过；3 提交逐个 push。

## 验证

实际执行（全部通过）：

1. `ruff check src tests`（全量）：exit 0（All checks passed）。
2. `compileall -q src tests`：exit 0；runner 模块 import OK。
3. targeted pytest：
   - Rule 005 + evidence 注册：76 passed；
   - foundation 集成：15 passed（3 次完整 runner 运行，含幂等双跑）；
   - 4 处同步的 protected-blob 套件（2D-C 方法论 / 2D-A / 2D-B / 2D-D / 2C-D）：
     90 passed（含 roadmap 同步后复验）。
4. full pytest：**886 passed**（795 基线 + 91 新增），2 warnings 均为既有
   `test_quality.py` 日期解析告警，与本任务无关。
5. `git diff --check`：exit 0（仅 LF→CRLF warning，非错误，与既往一致）。
6. 污染检查：`git ls-files` 与 untracked 均无 .duckdb/.wal/.pdf/.png；
   默认 `data/research.duckdb` SHA=`4a71d3c7…` before==after 不变；
   `stash@{0}` 未动（1 条，与起点一致）。
7. Runner trial run（`stage2de_trial`）实测：status=passed，
   transaction_committed=true，offline=true，network/pdf/cache=false，
   downloaded=0；counts={contexts:11, financial_facts:201,
   raw_ineligible:134, reconciled_eligible:67, version_chain_links:45,
   audit:201, lineage:201}；annual PIT 12/22/32/42/52；final PIT=52；
   上游 180 Fact ID 集=`2bd5b2d2…`、70 Result ID 集（newline 格式）=
   `bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0`、
   ROE 7 版本、prior-63 ID=`34edbbc3…`/语义=`e988394f…` 全部不变。

不变性证明（测试 + runner 内断言共同覆盖）：

- 180 Fact、70 Metric Result、ROE 7 版本、旧 63/38 Result ID 与语义：不变；
- Stage 2D-B/2D-C/2D-D 产物、Rule 001-004 代码、Concept Registry、
  既有 evidence（annual/earnings-quality/denominator/capex_cash）：blob 冻结；
- reconciliation/engine.py（`459adfc7…`→`828d7051…`）与 roadmap
  （`04d323dd…`→`a9fa3da1…`）为本阶段合法推进（纯新增 Rule 005 / append-only），
  9 处 protected-blob 引用跨阶段同步；
- 默认 DB、上游 DB（只读）、metrics DB（只读）前后 SHA 不变；stash 未动。

## 结果

- 2021-2025 consolidated `net_profit` 官方事实与重列覆盖落地（R=2）：
  15 v1 + 6 v2 = 21 个新 Fact，全部 canonical、版本链完整；
- Rule 005 落地，仅支持 `net_profit`，显式拒绝归母/扣非/营业利润/利润总额；
- 动态计数（R=2）全部符合 `/goal` 公式并实测一致；
- `net_profit_input_readiness.json` 登记 5 年 latest reconciled 事实，
  `ready_for_roa_numerator=true`；**"ROA numerator fact coverage" 阻塞解除**；
- Stage 2D-C 方法论 JSON 未修改；状态推进仅记录于验收报告与 roadmap append-only；
- 未计算 ROA/ROIC/评分；未进入 ROA Metric；未 merge main；未建 Tag/Release。

结论：

```text
M2 Stage 2D-E: PASS
2021—2025 consolidated net_profit facts: TRUSTED
ROA numerator: READY
ROA transparent metric computation: ALLOWED
ROIC: NOT YET
Scoring: STILL NOT YET
```

## 遗留问题

- 无硬阻塞。
- ROA 仍 NOT YET（本阶段仅解除分子事实覆盖阻塞，不计算）；
  ROIC / scoring 仍 NOT YET / STILL NOT YET。
- autocrlf 环境下 raw `_git_blob` 断言依赖工作区 LF 状态（既有模式，
  本次以 LF 写入维持；全新克隆检出为 CRLF 时该模式需要环境层处理，
  非本阶段范围，既往各阶段同一模式）。

## 下一步建议

仅价值评估核心目标内：

- **C. ROA 透明 Metric 计算**：基于 Stage 2D-C 合同与 `net_profit`（分子）+
  平均总资产（分母，Stage 2D-B 输入对）透明计算 2021-2025 ROA，
  含重列传播与 PIT 回放。
- ROIC 投入资本口径研究（仅价值评估模块需要时启动）。

## 最终文件变更

新增（14 个文件）：

1. `acceptance/fixtures/official_facts/601857.SH/supplemental/2021_net_profit.json`
2. `acceptance/fixtures/official_facts/601857.SH/supplemental/2022_net_profit.json`
3. `acceptance/fixtures/official_facts/601857.SH/supplemental/2023_net_profit.json`
4. `acceptance/fixtures/official_facts/601857.SH/supplemental/2024_net_profit.json`
5. `acceptance/fixtures/official_facts/601857.SH/supplemental/2025_net_profit.json`
6. `acceptance/fixtures/restatements/601857.SH/net_profit_2021_reviewed_by_2022.json`
7. `acceptance/fixtures/restatements/601857.SH/net_profit_2022_reviewed_by_2023.json`
8. `acceptance/fixtures/restatements/601857.SH/net_profit_2023_reviewed_by_2024.json`
9. `acceptance/fixtures/restatements/601857.SH/net_profit_2024_reviewed_by_2025.json`
10. `src/ashare_research/tools/official_net_profit_fact_foundation.py`
11. `tests/test_net_profit_reconciliation_rule.py`
12. `tests/test_registered_net_profit_evidence.py`
13. `tests/test_official_net_profit_fact_foundation.py`
14. `acceptance/m2_stage2de_petrochina_net_profit_fact_coverage.md`
15. `agent/record/2026-08-01_1353_m2_stage2de_net_profit_fact_coverage.md`（本记录）

修改（8 处 surgical edit，无语义改动以外的变更）：

1. `src/ashare_research/reconciliation/engine.py`（纯新增 Rule 005 常量与规则对象）；
2. `docs/value_fact_coverage_roadmap.md`（append-only 追加 2D-D/2D-E 状态）；
3-6. 4 处 protected-blob 引用同步：`tests/test_capital_return_methodology.py`、
   `tests/test_official_roe_metric_extension.py`、
   `tests/test_official_roe_roa_denominator_2025_acceptance.py`、
   `tests/test_official_roe_roa_denominator_foundation.py`（engine.py 与 roadmap blob）；
7. `tests/test_official_earnings_quality_2025_acceptance.py`（roadmap blob 引用同步）。

辅助脚本与运行产物（不入库，gitignored `output/`、`tmp/`）：
`output/verify_and_extract_net_profit.py`、`output/author_net_profit_evidence.py`、
`output/net_profit_extraction.txt`、`output/np_sections_exchange.txt`、
`output/np_555_financials.txt`、trial run 目录、commit message 文件。

## 最终Git状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`766a20d`
- 本任务三个提交（逐个 push）：
  1. `3160442` `feat: add consolidated net-profit reconciliation rule`
     ——Rule 005 + 9 份 evidence + Rule005/evidence 测试 + engine.py blob 同步
  2. `e5d036a` `test: add PetroChina net-profit fact foundation`
     ——离线 runner + 15 项集成测试 + roadmap append-only + roadmap blob 同步
  3. 本提交 `docs: finalize PetroChina net-profit acceptance`
     ——验收报告 + 本工作记录
- `stash@{0}` 保留未动；默认 `data/research.duckdb` SHA 不变；最终 worktree clean；
  local/origin/remote 一致（每次 push 后 rev-list ahead/behind=0/0 核验）。
- 不 merge main，不建 Tag/Release，不重写既有提交，不强制推送；
  不进入 ROA Metric、ROIC 或评分。
