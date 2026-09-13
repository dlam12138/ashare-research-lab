# DSH 多假设合成验收：限缩恢复核查

Verdict: **PASS**（限缩：仅适用于“恢复的本地 DSH 核查”这一范围）。

本判定只覆盖四件事：分支/HEAD 与干净跟踪工作树、排除 tempfile 用例后的聚焦测试、从既有不同 CWD 的全新子进程重算两个固定指纹、Ruff 与 Git 空白检查。它**不**表示原始三测试命令已在 DSH 内整体通过，**不**表示 Ubuntu/Windows CI 已在本分支运行，也**不**宣布 M4、跨 OS 复现或真实研究完成。

- 任务契约：[DSH 核查 Goal](../agent/goals/2026-09-13_m4_multi_hypothesis_dsh_review.md)（含 2026-09-13 限缩恢复条款）
- 实际过程：[工作记录](../agent/record/2026-09-13_02_m4-multi-hypothesis-dsh-review.md)
- 前置历史判定：[DSH 核查验收（BLOCKED）](2026-09-13_m4_multi_hypothesis_dsh_review.md)
- 恢复起点：`codex/m4-multi-hypothesis-acceptance@8a69de050c5caa6cee8d01a59b9b69e0671fa580`，跟踪工作树干净

## 实际检查与结果

| 检查 | 命令（要点） | 实际结果 |
| --- | --- | --- |
| 分支/HEAD/工作树 | `git rev-parse HEAD`、`git status --short --branch` | HEAD `8a69de0`；仅 `[ahead 5]`，无修改/暂存文件 |
| 聚焦测试 | `pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py -k "not pre_execution_fingerprints_reproduce_in_fresh_process_from_other_cwd"` | `2 passed, 1 deselected in 12.21s`，退出码 0 |
| 子进程指纹复现 | 全新子进程，CWD `D:/量化分析-m4a2i`，`PYTHONPATH` 指向本工作树 `src`+`tests`，断言两例等于 `EXPECTED_FINGERPRINTS` | 退出码 0；`SYNTH_DAILY_CONTROLLED_001` = `f7873a6fae2992f148ad3118fdbe139d418cdb2475205b586a80d12a225e1329`；`SYNTH_DAILY_THRESHOLD_002` = `0a9e300b9ee2c5953b524d83fce7b6a473a7adb6ed1ae5887a3a9521ede151bb` |
| Ruff | `python -m ruff check tests/test_m4_multi_hypothesis_portability.py` | `All checks passed!`，退出码 0 |
| Git 空白 | `git diff --check`、`git diff --cached --check` | 两者均无输出，退出码 0 |

子进程指纹的两例配置与契约完全一致：第一例 `LTE` / `-0.0100` / 两个控制 / bootstrap True；第二例 `GTE` / `0.0100` / 一个控制 / bootstrap False。该子进程还打印来源以排除跨工作树遮蔽：测试模块解析为本工作树 `tests/test_m4_multi_hypothesis_portability.py`，管线模块解析为本工作树 `src/ashare_research/mechanism/pipeline/__init__.py`。本步骤及本轮全部检查均未创建、枚举或删除任何临时目录。

保护基线只读复核结果：`main`、`origin/main` 与实时 GitHub `main` 均为 `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`；stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`；原 M2 工作树 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`，均未变化。

## 明确保留的历史结果与披露

- 历史 `acceptance/2026-09-13_m4_multi_hypothesis_dsh_review.md` 的 `BLOCKED` 判定保持原文，未被改写或撤销；本文件只是该恢复条款下的独立限定结论。
- 被 Git 忽略的空目录 `tmp/dsh-temp/tmpqb9tc2rv` 仍在磁盘上：本次按恢复条款不创建、不枚举、不清理。
- 被排除的 `test_pre_execution_fingerprints_reproduce_in_fresh_process_from_other_cwd` 本轮仍未在 DSH 内执行，**不计为通过**；其子进程断言逻辑已由第 2 步等价复算，而非原命令整体通过。
- 历史主机侧证据（聚焦 `3 passed`、九文件回归 `370 passed`、Ruff 通过）保持独立标识，未冒充本轮 DSH 重跑。
- Ubuntu/Windows CI 仍未在本分支运行；本地 Windows 与子进程证据不能闭合真实跨 OS CI。

## 边界与未覆盖项

- DSH 未修改 `src/**`、既有测试、CI、依赖、真实输入、holdout 或下一阶段设计。
- 未推送、未建 PR、未合并；本分支仍为本地分支。
- DSH 未重算默认数据库 SHA256，按契约由 Codex 独立复核。
- 本轮 DSH 交付（记录更新与本文件）**未提交**：`git add` 报 `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-multi-hypothesis-acceptance/index.lock': Permission denied`。共享 `.git` 位于会话工作区之外，写入被沙箱拒绝；DSH 按指示不绕过，交由 Codex 提交。工作树中两项文件状态为 ` M`（记录）与 `??`（本文件）。

## 后续

由 Codex 独立复核最终文件、Git 状态、远端、stash 与数据库后给出最终判定；未经授权不进入下一阶段。
