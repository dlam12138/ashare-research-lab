# 工作记录：M4 provider evidence acquisition v2

## 基本信息

- 日期：2026-09-22
- Agent：Codex（父代理）+ DSH（有界只读评审）
- 当前分支：`codex/m4-provider-evidence-acquisition-v2`
- 开始提交：`e42ad8acdfb5c29f980c4258013da39ce6b14309`
- 任务来源：用户逐项确认 v2 授权字段并授权
  `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`
- 对应模块：机制验证 / 数据底座 / 工程治理

## 任务目标

在 v2 契约的防火墙内尝试一次 FRED Brent 序列的证据型受限传输探针；若前置许可门禁不成立，则在网络访问前失败关闭。

## 范围

仅允许 Goal 中列出的授权、dossier（仅在探针实际运行时）、本记录、验收文件以及被忽略的 SHA256 命名原始响应。

## 非目标

不做适配器、真实研究、统计、数据库或 holdout 操作，不扩展主机/端点，不修改 v1，不合并后续阶段。

## 开始前状态

- 新工作树从 PR #26 合并提交建立；初始工作树干净。
- 用户批准一个主机、一个端点、一个新 dossier、固定五日窗口和两个字段。
- v2 契约要求原始响应留存必须有第一方许可依据；用户的项目内留存批准不能替代发布方许可。
- 已批准端点清单仅含 CSV 端点，不含许可或条款页面，这是预检的关键风险。

## 实施计划

1. 固化 Goal 与授权 JSON。
2. 由 DSH 对契约、授权和 licence-before-network 门禁做只读预检。
3. 父代理独立复核；仅在许可门禁通过时运行一次探针。
4. 生成结果/阻塞证据，验证差异、保护基线和同步状态。

## 决策记录

- 决策：不把“用户允许留存”解释为“发布方允许留存”。
- 原因：v2 契约要求第一方 licence artifact，并规定 retention 未证明时必须停止或拒绝。
- 替代方案：直接请求 CSV 后再判断；未采用，因为可能在许可未证明时产生必须保留但无权保留的原始字节。
- 风险：若授权不包含许可端点，本阶段可能在网络前 `BLOCKED`。

## 实际操作

1. 核验 PR #26 已合入远端 `main`。
2. 从 `origin/main@e42ad8a` 创建独立分支与工作树。
3. 阅读 v2 Goal、设计、机器契约、v1 manifest、工作规范和最近记录。
4. 建立本 Goal 与工作记录。
5. 首轮 DSH 只读预检返回 `BLOCKED`：原授权仅含 CSV 端点，缺少可建立第一方许可制品的端点；未发出网络请求。
6. 用户随后明确新增授权 FRED legal、FRED series 与 EIA copyright/reuse 三个只读端点，并要求沿用原超时、零重试、速率、响应上限和 evidence-only 限制。

## 数据与方法说明

- 计划数据源：FRED public graph CSV，系列 `DCOILBRENTEU`。
- 授权窗口：2015-03-09 至 2015-03-13。
- 授权字段：`DATE`, `DCOILBRENTEU`。
- 复权：不适用；单位预期为 USD/barrel，但不得在未验证响应时宣称。
- 缺失值：不做填充；仅证据扫描。
- 未来数据：严格日期防火墙，禁止开发期和 holdout 日期。
- 统计：不执行。

## 验证

- 首轮 DSH 预检：`BLOCKED`；正确阻止了未授权许可端点之外的网络访问，并确认授权摘要和 11 个必填字段。
- FRED legal GET：15 秒读超时，失败；零重试；无字节落盘。
- EIA copyright/reuse GET：HTTP 200，52,317 bytes，SHA-256
  `4758216ebe7e50dc7a62b97234b4d208c3d48ffc92f1a0b81f1c78d26508b8d6`；最终 host/path 与 allowlist 完全一致；原始字节保存在被忽略的 SHA256 路径。
- FRED series GET：15 秒读超时，失败；零重试；无字节落盘。
- 三次请求均为 HTTPS GET、无凭据、响应上限 1 MiB；请求启动间隔不少于 15 秒。
- FRED 两个第一方页面均失败，因此未运行第四个 CSV 请求，未接触任何观测值。
- 最终 JSON、Git、保护基线与 DSH 复核命令及结果见验收文件。
- 严格 JSON、三份摘要重算、授权字段、编码、raw identity、dossier 缺失、
  `git diff --check` 均通过。
- 最终 DSH 只读复核：`PASS`（确认 `BLOCKED` 结果被正确记录并执行）；其提出的
  “in authorization order”措辞歧义已改为“within the authorized licence/identity set”。

## 结果

`BLOCKED`。EIA 第一方页面提供了可复用范围证据，但 FRED legal 与 series
均超时，无法建立当前 FRED 传输身份与适用条款。依照 mandatory gates，停止在
CSV 请求之前；没有创建或消耗 v2 dossier ID。

## 遗留问题

FRED 第一方许可和系列身份仍未取得。当前零重试授权已消耗对应请求，不能在本阶段重试。

## 下一步建议

如需继续，必须由用户另行授权新的 FRED 端点或一次新的受限重试；不得自动回退到镜像或替代 provider。

## 最终文件变更

- `agent/goals/2026-09-22_m4_provider_evidence_acquisition_v2.md`
- `evidence/m4/provider_evidence_authorization_v2.json`
- `agent/record/2026-09-22_01_m4-provider-evidence-acquisition-v2.md`
- `acceptance/2026-09-22_m4_provider_evidence_acquisition_v2.md`

另有一个 Git 忽略的原始许可页文件，不会暂存或提交。

## 最终Git状态

最终 DSH 复核通过后，父代理只暂存四个授权路径并完成：

- 制品提交：`6f8d8e1`（`docs: record blocked M4 provider evidence probe v2`）；
- 使用显式 refspec 推送至
  `origin/codex/m4-provider-evidence-acquisition-v2`；
- 创建 PR #27：`https://github.com/dlam12138/ashare-research-lab/pull/27`。

本交接更新仅修改本记录与验收文件。未合并 PR，未启动重试、CSV 探针、
adapter 或其它下一阶段。
