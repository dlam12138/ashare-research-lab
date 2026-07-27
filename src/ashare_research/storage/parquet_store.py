"""Parquet 存储层。

负责：
- 将 DataFrame 写入 Parquet 文件
- 增量合并（按主键去重）
- 读取 Parquet 文件
- 原子替换（临时文件 → 正式文件）

主键约定：
    stock_daily:  symbol + trade_date + adjustment
    index_daily:  symbol + trade_date
    stock_basic:  symbol
    trade_calendar: exchange + trade_date
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pandas as pd

from ashare_research.exceptions import AshareDataError

logger = logging.getLogger(__name__)

_PRIMARY_KEYS: dict[str, list[str]] = {
    "stock_daily": ["symbol", "trade_date", "adjustment"],
    "index_daily": ["symbol", "trade_date"],
    "stock_basic": ["symbol"],
    "trade_calendar": ["exchange", "trade_date"],
}


def _get_parquet_path(parquet_dir: str, dataset: str, symbol: str = "") -> Path:
    """获取 Parquet 文件路径。

    结构：parquet_dir/dataset/symbol.parquet
    若 symbol 为空，使用 dataset.parquet
    """
    base = Path(parquet_dir) / dataset
    base.mkdir(parents=True, exist_ok=True)

    if symbol:
        safe_symbol = symbol.replace(".", "_").replace("/", "_")
        filename = f"{safe_symbol}.parquet"
    else:
        filename = f"{dataset}.parquet"

    return base / filename


def write_parquet(
    df: pd.DataFrame,
    parquet_dir: str,
    dataset: str,
    symbol: str = "",
    mode: str = "replace",
) -> str:
    """写入 Parquet 文件。

    Args:
        df: 要写入的 DataFrame
        parquet_dir: Parquet 根目录
        dataset: 数据集名称
        symbol: 标的代码（用于分区）
        mode: "replace" 覆盖写入, "append" 追加并去重

    Returns:
        str: 写入的 Parquet 文件路径

    Raises:
        DuplicateKeyError: reject_duplicate_keys 模式下发现重复主键
    """
    if df.empty:
        raise AshareDataError("Cannot write empty DataFrame to parquet")

    output_path = _get_parquet_path(parquet_dir, dataset, symbol)
    pk_cols = _PRIMARY_KEYS.get(dataset, [])

    # 写入前检查
    if pk_cols and df[pk_cols].isnull().any().any():
        raise AshareDataError(
            f"Primary key columns {pk_cols} contain null values in {dataset}"
        )

    if mode == "append" and output_path.exists():
        existing = pd.read_parquet(output_path)
        combined = pd.concat([existing, df], ignore_index=True)

        if pk_cols:
            duplicates = combined[pk_cols].duplicated()
            if duplicates.any():
                logger.warning(
                    f"Removing {duplicates.sum()} duplicate rows "
                    f"(keep='last') for {dataset}/{symbol}"
                )
                combined = combined.drop_duplicates(subset=pk_cols, keep="last")

        # 按完整主键排序（而非仅第一列）
        sort_cols = pk_cols if pk_cols else [combined.columns[0]]
        combined = combined.sort_values(sort_cols).reset_index(drop=True)
        df = combined

    elif pk_cols:
        dup_mask = df[pk_cols].duplicated()
        if dup_mask.any():
            logger.warning(
                f"Removing {dup_mask.sum()} duplicate rows within batch "
                f"for {dataset}/{symbol}"
            )
            df = df.drop_duplicates(subset=pk_cols, keep="last")

    # 原子写入：先写临时文件，再重命名
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".parquet", dir=output_path.parent)
    os.close(tmp_fd)
    try:
        df.to_parquet(tmp_path, index=False, engine="pyarrow")
        os.replace(tmp_path, str(output_path))
        logger.info(
            f"Wrote {len(df)} rows to {output_path} "
            f"({output_path.stat().st_size} bytes)"
        )
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # 验证写入
    verify_df = pd.read_parquet(output_path)
    if len(verify_df) != len(df):
        raise AshareDataError(
            f"Parquet write verification failed: expected {len(df)} rows, "
            f"got {len(verify_df)}"
        )

    return str(output_path)


def read_parquet(
    parquet_dir: str,
    dataset: str,
    symbol: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """读取 Parquet 文件。

    Args:
        parquet_dir: Parquet 根目录
        dataset: 数据集名称
        symbol: 标的代码
        start_date: 起始日期过滤
        end_date: 结束日期过滤

    Returns:
        DataFrame，不存在时返回空 DataFrame
    """
    path = _get_parquet_path(parquet_dir, dataset, symbol)
    if not path.exists():
        logger.warning(f"Parquet file not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # 日期过滤
    if "trade_date" in df.columns:
        if start_date:
            df = df[df["trade_date"] >= start_date]
        if end_date:
            df = df[df["trade_date"] <= end_date]

    return df.reset_index(drop=True)


def get_parquet_info(
    parquet_dir: str, dataset: str, symbol: str = ""
) -> dict:
    """获取 Parquet 文件信息。"""
    path = _get_parquet_path(parquet_dir, dataset, symbol)
    if not path.exists():
        return {"exists": False, "path": str(path)}

    df = pd.read_parquet(path)
    info = {
        "exists": True,
        "path": str(path),
        "rows": len(df),
        "columns": list(df.columns),
        "size_bytes": path.stat().st_size,
    }

    if "trade_date" in df.columns:
        info["date_min"] = str(df["trade_date"].min())
        info["date_max"] = str(df["trade_date"].max())

    if "source" in df.columns:
        info["sources"] = df["source"].unique().tolist()

    if "adjustment" in df.columns:
        info["adjustments"] = df["adjustment"].unique().tolist()

    return info
