# 工作记录：M4 多假设合成可复现验收

## 基本信息

- 日期：2026-09-13
- Agent：Codex 规划与独立验收；一个 Luna worker 执行有界测试实现
- 当前分支：`codex/m4-multi-hypothesis-acceptance`
- 开始提交：`dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`
- 任务来源：用户要求继续推进；上轮 M4 core readiness review 发现多合法假设与跨环境身份验收缺口
- 对应模块：机制验证 / 工程治理

## 任务目标与范围

按[任务契约](../goals/2026-09-13_m4_multi_hypothesis_synthetic_acceptance.md)，只新增一个聚焦的多假设合成验收测试、本记录和验收文件。不修改产品代码、既有测试、冻结合同、真实数据或其他工作树。

## 开始前状态

从干净 `origin/main@dec8a29` 建立独立工作树；本地 main、origin/main 和实时远端一致，无开放 PR。原 M2 脏树与 stash 保留；默认数据库只做文件 SHA256，值为 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。现有编排器仅接收调用方合成策略输入；现有测试多以一个基础 fixture 为主。当前未修改产品或执行真实研究。

## 实施计划

1. Codex 冻结 Goal 和初始记录并作本地提交。
2. Luna 在白名单内新增两个合法合成请求的验收测试；运行契约指定的聚焦回归与 Ruff。
3. Luna 补写实际命令、结果、偏差、遗留问题和验收文档；仅在白名单内本地提交。
4. Codex 独立审查实际分支、diff、测试、保护状态与授权边界。

## 决策记录

采用只比较合同、计划、数据集和矩阵规范身份的预执行 fingerprint；执行数值与运行时版本不进入跨系统固定身份断言。原因是现有执行产物明确绑定数值运行时，直接比较完整信封字节会把环境差异误判为前置规格漂移。完整信封跨系统字节相等不是本阶段验收结论。

## 实际操作与验证

已新增聚焦验收测试与验收文件。两个请求分别使用 LTE/两个控制/启用 bootstrap 和 GTE/一个控制/禁用 bootstrap；固定 pre-execution fingerprint 分别为 `f7873a6fae2992f148ad3118fdbe139d418cdb2475205b586a80d12a225e1329` 与 `0a9e300b9ee2c5953b524d83fce7b6a473a7adb6ed1ae5887a3a9521ede151bb`。交换绑定输入按预期以 `PIPELINE_INPUT_BINDING_MISMATCH` 失败。

## 验证

- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py`：exit 0，3 passed。
- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py`：exit 0，370 passed。
- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_m4_multi_hypothesis_portability.py`：exit 0。
- `git diff --check`、`git diff --cached --check`：通过。
- 子进程从临时其他 CWD 重建请求并复现两个 fingerprint：通过。

本地 Windows 和跨进程/CWD 验证通过；Ubuntu CI 尚未执行，完整 envelope 跨 OS 字节一致性不作声明。

## 结果、遗留问题与下一步建议

已完成本地合成多假设验收。真实数据适配、真实候选、holdout 与跨 OS CI 实际结果不属于本地交付；不据此声称 M4 完成。

## 最终文件变更与 Git 状态

新增 `tests/test_m4_multi_hypothesis_portability.py` 与 `acceptance/2026-09-13_m4_multi_hypothesis_synthetic_acceptance.md`，更新本记录。默认只本地提交，不推送、不建 PR、不合并。
