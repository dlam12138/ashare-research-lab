# 工作记录：为 FactService 添加顶层异常守卫

## 基本信息

- 日期：2026-07-28
- Agent：Claude Code
- 当前分支：feat/m2-value-assessment-mvp
- 开始提交：f578629
- 任务来源：facts 模块增强指令
- 对应模块：价值评估（数据层治理）

## 任务目标

为 `src/ashare_research/facts/service.py` 添加顶层异常守卫，确保每个 build_facts 运行都有完整的错误追踪和 manifest 记录。

1. 添加 FactBuildRunState dataclass 追踪运行状态
2. 添加 FactDomainError 业务异常基类
3. 在 build_facts() 中用顶层的 try/except Exception 包裹主体逻辑
4. 通过各阶段跟踪 failure_stage
5. 确保 _finalize_and_write_manifest 每次运行只调用一次
6. manifest 写入失败时记录并抛出清晰错误

## 范围

仅修改 `src/ashare_research/facts/service.py`。

## 非目标

- 不修改 repository.py, manifest.py 或其他文件
- 不修改现有测试
- 不调整业务流程逻辑

## 开始前状态

- 当前 Git：f578629，工作区有 3 个已修改文件和 2 个未跟踪文件
- service.py 已有分阶段 try/except（provider_fetch, transaction），但 phase 3-7 和 phase 11（输出）无异常保护
- FactDomainError 不存在，需新建
- _finalize_and_write_manifest 无 finalized 保护

## 实施计划

1. 添加 FactDomainError 和 FactBuildRunState
2. 在 FactService.__init__ 添加 _build_run_state 属性
3. 在 build_facts 开篇创建运行状态，然后用 try/except 包裹主体
4. 在主体内每个阶段更新 failure_stage
5. 在 _finalize_and_write_manifest 添加 finalized 保护和写清单异常处理
6. 运行静态检查和测试验证

## 实际操作

### 1. 添加 `from dataclasses import dataclass` 导入

### 2. 添加 FactDomainError 和 FactBuildRunState

在 PROFILE_CRITICAL_CONCEPTS 和 `_count_errors` 之间插入：
- `FactDomainError(Exception)` — 业务域错误基类
- `FactBuildRunState` dataclass — 含 run_id, manifest, output_dir, failure_stage, finalized, reported/derived/context_error_count

### 3. 在 FactService.__init__ 添加 `_build_run_state` 实例属性

`self._build_run_state: FactBuildRunState | None = None`

### 4. 在 build_facts 中创建运行状态

在 manifest 创建和 output_path 解析之后、actual_source_tiers 解析之前创建 `FactBuildRunState` 实例并赋值给 `self._build_run_state`。

### 5. 用 try/except Exception 包裹整个 body

使用 Python 脚本对 try 块内所有行添加 +4 空格缩进。修复了两处过度缩进问题（新增的注释/run_state 行被重复缩进，方法间注释被过度缩进）。

添加了两个 except 块：
- `FactDomainError`：记录错误、写失败 manifest、返回 status=failed
- `Exception`：记录错误、写失败 manifest、重新抛出 RuntimeError 并附加 stage 信息

### 6. 添加 failure_stage 跟踪

在 8 个阶段分别为 `run_state.failure_stage` 赋值：
- `provider_fetch` — 阶段 1 开始
- `context_build` — 阶段 3 开始
- `reported_validation` — 阶段 4 开始
- `derivation` — 阶段 5 开始
- `derived_validation` — 阶段 6 开始
- `checkpoint` — 阶段 7 开始
- `persistence` — 阶段 10 开始
- `output` — 阶段 11 开始

同时在各阶段完成后更新 run_state 的 error count 字段。

### 7. 更新 _finalize_and_write_manifest

- 添加 finalized 守卫：若 `self._build_run_state.finalized` 为 True，记录 warning 并直接返回
- 成功后设置 `self._build_run_state.finalized = True`
- manifest.write_manifest() 调用包裹在 try/except 中，失败时记录错误并抛出 RuntimeError 附带 run_id 和路径

## 验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| Ruff 静态检查 | `ruff check src/ashare_research/facts/service.py` | All checks passed |
| Python 编译检查 | `python -m py_compile src/ashare_research/facts/service.py` | COMPILE OK |
| 端到端测试 | `pytest tests/test_m2_integration.py::TestFactServiceEndToEnd -v` | 6 passed |
| 全量集成测试 | `pytest tests/test_m2_integration.py -v` | 30 passed |
| Git diff whitespace | `git diff --check` | No issues |

## 结果

- 已完成：FactDomainError、FactBuildRunState、顶层 try/except 守卫、failure_stage 全阶段跟踪、finalized 单次写保护、manifest 写失败异常处理
- 状态：completed

## 最终文件变更

| 文件 | 操作 |
|------|------|
| `src/ashare_research/facts/service.py` | 修改（+387 / -276 行） |

## 最终 Git 状态

- 当前分支：feat/m2-value-assessment-mvp
- 未提交修改：是（4 文件）
- 未推送：是
