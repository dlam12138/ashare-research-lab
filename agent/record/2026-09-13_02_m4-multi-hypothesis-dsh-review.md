# 工作记录：DSH 独立核查 M4 多假设合成验收

## 基本信息

- 日期：2026-09-13
- Agent：DeepSeek Harness 执行；Codex 独立验收
- 分支：`codex/m4-multi-hypothesis-acceptance`
- 开始提交：`1e3a514b61ece0f134011c4b84a60ca1931e31cc`
- 任务来源：用户指定改用 DSH 推进
- 对应模块：机制验证 / 工程治理

## 目标、范围和非目标

按[DSH 核查契约](../goals/2026-09-13_m4_multi_hypothesis_dsh_review.md)独立审查现有合成多假设验收，发现真实缺陷时只在白名单内修正。不修改产品源码、冻结研究合同、真实数据、其他工作树；不推送、建 PR 或合并。

## 开始前状态

当前工作树干净，本地分支 HEAD 为 `1e3a514b61ece0f134011c4b84a60ca1931e31cc`；local/origin/live main 为 `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`。原 M2 HEAD、stash 和默认数据库 SHA256 分别为 `3679b1bac7a1634c6452784a4d8f6d139966f222`、`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`、`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。

## 实施计划与决策

DSH 阅读真实接口、测试、契约和 CI，再运行聚焦验证。只有发现可复现缺陷才改验收测试；记录实际失败与修复。完整 envelope 包含数值运行时，不将其字节相等当作本阶段的跨系统结论。Codex 对 DSH 交付独立审查。

## 实际操作与验证

Codex 通过 `dsh --profile headless` 在本工作树启动 DSH。DSH 读取本契约、记录、真实配置/编译/适配/编排接口、合成测试辅助函数和 `.github/workflows/stage2g-reproducibility.yml`。它核实两个请求的控制角色与合约绑定、`GTE` 和禁用 bootstrap 的合法性、交换绑定输入的公共入口首错，以及该 CI 工作流在 push/PR 时于 Ubuntu/Windows 上执行全量 `pytest -q`。这些是源码审查证据，不是该分支的 CI 结果。

DSH 运行聚焦 pytest 时退出码为 1；其执行输出将失败定位在 `test_pre_execution_fingerprints_reproduce_in_fresh_process_from_other_cwd` 的 `tempfile.TemporaryDirectory()` 清理阶段：DSH 沙箱拒绝枚举/删除新临时目录（`PermissionError: [WinError 5]`）。DSH 报告子进程及指纹比较在清理前已执行，但没有完成一份通过的聚焦测试报告。它未发现已确认的产品或测试语义缺陷，未修改产品源码或验收测试。用户随后要求“推进到一个小阶段就结束”，Codex 用 Ctrl+C 停止 DSH 后续环境诊断；DSH 进程退出码为 1。原本计划的 DSH 回归、Ruff、最终验收文件和 DSH 本地提交均未完成，不能写成通过。

本地上一阶段的主机侧聚焦测试 `3 passed`、九文件回归 `370 passed` 和 Ruff 通过仍是先前证据，不冒充本次 DSH 重跑。Ubuntu/Windows CI 未在该分支运行，不能宣称跨 OS 指纹已验证。

DSH 在被 Git 忽略的 `tmp/dsh-temp/tmpqb9tc2rv` 留下空目录。Codex 只读确认该目标位于本工作树且目录为空；`Remove-Item` 递归与非递归清理命令均被自动命令审查以 `blocked by policy` 拒绝，故目录保留。不尝试跨 shell 绕过。未打开默认数据库，未修改原 M2 工作树或 stash。

## 结果、遗留问题与下一步建议

本次 DSH 核查为 **BLOCKED**：完成部分源码/CI 审查，但沙箱清理错误及用户要求停止使 DSH 验证与交付不完整。现有多假设本地验收结果仍有效；本次不追加通过结论。若将来继续，先处理临时残留并在可完成临时目录清理的环境重跑聚焦测试；推送/PR 和真实研究仍须分别授权。

## 最终文件变更与 Git 状态

本次新增本契约和记录，Codex 在 DSH 中断后更新本记录并新增 `acceptance/2026-09-13_m4_multi_hypothesis_dsh_review.md`。未修改 `src/**` 或既有测试，未推送、未建 PR、未合并。最终提交与工作树状态由 Codex 独立核查并在最终证据包报告；被 Git 忽略的空目录仍在磁盘上。

## 用户授权的限缩恢复（待执行）

用户要求继续，但本次仅推进到一个小阶段。Codex 先在同一[任务契约](../goals/2026-09-13_m4_multi_hypothesis_dsh_review.md)追加限缩恢复条款：DSH 不再创建或清理临时目录，只跑两个不使用该 fixture 的测试，并从现有不同 CWD 的子进程重算两个固定指纹。历史 `BLOCKED` 验收不改写；恢复结果另写 `acceptance/2026-09-13_m4_multi_hypothesis_dsh_resume.md`。本段为执行前记录，不预填验证结果。
