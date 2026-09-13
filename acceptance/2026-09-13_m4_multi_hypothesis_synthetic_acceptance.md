# M4 多假设合成可移植性验收

日期：2026-09-13
分支：`codex/m4-multi-hypothesis-acceptance`
基线：`c0279ef87b8f9dc8c5f0e0419867c1ec6ffc7d71`（Goal 提交，基于 `origin/main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`）

## 验收内容

新增测试通过公共 `run_synthetic_pipeline(request=...)` 构造并运行两个结构不同的调用方合成请求：

- `SYNTH_DAILY_CONTROLLED_001`：`LTE -0.01`、两个有序控制、启用移动块 bootstrap；
- `SYNTH_DAILY_THRESHOLD_002`：`GTE 0.01`、一个有序控制、禁用 bootstrap。

两条请求均通过各自 envelope 校验；合同、计划、数据集和矩阵身份均不同。每条请求的 `input_digest` 都由自身合同、计划、域、绑定和观测重新计算。将第二条请求的绑定输入交换到第一条请求时，公共入口以 `PIPELINE_INPUT_BINDING_MISMATCH` 失败，未产生部分接受 envelope。

预执行 fingerprint 只由四个身份字段组成：`contract_identity`、`plan_identity`、`dataset_identity`、`matrix_identity`。固定值为：

```text
SYNTH_DAILY_CONTROLLED_001 = f7873a6fae2992f148ad3118fdbe139d418cdb2475205b586a80d12a225e1329
SYNTH_DAILY_THRESHOLD_002  = 0a9e300b9ee2c5953b524d83fce7b6a473a7adb6ed1ae5887a3a9521ede151bb
```

## 验证证据

- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_multi_hypothesis_portability.py`：exit 0，`3 passed`。
- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_pipeline_orchestrator.py tests/test_m4_bounded_execution.py tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4b_hypothesis_registry.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py`：exit 0，`370 passed`。
- `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); & 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check tests/test_m4_multi_hypothesis_portability.py`：exit 0。
- `git diff --check` 与 `git diff --cached --check`：通过。
- 子进程从临时其他 CWD 重建两条请求并复现上述 fingerprint：通过。

上述结果是本地 Windows/独立子进程证据。Ubuntu CI 尚未运行，因此不声称完整 envelope 的跨 OS 字节相等；未来 `.github/workflows/stage2g-reproducibility.yml` 的 Ubuntu/Windows 矩阵运行后再补充跨 OS 证据。

## 保护状态

- 实时远端 `main`：`dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`，与 `origin/main` 一致。
- 保护数据库 SHA256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。
- 原 M2 工作树仍为 `3679b1bac7a1634c6452784a4d8f6d139966f222`；保护 stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` 未改变。
- 本次仅修改测试、记录和验收文件；未修改 `src`、既有测试、数据、工作流或其他工作树。

## Verdict

PASS

该 PASS 仅覆盖本地合成多假设验收；跨 OS CI 证据待远程运行。未推送、未建 PR、未合并。
