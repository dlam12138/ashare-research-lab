# 工作记录：M2 Stage 2D-A 工程门禁收口

## 基本信息

- 日期：2026-07-31
- Agent：Claude Code
- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`f7b565dbd55fadee14be0ffb892642412beaf4b6`（Stage 2D-A 文档收口提交）
- 任务来源：`/goal` 指令（Stage 2D-A 工程门禁收口，不新增事实/指标/功能）
- 对应模块：工程治理（价值评估模块的门禁收口，不改事实/指标/功能）

## 任务目标

关闭 Stage 2D-A 遗留的工程门禁：修复 3 个既有 `UP038`、重跑离线 runner 取得真实 `run_id`、
修正正式验收报告与 Stage 2D-A 工作记录中与门禁/`run_id`/提交描述相关的不一致。
不新增任何事实、指标或功能。

## 范围

仅允许修改：

- `src/ashare_research/tools/official_fact_acceptance.py`（3 处 `UP038` 中的 2 处，等价语法）
- `tests/test_official_fact_acceptance.py`（3 处 `UP038` 中的 1 处，等价语法）
- `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`（一致性修正）
- `agent/record/2026-07-31_m2_stage2da_2025_roe_roa_denominator_fact_acceptance.md`（一致性修正）
- 本工作记录（新增）

## 非目标

- 不新增事实、指标、Context、Rule、证据或功能
- 不修改 `pyproject.toml` 的 `ruff==0.13.2` 固定
- 不修改 Rule 001/002/003、Fact Schema、FactIdentity、AsOfQuery、VersionChainValidator、Metric 代码或既有事实/指标
- 不修改 engine.py / validator.py（Stage 2D-A 已提交，受 protected blob 测试保护）
- 不 merge main，不创建 Tag/Release
- 不在网络/PDF/缓存访问下重跑 runner

## 开始前状态

- 当前分支：`feat/m2-value-assessment-mvp`，HEAD：`f7b565d`（Stage 2D-A 文档收口提交）；
- worktree clean；`stash@{0}`：`protect pre-existing Stage 1B.4 record edit before Stage 1C`，未动；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（与基线一致）；
- `python -m ruff --version` = `0.12.0`（`pyproject.toml:24` 固定 `ruff==0.13.2`，但当前解释器解析为 0.12.0；0.12.0 仍含已弃用的 `UP038`）；
- 3 个既有 `UP038` 位于 `official_fact_acceptance.py:382/386`、`test_official_fact_acceptance.py:861`，自父提交 `d19b2c1` 已存在（非 Stage 2D-A 引入；Stage 2D-A 未修改这两个文件）；
- Stage 2D-A 正式报告与工作记录中：`run_id` 使用 `<timestamp>` 占位符；工程门禁处表述“Ruff 0.13.2 通过”（在 0.12.0 实际环境下不成立）；工作记录“最终Git状态”将 `9e3d1b4` 写为“当前提交/远程 HEAD”（实际 Stage 2D-A 最终 HEAD 为 `f7b565d`）。

## 决策记录：修复 3 处 `UP038`（取代 Stage 1C-C.2.1“不改 isinstance”取舍）

### 决策内容

将 3 处 `isinstance(x, (X, Y))` 改为等价 `isinstance(x, X | Y)`：

- `official_fact_acceptance.py:382`：`(list, tuple)` -> `list | tuple`
- `official_fact_acceptance.py:386`：`(datetime, date)` -> `datetime | date`
- `test_official_fact_acceptance.py:861`：`(ast.Import, ast.ImportFrom)` -> `ast.Import | ast.ImportFrom`

### 采用原因

- 当前实际环境 `python -m ruff` 解析为 `0.12.0`，`UP038` 仍生效并报 3 个诊断，`ruff check src tests` 不通过；
  故“全量 Ruff 通过”在 0.12.0 下不成立，工程门禁未真正关闭；
- `X | Y` 与 `(X, Y)` 在 `isinstance` 中行为完全等价（Python 3.10+；本项目运行 Python 3.13.9），不改变任何行为；
- 修改后 `ruff check src tests` 在 0.12.0（`UP038` 满足）与固定 0.13.2（`UP038` 规则已删除）下均退出码 0，门禁在两个版本下都关闭；
- 仅改 3 行，不顺带重构。

### 与 Stage 1C-C.2.1 的关系

Stage 1C-C.2.1（`agent/record/2026-07-29_m2_stage1cc21_ruff_toolchain_baseline_closure.md`）当时的取舍是
“固定 `ruff==0.13.2`、不修改 3 处 `isinstance`”，因 0.13.2 规则集中已删除 `UP038`，可在不改代码下通过。
本任务直接修改这 3 处，**取代该取舍中“不改 isinstance”的一半**；`ruff==0.13.2` 固定保留不动。
原因：实际解释器解析为 0.12.0（固定未在环境生效），门禁在 0.12.0 下未关闭；改代码使门禁在两个版本下都关闭，更稳健。

### 考虑过的替代方案

- 维持“仅固定 0.13.2、不改代码”：未采用——实际环境为 0.12.0，门禁未关闭，且 `/goal` 明确要求修复 3 个 `UP038`；
- 添加 `noqa: UP038`：未采用——`/goal` 要求“等价语法修改，不改变行为”，noqa 属绕过而非修正；
- 升级环境 ruff 到 0.13.2：超出本任务范围（不改 `pyproject.toml`、不动环境配置），且改代码方案已使门禁在两版本下均关闭。

### 潜在风险

- `X | Y` 在 `isinstance` 中需 Python 3.10+；本项目 3.13.9，无风险；
- 取代了既有工程决策，需在记录中明确（本节即此）。缓解：`ruff==0.13.2` 固定不动，行为等价，全量测试通过。

## 实际操作

1. 基线确认：`git status` clean、HEAD=`f7b565d`、stash 未动、默认 DB SHA=`4a71d3c7...`；
2. `python -m ruff check src tests --select UP038` 确认 3 个诊断位置；
3. 读取 `official_fact_acceptance.py:376-388`（`_jsonable`）与 `test_official_fact_acceptance.py:855-866`；
4. 应用 3 处等价语法修改（`Edit` 工具，未触碰其他行）；
5. 门禁（要求退出码 0）：
   - `python -m ruff check src tests` -> `All checks passed!` exit 0（`UP038=0`）；
   - `python -m compileall -q src tests` -> exit 0；
   - `python -m pytest -q` -> `711 passed, 2 warnings` exit 0（2 warnings 为既有 dateutil 回退，与本次无关）；
   - `git diff --check` -> exit 0（仅 CRLF 提示，非错误）；
6. 离线重跑 Stage 2D-A runner（`python -m ashare_research.tools.official_roe_roa_denominator_2025_acceptance --output-root output/value_assessment`，使用默认已提交证据，不访问网络/PDF/缓存）：
   - `status=passed`，run_id=`roe_roa_denominator_601857_SH_2024_2025_20260731_182147_333819`；
   - `offline=True / network_access=False / pdf_access=False / cache_access=False / downloaded=0`；
   - R=0；counts：contexts=7 / financial_facts=144 / raw_ineligible=96 / reconciled_eligible=48 / version_chain_links=27 / audit=lineage=144；
   - PIT：2024 报告可用 30、2025 报告可用 39、final PIT=39；
   - upstream 132 Fact ID 集合 SHA=`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`（不变）；
   - 默认 DB SHA 前后均=`4a71d3c7...`（不变）；upstream DuckDB 前后 SHA 一致；
   - run_manifest.json 位于 gitignored `output/`，未进 Git；
7. 单独运行 Stage 2D-A 验收测试 `tests/test_official_roe_roa_denominator_2025_acceptance.py -v` -> `11 passed`，
   覆盖 132 Fact ID / 63 Metric Result ID / 38 Metric Result ID / Rule 001-004 lineage / PIT39 / 默认 DB / protected blob 不变性；
8. 修正正式验收报告 `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`：写入精确 `run_id`；重写“工程门禁”节，记录 3 个既有 `UP038` 及其关闭，不再声称此前全量 Ruff 通过；
9. 修正 Stage 2D-A 工作记录 `agent/record/2026-07-31_m2_stage2da_2025_roe_roa_denominator_fact_acceptance.md`：补 `run_id`、63 Metric Result ID 集合 SHA；更新“Ruff 说明”为已关闭；修正“最终Git状态”将 `9e3d1b4` 描述为验收代码/报告提交、`f7b565d` 为文档收口提交，不自引用收口提交哈希；
10. （待执行）提交 1 `chore: close baseline Ruff diagnostics`（2 个代码文件）；提交 2 `docs: close Stage 2D-A acceptance inconsistencies`（报告 + Stage 2D-A 记录 + 本记录）；逐个 push。

## 数据与方法说明

- runner 数据来源：已提交证据 `acceptance/fixtures/official_facts/601857.SH/supplemental/2024_roe_roa_denominators.json`、`2025_roe_roa_denominators.json`、`acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2024_reviewed_by_2025.json`；
- 重跑时间：2026-07-31 18:21（run_id 时间戳）；
- 离线、无网络/PDF/缓存访问；`downloaded=0`；
- run_id 时间戳为运行时刻，非内容确定性标识；除时间戳外 runner 输出可由固定输入复现（Fact ID、计数、不变性摘要均与前序一致）。

## 验证

| 命令 | 是否通过 | 关键输出 |
|---|---|---|
| `python -m ruff check src tests` | 是 | `All checks passed!` exit 0，UP038=0 |
| `python -m ruff check src tests --select UP038` | 是 | `All checks passed!`（0 诊断） |
| `python -m compileall -q src tests` | 是 | exit 0 |
| `python -m pytest -q` | 是 | `711 passed, 2 warnings` exit 0 |
| `pytest tests/test_official_roe_roa_denominator_2025_acceptance.py -v` | 是 | `11 passed` |
| `git diff --check` | 是 | exit 0（仅 CRLF 提示） |
| 离线 runner 重跑 | 是 | status=passed，R=0，PIT 30/39，DB 不变 |
| `git check-ignore output/` | 是 | `output/` 已忽略，无产物进 Git |
| `git stash list` | 是 | stash 未动 |

不变性（全部未变）：

- 132 Fact ID 集合 SHA-256：`1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d`；
- 63 Metric Result ID 集合 SHA-256：`34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526`；
- 38 Metric Result ID 集合 SHA-256：`730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa`；
- 144 final Fact 集合（financial_facts=144）；Rule 001/002/003/004 lineage（57/18/57/12）；PIT39；
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`；
- engine.py / validator.py / Stage 2C-C.1 / 2C-D 报告 blob（protected blob 测试通过，未修改）；
- stash 未动；`output/` 产物未进 Git。

## 结果

- 已完成：3 处 `UP038` 关闭（等价语法，行为不变）；4 项门禁退出码 0；离线重跑取得真实 `run_id`；正式报告与 Stage 2D-A 工作记录一致性修正完成；
- 不变性全部未变；
- 当前可用；本任务不新增事实/指标/功能。

## 遗留问题

- 无。ROE/ROA 指标计算仍为 NOT YET（属下一阶段，不在本任务范围）。

## 下一步建议

- 不在本任务范围。下一阶段（ROE/ROA 平均余额与指标计算）需另行立项与记录。

## 最终文件变更

修改：
- `src/ashare_research/tools/official_fact_acceptance.py`（2 处 `UP038` 等价语法）
- `tests/test_official_fact_acceptance.py`（1 处 `UP038` 等价语法）
- `acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md`（`run_id` + 工程门禁节）
- `agent/record/2026-07-31_m2_stage2da_2025_roe_roa_denominator_fact_acceptance.md`（`run_id`/63-set/Ruff 说明/最终Git状态）

新增：
- `agent/record/2026-07-31_m2_stage2da_engineering_gate_closure.md`（本记录）

## 最终Git状态

- 当前分支：`feat/m2-value-assessment-mvp`
- 开始提交：`f7b565d`
- Stage 2D-A 验收代码/报告提交：`9e3d1b4`（`test: finalize PetroChina ROE ROA denominator acceptance`）
- Stage 2D-A 文档收口提交：`f7b565d`（`docs: finalize Stage 2D-A work record with results and git state`）
- 本次工程门禁收口提交：`chore: close baseline Ruff diagnostics` + `docs: close Stage 2D-A acceptance inconsistencies`（逐个 push；最终远程 HEAD 见终端汇报，本文件不自引用收口提交哈希）
- stash：`stash@{0}` 未动
- 默认 `data/research.duckdb` SHA-256：`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`（不变）
