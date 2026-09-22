# 工作记录：M4 provider evidence acquisition v2 retry

## 基本信息

- 日期：2026-09-22
- Agent：Codex（父代理）+ DSH（有界只读评审）
- 当前分支：`codex/m4-provider-evidence-acquisition-v2-retry`
- 开始提交：`6c76e6f63679c5751349bf19c06ccbf58f3427b6`
- 任务来源：用户明确授权新一轮 FRED 受限证据请求并要求持续推进
- 对应模块：机制验证 / 数据底座 / 工程治理

## 任务目标

在新增 FRED API 条款端点与本轮单次明确授权内完成许可、身份门禁；每个端点只允许一次请求且 `retry_count=0`，仅在全部门禁通过后运行一次既定 CSV 证据探针。

## 范围

仅限 Goal 列出的六个候选跟踪文件、忽略的 v2 quarantine 原始字节和忽略的临时工具。

## 非目标

不做 provider fallback、适配器、真实研究、统计、数据库或 holdout 操作，不合并或自动进入下一阶段。

## 开始前状态

- PR #27 已合入 `main@6c76e6f`，42 项 CI 全绿。
- 在原隔离工作树从最新 `origin/main` 创建新分支，保留同工作树内既有 EIA 原始证据。
- EIA raw identity 复核为 52,317 bytes / `4758216e…08b8d6`。
- 前一轮 FRED legal 与 series 均在 15 秒内超时，未重试、未留存字节；CSV 未请求。

## 实施计划

1. 固化新 Goal 与新授权 JSON。
2. DSH 只读预检授权、基线和四请求防火墙。
3. 顺序执行三个许可/身份请求并判定门禁。
4. 仅在门禁通过时执行 CSV，构造 proof、licence artifacts 与 dossier。
5. 独立验证、DSH 终审、精确提交、推送和 PR。

## 决策记录

- 决策：沿用同一隔离工作树中的 EIA SHA256 原始证据，不复制其它工作树 raw。
- 原因：该文件由上一已合入阶段在同一 v2 quarantine 命名空间产生且摘要未变。
- 风险：FRED 页面仍可能超时、重定向或不能明确支持所需留存范围；任一情况均在 CSV 前失败关闭。

## 实际操作

1. 核验 PR #27 合并、远端 `main`、stash、M2 与数据库保护值。
2. 从 `origin/main@6c76e6f` 创建新分支并复核 EIA raw identity。
3. 建立本 Goal 与本记录。
4. DSH 只读预检返回 `PASS`；要求执行前收紧旧临时脚本 allowlist、按授权 JSON 对全轮累计响应执行 1 MiB 上限，并澄清本记录的零重试措辞。三项均在网络前修正。
5. 更新忽略的临时 fetch helper：allowlist 仅含本轮四个 FRED 端点；新增端点去重、四请求计数、15 秒启动间隔、全轮 1 MiB 累计预算、精确 CSV query 校验和忽略账本。
6. 请求 `fred.stlouisfed.org/docs/api/terms_of_use.html`：15 秒读超时，`TimeoutError`；零重试、零响应字节、零 raw 文件。
7. 请求 `fred.stlouisfed.org/legal/`：15 秒读超时，`TimeoutError`；零重试、零响应字节、零 raw 文件。
8. 请求 `fred.stlouisfed.org/series/DCOILBRENTEU`：15 秒读超时，`TimeoutError`；零重试、零响应字节、零 raw 文件。
9. 三个请求启动时间分别为 `05:46:57Z`、`05:47:23Z`、`05:47:48Z`，间隔均大于 15 秒。账本 `629` bytes，SHA256 `acbb16e3165bc57743a6a7a7c8e69ba6a57d9a63939cf1c82efe51d534ca1674`，仅位于忽略的 `tmp/`。
10. licence 与 endpoint identity mandatory gates 均未通过；未执行第四个 CSV 请求，未创建 licence artifact 或 dossier。
11. DSH 最终只读复核返回 `PASS`，独立复算授权与合同摘要、请求账本、速率/超时/零重试约束、条件产物缺失及全部保护值，确认 `BLOCKED` 失败关闭结论正确。

## 数据与方法说明

- 数据源：仅用户批准的 FRED 第一方条款、legal、series 和条件式 CSV 端点；既有 EIA 第一方复用页。
- CSV 窗口：2015-03-09 至 2015-03-13；字段 `DATE`,`DCOILBRENTEU`。
- 复权/缺失值/统计：不适用；不填充、不聚合、不解释数值。
- 未来信息：日期扫描防火墙，任何超窗、开发期或 holdout 日期失败关闭。

## 验证

- DSH 预检：`PASS`，核验分支、基线、授权摘要、四请求 envelope、未使用 dossier ID、EIA raw 和保护值。
- 严格 JSON、摘要、授权字段、编码、账本、raw inventory、dossier/licence absence、Git 和保护状态验证见验收文件。
- 最终 DSH 只读复核：`PASS`；无文件修改、网络请求、数据库引擎访问、递归委派或 Luna fallback。

## 结果

`BLOCKED`。三个获批 FRED 第一方端点均超时，无法建立 licence 或 endpoint identity；按 Goal 在 CSV 前失败关闭。适用代码为 `REAL_LICENSE_EVIDENCE_MISSING`，并同时保留 endpoint identity 未证明的事实；未消耗 dossier ID。

## 遗留问题

FRED 第一方条款与系列页面在当前 15 秒、零重试传输条件下均不可达。授权范围内没有剩余的许可/身份请求。

## 下一步建议

若继续，需要改变外部传输条件或新增明确授权；不得自动使用镜像、第三方页面、凭据或 provider fallback。

## 最终文件变更

- `agent/goals/2026-09-22_m4_provider_evidence_acquisition_v2_retry.md`
- `evidence/m4/provider_evidence_authorization_v2_retry_01.json`
- `agent/record/2026-09-22_02_m4-provider-evidence-acquisition-v2-retry.md`
- `acceptance/2026-09-22_m4_provider_evidence_acquisition_v2_retry.md`

无 licence artifact 或 dossier。既有 EIA raw 与本轮请求账本保持 Git 忽略，不会暂存。

## 最终Git状态

- 证据提交：`7b65bb5`（`docs: record blocked FRED evidence retry`）。
- 已精确推送至 `origin/codex/m4-provider-evidence-acquisition-v2-retry`。
- PR：https://github.com/dlam12138/ashare-research-lab/pull/28
- PR/CI 交接证据由后续仅文档提交回填；未合并。
