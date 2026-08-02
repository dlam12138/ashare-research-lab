# A-Share Research Lab

> A股价值评估与市场机制验证实验室

一个使用免费数据、本地运行、面向A股的可解释研究平台：通过价值评估寻找值得研究的公司，通过机制验证检验个股与市场因素之间的真实关系。

> [!IMPORTANT]
> 本项目仅用于数据分析、统计研究和软件工程学习，不构成任何投资建议，也不提供自动交易能力。

**当前阶段：Milestone 1 数据底座已完成；Milestone 2 价值评估 MVP 进行中**

---

## 项目定位

本项目围绕两个核心模块：

1. **个股价值评估** — 企业质量、估值吸引力、价值兑现能力、风险否决项（M2 正在实现）
2. **市场机制验证** — 用统计方法检验个股与市场之间的可复现关系（尚未开始）

当前已完成第一阶段的**免费数据底座**：可运行、可测试、可追溯的本地数据基础设施。M2 已有 PetroChina（601857.SH）一份 PIT value profile 纵向切片；收益/现金、ROE/ROA、财务安全、股息和估值均已有阶段性能力。

M2 当前切片的正式验收见：[Stage 2G.1 trusted-lineage closeout](acceptance/m2_stage2g1_trusted_lineage_closeout.md) 和 [PetroChina value profile](reports/petrochina_value_profile_2021_2026.md)。Stage 2F 仍保留 9 个交易所证据缺口；只有完成 Stage 2G.1 后，才能称为该纵向切片的 canonical lineage closeout。

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
- M2 尚未完成 ROIC
- 评分闭环仍未开始
- 市场机制验证尚未开始
- Web 界面、目标价、推荐和自动交易尚未实现
- 当前 value profile 只覆盖 PetroChina（601857.SH）这一份 PIT 纵向切片
- Stage 2F 仍有 9 个交易所证据缺口；股本 A/H 拆分也需继续补充登记证据
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
| Milestone 2: 价值评估 MVP | 企业质量、估值、现金流、安全边际、风险否决项 | 🚧 进行中 |
| Milestone 3: 机制验证 MVP | 假设检验、条件收益、控制变量、证据分级 | 🔲 计划中 |
| Milestone 4: 通用研究器 | 可配置的假设验证框架 | 🔲 计划中 |
| Milestone 5: 分钟级研究 | 按需分钟数据验证 | 🔲 计划中 |
| Milestone 6: 本地 Web 界面 | Streamlit 工作台 | 🔲 计划中 |

---

## 许可

A software license has not yet been selected. The repository is currently public for review and research discussion; no additional reuse rights are granted unless a license is added later.
