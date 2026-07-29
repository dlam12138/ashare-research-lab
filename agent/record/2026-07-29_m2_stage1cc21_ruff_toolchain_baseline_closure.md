# M2 Stage 1C-C.2.1 工作记录：Ruff 工具链基线收口

## 启动状态

- Branch：`feat/m2-value-assessment-mvp`
- Base commit：`5ffd3796ee2356146bc91f97e9bfa5c0680dc6f8`
- Worktree：clean
- `stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，保持原状
- Python：`3.13.9`
- pip：`25.3`
- 当前 Ruff：`0.12.0`
- Ruff 安装位置：`D:\anaconda\Lib\site-packages`
- 原开发依赖约束：`ruff>=0.1.0`
- 目标固定约束：`ruff==0.13.2`

## 原始严格门禁

命令：`python -m ruff check src tests`

结果：exit 1，三条 `UP038`：

- `src/ashare_research/tools/official_fact_acceptance.py:344`：`isinstance(value, (list, tuple))`
- `src/ashare_research/tools/official_fact_acceptance.py:348`：`isinstance(value, (datetime, date))`
- `tests/test_official_fact_acceptance.py:757`：`isinstance(node, (ast.Import, ast.ImportFrom))`

本阶段不修改上述三处代码，不添加 `ignore`、`noqa`，不运行自动修复。

## 证据不可变基线

- 2023 bundle blob：`6612148ea91b2004605b98e0c8fe799a4d2686ea`
- 2024 bundle blob：`03a2ec2813c31676aebed20e4df50042f42f140b`
- 2025 bundle blob：`0ababb5262e6cbf1646e165ccfb3e7bfe2769670`

## 范围

- 目标：固定 Ruff 0.13.2，恢复可复现的严格全仓 lint 门禁，并在全部证据不变时将 2023 验收定稿为 Pass。
- 非目标：业务修复、依赖管理重构、全仓格式化、事实修改、runner/Reconciliation/Schema 修改、2022 数据录入。
- 北极星对齐：只结束工具链版本争议，随后返回中国石油历史年度官方事实主线。
- 2023 六个原始 fact_id、三个 reconciled fact_id、PIT、Audit、Lineage 均不得改变。

## 待确认

- 提交、远程状态与最终结论

## 固定工具链结果

- 项目环境：仓库既有、Git 忽略的 `.venv`
- 固定后 Ruff：`0.13.2`
- 修改后依赖约束：`ruff==0.13.2`
- 配置来源：仓库根目录 `pyproject.toml`
- target version：Python 3.11
- line length：100
- select：保留 `E`、`F`、`W`、`I`、`N`、`UP`、`B`、`SIM`
- Ruff 0.13.2 配置中不存在 `UP038` / `non-pep604-isinstance`
- 未修改三处 `isinstance`，未添加 ignore 或 noqa。
- 严格命令：`python -m ruff clean` 后 `python -m ruff check src tests`
- 严格结果：`All checks passed!`，exit 0

## 验证结果

- 2023 注册证据与年度验收：`122 passed in 5.24s`
- Reconciliation 回归：`86 passed in 6.89s`
- 全量测试：`444 passed, 2 warnings in 51.10s`
- warnings：与原验收相同的 pandas 日期解析两条 warning，无新增
- compileall：exit 0
- import：OK
- diff check：exit 0
