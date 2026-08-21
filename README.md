# A-Share Research Lab

> A股价值评估与市场机制验证实验室

一个使用免费数据、本地运行、面向A股的可解释研究平台：通过价值评估寻找值得研究的公司，通过机制验证检验个股与市场因素之间的真实关系。

> [!IMPORTANT]
> 本项目仅用于数据分析、统计研究和软件工程学习，不构成任何投资建议，也不提供自动交易能力。

**Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM CONDITIONALLY CLOSED**

Stage 2K.1R4F.4B decision:
`PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE`. ROIC is
`not_computable_under_strict_evidence_contract`; no numeric ROIC, shadow, or
production Metric/Result exists. Raw PE and trusted 3Y/5Y percentiles remain
descriptive evidence, but frozen-5Y independent cycle-context validation is not
testable, so no PE or valuation-dimension numeric score is authorized. The
scoring addendum is conditionally closed; this is not a production engine,
rank, or signal. M3 Stage 3A research contracts are frozen. Stage 3B completed
fail-closed (strict primary-proxy inputs under free data were not obtainable, so
no proxy was substituted). Stage 3B-R1 primary-proxy resolution is current: the
type-1 exact divisor reconstruction is superseded by a North-Star-aligned
equal-weight ex-target Shanghai A-share proxy (v2). Stage 3B-R2 froze a pre-outcome
oil alignment supersession (strictly-prior Brent observation-date) and the Shenwan
  industry regime control. Stage 3B-R3 added a secret-redacted bounded EIA Open Data API v2
transport (oil) and a Shenwan official-source-resolution ladder (industry). Stage 3B-R4 formally
amends only the pre-outcome source/control implementation: the unchanged
DCOILBRENTEU Brent variable now uses no-credential bounded FRED public CSV, and the primary
industry control is the official CNI Oil & Gas Index 399439. Both are TRUSTED through 2022-12-31;
the frozen R1 market proxy is reused and joint Tier-1 readiness has 1,902 valid development dates.
Stage 3C-A pipeline-lock implementation is recovered and locked on the canonical M3 baseline;
execution remains synthetic-only. Stage 3C real analysis remains unauthorized and no real mechanism
inference has been executed. Holdout remains sealed.
No real mechanism inference has been executed.

---

## 项目定位

本项目围绕两个核心模块：

1. **个股价值评估** — 企业质量、估值吸引力、价值兑现能力、风险否决项（M2 正在实现）
2. **市场机制验证** — 用统计方法检验个股与市场之间的可复现关系（Stage 3A 契约已冻结；Stage 3B 已 fail-closed 完成；Stage 3B-R1 主市场代理解析为当前状态；Stage 3B-R2 冻结严格 prior Brent 观测日与申万行业 regime；Stage 3B-R4 在结果出现前将 oil transport 改为无认证 bounded FRED `DCOILBRENTEU`，并将行业 primary amendment 固定为官方 CNI `399439`，两项均 TRUSTED；复用 R1 market proxy 后 joint Tier-1 共有 1,902 个有效 development dates；Stage 3C-A pipeline-lock implementation allowed，但 Stage 3C real analysis 未授权，尚未执行真实机制推断）

当前已完成第一阶段的**免费数据底座**：可运行、可测试、可追溯的本地数据基础设施。M2 已有 PetroChina（601857.SH）一份 PIT value profile 纵向切片；收益/现金、ROE/ROA、财务安全、股息和估值均已有阶段性能力。Stage 2G.2 增加了 clean-clone 测试胶囊、显式真实输入解析器、Rule007 严格来源配对和 artifact checksums。

M2 当前切片的正式验收见：[Stage 2G.1 trusted-lineage closeout](acceptance/m2_stage2g1_trusted_lineage_closeout.md)、[Stage 2H risk-veto evidence](acceptance/m2_stage2h_petrochina_risk_veto_evidence.md)、[Stage 2H.1R historical/profile closeout](acceptance/m2_stage2h1r_historical_risk_completeness_and_profile_canonicalization.md) 和 [PetroChina value profile](reports/petrochina_value_profile_2021_2026.md)。Stage 2F 仍保留 9 个交易所股息证据缺口；Stage 2H 的监管/纪律与相关资金占用搜索缺口保持为 `missing_evidence`，不会被改写为负面结论。

ROIC 的当前决定见 [strict-evidence non-computability ADR](docs/decisions/ADR-ROIC-001-strict-evidence-non-computability.md)。Plan v3 与 Stage 2I.2R 保留 9 个已取得单元和 7 个明确事实/年度缺口；没有使用税率代理、联营/合营残差分配、无依据非经营资产扣除、手工 plug 或弱化 scope matching。当前 M2 模块状态见 [completion matrix](reports/m2_value_assessment_completion_matrix.md)，全部当前缺口见 [canonical gap ledger](reports/m2_explicit_gap_ledger.md)，条件关闭验收见 [Stage 2J closeout](acceptance/m2_value_assessment_mvp_conditional_closeout.md)。

---

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

## 快速开始

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

Stage 2H stops at evidence status and veto eligibility. It does not start ROIC,
scoring, web search, target price, recommendation, automatic trading, or
market-mechanism work.

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

## 当前限制

当前阶段的已知限制：

- 仅支持日线数据，不支持分钟数据
- M2 是有明确证据缺口的条件关闭，不是完全完成
- Stage 2I.2R 已完成捕获派生、双官方证据重协调和七个缺口的执行式版本化搜索：9/16 个事实/年度单元已取得，7 个单元保留为明确缺口；结论为 `ROIC_FACT_GAPS_REMAIN`，未运行 shadow ROIC。更正产物位于 `reports/*stage2i2r*`，原 Stage 2I.2 产物保留供审计。
- ROIC 在严格证据合同下不可计算；不存在数值、proxy、shadow 或生产 Metric/Result
- 评分附加项已**条件关闭**：PE 原始值与 3Y/5Y 分位保留为描述证据；冻结 5Y 内独立 cycle-context 验证不可检验，故 PE 与估值维度 numeric score 均为 `null`，不补 0、不转移权重，也没有生产 score engine、排名或推荐
- M3 Stage 3A 研究契约已冻结；Stage 3B 已 fail-closed 完成；Stage 3B-R1 主市场代理解析为当前状态；Stage 3B-R2 已冻结严格 prior Brent 观测日与申万行业 regime；Stage 3B-R4 在结果出现前将 oil transport 改为无认证 bounded FRED `DCOILBRENTEU`，并将行业 primary amendment 固定为官方 CNI `399439`，两项 Tier-1 控制均 TRUSTED，复用 R1 market proxy 后 joint Tier-1 共有 1,902 个有效 development dates；Stage 3C-A pipeline-lock implementation allowed，但 Stage 3C real analysis 未授权；尚未执行真实机制推断
- Web 界面、目标价、推荐和自动交易尚未实现
- 当前 value profile 只覆盖 PetroChina（601857.SH）这一份 PIT 纵向切片
- Stage 2F 仍有 9 个交易所证据缺口；股本 A/H 拆分也需继续补充登记证据
- 当前严格 Rule007 只有 1 个 issuer-official + exchange-official eligible event；指定披露平台不计为 exchange side
- 真实行情缓存是外部输入，仓库只提交 path-independent registry；clean-clone 只使用 synthetic test capsule
- 数据日期间隔较小时，免费接口可能返回空结果
- 不同数据源的成交量单位可能不一致（已在标准化层转换）
- AKShare 接口字段可能随版本变化（已做字段检查，缺失时明确报错）

---

## 项目结构

```text
.
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .gitignore
├── config/
│   └── data_sources.example.yaml
├── data/
│   ├── raw/           # 原始数据（不提交）
│   ├── parquet/       # 标准化数据（不提交）
│   └── reports/
├── src/
│   └── ashare_research/
│       ├── cli.py              # 命令行入口
│       ├── config.py           # 配置加载
│       ├── exceptions.py       # 自定义异常
│       ├── models.py           # 数据模型与代码转换
│       ├── providers/
│       │   ├── base.py         # 提供方抽象接口
│       │   ├── baostock_provider.py
│       │   └── akshare_provider.py
│       ├── storage/
│       │   ├── duckdb_store.py # DuckDB 元数据
│       │   └── parquet_store.py # Parquet 存储
│       ├── quality/
│       │   └── validators.py   # 数据质量检查
│       └── services/
│           └── data_service.py # 编排层
├── tests/
│   ├── test_models.py
│   ├── test_quality.py
│   ├── test_parquet_store.py
│   ├── test_duckdb_store.py
│   └── test_data_service.py
└── agent/
    ├── agent.md
    └── record/
```

---

## 路线图

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| Milestone 1: 免费数据底座 | 股票基础信息、交易日历、日线行情、Parquet/DuckDB 存储 | ✅ 已完成 |
| Milestone 2: 价值评估 MVP | 企业质量、估值、现金流、安全边际、风险否决项 | 条件关闭；评分附加项已条件关闭，PE numeric scoring deferred |
| Milestone 3: 机制验证 MVP | 假设检验、条件收益、控制变量、证据分级 | Stage 3C-A recovered and locked on canonical M3 baseline；synthetic-only；real development not executed；holdout sealed |
| Milestone 4: 通用研究器 | 可配置的假设验证框架 | 🔲 计划中 |
| Milestone 5: 分钟级研究 | 按需分钟数据验证 | 🔲 计划中 |
| Milestone 6: 本地 Web 界面 | Streamlit 工作台 | 🔲 计划中 |

---

## 许可

A software license has not yet been selected. The repository is currently public for review and research discussion; no additional reuse rights are granted unless a license is added later.
