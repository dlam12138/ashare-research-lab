# 工作记录：M2 Stage 2K.1R4E.4 — Selected Secondary Provider Integration, Registry v4 and Formal PIT Valuation Candidate Release

Status: completed
Closeout verdict: PASS — LOCAL CANDIDATE
Remote CI: GREEN
Implementation commits:
- be7bbdb feat: integrate selected secondary market provider
- 9365b2f feat: release formal PIT valuation candidate v2
- b574024 docs: record R4E.4 local closeout
CI run: 31148153204 (push b574024)
- Ubuntu clean-clone: PASS (1636 passed, 3 skipped, 3 warnings)
- Windows clean-clone: PASS (1636 passed, 3 skipped, 2 warnings)
- identity-compare: PASS
- R4E.4 manifest verifier: PASS
- R4C1 manifest verifier: PASS
Decision:
PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED
Historical percentiles: NOT COMPUTED
Next-stage implementation: NOT STARTED

## 基本信息

- 日期：2026-08-07
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`473cd67`（== 预期起点）
- 任务来源：用户指令 M2 Stage 2K.1R4E.4
- 对应模块：价值评估（selected secondary provider integration）

## 任务目标

把 R4E.3 已通过真实预检的 `tencent_via_akshare` 正式集成为 secondary market provider，
建立不可变 registry v4，完成 Baostock + Tencent 正式双源 reconciliation，并发布非生产
PIT PE/PB/PS candidate v2。本轮只允许放行 `PIT_VALUATION_PERCENTILE_PREFLIGHT_ALLOWED`；
不计算历史 percentile、不更新评分、不采集同行、不启动 M3。

## 范围

- 新增 `docs/selected_secondary_provider_integration_contract.md`（设计记录）。
- 先修 provider-role 合同：`market_reconciliation.py`、`m2_stage2k1r4e_series_preflight.py`
  消除 `primary=baostock` / `secondary=akshare` 业务硬编码（registry v4 用
  provider_id / provider_role / transport_library / underlying_provider）。
- 新增 `src/ashare_research/pit_valuation/provider_roles.py`（role 解析，fail-closed）。
- 新增 R4E.4 薄 CLI `m2_stage2k1r4e4_secondary_provider_integration.py`
  （promote / registry-draft / reconcile / verify / fixtures）。
- 正式集成复用 R4E.3 精确对象 `d760923a…`（内容寻址复制，字节全等）。
- 建立 `events/market_data_snapshot_registry_v4.json`（draft → 正式 reconciliation 后 COMPLETE）。
- 正式双源 reconciliation（复用 `market_reconciliation.py`，v2 合同）。
- 发布 candidate v2（用 `m2_stage2k1r4e_series_preflight formal --market-registry v4`）。
- 经济值迁移 v2、双 Oracle、coverage gate、R4E.4 decision、manifest v2。
- 新增测试、acceptance、本工作记录。

## 非目标

- 不计算任何 PE/PB/PS percentile；不写 percentile JSON；不改 valuation shadow/scoring/sensitivity。
- 不采集同行；不写生产 Metric Result；不写默认 DB；不启动 M3；不自动进入下一阶段。
- 不删除/修改 registry v3；不覆盖 R4E.3 decision；不把 Sina 当静默 fallback。
- 不引入大型 provider framework；不重构整个 data provider 层。
- 未经明确授权不提交、不推送、不创建 PR/tag/release。

## 开始前状态

- 分支 `feat/m2-value-assessment-mvp`；HEAD `473cd67`；local == origin（0 ahead / 0 behind）。
- R4E.3 CI 全绿（`docs: record R4E.3 provider selection` → success）。
- R4E.3 decision = `ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED`；
  selected=`tencent_via_akshare`；underlying=`tencent`；transport=`akshare`；
  object_sha256=`d760923aae952d9ba400d792d4155b4c6dfa3b728210de64001aa6024c8f7dd7`；
  table_digest=`e6cbee888949b13c0ee47a6193d58026ad6da72a332ffd66948ee4bc4b908cda`；
  row_count=1351；range=2021-01-04..2026-07-31。
- 默认 DB SHA-256 `4a71d3c7b88c0b16…`（未变；financial_facts=0）。354 Fact / 102 Metric
  Result / 16 definitions 为受保护冻结基线（Stage 2F 前）。
- registry v3 `events/market_data_snapshot_registry_v3.json`：baostock `c6771aa5…`
  （1351 行，2021-01-04..2026-07-31，adjustment=none），akshare provider_gap，
  `reconciliation_status=pending_real_reconciliation`。
- R4E.3 选中 Tencent 对象存在于 `tmp/market_cache/r4e3/tencent_via_akshare/d760923a….parquet`
  （本阶段重算 SHA/digest/1351/日期范围全部匹配）。
- Baostock `c6771aa5…` 对象存在于 `tmp/market_cache/baostock/`。
- 旧 baostock `defd0b95…`（R4E v1 candidate 用）与 `c6771aa5…` close 全等（1351 天，0 差异）。
- v1 candidate `reports/petrochina_pit_valuation_series_candidate_v1.json` 已发布（4053 obs）。
- 受保护项：`AGENTS.md`、`agent/goals/`（untracked）、`acceptance/m2_stage2i2r_*` 既有 1 行编辑、
  `stash@{0}`、默认 DB。
- 环境：Python 3.13.9；akshare 1.18.79；baostock 0.9.3；pandas 2.3.3；duckdb 1.5.5。

## 实施计划

1. 建工作记录（本文件）。
2. 新增 `provider_roles.py`（role 合同、fail-closed、legacy adapter）。
3. `market_reconciliation.py` 增加 v2 合同（保留 v1 完全向后兼容）。
4. `artifact_manifest.py` 注册 R4E.4 manifest schema。
5. 新增 R4E.4 薄 CLI（promote / registry-draft / reconcile / verify / fixtures）。
6. `m2_stage2k1r4e_series_preflight.py` formal 按 role 解析 + v4 分支。
7. 新增设计文档 `docs/selected_secondary_provider_integration_contract.md`。
8. 真实执行：promote → registry v4 draft → formal reconciliation → finalize registry v4 →
   formal candidate v2（A/B 两次，字节/identity 比较）→ 双 oracle → migration v2 →
   coverage → decision → manifest。
9. 新增测试。
10. 全量验证（pytest/ruff/compileall/git diff --check/manifest/pollution/protected/R4C1 重生成）。
11. 写 acceptance 与本记录结果。

## 决策记录

| 决策 | 采用原因 | 考虑过的替代方案 | 未采用原因 | 潜在风险 |
| --- | --- | --- | --- | --- |
| provider-role 合同：registry v4 用 provider_id/provider_role/transport_library/underlying_provider | 消除 primary=baostock / secondary=akshare 业务硬编码 | 继续用 provider 名 | 掩盖角色与来源分离 | 无 |
| 维持 v1 合同完全向后兼容（旧 registry v2/v3 可读，历史工件摘要不变） | 不破坏 R4E.1/R4E.2 既有合同与测试 | 直接改 v1 合同 | 破坏历史可复现性 | 无 |
| 复用 R4E.3 精确 Tencent 对象（内容寻址复制，字节全等），不重新请求 | 确定性、可审计、避免无意义网络请求 | 重新 acquire | 引入变化风险 | 无 |
| registry v4 分两步：draft（PENDING）→ 真实 reconciliation 后 COMPLETE | 禁止先写 pass 再运行 validator | 一步建成 | 掩盖真实验证 | 无 |
| formal reconciliation 用 v2 合同（绑定 role/identity/table digest/daily digest） | 复用真实 verifier 重算 | 复用 R4E.3 comparison digest | R4E.3 是 preflight 非 formal | 无 |
| 正式 candidate 用既有 formal CLI + `--market-registry v4` | 单一入口、显式指定 registry | 新建大型 CLI | 增加不必要复杂度 | 无 |
| 迁移 v2 比较 v1 已发布 candidate vs v2 正式 candidate | 证明经济值不变 | 只比较 identity | 无法证明经济值 | 无 |
| CI 只用 synthetic 双源 fixtures；正式 ALLOWED 只能来自本地真实 external cache | 不依赖外部真实 Parquet | CI 用真实对象 | 泄漏/不可复现 | 无 |

## 实际操作

按计划实施并真实执行：

1. 新增 `src/ashare_research/pit_valuation/provider_roles.py`：role 合同，
   `resolve_registry_providers` fail-closed（0 或 >1 primary/secondary -> ProviderRoleError），
   legacy adapter（baostock->primary, akshare->secondary）。
2. `market_reconciliation.py` 增加 v2 合同
   `pit_valuation_market_double_source_reconciliation_v2`：`load_and_validate_market_object_entry`
   （支持 v4 role 条目 + legacy），`reconcile_market_close_series_v2`、`build_mismatch_ledger_v2`、
   `build_reconciliation_digest_v2`（绑定 role identity）、`build_reconciliation_report_v2`、
   `validate_reconciliation_report_v2`。v1 合同输出保持字节全等。
3. `artifact_manifest.py` 注册 `m2_stage2k1r4e4_artifact_manifest_v2`（ALLOWED + V2_SCHEMAS），
   重生成 R4C1 manifest（diff 仅 artifact_manifest.py SHA/长度）。
4. 新增 R4E.4 薄 CLI `m2_stage2k1r4e4_secondary_provider_integration.py`
   （promote / registry-draft / reconcile / verify / fixtures）。promote 复用 R4E.3 对象
   `d760923a…` 字节全等复制，不重新请求、无 Sina fallback；抽出 `validate_endpoint_identity`
   独立可测。
5. `m2_stage2k1r4e_series_preflight.py` formal 按 role 解析 + v4 分支，新增
   `_cmd_formal_r4e4`（v2 migration、dual oracle、coverage、R4E.4 decision、manifest v2），
   manifest 绑定 acceptance/config/docs/code/tests（`R4E4_DEFINITION_FILES`，22 文件）。
6. 新增设计文档 `docs/selected_secondary_provider_integration_contract.md`。
7. 真实执行（本地 external cache `tmp/`）：
   - promote：`reports/petrochina_tencent_snapshot_promotion_receipt_v1.json`
     （`byte_identity_preserved=true`，`d760923a…`）。
   - registry v4 draft（PENDING_REAL_RECONCILIATION/pending）→ formal reconciliation →
     冻结 COMPLETE/pass。
   - formal candidate v2 两次（A 与 B，`tmp/r4e4-candidate*`），字节/identity 全等；
     最终发布到 `reports/`：`m2_stage2k1r4e_series_preflight formal --market-cache-root
     tmp/r4e4-cache --market-registry events/market_data_snapshot_registry_v4.json
     --output-root reports`，exit 0，`formal_reconciliation_digest=4fb3382b25e5…`。
   - 结果：4053 obs、ALLOWED、coverage 3y/5y READY、dual oracle all_identical、
     migration ratio/status/market-close = 0/0/0。
8. 新增测试 `tests/test_m2_stage2k1r4e4_selected_provider_integration.py`（40 个）。
9. 新增 acceptance `acceptance/m2_stage2k1r4e4_selected_secondary_provider_integration.md`。
10. 全量验证（见下）。

## 数据与方法说明

- 数据来源：复用 R4E.3 已/真实预检的 Baostock 主源 `c6771aa5…` 与 Tencent 次源 `d760923a…`
  （transport akshare，underlying tencent，endpoint `web.ifzq.gtimg.cn`）。
- 接口/文件：内容寻址 parquet（`tmp/r4e4-cache/baostock/c6771aa5….parquet`、
  `tmp/r4e4-cache/r4e4/tencent_via_akshare/d760923a….parquet`）。
- 数据日期范围：2021-01-04..2026-07-31，1351 个交易日，adjustment=none。
- 复权方式：不复权（unadjusted）；close 为原始收盘。
- 单位：close CNY；volume shares；amount CNY。
- 缺失值处理：candidate 缺失 -> 不自动补零；status=missing_ttm_input 保留。
- 财报公告日期：financial-state timeline 按实际 available_at/effective_from 生效（既有合同）。
- 未来数据泄漏：无；join 为 backward-only（`effective_from <= trade_date`），双 oracle 核对。
- 统计假设：close 容差 0.01；双源 economic 比较用 Decimal 归一化（`6.0 == 6`）。
- 证据等级：真实本地双源 reconciliation = TRUSTED；CI 仅 synthetic fixtures。

## 验证

- R4E.4 新测试：**40 passed**（offline）。
- R4E.3 + R4E.4：**99 passed**。
- 全量 pytest：**1639 passed, 2 pre-existing warnings**（ruff 修复后重跑确认）。
- `ruff check`（全部改动的 src + tests）：All checks passed。
- `compileall src/ashare_research`：pass。
- `git diff --check`：pass。
- R4E.4 manifest：`status: pass`，22 文件（registry/receipt/reconciliation v2/ledger v2/
  candidate v2/timeline/coverage/audit/dual/migration/decision/acceptance/config/docs/code/tests），
  0 missing / 0 mismatch。
- R4C1 manifest：`status: pass`（重生成后；diff 仅 artifact_manifest.py SHA/长度）。
- 污染/密钥扫描（新 src/config/reports）：NONE（无绝对路径、proxy、token）。
- 受保护项：`AGENTS.md`、`agent/goals/`、`acceptance/m2_stage2i2r_*` 既有 M、`stash@{0}`、
  默认 DB 均未改动。
- 确定性：candidate v2 reports 与 B 运行字节全等；registry v4 保持 COMPLETE/pass。

## 结果

- 已完成：provider-role 合同、registry v4（COMPLETE/pass）、Tencent 字节全等 promote、
  formal reconciliation v2（1351 天，max diff 0，digest `4fb3382b25e5…`）、
  非生产 candidate v2（4053 obs）、economic migration v2（0/0/0）、dual oracle、
  coverage gate READY、R4E.4 decision ALLOWED、manifest v2（22 文件）、测试、acceptance。
- 未完成：无功能缺口。
- 当前是否可用：本地验证完成，结果可复现。
- 条件通过：无（全部 PASS）。
- 未提交未推送（按用户指令停止）。

## 遗留问题

- R4E.4 工件全部未提交（等用户明确授权后再 commit/push）。
- 未计算历史 percentile（下一阶段，等授权）。

## 下一步建议

- R4E.4 之后：historical valuation percentile preflight（下一阶段，等授权）。

## 最终文件变更

- 新增：`provider_roles.py`、`m2_stage2k1r4e4_secondary_provider_integration.py`、
  `events/market_data_snapshot_registry_v4.json`、`docs/selected_secondary_provider_integration_contract.md`、
  `tests/test_m2_stage2k1r4e4_selected_provider_integration.py`、
  `acceptance/m2_stage2k1r4e4_selected_secondary_provider_integration.md`、
  R4E.4 各 reports（decision/manifest/receipt/reconciliation v2/ledger v2/timeline/candidate v2/
  coverage/audit/dual/migration v2）、本记录。
- 修改：`market_reconciliation.py`、`artifact_manifest.py`、`m2_stage2k1r4e_series_preflight.py`、
  `reports/m2_stage2k1r4c1_artifact_manifest.json`（重生成）。
- 未改动：registry v3、R4E.3 decision、默认 DB、受保护项。

## 最终 Git 状态

- 分支：`feat/m2-value-assessment-mvp`；HEAD：`473cd67`（本地 == origin）。
- R4E.4 新增/修改按三笔提交推送（见下 提交记录）。
- 未创建 tag/release；未 force push；未 reset --hard；未 merge main。
- 按用户指令：完成远程 CI 前阶段状态保持 `PASS — LOCAL CANDIDATE`；CI 全绿后追加 closeout 提交。

## 提交记录

- Commit 1 `feat: integrate selected secondary market provider`：provider-role 合同、
  market_reconciliation v2、formal CLI role 解析、R4E.4 integration CLI、integration contract、
  registry v4、promotion receipt、reconciliation v2、ledger v2、相关 tests、
  artifact_manifest schema、R4C1 manifest 迁移。
- Commit 2 `feat: release formal PIT valuation candidate v2`：timeline v2、candidate v2、
  coverage v2、audit v2、dual oracle v2、identity migration v2、R4E.4 decision、正式 tests。
- Commit 3 `docs: record R4E.4 local closeout`：acceptance、work record、最终 R4E.4 manifest。
- push：`git push origin feat/m2-value-assessment-mvp`（普通 push）。