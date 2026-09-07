# A-Share Research Lab

> A股价值评估与市场机制验证实验室

本地运行、免费数据优先的可解释研究平台。提供数据底座、中石油价值评估切片、日频机制研究记录，以及通用假设合同与分析计划编译能力。
仅用于数据分析、统计研究和软件工程学习，不构成投资建议，也不提供自动交易能力。

## 当前可用能力

主线已包含 PIT/TTM 修复与 A.2 冻结设计。下表中的 A.2I 是本实现 PR 提供的能力，待合并；设计和计划编译均不代表统计执行已实现。

| 能力 | 当前状态 | 如何使用 | 限制 | 证据 |
| --- | --- | --- | --- | --- |
| M1 数据底座 | 已实现 | 下方数据获取 CLI；Parquet/DuckDB 存储 | 获取需网络，免费源可能失效 | [数据服务测试](tests/test_data_service.py) |
| M2 价值评估 | M2 已条件关闭；中石油 PIT 切片 | 下方离线胶囊；真实输入需显式提供 | ROIC 证据不足；PE 数值评分暂缓，无生产排名 | [完成矩阵](reports/m2_value_assessment_completion_matrix.md)、[缺口台账](reports/m2_explicit_gap_ledger.md) |
| M3 机制验证 | CONDITIONALLY CLOSED；日频机制未建立 | 阅读开发期研究与最终处置 | holdout primary inconclusive；不支持因果或行为主体推断 | [最终验收](acceptance/m3_stage3e_daily_mechanism_final_disposition_and_milestone_closeout_preflight.md) |
| M4-A.1 假设合同 | CANONICAL ON MAIN | 下方 Python 编译接口与合成测试 | 仅配置校验、合同冻结和摘要，没有通用研究执行器 | [编译验收](acceptance/m4_stage4a1_typed_hypothesis_config_and_frozen_contract_compiler.md) |
| M4-A.2 分析计划 | 设计已在主线；A.2I 计划编译已实现（本 PR，待合并） | 下方 `build_analysis_plan(contract)` Python 入口与合成测试 | compile-only；数据适配、执行尚未实现；holdout 始终不授权执行 | [冻结设计](reports/m4_stage4a2_deterministic_analysis_plan_design_v1.json)、[实现验收](acceptance/2026-09-07_m4a2i_analysis_plan_compiler.md) |
| M4-B 与后续研究 | NOT STARTED | 参见路线图 | 真实假设执行、M5/M6 仍未授权 | [Stage4P](acceptance/m4_stage4p_north_star_v2_adoption_and_architecture_preflight.md) |

### 研究结论与边界

**Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM CONDITIONALLY CLOSED**。
PE 决定为 `PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE`；原始 PE 和 3Y/5Y 分位仅作描述证据。ROIC 保持 `not_computable_under_strict_evidence_contract`，没有替代数值。

M3 最终处置为 `M3_DAILY_MECHANISM_NOT_ESTABLISHED`。Holdout 已使用一次性解封机会，但覆盖率 `0.9736963544070143` 低于冻结门槛 `0.99`，状态为 `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`，未运行 holdout 回归/bootstrap。

### 历史停止与当前授权

历史脉络见 [阶段历史](docs/project-history.md)。为区分当时与当前，保留以下验收声明：

- M3 Stage 3A research contracts are frozen. Stage 3B completed fail-closed. Stage 3B-R1 primary-proxy resolution is current within the frozen M3 market-proxy lineage.
- At M3 closeout, further holdout recovery, minute escalation, index contribution, and M4 were not authorized.
- Historical M3 closeout stop: `STOP_FOR_NORTH_STAR_REVIEW`.
- Subsequently, M4-A.1 has since been implemented and canonicalized on main. M4-A.2 design is now on main; A.2I compile-only implementation is authorized in this PR. Dataset adapters, executors, M4-B and real hypothesis execution remain separately unauthorized.
- No real mechanism inference beyond the frozen development-primary and registered robustness execution has been executed.

## 系统要求

- Python >= 3.11
- Windows / macOS / Linux
- 不需要数据库服务器

---

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

---

## M4-A.1 Python 接口

接口位于 `ashare_research.mechanism.hypothesis_config` 与 `ashare_research.mechanism.contract_compiler`：
`load_hypothesis_config(path)` / `parse_hypothesis_config(document)` → `compile_hypothesis_config(config)` → `serialize_frozen_contract(contract)`。
返回 `FrozenMechanismContract`；通过 `validate_contract` 验证，以 `compute_contract_digest` 计算摘要。
只编译合同，不获取数据或执行统计研究；目前没有 M4 执行 CLI。

完整合成配置与用法见 [类型化合同测试](tests/test_m4_stage4a1_typed_contract.py)。安装后可离线运行：

```powershell
python -m pytest -q tests/test_m4_stage4a1_typed_contract.py
```

## M4-A.2I Python 接口

在已有 `FrozenMechanismContract` 上编译不可变的 `DeterministicAnalysisPlan`：

```python
from ashare_research.mechanism.planning import (
    build_analysis_plan,
    plan_to_canonical_dict,
    serialize_analysis_plan,
    compute_plan_digest,
    validate_analysis_plan,
)

plan = build_analysis_plan(contract)
validate_analysis_plan(plan)
payload = plan_to_canonical_dict(plan)  # 独立副本
encoded = serialize_analysis_plan(plan)  # UTF-8、排序键、紧凑 JSON、结尾换行
digest = compute_plan_digest(plan)
```

计划声明语义角色、有序控制项、条件、窗口、质量门槛和调度规则。
Bootstrap 只声明块长策略；稳健性及证据规则只保存调度说明。
编译不读取数据、不计算回归或 bootstrap，也不授权 holdout。数据适配、执行尚未实现。
仅需安装依赖即可运行 [合成计划测试](tests/test_m4_stage4a2i_analysis_plan.py)：

```powershell
python -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py
```

## 数据获取与离线复现

步骤 1–5 写入本地数据，其中 2–5 访问外部数据源。步骤 6 查询已有本地数据。
步骤 7 的胶囊构建/比较和步骤 8 的 test-capsule 模式使用固定测试输入，不需要默认数据库或外部行情。
真实验收命令另需显式的数据库、行情或 PDF 缓存；缺失时失败，不回退到合成数据。

### 1. 初始化

```powershell
ashare-research init-db
```

### 2. 获取股票基础信息

```powershell
ashare-research fetch-stock-basic --provider baostock
```

### 3. 获取交易日历

```powershell
ashare-research fetch-calendar --start 2026-01-01 --end 2026-07-27
```

### 4. 获取个股日线

```powershell
ashare-research fetch-stock-daily 601857.SH --start 2026-05-01 --end 2026-07-27 --provider baostock --adjustment none -v
```

### 5. 获取指数日线

```powershell
ashare-research fetch-index-daily 000001 --start 2026-05-01 --end 2026-07-27 --provider akshare
```

### 6. 查看已保存数据

```powershell
ashare-research inspect stock-daily 601857.SH --show-data
```

### 7. Stage 2G.2 可复现测试

普通测试不依赖 `output/`、`data/research.duckdb`、外部行情缓存或网络：

```powershell
python -m ashare_research.tools.stage2g_reproducibility verify-contracts
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-a
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility compare-capsules --left tmp/stage2g2-local/capsule-a --right tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-a --output tmp/stage2g2-local/run-a --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-b --output tmp/stage2g2-local/run-b --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility compare-runs --left tmp/stage2g2-local/run-a/stage2g2_local_ab --right tmp/stage2g2-local/run-b/stage2g2_local_ab
pytest -q
ruff check src/ tests/
```

### 8. Stage 2H 风险否决证据切片

正式评估只读取提交的证据/事件/有界搜索台账，默认离线、PIT-aware、不可写默认数据库；官方 PDF 获取必须显式指定外部内容寻址缓存：

```powershell
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice verify-contracts
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice acquisition-preflight `
  --official-cache-root <official-pdf-cache> `
  --output tmp/stage2h-preflight.json
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice run-offline-formal `
  --output tmp/stage2h-run `
  --run-id petrochina_stage2h `
  --official-cache-root <official-pdf-cache>
python -m ashare_research.tools.petrochina_risk_veto_vertical_slice run-test-capsule `
  --output tmp/stage2h-test `
  --run-id stage2h_test_capsule
pytest -q tests/test_stage2h_risk_veto.py
pytest -q tests/test_stage2h1r_historical_completeness.py
```

Stage 2H.1R 的当前风险状态唯一 canonical 路径是
`reports/petrochina_value_profile.json:current_risk_veto_profile`，固定输出
8 个 `risk_evaluation_slot_v1`。`observations` 可以少于 8，但 slot 不会消失；
没有 PIT-visible input 的 slot 保持 `missing_evidence`。完整风险档案见
[canonical risk-veto profile](reports/petrochina_risk_veto_profile_2021_2026.md)。
旧的 `governance_risk`、`audit_risk` 和 `related_party_risk` 只在
`legacy_risk_veto_checks` 中保留，且 `current=false`、`do_not_use_for_current_profile=true`；
消费者不得把它们当作当前结论。

Stage 2H 的历史范围停在风险证据状态与否决资格；该阶段记录不代表当前整个主线的进度。

测试胶囊中的 Fact 是由 canonical Fact 仓库导出的有界 read model；行情是固定算法生成的
`synthetic_test_only` CSV。它们只用于显式 `test_capsule` 模式，不是 PetroChina 真实输入，
不会成为真实报告的 fallback。

真实本地验收必须显式提供 canonical DB 与外部行情缓存根目录：

```powershell
python -m ashare_research.tools.stage2g_reproducibility verify-real-inputs `
  --fact-db <canonical-db> `
  --market-cache-root <external-market-cache> `
  --output <preflight.json>
python -m ashare_research.tools.stage2g_reproducibility run-real `
  --fact-db <canonical-db> `
  --market-cache-root <external-market-cache> `
  --output <run-root> --run-id stage2g2_real_local
```

真实 provider 数据与 PDF 不随仓库重新分发；缺失或 hash 不匹配时失败并报告
`missing_external_research_input`，不会回退到本地小 Parquet 或测试胶囊。详见
[Stage 2G.2 reproduction guide](docs/stage2g_reproduction_guide.md)。

---

## 数据目录

```text
data/
├── research.duckdb          # DuckDB 元数据
├── raw/                     # 原始下载数据（不提交 Git）
│   ├── baostock/
│   └── akshare/
└── parquet/                 # 标准化后数据（不提交 Git）
    ├── stock_daily/
    ├── index_daily/
    ├── stock_basic/
    └── trade_calendar/
```

---

## 数据源

| 数据源 | 用途 | 状态 |
|--------|------|------|
| [Baostock](http://baostock.com) | 股票基本信息、交易日历、个股日线 | ✅ 已接入 |
| [AKShare](https://akshare.akfamily.xyz) | 指数日线、备用个股数据 | ✅ 已接入 |

### 数据源可能失效的风险

Baostock 和 AKShare 均为免费公开接口，可能因上游变更而暂时或永久不可用。
本项目设计为**数据源可替换**，通过统一接口适配不同的数据提供方。

---

## 数据字段与单位

### 个股日线 (stock_daily)

| 字段 | 说明 | 单位 |
|------|------|------|
| symbol | 股票代码 | `600000.SH` 格式 |
| trade_date | 交易日 | `YYYY-MM-DD` |
| open | 开盘价 | 元（人民币） |
| high | 最高价 | 元 |
| low | 最低价 | 元 |
| close | 收盘价 | 元 |
| pre_close | 前收盘价 | 元 |
| volume | 成交量 | 股 |
| amount | 成交额 | 元（人民币） |
| turnover_rate | 换手率 | % |
| is_trading | 是否交易 | 布尔值 |
| adjustment | 复权方式 | `none`/`qfq`/`hfq` |
| source | 数据来源 | `baostock`/`akshare` |
| fetched_at | 抓取时间 | ISO datetime |

### 指数日线 (index_daily)

| 字段 | 说明 | 单位 |
|------|------|------|
| symbol | 指数代码 | 如 `000001`（上证指数） |
| trade_date | 交易日 | `YYYY-MM-DD` |
| open/high/low/close | OHLC | 点位 |
| volume | 成交量 | 手 |
| amount | 成交额 | 元（人民币） |

### 股票代码格式

- **内部统一格式**：`600000.SH` / `000001.SZ`
- **Baostock 格式**：`sh.600000` / `sz.000001`
- **纯数字推断**：6/9 开头 → SH，0/3/2 开头 → SZ

---

## 复权说明

- `none`：不复权（默认），价格与历史实际成交价一致
- `qfq`：前复权，以最新价为基准向前调整历史价格
- `hfq`：后复权，以上市首日为基准向后调整价格

默认保存不复权数据。需要复权数据时，请在参数中明确指定 `--adjustment qfq`。

---

## 质量检查

每次数据抓取自动运行以下检查：

- 必需字段完整性
- 日期可解析性
- 主键唯一性（symbol + trade_date + adjustment）
- OHLC 逻辑一致性（high >= open, high >= close, low <= open, low <= close）
- 价格和成交量非负
- 日期排序
- 数据来源不为空

检查结果记录在 DuckDB `data_quality_results` 表中。

---

## 运行测试

```powershell
# 全部测试（Mock，不依赖网络）
pytest -q

# 带覆盖率
pytest --cov=ashare_research --cov-report=term-missing

# 代码检查
ruff check src/ tests/
```

---

## 项目结构

以下模块目录位于 `src/ashare_research/`：

| 目录 | 职责 |
| --- | --- |
| `providers`, `services`, `storage`, `quality` | 数据获取、编排、存储和质量检查 |
| `facts`, `validation`, `reconciliation`, `lineage` | PIT 事实、版本校验、协调和溯源 |
| `metrics`, `pit_valuation`, `risk_veto`, `scoring` | 指标、估值时间线、风险证据与受限评分实验 |
| `mechanism` | 已冻结 M3 方法和 M4-A.1 合同编译 |
| `tools` | 阶段命令行工具；运行前查阅对应合同 |

仓库根目录的 `tests`、`reports`、`acceptance` 保存测试和研究验收证据；
`agent/goals`、`agent/record` 保存任务契约与记录；`docs` 保存方法说明、复现指南与阶段历史。
当前能力以本页为准；历史记录不自动授权新阶段。

## 路线图

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| Milestone 1: 免费数据底座 | 数据获取与存储 | 已实现 |
| Milestone 2: 价值评估 MVP | 中石油 PIT 切片 | CONDITIONALLY CLOSED；评分附加项条件关闭 |
| Milestone 3: 机制验证 MVP | 日频机制验证 | CONDITIONALLY CLOSED；daily mechanism not established；holdout primary inconclusive |
| Milestone 4: Generic Mechanism Research Engine + Theory / Hypothesis Registry | 通用机制研究契约与理论/假设注册 | IN PROGRESS; Stage4P COMPLETE; M4-A.1 CANONICAL ON MAIN; M4-A.2 DESIGN ON MAIN; M4-A.2I COMPILE-ONLY IMPLEMENTED（本 PR，待合并）; dataset adapter / executor NOT STARTED; M4-B NOT STARTED; real hypothesis execution NOT AUTHORIZED |
| Milestone 5: 分钟级研究 | 按需验证 | 未开始、未授权 |
| Milestone 6: 本地 Web 界面 | 研究工作台 | 未开始、未授权 |

## 许可

A software license has not yet been selected. The repository is currently public for review and research discussion; no additional reuse rights are granted unless a license is added later.
