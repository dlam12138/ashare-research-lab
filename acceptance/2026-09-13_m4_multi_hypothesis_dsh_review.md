# DSH 多假设合成验收核查

Verdict: **BLOCKED**。本次仅评估 DSH 独立核查是否完成；不撤销先前主机侧本地合成验收，也不宣称 M4 或跨 OS 复现已完成。

任务契约：[DSH 核查 Goal](../agent/goals/2026-09-13_m4_multi_hypothesis_dsh_review.md)；实际过程：[工作记录](../agent/record/2026-09-13_02_m4-multi-hypothesis-dsh-review.md)。基线为本地分支 `codex/m4-multi-hypothesis-acceptance@1e3a514b61ece0f134011c4b84a60ca1931e31cc`，随后 Codex 提交 Goal 与初始记录 `6f91c87`；`main`/`origin/main`/实时远端仍为 `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`。

DSH 读取真实接口和 CI 工作流，审查两个请求的合法性、输入摘要重绑定、不同条件/控制/bootstrap、固定执行前指纹和其他 CWD 子进程路径；未发现已确认的语义缺陷，也没有修改验收测试。它启动的聚焦 pytest 退出码为 1，失败位于 DSH 沙箱中 Python 临时目录的清理阶段（`PermissionError: [WinError 5]`），不是一个可据此判定的产品断言失败。用户要求在一个小阶段后结束，Codex 因而停止 DSH 后续诊断。DSH 未完成计划中的回归、Ruff 或最终提交；不将历史主机测试伪称本轮 DSH 结果。

本次只新增/更新 Goal、记录和本文件。原 M2 HEAD、stash、默认数据库 SHA256 与本地/远端 main 均未因本轮改变。DSH 在被 Git 忽略的 `tmp/dsh-temp/tmpqb9tc2rv` 留下空目录；自动命令审查以 `blocked by policy` 拒绝清理，故保留并披露。没有推送、PR、合并、真实数据、holdout 或下一阶段执行。Ubuntu/Windows CI 仍未在本分支运行。
