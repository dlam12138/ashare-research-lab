# 工作记录：M2 Stage 2K.1R4D.1b — Calendar Object Pinning Closeout

Status: `completed`
Closeout verdict: `PASS`
Implementation commit: `4223aee`
CI run: `31066461569`
CI Ubuntu: `success`
CI Windows: `success`
Identity compare: `success`

## 基本信息

- 日期：2026-08-06
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`878727e`
- 任务来源：reviewer 复核结论（R4D.1a 的日历对象选择合同 NEEDS MICRO-FIX）
- 对应模块：价值评估（PIT 估值分母事实的日历/PIT 时间契约）

## 任务目标

很小的收口，不重做 R4D.1/R4D.1a，不开始 PE/PB/PS 序列：

1. 把市场日历对象从“前缀匹配 + 任意 fallback”改为“显式内容寻址 + fail-closed”。
   `load_market_calendar` 必须只读取已提交 registry 钉住的唯一日历对象，绝不扫描
   缓存目录、绝不在钉住对象缺失/损坏时静默选用另一个 parquet。
2. 新增已提交 registry：`config/pit_valuation_market_calendar_registry_v1.json`
   （object_sha256、object_key、row_count、first/last trading day、evidence_cutoff、
   resolver_contract）。
3. 加载后校验内容地址与结构（sha256 == registry、object_key stem == sha256、
   row_count、first/last trading day、trade_date 唯一/严格递增、is_trading 存在、
   无空日期）；任意不一致直接失败。
4. 针对 loader 的选择行为补测试（目标对象存在→PASS；目标缺失但目录有旧对象→FAIL；
   文件名是预期 SHA 但内容 SHA 不匹配→FAIL；row_count 不匹配→FAIL；日期重复/非递增→FAIL；
   覆盖起点/终点不足→FAIL；正确对象与旧对象共存→只使用显式目标对象）。
5. 修正 R4D.1a 工作记录状态（in_progress → completed + PASS）。
6. 更新 acceptance 与本次工作记录；重新跑正式管线与双平台 CI（受官方缓存与推送授权约束）。

## 范围

- 新增 `config/pit_valuation_market_calendar_registry_v1.json`。
- `contracts.py`：`MARKET_CALENDAR_REGISTRY_PATH`、`load_market_calendar_registry`、
  `validate_market_calendar_registry`，并入 `validate_all_contracts` 与 digest。
- `fact_builder.py`：重写 `load_market_calendar`（显式内容寻址 + 结构校验 + fail-closed）。
- 新增 `tests/test_m2_stage2k1r4d1b_calendar_object_pinning.py`。
- 更新 R4D.1a 工作记录状态、R4D.1a acceptance 状态、新增 R4D.1b acceptance 与工作记录。

## 非目标

- 不重做 R4D.1/R4D.1a 的 Context、重述、股本连续性或日期修复。
- 不生成日频 PE/PB/PS、TTM、分位、评分。
- 不采集 peer；不启动 M3；不写默认 DuckDB。
- 不重新下载官方缓存（R4D 官方 PDF 为 gitignored 外部缓存；重新抓取 30 份 SSE PDF 通过
  JS challenge 属网络脆弱操作，且可能引入与已验证缓存不同的字节）。
- 不合并 main、不创建 PR/Tag/Release、不强制推送、不重写已有提交、不删除 stash。

## 已确认的审查背景（reviewer 2026-08-06）

```text
M2 Stage 2K.1R4D.1a: CONDITIONAL PASS
- 2020 effective_from 修正 / Calendar boundary fail-closed / Fact PIT provenance /
  Gap classification / Committed readiness artifacts / Dual-platform CI: TRUSTED
- Calendar content-object selection: NOT TRUSTED   <- 本次 R4D.1b 修复
- Work-record closeout status: NEEDS CORRECTION    <- 本次修正
```

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `878727e`（本地 == origin）。
- `load_market_calendar` 用前缀匹配选择对象，`matches[0] if matches else parquet_files[0]`
  存在 fail-open：钉住对象缺失时会静默选用目录第一个 parquet。
- 真实日历对象 `tmp/market_cache/baostock/77021dce….parquet` 存在（1597 行，
  2020-01-02..2026-08-05），内容 SHA == 文件名（已实测匹配）。
- 受保护项（用户未提交修改）：`acceptance/m2_stage2i2r_*.md`（1 行状态措辞）、
  `AGENTS.md`、`agent/goals/`。这些项不得改动。
- 官方 R4D 缓存（`official-cache-root`，30 份 PDF）本地不存在（gitignored）。

## 实施计划

1. 建工作记录（本文件）。
2. 新增 `config/pit_valuation_market_calendar_registry_v1.json`（钉住真实对象）。
3. `contracts.py`：日历 registry 加载 + 校验 + 并入 `validate_all_contracts`。
4. `fact_builder.load_market_calendar`：改为 `root / registry.object_key` 显式读取，
   校验内容地址与结构，任意不一致抛 `CalendarCoverageGapError`（fail-closed）。
5. 新增 loader 测试（12 项）。
6. 运行新测试 + 相关 R4D 测试 + 全量离线套件 + ruff + compileall + verify-contracts。
7. 用真实日历对象实测 loader（integration）。
8. 修正 R4D.1a 工作记录状态；更新 R4D.1a acceptance；新增 R4D.1b acceptance 与记录。
9. 检查最终差异；记录正式管线重跑与双平台 CI 的约束。

## 决策记录

### D1：日历钉住信息放已提交 registry，而非硬编码在 Python 模块

- 决策内容：新增 `config/pit_valuation_market_calendar_registry_v1.json`，loader 从
  `contracts.load_market_calendar_registry()` 读取钉住对象；不在 `fact_builder.py`
  硬编码完整对象 SHA。
- 采用原因：reviewer 明确要求“不要把完整对象 SHA 硬编码在 Python 模块中”；registry
  与其它 R4D registry 同构，可被 `validate_all_contracts` 统一校验并生成 digest。
- 替代方案：1) 继续硬编码 SHA 前缀（当前实现）；2) 复用 `tmp/market_registry_baostock_only.json`。
- 未采用原因：1) fail-open 且 SHA 散落在代码里；2) 该文件在 `tmp/`（gitignored），
  不是已提交的权威契约。
- 潜在风险：新增一个 registry 文件需纳入 contract digest；CI 需在 `verify-contracts`
  中校验。

### D2：所有日历失败统一抛 `CalendarCoverageGapError`

- 决策内容：缺文件、内容 SHA 不匹配、结构不匹配、覆盖不足均抛
  `CalendarCoverageGapError`。
- 采用原因：`load_market_calendar` 在 `_cmd_formal` 顶部、无 try/except 地调用，
  任何异常都会中止正式运行（fail-closed）；复用既有契约异常保持表面最小。
- 替代方案：为内容完整性单独定义 `CalendarObjectIntegrityError`。
- 未采用原因：新增异常类型扩大契约表面；缺文件/损坏/覆盖不足本质都是“已验证日历
  不可信”，统一失败即可，CLI 已按 fail-closed 处理。
- 潜在风险：语义上“内容完整性失败”与“覆盖缺口”被归为一类；已在消息中区分，且都
  会导致正式运行中止而非静默降级。

### D3：不重新下载官方缓存重跑完整正式管线

- 决策内容：本地不重抓 30 份 R4D 官方 PDF；R4D.1b 的验证以 loader 定向测试 +
  真实日历对象 integration + contract gate + 全量离线套件为主。
- 采用原因：官方缓存为 gitignored 外部产物；重新抓取需过 SSE JS challenge，网络脆弱，
  且 R4D.1b 只改日历加载器，事实包确定性不变（已实测：reported bundle 已引用钉住
  对象与正确 effective_from）。
- 替代方案：触发 `acquire` 重抓官方缓存后跑 `formal`。
- 未采用原因：重抓可能得到不同的字节集，需重新校验；超出最小收口范围。
- 潜在风险：正式管线的端到端重跑与双平台 CI 需在具备官方缓存/推送授权时执行；本记录
  明确标为待办，不伪装成已完成。

## 实际操作

按执行顺序记录（2026-08-06）：

1. 核验 Git 状态（HEAD `878727e`）；读 R4D.1a 工作记录、acceptance、
   `fact_builder.load_market_calendar`、`contracts.py`、CLI、R4D.1a 测试。
2. 实测真实日历对象：内容 SHA == 文件名（`77021dce…`），1597 行，首 2020-01-02、
   末 2026-08-05，trade_date 唯一且单调，is_trading 存在，无空日期。
3. 新增 `config/pit_valuation_market_calendar_registry_v1.json`（见下）。
4. `contracts.py`：新增 `MARKET_CALENDAR_REGISTRY_PATH`、`load_market_calendar_registry`、
   `validate_market_calendar_registry`（校验 schema/symbol/sha256 长度/object_key 命名/
   row_count/首末交易日/evidence_cutoff/resolver_contract 禁止扫描 fallback），并入
   `validate_all_contracts` 与 digest（新增 `market_calendar_registry_digest`）。
5. `fact_builder.load_market_calendar`：重写为 `root / registry.object_key` 显式读取；
   顺序校验 object_key stem、文件存在、内容 SHA == registry、row_count、
   is_trading/trade_date 列、无空日期、唯一、严格递增、首末交易日、required_start/end
   覆盖；任意失败抛 `CalendarCoverageGapError`。
6. 新增 `tests/test_m2_stage2k1r4d1b_calendar_object_pinning.py`（12 项，含
   `_provision` 自洽对象生成 + 真实对象 integration）。
7. 实测 loader 对真实对象：`required_start='2020-04-30'` →
   object_id=`77021dce….parquet`，sha 匹配，1597 交易日，2020-04-30→05-06。
8. `verify-contracts`：通过，含 `market_calendar_registry_digest=17f4480c…`。
9. 新测试 12 passed；相关 R4D 测试（R4D.1a / fact_identity / context_restatement /
   restatement_and_readiness / true_upstream_capsule）83 passed。
10. ruff check src/ tests/：All checks passed；compileall：pass。
11. 全量离线测试套件（后台）结果见“验证”。
12. 核对 committed reported bundle：唯一 calendar_object_id / calendar_sha256 均为
    `77021dce…`；2020-04-30 fact effective_from=2020-05-06、available_at=2020-04-30
    （R4D.1b 不改事实，仅钉死日历选择合同）。
13. 修正 R4D.1a 工作记录状态（completed + PASS + reviewer 注记）；更新 R4D.1a
    acceptance 状态；写本记录与 R4D.1b acceptance。

## 数据与方法说明

- 数据来源：baostock（R4D.1a 已抓取的日历对象，本次未重新下载）。
- 钉住对象：`tmp/market_cache/baostock/77021dceda….parquet`（gitignored，未提交）。
- registry：`config/pit_valuation_market_calendar_registry_v1.json`（已提交）。
- 内容地址：对象按其自身 sha256 命名；loader 校验 `sha256(bytes)==object_sha256` 且
  `Path(object_key).stem==object_sha256`。
- 结构事实（registry 记录）：row_count=1597、first_trading_day=2020-01-02、
  last_trading_day=2026-08-05、evidence_cutoff=2026-08-02。
- 复权方式：不复权（`adjustflag='3'`），仅用交易日历，不用行情数值。
- 未来数据泄漏：无 — 日历只决定 effective_from（公告后的下一交易日），不引入未来值。

## 验证

- `verify-contracts`：pass，输出含 `market_calendar_registry_digest`。
- 新测试 `test_m2_stage2k1r4d1b_calendar_object_pinning.py`：**12 passed**。
- 相关 R4D 测试：**83 passed**（R4D.1a 12、fact_identity、context_restatement、
  restatement_and_readiness、true_upstream_capsule）。
- 真实对象 loader 实测：object_id / sha 匹配，1597 交易日，2020-04-30→05-06。
- `ruff check src/ tests/`：All checks passed。
- `python -m compileall -q src`：pass。
- 全量离线测试套件：**1433 passed, 2 warnings**（1421 R4D.1a 基线 + 12 新 R4D.1b 测试）。
- `git diff --check`：pass。
- 正式管线端到端重跑：**NOT_RUN_EXTERNAL_OFFICIAL_CACHE_UNAVAILABLE** —— 本地
  无既有 verified official cache（registry 25 个对象均不在工作区），不进行网络重抓、
  不临时换用第三方/其他 PDF；R4D.1b 只改日历加载器，事实包确定性不变（已通过
  committed bundle 核对确认：reported 127 / reconciled 38 / 150 cells / 0 gaps，
  effective_from 与 fact_id 均不变）。不声称正式 PDF 提取被重新执行。
- 双平台 CI（Stage 2G reproducibility，run 31066461569，headSha `4223aee`）：**success**。
  - clean-clone (ubuntu-latest)：success（2m24s），含 Full offline test suite
    **1430 passed, 3 skipped, 3 warnings**（0 failed；3 skip 为 clean-clone 无本地
    快照的网络/integration 测试，与本地 1433 总数一致）。
  - clean-clone (windows-latest)：success（4m47s）。
  - identity-compare：success（28s，跨平台 identity payload 一致）。
  - R4D contract gate（含 `market_calendar_registry_digest=17f4480c…`）：pass。

## 结果

- R4D.1b 收口完成：日历对象选择改为显式内容寻址 + fail-closed，不再扫描/回退。
- 已提交 registry 钉住真实对象；`validate_all_contracts` 现含日历 registry 校验。
- 12 项 loader 测试覆盖 reviewer 要求的全部选择行为。
- R4D.1a 工作记录状态修正为 `completed / PASS`。
- 双平台 CI（run 31066461569）Ubuntu/Windows/identity-compare 全部 success。
- gate 可正式升级为 **PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT**。
- 正式管线端到端重跑：**NOT_RUN_EXTERNAL_OFFICIAL_CACHE_UNAVAILABLE**（官方缓存缺失，
  不阻断 R4D.1b loader 微修复；不声称正式 PDF 提取被重新执行）。

## 遗留问题

- 正式管线的端到端重跑未在本地执行（官方缓存 gitignored 缺失）。
- 双平台 CI 未运行（需推送）。
- 日历仍为 baostock 单源；扩展历史窗口完整性受数据源覆盖约束（继承 R4D.1a）。
- A+H 总股本假设与 SSE 归档完整性为 constancy 派生的 residual risks（继承 R4D.1）。

## 下一步建议

- 具备官方缓存后重跑 `formal`；推送本地提交并由 Stage 2G reproducibility 双平台 CI
  复验；随后将 gate 正式升级为 `PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT`。
- 在这之后才允许开始日频 PE/PB/PS preflight（当前 NOT YET）。

## 最终文件变更

新增：
- `config/pit_valuation_market_calendar_registry_v1.json`
- `tests/test_m2_stage2k1r4d1b_calendar_object_pinning.py`
- `agent/record/2026-08-06_Stage2K1R4D1b_calendar_object_pinning_closeout.md`
- `acceptance/m2_stage2k1r4d1b_calendar_object_pinning_closeout.md`

修改：
- `src/ashare_research/pit_valuation/contracts.py`（日历 registry 加载/校验/digest）
- `src/ashare_research/pit_valuation/fact_builder.py`（重写 `load_market_calendar`）
- `agent/record/2026-08-05_Stage2K1R4D1a_historical_calendar_closeout.md`（状态 → completed/PASS）
- `acceptance/m2_stage2k1r4d1a_historical_calendar_closeout.md`（状态 → PASS，标注 R4D.1b 收口）

受保护项 untouched：`acceptance/m2_stage2i2r_*` 编辑、`AGENTS.md`、`agent/goals/`、
默认 DB、`stash@{0}`。

## 最终 Git 状态

- 分支 `feat/m2-value-assessment-mvp`；开始 HEAD `878727e`。
- 第一笔提交 `4223aee`（fix: pin PIT market calendar content object）已推送 origin
  （`878727e..4223aee`），双平台 CI 成功。
- 第二笔提交（本工作记录 + acceptance 的 CI 证据收尾）将随后推送。
- 受保护项未纳入提交（`acceptance/m2_stage2i2r_*`、`AGENTS.md`、`agent/goals/`、
  默认 DB、`stash@{0}` 均未 stage/改动）。