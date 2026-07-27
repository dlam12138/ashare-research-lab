# 工作记录：M2 Stage 1 — 官方财务事实层、数据血缘与 Point-in-Time 基础

## 基本信息

- 日期：2026-07-27
- Agent：Claude Code (deepseek-v4-pro, ultracode)
- 分支：feat/m2-value-assessment-mvp
- 基线：9e016e7 (m1-data-foundation-trusted)
- 任务来源：Milestone 2 Stage 1
- 对应模块：价值评估（数据层）

## 任务目标

为中国石油 601857.SH 建立 2021—2025 年度、最近 8 个单季度，以及分红、回购、增持和审计事项的官方财务事实账本，并提供统一模型、结构化校验、运行血缘和 Point-in-Time 查询。

## 范围

- 新增 official_sources/, facts/, derivations/, validation/, lineage/, reports/ 模块
- 配置 official_sources/601857.SH.yaml 和 official_facts/601857.SH/ 目录
- 复用现有 BaseProvider、DuckDB、Parquet、QualityValidator 模式
- CLI 新增 build-value-facts, verify-value-facts, query-value-facts 命令

## 非目标

不实现评分、ROE、ROIC、估值、情景分析、Web 页面、全市场抓取

## 开始前状态

- 分支：feat/m2-value-assessment-mvp，干净
- 基线：9e016e7，tag m1-data-foundation-trusted 已推送
- 85 个测试通过，ruff 退出码 0

## 架构审查

### 现有模式（需复用）

| 模式 | 位置 | 复用方式 |
|------|------|---------|
| `BaseProvider` ABC | `providers/base.py` | `OfficialSourceProvider` 继承其 raw_dir/_save_raw_response 模式 |
| `DuckDBStore` | `storage/duckdb_store.py` | `FactRepository` 包装 DuckDBStore，复用 init_db/query 接口 |
| `QualityValidator` | `quality/validators.py` | `FactValidator` 复用 validate()→[{check_name,status,details}] 模式 |
| `DataService` | `services/data_service.py` | `FactService` 复用 fetch→validate→store 编排模式 |
| `write_parquet` / `read_parquet` | `storage/parquet_store.py` | 事实 Parquet 快照复用原子写入 |
| `load_config` | `config.py` | 新增 fact 相关配置项 |
| `AshareDataError` 异常族 | `exceptions.py` | 新增 FactValidationError、ConceptNotFoundError 等 |
| argparse CLI | `cli.py` | 新增 build-value-facts/verify-value-facts/query-value-facts 子命令 |

### 新增模块总览

```
src/ashare_research/
├── official_sources/       # 官方数据源提供方
│   ├── __init__.py
│   ├── base.py             # OfficialSourceProvider(ABC)
│   ├── petrochina.py       # PetroChinaProvider(OfficialSourceProvider)
│   └── registry.py         # OfficialSourceRegistry
├── facts/                  # 事实模型与存储
│   ├── __init__.py
│   ├── models.py           # Fact, FactContext, FactSet
│   ├── concepts.py         # ConceptRegistry（概念字典）
│   ├── contexts.py         # FactContext 构建与验证
│   ├── units.py            # UnitRegistry（单位字典与转换）
│   ├── mappings.py         # ConceptMapping（源字段→标准概念）
│   ├── repository.py       # FactRepository（DuckDB 事实存储）
│   ├── service.py          # FactService（编排层）
│   └── as_of.py            # AsOfQuery（PIT 查询引擎）
├── derivations/            # 派生事实计算
│   ├── __init__.py
│   ├── definitions.py      # DerivationRegistry（派生规则注册表）
│   └── engine.py           # DerivationEngine（执行派生计算）
├── validation/             # 财务事实校验
│   ├── __init__.py
│   ├── fact_schema.py      # 事实模式定义
│   ├── rule_registry.py    # FactValidationRuleRegistry
│   ├── validator.py        # FactValidator
│   └── results.py          # FactValidationResult
├── lineage/                # 数据血缘
│   ├── __init__.py
│   └── manifest.py         # LineageManifest
└── reports/                # 报告生成
    ├── __init__.py
    └── fact_profile.py     # FactProfileReport（Markdown）
```

### DuckDB Schema 扩展

在现有 schema（data_fetch_runs, dataset_registry, data_quality_results）基础上新增 5 张表：

```sql
-- 财务事实主表
CREATE TABLE IF NOT EXISTS financial_facts (
    fact_id VARCHAR PRIMARY KEY,
    concept_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    value DOUBLE,
    unit VARCHAR NOT NULL,
    context_id VARCHAR NOT NULL,
    is_derived BOOLEAN DEFAULT FALSE,
    derived_from VARCHAR DEFAULT '',     -- 逗号分隔的源 fact_id 列表
    source_provider VARCHAR NOT NULL,
    source_document VARCHAR DEFAULT '',
    filing_date VARCHAR NOT NULL,         -- 财报实际公告日期
    period_end VARCHAR NOT NULL,          -- 报告期截止日
    ingested_at VARCHAR NOT NULL,
    fetch_run_id VARCHAR DEFAULT '',
    quality_status VARCHAR DEFAULT ''
);

-- 事实上下文（报告期 + 公告日期）
CREATE TABLE IF NOT EXISTS fact_contexts (
    context_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    fiscal_year INTEGER NOT NULL,
    period_type VARCHAR NOT NULL,         -- FY, Q1, Q2, Q3, Q4
    period_start VARCHAR NOT NULL,
    period_end VARCHAR NOT NULL,
    filing_date VARCHAR NOT NULL,
    source_document VARCHAR DEFAULT '',
    created_at VARCHAR NOT NULL
);

-- 概念注册表
CREATE TABLE IF NOT EXISTS concept_registry (
    concept_id VARCHAR PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    display_name_zh VARCHAR DEFAULT '',
    description VARCHAR DEFAULT '',
    parent_concept_id VARCHAR DEFAULT '',
    category VARCHAR NOT NULL,            -- balance_sheet, income_statement, cash_flow,
                                          -- dividend, buyback, shareholder_increase, audit
    standard_unit VARCHAR DEFAULT '',
    created_at VARCHAR NOT NULL
);

-- 事实血缘
CREATE TABLE IF NOT EXISTS fact_lineage (
    lineage_id INTEGER PRIMARY KEY,
    fact_id VARCHAR NOT NULL,
    source_provider VARCHAR NOT NULL,
    source_method VARCHAR DEFAULT '',
    raw_file_path VARCHAR DEFAULT '',
    staging_file_path VARCHAR DEFAULT '',
    fetch_run_id VARCHAR DEFAULT '',
    parent_fact_ids VARCHAR DEFAULT '',
    recorded_at VARCHAR NOT NULL
);

-- 事实校验结果
CREATE TABLE IF NOT EXISTS fact_validation_results (
    id INTEGER PRIMARY KEY,
    fact_id VARCHAR NOT NULL,
    rule_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details VARCHAR DEFAULT '',
    checked_at VARCHAR NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS fact_lineage_seq START 1;
CREATE SEQUENCE IF NOT EXISTS fact_validation_seq START 1;
```

---

## M2 Stage 1 详细架构设计

### 1. official_sources/ — 官方数据源提供方

#### 1.1 base.py: `OfficialSourceProvider(ABC)`

**职责**：定义官方财务数据提供方的统一接口。复用现有 `BaseProvider` 的 raw_dir/_save_raw_response 模式。

**接口方法**：

```python
class OfficialSourceProvider(ABC):
    provider_name: str = "official_base"

    def __init__(self, raw_dir: str = ""):
        self.raw_dir = raw_dir
        self._last_raw_path: str = ""

    @abstractmethod
    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取财务报表数据。

        Returns DataFrame columns:
            symbol, report_type, fiscal_year, period_end, filing_date,
            concept_id, value, unit, source_document
        """

    @abstractmethod
    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取分红记录。"""

    @abstractmethod
    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取回购记录。"""

    @abstractmethod
    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取大股东增持记录。"""

    @abstractmethod
    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取审计意见。"""
```

**关键约束**：
- 所有方法返回的 DataFrame 使用标准 concept_id，源字段映射由 mappings 模块处理
- 财务数值保留原始单位，单位标准化在 FactService 层完成
- 报告截止日（period_end）和公告日（filing_date）必须同时提供
- 复用 `_save_raw_response()` 保存上游原始响应

#### 1.2 petrochina.py: `PetroChinaProvider(OfficialSourceProvider)`

**职责**：中国石油 601857.SH 的官方财务数据提供方。当前阶段数据来源为 AKShare 财务接口。

**数据来源**：
| 数据类型 | AKShare 接口 | 说明 |
|---------|-------------|------|
| 资产负债表 | `ak.stock_financial_balance_sheet_by_report_em` | 按报告期 |
| 利润表 | `ak.stock_financial_profit_by_report_em` | 按报告期 |
| 现金流量表 | `ak.stock_financial_cash_flow_by_report_em` | 按报告期 |
| 分红 | `ak.stock_dividents_detail_em` | 分红明细 |
| 审计意见 | `ak.stock_financial_abstract_ths` 或手工录入 | 审计意见需从年报摘要提取 |

**方法实现策略**：
- `get_financial_statements()` 调用三个报表接口，合并为统一事实流
- 每个财务指标映射为一条 Fact（concept_id + value + unit + context）
- 原始字段名→标准 concept_id 通过 ConceptMapping 转换
- 值乘以单位转换因子（如元→亿元）进入单位标准化阶段

#### 1.3 registry.py: `OfficialSourceRegistry`

**职责**：管理股票代码到官方数据提供方的映射。

```python
class OfficialSourceRegistry:
    def __init__(self):
        self._providers: dict[str, OfficialSourceProvider] = {}

    def register(self, symbol: str, provider: OfficialSourceProvider) -> None:
        """为指定标的注册提供方。"""

    def get_provider(self, symbol: str) -> OfficialSourceProvider:
        """获取标的对应提供方。"""
```

**设计理由**：与 DataService 的 provider 注册模式一致。未来扩展其他股票时只需注册新 provider，不修改 FactService。

---

### 2. facts/ — 事实模型与存储

#### 2.1 models.py: 核心数据模型

```python
@dataclass
class Fact:
    """原子财务事实。"""
    fact_id: str              # uuid hex 12
    concept_id: str           # 标准概念 ID
    symbol: str               # 601857.SH
    value: float | None       # 数值（可为 None 表示未披露）
    unit: str                 # CNY_100M / SHARES / PERCENT / RATIO / ...
    context_id: str           # 关联 FactContext
    is_derived: bool = False
    derived_from: str = ""    # 逗号分隔源 fact_id
    source_provider: str = ""
    source_document: str = "" # 如 "2024年年度报告"
    filing_date: str = ""     # 公告日期 YYYY-MM-DD
    period_end: str = ""      # 报告截止日 YYYY-MM-DD
    ingested_at: str = ""     # ISO datetime
    fetch_run_id: str = ""
    quality_status: str = ""

@dataclass
class FactContext:
    """事实的报告上下文。"""
    context_id: str
    symbol: str
    fiscal_year: int          # 2024
    period_type: str          # FY / Q1 / Q2 / Q3 / Q4
    period_start: str         # YYYY-MM-DD
    period_end: str           # YYYY-MM-DD
    filing_date: str          # 财报实际公告日期
    source_document: str = ""

@dataclass
class Concept:
    """标准财务概念。"""
    concept_id: str           # total_assets / net_profit_attr_parent / ...
    display_name: str         # "Total Assets"
    display_name_zh: str      # "总资产"
    description: str = ""
    parent_concept_id: str = ""
    category: str = ""        # balance_sheet / income_statement / ...
    standard_unit: str = ""   # 推荐单位

@dataclass
class FactSet:
    """一组相关事实的集合。"""
    facts: list[Fact]
    contexts: dict[str, FactContext]  # context_id → FactContext
    symbol: str
    generated_at: str = ""
    provider_name: str = ""
```

#### 2.2 concepts.py: `ConceptRegistry`

**职责**：管理所有标准金融概念的定义和层级关系。

**核心设计**：
- 概念 ID 使用蛇形命名：`total_assets`, `net_profit_attr_parent`, `operating_revenue`
- 概念按 category 分组：`balance_sheet`, `income_statement`, `cash_flow`, `dividend`, `buyback`, `shareholder_increase`, `audit`
- 支持父子层级（`parent_concept_id`），用于概念分组展示
- 初始概念集覆盖中国石油年报核心财务指标（约 40-60 个概念）

**关键概念清单（部分）**：

| concept_id | 中文名 | category | standard_unit |
|------------|--------|----------|---------------|
| total_assets | 总资产 | balance_sheet | CNY_100M |
| total_liabilities | 总负债 | balance_sheet | CNY_100M |
| total_equity_attr_parent | 归母权益 | balance_sheet | CNY_100M |
| current_assets | 流动资产 | balance_sheet | CNY_100M |
| non_current_assets | 非流动资产 | balance_sheet | CNY_100M |
| current_liabilities | 流动负债 | balance_sheet | CNY_100M |
| non_current_liabilities | 非流动负债 | balance_sheet | CNY_100M |
| operating_revenue | 营业收入 | income_statement | CNY_100M |
| operating_cost | 营业成本 | income_statement | CNY_100M |
| net_profit_attr_parent | 归母净利润 | income_statement | CNY_100M |
| net_profit | 净利润 | income_statement | CNY_100M |
| total_comprehensive_income | 综合收益总额 | income_statement | CNY_100M |
| operating_cash_flow | 经营活动现金流净额 | cash_flow | CNY_100M |
| investing_cash_flow | 投资活动现金流净额 | cash_flow | CNY_100M |
| financing_cash_flow | 筹资活动现金流净额 | cash_flow | CNY_100M |
| free_cash_flow | 自由现金流 | cash_flow | CNY_100M |
| basic_eps | 基本每股收益 | income_statement | CNY |
| diluted_eps | 稀释每股收益 | income_statement | CNY |
| total_shares | 总股本 | balance_sheet | SHARES_100M |
| dividend_per_share | 每股股利 | dividend | CNY |
| dividend_payout_amount | 分红总额 | dividend | CNY_100M |
| buyback_amount | 回购金额 | buyback | CNY_100M |
| buyback_shares | 回购股数 | buyback | SHARES |
| shareholder_increase_shares | 增持股数 | shareholder_increase | SHARES |
| shareholder_increase_amount | 增持金额 | shareholder_increase | CNY_100M |
| audit_opinion | 审计意见 | audit | TEXT |
| audit_firm | 审计机构 | audit | TEXT |

#### 2.3 contexts.py: 上下文构建

**职责**：从财务数据行构建 FactContext 对象。

**核心逻辑**：
- 从 report_type 字段解析 period_type（FY/Q1/Q2/Q3/Q4）
- 根据 fiscal_year 和 period_type 计算 period_start 和 period_end
- 中国石油财年 = 自然年（1月1日 - 12月31日），Q1=1-3月, Q2=1-6月（累计）, Q3=1-9月（累计）, Q4=1-12月（全年）
- filing_date 从财报数据中获取实际公告日期
- context_id 由 symbol + fiscal_year + period_type + filing_date 哈希生成

**辅助函数**：
```python
def build_context_id(symbol, fiscal_year, period_type, filing_date) -> str
def parse_period_type(report_type: str) -> str
def compute_period_dates(fiscal_year: int, period_type: str) -> tuple[str, str]
```

#### 2.4 units.py: `UnitRegistry`

**职责**：定义所有标准单位，提供转换辅助。

**标准单位**：
```python
class Unit(Enum):
    CNY = "CNY"                   # 人民币元
    CNY_100M = "CNY_100M"         # 人民币亿元
    CNY_10K = "CNY_10K"           # 人民币万元
    SHARES = "SHARES"             # 股
    SHARES_100M = "SHARES_100M"   # 亿股
    SHARES_10K = "SHARES_10K"     # 万股
    PERCENT = "PERCENT"           # 百分比
    PERMILLE = "PERMILLE"         # 千分比
    RATIO = "RATIO"               # 无单位比率
    TIMES = "TIMES"               # 倍数
    DAYS = "DAYS"                 # 天数
    TEXT = "TEXT"                 # 文本（审计意见等）
```

**单位转换表**（显式、不可隐式）：
```python
UNIT_CONVERSIONS = {
    ("CNY", "CNY_100M"): 1e-8,
    ("CNY_100M", "CNY"): 1e8,
    ("CNY_10K", "CNY_100M"): 1e-4,
    ("SHARES", "SHARES_100M"): 1e-8,
    # ... 仅定义明确的一对一转换
}
```

**关键约束**：禁止隐式单位转换。FactService 必须显式调用 convert_unit()。

#### 2.5 mappings.py: `ConceptMapping`

**职责**：将数据源字段名映射为标准 concept_id，同时进行单位转换。

**映射表结构**：
```python
# 示例：AKShare 利润表字段 → 标准概念
PETROCHINA_AKSHARE_INCOME_MAPPING = {
    "营业收入": {
        "concept_id": "operating_revenue",
        "unit": Unit.CNY,           # AKShare 返回的是元
        "target_unit": Unit.CNY_100M,  # 标准化为亿元
    },
    "净利润": {
        "concept_id": "net_profit",
        "unit": Unit.CNY,
        "target_unit": Unit.CNY_100M,
    },
    "归属母公司股东的净利润": {
        "concept_id": "net_profit_attr_parent",
        "unit": Unit.CNY,
        "target_unit": Unit.CNY_100M,
    },
    # ...
}
```

**映射接口**：
```python
class ConceptMapping:
    def map_field(self, provider: str, raw_field: str) -> tuple[str, Unit, Unit] | None:
        """返回 (concept_id, source_unit, target_unit) 或 None（未映射字段跳过）。"""

    def get_mapped_concepts(self, provider: str) -> list[str]:
        """返回该提供方支持的所有标准概念 ID。"""
```

#### 2.6 repository.py: `FactRepository`

**职责**：事实的 DuckDB 持久化层，封装所有事实相关数据库操作。

**核心方法**：
```python
class FactRepository:
    def __init__(self, duckdb_store: DuckDBStore):
        """包装现有 DuckDBStore。"""

    def init_schema(self) -> None:
        """创建 financial_facts, fact_contexts, concept_registry,
        fact_lineage, fact_validation_results 表。"""

    def store_facts(self, facts: list[Fact]) -> int:
        """批量插入事实（使用 INSERT OR REPLACE 按 fact_id 去重）。
        Returns: 实际写入行数。"""

    def store_contexts(self, contexts: list[FactContext]) -> int:
        """批量插入上下文。"""

    def store_concepts(self, concepts: list[Concept]) -> int:
        """批量插入概念定义。"""

    def query_facts(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
        period_types: list[str] | None = None,
        fiscal_years: list[int] | None = None,
        as_of: str | None = None,
    ) -> pd.DataFrame:
        """查询事实。as_of 不为 None 时仅返回 filing_date <= as_of 的事实。"""

    def get_context(self, context_id: str) -> dict | None:

    def get_concept(self, concept_id: str) -> dict | None:

    def get_all_concepts(self) -> pd.DataFrame:

    def delete_facts_for_symbol(self, symbol: str) -> int:
        """删除指定标的的全部事实（用于重建）。"""
```

**关键约束**：
- `store_facts()` 使用 `INSERT OR REPLACE`，允许重复构建（幂等）
- 写入前验证 fact_id、context_id、concept_id 完整性
- fact_id 格式：`{symbol}_{concept_id}_{context_id}` 的 SHA-256 前 12 位

#### 2.7 service.py: `FactService`

**职责**：编排事实构建全流程。复用 DataService 的 fetch→validate→store 编排模式。

**核心方法**：
```python
class FactService:
    def __init__(self, repository: FactRepository, validator: FactValidator,
                 derivation_engine: DerivationEngine, lineage: LineageManifest,
                 config: dict):
        ...

    def build_facts(
        self, symbol: str, start_year: int, end_year: int, provider_name: str = ""
    ) -> dict:
        """全量构建事实。

        流程：
        1. 获取官方数据提供方
        2. 调用 get_financial_statements() → 标准化 → Fact 对象列表
        3. 调用 get_dividends(), get_buybacks(), get_shareholder_increases(),
           get_audit_opinions()
        4. FactRepository.store_contexts()
        5. FactRepository.store_facts()
        6. FactValidator.validate() → 质量检查
        7. DerivationEngine.derive() → 单季度派生事实
        8. FactRepository.store_facts(derived)
        9. LineageManifest.record() → 血缘记录
        10. 返回构建摘要

        Returns:
            dict with: total_facts, reported_facts, derived_facts, quality_status,
                       validation_summary
        """

    def rebuild_facts(self, symbol: str, start_year: int, end_year: int) -> dict:
        """重建事实（先删后建）。"""
```

**与 DataService 模式的差异**：
- FactService 不直接调用 Provider，通过 OfficialSourceRegistry 间接调用
- 编排粒度更细：事实是逐条构建的，而非批次 DataFrame
- 派生步骤在验证和存储之间插入
- 血缘记录是独立步骤，与存储解耦

#### 2.8 as_of.py: `AsOfQuery`

**职责**：Point-in-Time 查询引擎。

**核心方法**：
```python
class AsOfQuery:
    def __init__(self, repository: FactRepository):
        self.repo = repository

    def query(
        self,
        symbol: str,
        concept_ids: list[str],
        as_of_date: str,
    ) -> pd.DataFrame:
        """以 as_of_date 为截止点查询已知事实。

        仅返回 filing_date <= as_of_date 的事实。
        这意味着：
        - 2025-03-31 查询：看不到 2024 年年报（4月才公告）
        - 2025-05-01 查询：可以看到 2024 年年报
        """

    def get_latest_for_period(
        self, symbol: str, fiscal_year: int, period_type: str
    ) -> dict[str, Fact]:
        """获取某报告期的最新已知事实（即使有修正稿也取最新公告日）。"""

    def compare_as_of(
        self, symbol: str, concept_ids: list[str], date_a: str, date_b: str
    ) -> pd.DataFrame:
        """比较两个时点的已知事实差异（用于审计修正追踪）。"""
```

**关键设计**：
- PIT 的基础是 filing_date，不是 period_end
- filing_date 严格从财报公告日期获取（来自 AKShare 或手工配置）
- 同一 period_end 可能有多次公告（修正稿），取 filing_date 最大者为最新
- 查询结果中额外标注 `knowledge_date` = max(filing_date) for each (concept_id, period_end) pair

---

### 3. derivations/ — 派生事实计算

#### 3.1 definitions.py: `DerivationRegistry`

**职责**：注册和管理派生规则定义。

**规则结构**：
```python
@dataclass
class DerivationRule:
    rule_id: str                # e.g. "single_quarter_net_profit"
    output_concept_id: str      # e.g. "net_profit_attr_parent_single_q"
    input_concept_ids: list[str]  # e.g. ["net_profit_attr_parent"]
    description: str
    formula: Callable           # 计算函数

    def compute(self, facts: dict[str, float]) -> float | None:
        """从输入事实值计算派生值。"""
```

**初始派生规则**（仅单季度拆分）：

| rule_id | 输出概念 | 输入概念 | 公式 |
|---------|---------|---------|------|
| single_q_net_profit | net_profit_attr_parent_q | net_profit_attr_parent | Q1单季=Q1累计; Q2单季=Q2累计-Q1累计; Q3单季=Q3累计-Q2累计; Q4单季=Q4累计-Q3累计 |
| single_q_revenue | operating_revenue_q | operating_revenue | 同上模式 |
| single_q_operating_cf | operating_cash_flow_q | operating_cash_flow | 同上模式 |
| single_q_capex | capex_q | capex | 同上模式 |
| single_q_fcf | free_cash_flow_q | free_cash_flow | FCF_q = operating_cash_flow_q - capex_q |

**关键约束**：
- **仅支持单季度拆分**：从累计值计算单季度值
- 不做 TTM（滚动十二个月）
- 不做同比/环比计算（那是评估层的职责）
- 不做 CAGR 或任何多期聚合

#### 3.2 engine.py: `DerivationEngine`

**职责**：执行派生计算。

```python
class DerivationEngine:
    def __init__(self, registry: DerivationRegistry):
        self.registry = registry

    def derive(
        self, reported_facts: list[Fact], symbol: str
    ) -> list[Fact]:
        """从报告事实计算派生事实。

        输入：同一 symbol 的报告事实（含所有 period_type，FY/Q1/Q2/Q3/Q4）
        输出：派生事实列表（is_derived=True, derived_from=源fact_id列表）

        对于每个 DerivationRule：
        1. 按 fiscal_year 分组
        2. 对每个 fiscal_year，收集所需 period_type 的输入事实值
        3. 调用 formula 计算
        4. 生成派生 Fact，标记 is_derived=True

        派生事实的 context_id 复用对应 period_type 的报告上下文。
        Q1 单季度 → 复用 Q1 context
        Q2 单季度 → 需要构造"Q2 单季度" context（period_start=04-01, period_end=06-30）
        """

    def derive_single_quarter(
        self, facts: list[Fact], concept_id: str, symbol: str
    ) -> list[Fact]:
        """通用单季度拆分：从 FY/Q1/Q2/Q3/Q4 累计值计算 Q1/Q2/Q3/Q4 单季度值。

        逻辑：
        - Q1 单季度 = Q1 值（Q1 报告本身就是单季度）
        - Q2 单季度 = Q2 累计值 - Q1 累计值
        - Q3 单季度 = Q3 累计值 - Q2 累计值
        - Q4 单季度 = Q4 累计值 - Q3 累计值
        - 若所需输入缺失则跳过该季度
        """
```

---

### 4. validation/ — 财务事实校验

#### 4.1 fact_schema.py: 事实模式定义

**职责**：定义每种概念类别的必需字段和约束。

```python
FACT_REQUIRED_FIELDS = [
    "fact_id", "concept_id", "symbol", "unit", "context_id",
    "source_provider", "filing_date", "period_end",
]

# 概念类别 → 数值约束
CONCEPT_VALUE_CONSTRAINTS = {
    "balance_sheet": {"min": 0},          # 资产/负债/权益 >= 0
    "income_statement": {},               # 利润可为负
    "cash_flow": {},                      # 现金流可为负
    "dividend": {"min": 0},               # 分红 >= 0
    "buyback": {"min": 0},                # 回购 >= 0
    "shareholder_increase": {"min": 0},   # 增持 >= 0
    "audit": {"value_type": "text"},      # 审计意见是文本
}

# 跨事实一致性约束
CROSS_FACT_RULES = {
    "accounting_identity": {
        "description": "资产 = 负债 + 权益",
        "formula": "total_assets ≈ total_liabilities + total_equity_attr_parent + minority_interest",
        "tolerance": 0.01,  # 1% 容差
    },
}
```

#### 4.2 rule_registry.py: `FactValidationRuleRegistry`

**职责**：注册和管理所有校验规则。复用 QualityValidator 的规则注册模式。

```python
class FactValidationRuleRegistry:
    def __init__(self):
        self._rules: dict[str, Callable] = {}

    def register(self, rule_name: str, rule_fn: Callable) -> None:
        """注册校验规则。"""

    def get_rules(self) -> dict[str, Callable]:
        """获取所有已注册规则。"""

    def get_rules_for_category(self, category: str) -> list[str]:
        """获取某概念类别的适用规则。"""
```

**预定义规则清单**：

| rule_name | 类别 | 描述 |
|-----------|------|------|
| required_fields_present | 所有 | fact_id, concept_id, symbol, unit, context_id 非空 |
| value_is_finite | 数值事实 | value 不是 NaN、inf、-inf |
| concept_id_known | 所有 | concept_id 在 ConceptRegistry 中存在 |
| context_id_valid | 所有 | context_id 在 fact_contexts 表中存在 |
| unit_known | 所有 | unit 在 UnitRegistry 中存在 |
| unit_matches_concept | 数值事实 | unit 与该 concept 的 standard_unit 兼容 |
| filing_date_after_period_end | 所有 | filing_date >= period_end |
| period_end_valid | 所有 | period_end 是有效日期 |
| positive_assets | balance_sheet | 资产类概念 value >= 0 |
| positive_equity | balance_sheet | 归母权益 value 合理 |
| no_duplicate_facts | 所有 | (concept_id, symbol, context_id) 唯一（同报告期同概念不重复） |
| accounting_identity | balance_sheet | 总资产 ≈ 总负债 + 归母权益 + 少数股东权益（容差 1%） |

#### 4.3 validator.py: `FactValidator`

**职责**：执行所有校验规则。复用 QualityValidator 的 validate() 接口模式。

```python
class FactValidator:
    def __init__(self, rule_registry: FactValidationRuleRegistry,
                 concept_registry: ConceptRegistry):
        ...

    def validate(self, facts: list[Fact]) -> list[FactValidationResult]:
        """对事实集合运行全部适用规则。

        Returns: 校验结果列表，每条对应一个 (fact_id, rule_name) 组合。
        """

    def validate_single(self, fact: Fact) -> list[FactValidationResult]:
        """对单条事实运行适用规则。"""

    def validate_cross_fact(self, facts: list[Fact]) -> list[FactValidationResult]:
        """运行跨事实一致性规则（如 accounting_identity）。"""

    def record_results(
        self, results: list[FactValidationResult], duckdb_store: DuckDBStore
    ) -> None:
        """将校验结果写入 DuckDB fact_validation_results 表。"""
```

#### 4.4 results.py: `FactValidationResult`

```python
@dataclass
class FactValidationResult:
    fact_id: str
    rule_name: str
    status: str          # passed / failed / warning
    details: str = ""
    checked_at: str = ""
```

---

### 5. lineage/ — 数据血缘

#### 5.1 manifest.py: `LineageManifest`

**职责**：记录和查询完整的数据血缘。

```python
class LineageManifest:
    def __init__(self, duckdb_store: DuckDBStore):
        ...

    def record_fact_lineage(
        self,
        fact: Fact,
        source_provider: str,
        source_method: str,
        raw_file_path: str = "",
        staging_file_path: str = "",
        fetch_run_id: str = "",
        parent_fact_ids: str = "",
    ) -> None:
        """记录单条事实的血缘。"""

    def record_batch_lineage(
        self, facts: list[Fact], source_provider: str,
        source_method: str, fetch_run_id: str, raw_file_path: str = "",
    ) -> None:
        """批量记录血缘。"""

    def get_fact_lineage(self, fact_id: str) -> dict:
        """查询单条事实的完整血缘链。"""

    def get_symbol_lineage(self, symbol: str) -> pd.DataFrame:
        """查询某标的全部事实的血缘摘要。"""

    def generate_manifest(self, symbol: str) -> str:
        """生成 Markdown 格式的血缘清单。

        包含：
        - 数据源和接口
        - 原始文件路径
        - 抓取时间和 run_id
        - 派生关系图（derived facts → source facts）
        - 质量检查摘要
        """
```

**血缘追踪的完整路径**：
```
AKShare API → raw/akshare/financial/601857_SH_20260727_120000.parquet
           → staging/akshare/financial/601857_SH_20260727_120000_abc123.parquet
           → Fact objects (fact_id list)
           → DuckDB financial_facts table
           → [if derived] parent_fact_ids → source facts
```

---

### 6. reports/ — 报告生成

#### 6.1 fact_profile.py: `FactProfileReport`

**职责**：生成中国石油官方财务事实档案 Markdown 报告。

```python
class FactProfileReport:
    def __init__(self, repository: FactRepository, lineage: LineageManifest,
                 config: dict):
        ...

    def generate(
        self, symbol: str, as_of: str | None = None, output_path: str = ""
    ) -> str:
        """生成完整的 Markdown 事实档案。

        报告结构：
        1. 标题与元信息（标的代码、名称、报告生成时间、数据截止时点）
        2. 数据来源声明（提供方、接口、抓取时间）
        3. 资产负债表事实（按年度表格展示，最近 5 年）
        4. 利润表事实（同上）
        5. 现金流量表事实（同上）
        6. 每股指标事实
        7. 分红记录（历史分红一览）
        8. 回购与增持记录
        9. 审计历史（审计意见、审计机构）
        10. 派生事实（单季度指标）
        11. 数据质量摘要（校验通过/失败/警告统计）
        12. 血缘摘要（数据来源和追溯路径）
        13. 免责声明（数据不构成投资建议）

        Output path: data/reports/fact_profile_601857_SH_{YYYYMMDD}.md
        """

    def _render_balance_sheet_section(self, symbol: str, as_of: str | None) -> str:
        """渲染资产负债表部分。"""

    def _render_income_statement_section(self, symbol: str, as_of: str | None) -> str:
        """渲染利润表部分。"""

    def _render_cash_flow_section(self, symbol: str, as_of: str | None) -> str:
        """渲染现金流量表部分。"""

    def _render_quality_summary(self, symbol: str) -> str:
        """渲染质量检查摘要。"""

    def _render_lineage_summary(self, symbol: str) -> str:
        """渲染血缘摘要。"""
```

---

### 7. 数据流全貌

```
┌─────────────────────────────────────────────────────────────────────┐
│                        M2 Stage 1 Data Flow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CLI: build-value-facts 601857.SH --start 2021 --end 2025            │
│    │                                                                 │
│    ▼                                                                 │
│  FactService.build_facts()                                           │
│    │                                                                 │
│    ├─► OfficialSourceRegistry.get_provider("601857.SH")              │
│    │     └─► PetroChinaProvider                                      │
│    │                                                                 │
│    ├─► PetroChinaProvider.get_financial_statements()                 │
│    │     ├─► akshare API (三大报表)                                   │
│    │     ├─► _save_raw_response() → data/raw/akshare/financial/     │
│    │     ├─► ConceptMapping.map_field() → 标准化                     │
│    │     └─► 返回 list[Fact]                                         │
│    │                                                                 │
│    ├─► PetroChinaProvider.get_dividends/get_buybacks/...             │
│    │     └─► 同上流程                                                 │
│    │                                                                 │
│    ├─► FactRepository.store_contexts() → DuckDB fact_contexts        │
│    ├─► FactRepository.store_facts() → DuckDB financial_facts         │
│    │                                                                 │
│    ├─► FactValidator.validate()                                      │
│    │     ├─► 逐条校验 (required_fields, unit, concept_id...)         │
│    │     ├─► 跨事实校验 (accounting_identity)                        │
│    │     └─► 结果 → DuckDB fact_validation_results                   │
│    │                                                                 │
│    ├─► DerivationEngine.derive()                                     │
│    │     ├─► 从累计值计算单季度值                                     │
│    │     ├─► 标记 is_derived=True, derived_from=源fact_id            │
│    │     └─► 返回 list[Fact] (derived)                               │
│    │                                                                 │
│    ├─► FactRepository.store_facts(derived) → DuckDB                  │
│    │                                                                 │
│    ├─► LineageManifest.record_batch_lineage()                        │
│    │     └─► 全部事实的源→路径→时间链 → DuckDB fact_lineage          │
│    │                                                                 │
│    └─► FactProfileReport.generate()                                  │
│          └─► data/reports/fact_profile_601857_SH_YYYYMMDD.md         │
│                                                                      │
│  CLI: query-value-facts 601857.SH --concept net_profit_attr_parent   │
│                              --as-of 2026-03-31                       │
│    │                                                                 │
│    ▼                                                                 │
│  AsOfQuery.query()                                                   │
│    ├─► SELECT * FROM financial_facts                                 │
│    │    WHERE symbol='601857.SH' AND concept_id='...'                │
│    │    AND filing_date <= '2026-03-31'                              │
│    └─► 返回事实列表（2026-03-31 之前公告的全部已知事实）              │
│                                                                      │
│  CLI: verify-value-facts 601857.SH                                   │
│    │                                                                 │
│    ▼                                                                 │
│  FactValidator.validate(已存储的事实) → 输出 check 结果               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 8. CLI 扩展

在现有 CLI 基础上新增 3 个子命令：

```bash
# 构建事实
ashare-research build-value-facts 601857.SH --start 2021 --end 2025
    [--provider petrochina_akshare] [--rebuild] [--verbose]

# 校验事实
ashare-research verify-value-facts 601857.SH
    [--verbose]

# PIT 查询
ashare-research query-value-facts 601857.SH
    --concept net_profit_attr_parent,total_assets,operating_revenue
    [--as-of 2026-03-31] [--format table|json]
```

---

### 9. 配置扩展

在 `config/data_sources.example.yaml` 中新增：

```yaml
official_sources:
  petrochina:
    provider: petrochina_akshare
    fiscal_year_start: 2021
    fiscal_year_end: 2025

facts:
  parquet_snapshot_dir: "data/parquet/facts"
  rebuild_on_mismatch: true

validation:
  accounting_identity_tolerance: 0.01
  warn_missing_filing_date: true
  reject_negative_assets: true

reports:
  output_dir: "data/reports"
  include_lineage: true
  include_quality_summary: true
```

---

### 10. 关键工程决策

#### 决策一：事实粒度采用"一概念一行"

- **内容**：每条 Fact 对应一个 (concept_id, symbol, context_id) 组合
- **原因**：查询灵活，PIT 过滤精确，派生事实可追溯
- **替代方案**：宽表（一行包含所有概念）
- **未采用原因**：宽表不便于 PIT 查询（无法区分每个概念的公告时间差异，如同一报表中不同附注可能有不同修正日期）

#### 决策二：单季度派生从累计值计算

- **内容**：DerivationEngine 仅从 Q1/Q2/Q3/Q4 累计值拆分单季度值
- **原因**：AKShare 财务接口通常返回累计值，需要拆分才能获得单季度数据
- **替代方案**：直接从季度报告获取单季度值
- **未采用原因**：需要额外数据源或手工录入，不符合当前免费数据优先原则

#### 决策三：派生事实的 context 复用报告上下文

- **内容**：Q2 单季度净利的事实复用"2024年半年报"的 context（period_end=2024-06-30, filing_date=实际公告日）
- **原因**：单季度值的信息在半年报/三季报/年报中首次披露，context 应反映信息来源
- **风险**：若 Q2 累计值来自 Q2 报告而 Q1 累计值来自 Q1 报告，派生事实的 filing_date 应取两者的较晚者

#### 决策四：FactRepository 不新建 DuckDB 连接

- **内容**：FactRepository 包装现有 DuckDBStore 实例，不独立建连接
- **原因**：保持单一数据库连接，避免锁冲突
- **风险**：所有事实操作共享同一个 DuckDB 文件，需注意事务边界

#### 决策五：报告使用纯 Markdown

- **内容**：FactProfileReport 输出 Markdown 文件，不做 HTML/PDF
- **原因**：Markdown 可直接版本控制、diff、简单渲染
- **替代方案**：Jinja2 模板 + HTML 报告
- **未采用原因**：额外依赖，过度设计；后续可用 md-to-docx skill 转 Word

---

### 11. 与现有模块的关系（不修改现有代码）

| 现有模块 | 关系 | 说明 |
|---------|------|------|
| `providers/base.py` | 模式复用 | OfficialSourceProvider 是独立 ABC，不继承 BaseProvider（接口不同） |
| `providers/akshare_provider.py` | 数据源 | PetroChinaProvider 内部使用 akshare API，但不继承 AKShareProvider |
| `storage/duckdb_store.py` | 依赖注入 | FactRepository 接收 DuckDBStore 实例，通过 .query() 执行 SQL |
| `storage/parquet_store.py` | 直接复用 | 事实 Parquet 快照复用 write_parquet/read_parquet |
| `quality/validators.py` | 模式复用 | FactValidator 独立实现，复用 validate()→[{check_name,status,details}] 模式 |
| `services/data_service.py` | 模式复用 | FactService 独立实现，复用编排模式 |
| `config.py` | 扩展 | 新增 official_sources/facts/validation/reports 配置节 |
| `exceptions.py` | 扩展 | 新增 FactValidationError、ConceptNotFoundError、DerivationError |
| `models.py` | 扩展 | 新增 Fact、FactContext、Concept 等 dataclass |
| `cli.py` | 扩展 | 新增 3 个子命令，不修改现有命令 |

---

### 12. 文件创建清单（预估 35 个文件）

**新增模块文件（24 个 .py 文件 + 6 个 \_\_init\_\_.py）**：

```
src/ashare_research/official_sources/__init__.py
src/ashare_research/official_sources/base.py
src/ashare_research/official_sources/petrochina.py
src/ashare_research/official_sources/registry.py

src/ashare_research/facts/__init__.py
src/ashare_research/facts/models.py
src/ashare_research/facts/concepts.py
src/ashare_research/facts/contexts.py
src/ashare_research/facts/units.py
src/ashare_research/facts/mappings.py
src/ashare_research/facts/repository.py
src/ashare_research/facts/service.py
src/ashare_research/facts/as_of.py

src/ashare_research/derivations/__init__.py
src/ashare_research/derivations/definitions.py
src/ashare_research/derivations/engine.py

src/ashare_research/validation/__init__.py
src/ashare_research/validation/fact_schema.py
src/ashare_research/validation/rule_registry.py
src/ashare_research/validation/validator.py
src/ashare_research/validation/results.py

src/ashare_research/lineage/__init__.py
src/ashare_research/lineage/manifest.py

src/ashare_research/reports/__init__.py
src/ashare_research/reports/fact_profile.py
```

**修改的现有文件（6 个）**：
- `src/ashare_research/exceptions.py` — 新增异常类
- `src/ashare_research/models.py` — 新增 dataclass
- `src/ashare_research/config.py` — 新增默认配置节
- `src/ashare_research/cli.py` — 新增 3 个子命令
- `config/data_sources.example.yaml` — 新增配置节
- `pyproject.toml` — version bump 0.1.0 → 0.2.0

**新增测试文件（预估 8 个）**：
- `tests/test_fact_models.py`
- `tests/test_fact_concepts.py`
- `tests/test_fact_units.py`
- `tests/test_fact_repository.py`
- `tests/test_fact_service.py`
- `tests/test_derivation_engine.py`
- `tests/test_fact_validator.py`
- `tests/test_as_of_query.py`

---

### 13. 测试策略

| 测试类别 | 目标覆盖 | 策略 |
|---------|---------|------|
| 模型测试 | Fact, FactContext, Concept, FactValidationResult | 纯单元测试，无需网络 |
| 概念/单位注册表测试 | ConceptRegistry, UnitRegistry | 验证注册、查询、去重 |
| 派生引擎测试 | DerivationEngine | Mock 输入事实，验证输出正确性 |
| 校验器测试 | FactValidator | Mock 事实，验证每条规则通过/失败 |
| 仓储测试 | FactRepository | 使用临时 DuckDB，验证 CRUD |
| 服务测试 | FactService | Mock Provider，验证编排流程 |
| PIT 查询测试 | AsOfQuery | 插入不同 filing_date 的事实，验证过滤 |
| 报告生成测试 | FactProfileReport | 验证 Markdown 格式、数据呈现 |

---

### 14. 架构设计核查清单

**复用现有模式**：
- [x] OfficialSourceProvider 复用 BaseProvider 的 raw_dir/_save_raw_response 模式
- [x] FactRepository 包装 DuckDBStore 实例（不独立建连接）
- [x] FactValidator 复用 QualityValidator 的 validate()→[{check_name,status,details}] 接口
- [x] FactService 复用 DataService 的编排模式（fetch→validate→store）
- [x] 事实 Parquet 快照复用 write_parquet/read_parquet 原子写入
- [x] CLI 复用 argparse 模式（新增子命令，不改现有命令）
- [x] 配置复用 load_config/_deep_merge 模式
- [x] 异常继承 AshareDataError

**数据原则遵守**：
- [x] 所有事实带 source_provider + filing_date + period_end
- [x] 原始 API 响应通过 _save_raw_response 留存
- [x] 单位显式标注（Unit enum），不隐式转换
- [x] 财务数据按 filing_date 生效（PIT 基础）
- [x] 禁止未来数据泄漏（as_of 查询基于 filing_date）
- [x] 数据缺失不自动视为零（value 可为 None）
- [x] 接口失败不静默返回空

**项目边界遵守**：
- [x] 不实现评分、ROE、ROIC、估值计算
- [x] 不实现明日涨跌预测
- [x] 不实现黑箱荐股
- [x] 单季度派生仅做减法拆分，不做 TTM/同比/环比
- [x] 报告仅呈现事实，不给投资建议
- [x] 不开发自动交易、券商接口

**架构质量**：
- [x] 模块职责单一，边界清晰
- [x] 接口通过 ABC 或 Protocol 定义
- [x] 无循环依赖（依赖方向：reports→lineage→facts→official_sources→外部 API）
- [x] DuckDB schema 有版本号
- [x] 事实 ID 可复现（SHA-256 前 12 位，基于内容）
- [x] 幂等构建（INSERT OR REPLACE）
- [x] 完整血缘追踪链

---

## 实施计划

### 阶段 A：基础模型与注册表（无外部依赖）

1. 创建 `facts/models.py` — Fact, FactContext, Concept, FactSet dataclass
2. 创建 `facts/concepts.py` — ConceptRegistry 及初始概念集（~40-60 个概念）
3. 创建 `facts/units.py` — Unit enum 及 UnitRegistry
4. 创建 `facts/contexts.py` — FactContext 构建与验证辅助函数
5. 更新 `models.py` — 添加 dataclass 引用（或保持独立）
6. 更新 `exceptions.py` — 新增 FactValidationError, ConceptNotFoundError, DerivationError

### 阶段 B：官方数据源

7. 创建 `official_sources/base.py` — OfficialSourceProvider ABC
8. 创建 `official_sources/registry.py` — OfficialSourceRegistry
9. 创建 `facts/mappings.py` — ConceptMapping（PetroChina AKShare 字段映射）
10. 创建 `official_sources/petrochina.py` — PetroChinaProvider 实现

### 阶段 C：存储与校验

11. 创建 `facts/repository.py` — FactRepository（DuckDB schema + CRUD）
12. 创建 `validation/results.py` — FactValidationResult dataclass
13. 创建 `validation/fact_schema.py` — 事实模式定义和约束
14. 创建 `validation/rule_registry.py` — FactValidationRuleRegistry
15. 创建 `validation/validator.py` — FactValidator

### 阶段 D：派生引擎

16. 创建 `derivations/definitions.py` — DerivationRegistry + DerivationRule
17. 创建 `derivations/engine.py` — DerivationEngine

### 阶段 E：服务编排与查询

18. 创建 `facts/service.py` — FactService（主编排器）
19. 创建 `facts/as_of.py` — AsOfQuery（PIT 查询）
20. 创建 `lineage/manifest.py` — LineageManifest

### 阶段 F：报告与 CLI

21. 创建 `reports/fact_profile.py` — FactProfileReport
22. 更新 `cli.py` — 新增 build-value-facts, verify-value-facts, query-value-facts
23. 更新 `config.py` — 新增配置默认值
24. 更新 `config/data_sources.example.yaml`
25. 更新 `pyproject.toml` — version bump

### 阶段 G：测试

26. 编写所有测试文件
27. 运行 ruff + pytest
28. 真实 Smoke：对中国石油 2021-2025 构建事实并生成报告

---

## 实际操作

（执行过程中持续更新）

---

## 决策记录

### 决策一：事实粒度采用"一概念一行"

- 决策内容：每条 Fact 对应一个 (concept_id, symbol, context_id) 组合
- 采用原因：查询灵活，PIT 过滤精确，派生事实可追溯
- 考虑过的替代方案：宽表（一行包含所有概念）
- 未采用替代方案的原因：宽表不便于 PIT 查询（无法区分每个概念的公告时间差异）
- 潜在风险：事实数量较大（~60 概念 x 5 年 x 4 季 = 1200 条），但在 DuckDB 中完全可控

### 决策二：单季度派生从累计值计算

- 决策内容：DerivationEngine 仅从 Q1/Q2/Q3/Q4 累计值拆分单季度值
- 采用原因：AKShare 财务接口通常返回累计值，需要拆分才能获得单季度数据
- 考虑过的替代方案：直接从季度报告获取单季度值
- 未采用替代方案的原因：需要额外数据源或手工录入，不符合当前免费数据优先原则
- 潜在风险：若累计值在修正报告中更改，派生事实需随之更新

### 决策三：派生事实的 context 复用报告上下文

- 决策内容：Q2 单季度净利的事实复用"半年报"的 context
- 采用原因：单季度值的信息在半年报/三季报/年报中首次披露，context 应反映信息来源
- 考虑过的替代方案：构造独立的"单季度" context
- 未采用替代方案的原因：会丢失 filing_date 信息，无法 PIT 查询
- 潜在风险：若 Q2 累计值和 Q1 累计值来自不同公告日期的报告，派生事实的 filing_date 需取较晚者

### 决策四：FactRepository 不新建 DuckDB 连接

- 决策内容：FactRepository 包装现有 DuckDBStore 实例，不独立建连接
- 采用原因：保持单一数据库连接，避免锁冲突，复用现有连接管理
- 考虑过的替代方案：FactRepository 内部创建独立 DuckDB 连接
- 未采用替代方案的原因：双连接会导致写入冲突和事务不一致
- 潜在风险：所有事实操作共享同一个 DuckDB 文件，需注意事务边界

### 决策五：报告使用纯 Markdown

- 决策内容：FactProfileReport 输出 Markdown 文件
- 采用原因：可直接版本控制、diff、简单渲染
- 考虑过的替代方案：Jinja2 模板 + HTML 报告
- 未采用替代方案的原因：额外依赖，过度设计；后续可用 md-to-docx skill 转 Word
- 潜在风险：Markdown 表格在大量数据时排版受限

## 验证

（执行过程中持续更新）

## 结果

（执行完成后更新）

## 遗留问题

（执行过程中持续更新）

## 下一步建议

- 架构确认后进入阶段 A 实现（基础模型与注册表）
- 实现过程中遇到 AKShare 接口问题应记录到决策记录

## 最终文件变更

（执行完成后更新）

## 最终 Git 状态

（执行完成后更新）

