"""数据服务层。

编排数据获取、存储和质量检查流程。

流程：
    数据源 → 原始留存 → 质量检查 → Parquet 写入 → DuckDB 登记
"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashare_research.config import load_config
from ashare_research.exceptions import AshareDataError
from ashare_research.providers.base import BaseProvider
from ashare_research.quality.validators import QualityValidator
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.storage.parquet_store import read_parquet, write_parquet

logger = logging.getLogger(__name__)


class DataService:
    """数据服务。

    协调 provider、storage 和 quality 模块。
    """

    def __init__(
        self,
        duckdb_store: DuckDBStore,
        config: dict | None = None,
    ):
        self.store = duckdb_store
        self.config = config or load_config()
        self.validator = QualityValidator()
        self._providers: dict[str, BaseProvider] = {}

    def register_provider(self, name: str, provider: BaseProvider) -> None:
        """注册数据提供方。"""
        self._providers[name] = provider

    def get_provider(self, name: str) -> BaseProvider:
        """获取已注册的提供方。"""
        if name not in self._providers:
            raise AshareDataError(f"Provider not registered: {name}")
        return self._providers[name]

    # ── 核心流程 ─────────────────────────────────────────

    def fetch_and_store(
        self,
        provider_name: str,
        method_name: str,
        dataset: str,
        symbol: str = "",
        start_date: str = "",
        end_date: str = "",
        adjustment: str = "none",
        **kwargs,
    ) -> dict:
        """执行完整的数据抓取和存储流程。

        Args:
            provider_name: 已注册的提供方名称
            method_name: 提供方方法名 (get_stock_basic, get_stock_daily, ...)
            dataset: 数据集类型
            symbol: 标的代码
            start_date: 开始日期
            end_date: 结束日期
            adjustment: 复权方式

        Returns:
            dict: {run_id, row_count, parquet_path, raw_path, quality_results}
        """
        provider = self.get_provider(provider_name)

        # 1. 记录任务开始
        run_id = self.store.start_fetch_run(
            dataset=dataset,
            provider=provider_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        raw_path = ""
        parquet_path = ""
        row_count = 0
        quality_status = "pending"
        quality_results = []

        try:
            # 2. 调用数据提供方
            method = getattr(provider, method_name)
            if method_name == "get_stock_basic":
                df = method()
            elif method_name == "get_trade_calendar":
                df = method(start_date, end_date)
            elif method_name == "get_stock_daily":
                df = method(symbol, start_date, end_date, adjustment)
            elif method_name == "get_index_daily":
                df = method(symbol, start_date, end_date)
            else:
                df = method(**kwargs)

            if df is None or df.empty:
                raise AshareDataError(
                    f"Provider {provider_name}.{method_name}() returned empty data"
                )

            row_count = len(df)
            logger.info(f"Fetched {row_count} rows from {provider_name}.{method_name}()")

            # 3. 保存原始数据
            raw_path = self._save_raw_data(df, provider_name, dataset, symbol, run_id)

            # 4. 写入 Parquet
            parquet_dir = self.config["storage"]["parquet_dir"]
            parquet_path = write_parquet(
                df=df,
                parquet_dir=parquet_dir,
                dataset=dataset,
                symbol=symbol if symbol else "",
                mode="append",
            )

            # 5. 质量检查
            quality_results = self.validator.validate(
                df, dataset, self.store, run_id
            )
            quality_status = self._summarize_quality(quality_results)

            # 6. 标记成功
            self.store.complete_fetch_run(
                run_id=run_id,
                row_count=row_count,
                raw_file_path=raw_path,
                parquet_path=parquet_path,
                quality_status=quality_status,
            )

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            self.store.fail_fetch_run(
                run_id=run_id,
                error_type=error_type,
                error_message=error_msg,
            )
            # 如果是提供方的上下文管理器问题，尝试清理
            if hasattr(provider, "logout"):
                with contextlib.suppress(Exception):
                    provider.logout()
            raise

        return {
            "run_id": run_id,
            "row_count": row_count,
            "parquet_path": parquet_path,
            "raw_path": raw_path,
            "quality_status": quality_status,
            "quality_results": quality_results,
        }

    def fetch_with_fallback(
        self,
        primary_provider_name: str,
        primary_method: str,
        fallback_provider_name: str,
        fallback_method: str,
        dataset: str,
        symbol: str = "",
        start_date: str = "",
        end_date: str = "",
        adjustment: str = "none",
    ) -> dict:
        """使用主数据源，失败时回退到备用数据源。

        简单回退策略：
            主数据源成功 → 使用主数据源
            主数据源明确失败 → 尝试备用数据源
            两个都失败 → 抛出聚合错误
        """
        errors = []

        # 尝试主数据源
        try:
            logger.info(
                f"Trying primary provider: {primary_provider_name}.{primary_method}()"
            )
            return self.fetch_and_store(
                provider_name=primary_provider_name,
                method_name=primary_method,
                dataset=dataset,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjustment=adjustment,
            )
        except Exception as e:
            errors.append(f"{primary_provider_name}: {e}")
            logger.warning(
                f"Primary provider failed: {e}. Trying fallback..."
            )

        # 尝试备用数据源
        try:
            logger.info(
                f"Trying fallback provider: {fallback_provider_name}.{fallback_method}()"
            )
            return self.fetch_and_store(
                provider_name=fallback_provider_name,
                method_name=fallback_method,
                dataset=dataset,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjustment=adjustment,
            )
        except Exception as e:
            errors.append(f"{fallback_provider_name}: {e}")

        # 两个都失败
        raise AshareDataError(
            f"All providers failed for {dataset}/{symbol}: {'; '.join(errors)}"
        )

    # ── 查询 ─────────────────────────────────────────────

    def inspect(self, dataset: str, symbol: str = "") -> dict:
        """查询已保存数据集的信息。"""
        parquet_dir = self.config["storage"]["parquet_dir"]
        from ashare_research.storage.parquet_store import get_parquet_info

        info = get_parquet_info(parquet_dir, dataset, symbol)

        # 补充 DuckDB 元数据
        symbol_key = symbol if symbol else "_all"
        db_info = self.store.get_dataset_info(dataset, symbol_key)
        info["duckdb"] = db_info

        return info

    def query_stored(
        self,
        dataset: str,
        symbol: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """查询已保存的数据。"""
        parquet_dir = self.config["storage"]["parquet_dir"]
        return read_parquet(parquet_dir, dataset, symbol, start_date, end_date)

    # ── 内部方法 ─────────────────────────────────────────

    def _save_raw_data(
        self,
        df: pd.DataFrame,
        provider_name: str,
        dataset: str,
        symbol: str,
        run_id: str,
    ) -> str:
        """保存原始 CSV 到 data/raw/。"""
        raw_dir = Path(self.config["storage"]["raw_dir"])
        target_dir = raw_dir / provider_name / dataset
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_symbol = symbol.replace(".", "_") if symbol else "all"
        filename = f"{safe_symbol}_{timestamp}_{run_id}.csv"
        filepath = target_dir / filename

        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info(f"Raw data saved: {filepath} ({len(df)} rows)")

        return str(filepath)

    def _summarize_quality(self, results: list[dict]) -> str:
        """汇总质量检查结果。"""
        statuses = [r["status"] for r in results]
        if "failed" in statuses:
            return "failed"
        if "warning" in statuses:
            return "warning"
        return "passed"
