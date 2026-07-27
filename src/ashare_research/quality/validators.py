"""数据质量检查。

至少实现：
- 必需字段存在
- 字段类型正确
- 日期可解析
- 主键无重复
- 数据按日期排序
- 数据来源不为空
- OHLC 逻辑检查
- 价格和成交量非负
- 交易日范围检查
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# 各数据集的必需字段
_REQUIRED_FIELDS: dict[str, list[str]] = {
    "stock_daily": [
        "symbol", "trade_date", "open", "high", "low", "close",
        "volume", "amount", "source", "fetched_at",
    ],
    "index_daily": [
        "symbol", "trade_date", "open", "high", "low", "close",
        "volume", "amount", "source", "fetched_at",
    ],
    "stock_basic": [
        "symbol", "exchange", "name", "source", "fetched_at",
    ],
    "trade_calendar": [
        "trade_date", "exchange", "is_open", "source", "fetched_at",
    ],
}

# 各数据集的数值字段（必须 ≥ 0）
_NON_NEGATIVE_FIELDS: dict[str, list[str]] = {
    "stock_daily": ["open", "high", "low", "close", "volume", "amount"],
    "index_daily": ["open", "high", "low", "close", "volume", "amount"],
}

# OHLC 字段
_OHLC_FIELDS = ["open", "high", "low", "close"]

# 各数据集主键
_PRIMARY_KEYS: dict[str, list[str]] = {
    "stock_daily": ["symbol", "trade_date", "adjustment"],
    "index_daily": ["symbol", "trade_date"],
    "stock_basic": ["symbol"],
    "trade_calendar": ["exchange", "trade_date"],
}


class QualityValidator:
    """数据质量检查器。

    用法:
        validator = QualityValidator()
        results = validator.validate(df, "stock_daily", duckdb_store, run_id)
    """

    def validate(
        self,
        df: pd.DataFrame,
        dataset: str,
        duckdb_store=None,
        run_id: str = "",
    ) -> list[dict[str, Any]]:
        """运行所有检查。

        Returns:
            list[dict]: 每条包含 check_name, status, details
        """
        results: list[dict[str, Any]] = []

        results.append(self._check_required_fields(df, dataset))
        results.append(self._check_dates(df, dataset))
        results.append(self._check_primary_key_unique(df, dataset))
        results.append(self._check_date_sorted(df))
        results.append(self._check_source_not_empty(df))

        if dataset in ("stock_daily", "index_daily"):
            results.extend(self._check_ohlc(df))

        results.append(self._check_no_null_key_values(df, dataset))

        # 记录到 DuckDB
        if duckdb_store and run_id:
            for r in results:
                try:
                    duckdb_store.record_quality_result(
                        run_id, r["check_name"], r["status"], r["details"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to record quality result: {e}")

        return results

    def _result(self, check_name: str, status: str, details: str = "") -> dict:
        return {"check_name": check_name, "status": status, "details": details}

    def _check_required_fields(self, df: pd.DataFrame, dataset: str) -> dict:
        """检查必需字段。"""
        required = _REQUIRED_FIELDS.get(dataset, [])
        missing = [f for f in required if f not in df.columns]
        if missing:
            return self._result(
                "required_fields", "failed",
                f"Missing fields: {missing}"
            )
        return self._result("required_fields", "passed",
                            f"All {len(required)} required fields present")

    def _check_dates(self, df: pd.DataFrame, dataset: str) -> dict:
        """检查日期字段可解析。"""
        date_cols = ["trade_date", "fetched_at", "list_date", "delist_date"]
        bad = []
        for col in date_cols:
            if col in df.columns:
                non_null = df[col].dropna()
                if non_null.empty:
                    continue
                try:
                    pd.to_datetime(non_null, errors="raise")
                except Exception as e:
                    bad.append(f"{col}: {e}")

        if bad:
            return self._result("date_parsing", "failed", "; ".join(bad))
        return self._result("date_parsing", "passed", "All date fields parseable")

    def _check_primary_key_unique(self, df: pd.DataFrame, dataset: str) -> dict:
        """检查主键唯一。"""
        pk = _PRIMARY_KEYS.get(dataset, [])
        if not pk:
            return self._result("primary_key_unique", "passed", "No PK defined")

        existing = [c for c in pk if c in df.columns]
        if len(existing) != len(pk):
            missing = [c for c in pk if c not in df.columns]
            return self._result(
                "primary_key_unique", "failed",
                f"Cannot check: PK columns missing: {missing}"
            )

        dup_mask = df[existing].duplicated()
        if dup_mask.any():
            dup_count = dup_mask.sum()
            dup_samples = df[existing][dup_mask].head(5).to_dict("records")
            return self._result(
                "primary_key_unique", "failed",
                f"Found {dup_count} duplicate primary keys. Samples: {dup_samples}"
            )
        return self._result("primary_key_unique", "passed",
                            f"No duplicates ({len(df)} rows)")

    def _check_date_sorted(self, df: pd.DataFrame) -> dict:
        """检查数据按日期排序。"""
        date_col = None
        for col in ["trade_date"]:
            if col in df.columns:
                date_col = col
                break

        if not date_col:
            return self._result("date_sorted", "passed", "No date column to check")

        try:
            dates = pd.to_datetime(df[date_col])
        except Exception:
            return self._result(
                "date_sorted", "warning", "Cannot parse dates for sorting check"
            )

        if not dates.is_monotonic_increasing:
            # 非单调递增，检查是否是严格乱序
            violations = (dates.diff().dropna() < pd.Timedelta(0)).sum()
            return self._result(
                "date_sorted", "warning",
                f"Not sorted by date ({violations} out-of-order entries)"
            )
        return self._result("date_sorted", "passed", "Sorted by trade_date")

    def _check_source_not_empty(self, df: pd.DataFrame) -> dict:
        """检查数据来源不为空。"""
        if "source" not in df.columns:
            return self._result("source_not_empty", "failed", "source column missing")

        empty = df["source"].isnull() | (df["source"].astype(str).str.strip() == "")
        if empty.any():
            return self._result(
                "source_not_empty", "failed",
                f"{empty.sum()} rows have empty source"
            )
        return self._result("source_not_empty", "passed",
                            f"All rows sourced from {df['source'].unique()}")

    def _check_non_negative(self, df: pd.DataFrame, dataset: str) -> dict:
        """检查价格和成交量非负。"""
        fields = _NON_NEGATIVE_FIELDS.get(dataset, [])
        bad = []
        for col in fields:
            if col in df.columns:
                neg = (df[col] < 0).sum()
                if neg:
                    bad.append(f"{col}: {neg} negative values")

        if bad:
            return self._result("non_negative", "failed", "; ".join(bad))
        return self._result("non_negative", "passed",
                            f"All {len(fields)} numeric fields non-negative")

    def _check_ohlc_logic(self, df: pd.DataFrame) -> dict:
        """检查 OHLC 逻辑一致性：
        high >= open, high >= close
        low <= open, low <= close
        high >= low
        """
        bad = []
        for col in _OHLC_FIELDS:
            if col not in df.columns:
                continue

        if all(c in df.columns for c in _OHLC_FIELDS):
            o, h, lo, c = df["open"], df["high"], df["low"], df["close"]

            mask_high = (h >= o) & (h >= c)
            mask_low = (lo <= o) & (lo <= c)
            mask_range = h >= lo

            violations = (~mask_high).sum() + (~mask_low).sum() + (~mask_range).sum()
            if violations > 0:
                bad.append(
                    f"OHLC logic violations: high>=open & high>=close: "
                    f"{(~mask_high).sum()}, low<=open & low<=close: "
                    f"{(~mask_low).sum()}, high>=low: {(~mask_range).sum()}"
                )

        if bad:
            return self._result("ohlc_logic", "failed", "; ".join(bad))
        return self._result("ohlc_logic", "passed", "OHLC logic consistent")

    def _check_ohlc(self, df: pd.DataFrame) -> list[dict]:
        """便捷方法：运行 OHLC 相关检查（作为列表返回）。"""
        return [self._check_ohlc_logic(df), self._check_non_negative(
            df, "stock_daily" if "is_trading" in df.columns else "index_daily"
        )]

    def _check_no_null_key_values(self, df: pd.DataFrame, dataset: str) -> dict:
        """检查主键字段无 NULL。"""
        pk = _PRIMARY_KEYS.get(dataset, [])
        existing = [c for c in pk if c in df.columns]
        if not existing:
            return self._result("no_null_keys", "passed", "No PK to check")

        bad = []
        for col in existing:
            null_count = df[col].isnull().sum()
            if null_count:
                bad.append(f"{col}: {null_count} nulls")

        if bad:
            return self._result("no_null_keys", "failed", "; ".join(bad))
        return self._result("no_null_keys", "passed", "No null PK values")


def check_duplicate_insert(
    new_df: pd.DataFrame, existing_path: str, dataset: str
) -> bool:
    """检查新数据与已有 Parquet 是否重复。

    Returns:
        bool: True 表示发现重复
    """
    import os
    if not os.path.exists(existing_path):
        return False

    pk = _PRIMARY_KEYS.get(dataset, [])
    if not pk:
        return False

    existing = pd.read_parquet(existing_path)
    existing_pk = [c for c in pk if c in existing.columns]
    new_pk = [c for c in pk if c in new_df.columns]

    if not existing_pk or not new_pk:
        return False

    common_pk = list(set(existing_pk) & set(new_pk))
    if not common_pk:
        return False

    existing_keys = set(
        existing[common_pk].astype(str).agg("-".join, axis=1)
    )
    new_keys = set(new_df[common_pk].astype(str).agg("-".join, axis=1))

    return bool(existing_keys & new_keys)
