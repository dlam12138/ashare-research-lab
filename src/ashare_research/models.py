"""统一数据模型。

定义项目中所有标准化数据结构，以及股票代码格式转换函数。

股票代码内部统一格式：600000.SH / 000001.SZ
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── 代码转换 ────────────────────────────────────────────────

_SYMBOL_RE = re.compile(r"^(\d{6})\.(SH|SZ)$")
_BAOSTOCK_RE = re.compile(r"^(sh|sz)\.(\d{6})$", re.IGNORECASE)


def to_standard_code(code: str) -> str:
    """将各种代码格式统一转为 600000.SH 格式。

    支持的输入格式：
        - 600000.SH → 600000.SH
        - sh.600000 → 600000.SH
        - 000001.SZ → 000001.SZ
        - sz.000001 → 000001.SZ

    Raises:
        CodeFormatError: 无法识别的格式
    """
    from ashare_research.exceptions import CodeFormatError

    code = code.strip()

    m = _SYMBOL_RE.match(code)
    if m:
        return code

    m = _BAOSTOCK_RE.match(code)
    if m:
        return f"{m.group(2)}.{m.group(1).upper()}"

    # 尝试 6 位数字 + 推断交易所
    if re.match(r"^\d{6}$", code):
        if code.startswith(("6", "9")):
            return f"{code}.SH"
        elif code.startswith(("0", "3", "2")):
            return f"{code}.SZ"
        else:
            raise CodeFormatError(f"Cannot infer exchange from code: {code}")

    raise CodeFormatError(f"Unrecognized code format: {code}")


def to_baostock_code(code: str) -> str:
    """将标准代码转为 Baostock 格式：sh.600000。

    Raises:
        CodeFormatError: 无法识别格式
    """
    from ashare_research.exceptions import CodeFormatError

    code = to_standard_code(code)
    m = _SYMBOL_RE.match(code)
    if m:
        return f"{m.group(2).lower()}.{m.group(1)}"
    raise CodeFormatError(f"Cannot convert to baostock format: {code}")


def extract_exchange(code: str) -> str:
    """从标准化代码中提取交易所：SH 或 SZ。"""
    code = to_standard_code(code)
    return code.split(".")[1]


def extract_digits(code: str) -> str:
    """从标准化代码中提取6位数字。"""
    code = to_standard_code(code)
    return code.split(".")[0]


# ── 数据模型 ─────────────────────────────────────────────────


@dataclass
class StockBasic:
    """股票基础信息。"""
    symbol: str            # 600000.SH
    exchange: str          # SH / SZ
    name: str
    list_date: str | None = None    # YYYY-MM-DD
    delist_date: str | None = None
    status: str = "1"                  # 1=正常
    source: str = ""
    fetched_at: str = ""               # ISO datetime


@dataclass
class TradeCalendarEntry:
    """交易日历条目。"""
    trade_date: str        # YYYY-MM-DD
    exchange: str          # SH / SZ
    is_open: bool = True
    source: str = ""
    fetched_at: str = ""


@dataclass
class StockDaily:
    """个股日线行情。"""
    symbol: str            # 600000.SH
    trade_date: str        # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    volume: float          # 成交量，单位：股
    amount: float          # 成交额，单位：元（人民币）
    turnover_rate: float | None = None  # 换手率，单位：%
    is_trading: bool = True
    adjustment: str = "none"  # none / qfq / hfq
    source: str = ""
    fetched_at: str = ""


@dataclass
class IndexDaily:
    """指数日线行情。"""
    symbol: str            # 000001 (上证指数)
    trade_date: str        # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: float          # 成交量，单位：手（指数）或股
    amount: float          # 成交额，单位：元（人民币）
    source: str = ""
    fetched_at: str = ""


@dataclass
class FetchRun:
    """数据抓取任务记录。"""
    run_id: str
    dataset: str           # stock_basic / trade_calendar / stock_daily / index_daily
    provider: str          # baostock / akshare
    symbol: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "pending"  # pending / running / success / failed
    row_count: int = 0
    started_at: str = ""
    finished_at: str = ""
    raw_file_path: str = ""
    parquet_path: str = ""
    schema_version: str = "1.0"
    quality_status: str = ""   # passed / failed / warning
    error_type: str = ""
    error_message: str = ""


@dataclass
class QualityResult:
    """数据质量检查结果。"""
    run_id: str
    check_name: str
    status: str            # passed / failed / warning
    details: str = ""
    checked_at: str = ""
