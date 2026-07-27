"""数据服务层。

编排数据获取、存储和质量检查流程。

流程（修正后）：
    数据源 → 不可变原始快照
         → 标准化
         → 批次质量检查
         → 不通过 → 隔离(quarantine) + 标记失败 + 返回非零
         → 通过   → 与已有Parquet合并
                  → 合并数据再次质量检查
                  → 不通过 → 隔离
                  → 通过   → 原子写入Parquet → DuckDB登记 → 标记成功
"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashare_research.config import load_config
from ashare_research.exceptions import (
    AshareDataError,
    QualityCheckError,
    RawPersistenceError,
)
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

        流程：
            1. 获取数据
            2. 保存标准化快照
            3. 批次质量检查 → 不通过则隔离并抛出异常
            4. 与已有 Parquet 合并
            5. 合并数据再次质量检查 → 不通过则隔离
            6. 原子写入 Parquet
            7. DuckDB 登记（记录合并后总行数）
            8. 标记成功

        Returns:
            dict: {run_id, row_count, parquet_path, staging_path, quality_results}
        """
        provider = self.get_provider(provider_name)

        run_id = self.store.start_fetch_run(
            dataset=dataset,
            provider=provider_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        staging_path = ""
        parquet_path = ""
        new_row_count = 0

        try:
            # 0. 清空上次 raw 路径，避免跨调用复用
            if hasattr(provider, "reset_last_raw_path"):
                provider.reset_last_raw_path()

            # 1. 调用数据提供方
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

            new_row_count = len(df)
            logger.info(f"Fetched {new_row_count} rows from {provider_name}.{method_name}()")

            # 1b. 从 Provider 获取真实原始响应路径
            raw_path = getattr(provider, "last_raw_path", "")
            provider_raw_dir = getattr(provider, "raw_dir", "")

            # 若 Provider 配置了 raw_dir，必须成功保存原始快照
            if provider_raw_dir:
                if not raw_path:
                    raise RawPersistenceError(
                        f"Provider {provider_name}.{method_name}() returned "
                        "data but did not persist a raw snapshot"
                    )
                raw_file = Path(raw_path)
                if not raw_file.is_file():
                    raise RawPersistenceError(
                        f"Provider raw snapshot does not exist: {raw_path}"
                    )

            # 2. 保存标准化快照（供调试和追溯，区别于不可变原始响应）
            staging_path = self._save_staging_data(
                df, provider_name, dataset, symbol, run_id
            )

            # 3. 批次质量检查 — 先于写入，不通过则隔离
            batch_quality = self.validator.validate(
                df, dataset, self.store, run_id
            )
            batch_status = self._summarize_quality(batch_quality)
            if batch_status == "failed":
                quarantine_path = self._save_quarantine(
                    df, provider_name, dataset, symbol, run_id,
                    reason="batch_quality_failed",
                )
                self.store.fail_fetch_run(
                    run_id=run_id,
                    error_type="QualityCheckError",
                    error_message=f"Batch quality failed: "
                                  f"{[r['check_name'] for r in batch_quality if r['status'] == 'failed']}",
                )
                self.store._update_run_quality(run_id, "failed")
                raise QualityCheckError(
                    f"Batch quality check failed for {dataset}/{symbol}. "
                    f"Data quarantined at: {quarantine_path}"
                )

            # 4. 与已有数据合并
            parquet_dir = self.config["storage"]["parquet_dir"]
            merged_df = self._merge_with_existing(
                df, parquet_dir, dataset, symbol
            )

            # 5. 合并后再次质量检查
            merged_quality = self.validator.validate(
                merged_df, dataset, self.store, run_id
            )
            merged_status = self._summarize_quality(merged_quality)
            if merged_status == "failed":
                quarantine_path = self._save_quarantine(
                    merged_df, provider_name, dataset, symbol, run_id,
                    reason="merged_quality_failed",
                )
                self.store.fail_fetch_run(
                    run_id=run_id,
                    error_type="QualityCheckError",
                    error_message=f"Merged data quality failed: "
                                  f"{[r['check_name'] for r in merged_quality if r['status'] == 'failed']}",
                )
                self.store._update_run_quality(run_id, "failed")
                raise QualityCheckError(
                    f"Merged data quality check failed for {dataset}/{symbol}. "
                    f"Data quarantined at: {quarantine_path}"
                )

            # 6. 原子写入 Parquet
            final_row_count = len(merged_df)
            parquet_path = write_parquet(
                df=merged_df,
                parquet_dir=parquet_dir,
                dataset=dataset,
                symbol=symbol if symbol else "",
                mode="replace",
            )

            # 7. 标记成功（记录合并后总行数）
            self.store.complete_fetch_run(
                run_id=run_id,
                row_count=final_row_count,
                raw_file_path=raw_path,
                parquet_path=parquet_path,
                quality_status="passed",
            )

        except (AshareDataError, QualityCheckError) as e:
            # 质量失败已在内部调用过 fail_fetch_run；
            # 提供方错误等其他 AshareDataError 需要在此处标记失败
            status = self.store.query(
                "SELECT status FROM data_fetch_runs WHERE run_id = ?",
                [run_id],
            )
            if status.empty or status["status"].iloc[0] not in ("failed",):
                self.store.fail_fetch_run(
                    run_id=run_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            raise
        except Exception as e:
            error_type = type(e).__name__
            self.store.fail_fetch_run(
                run_id=run_id,
                error_type=error_type,
                error_message=str(e),
            )
            if hasattr(provider, "logout"):
                with contextlib.suppress(Exception):
                    provider.logout()
            raise

        return {
            "run_id": run_id,
            "row_count": final_row_count,
            "new_rows": new_row_count,
            "parquet_path": parquet_path,
            "staging_path": staging_path,
            "quality_status": "passed",
            "quality_results": merged_quality,
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

    def _merge_with_existing(
        self,
        new_df: pd.DataFrame,
        parquet_dir: str,
        dataset: str,
        symbol: str,
    ) -> pd.DataFrame:
        """将新数据与已有 Parquet 合并，按主键去重并排序。

        首次写入和增量合并走同一路径，确保始终按完整主键排序。
        """
        existing = read_parquet(parquet_dir, dataset, symbol)

        if existing.empty:
            combined = new_df.copy()
        else:
            # 确保关键列类型一致
            for col in ["trade_date"]:
                if col in new_df.columns and col in existing.columns:
                    new_df[col] = new_df[col].astype(str)
                    existing[col] = existing[col].astype(str)
            combined = pd.concat([existing, new_df], ignore_index=True)

        from ashare_research.quality.validators import _PRIMARY_KEYS

        pk = _PRIMARY_KEYS.get(dataset, [])
        if pk:
            missing_pk = [c for c in pk if c not in combined.columns]
            if missing_pk:
                raise AshareDataError(
                    f"Cannot merge {dataset}: missing primary-key "
                    f"columns {missing_pk}"
                )
            combined = combined.drop_duplicates(subset=pk, keep="last")
            combined = combined.sort_values(pk, kind="stable").reset_index(
                drop=True
            )
        return combined

    def _save_staging_data(
        self,
        df: pd.DataFrame,
        provider_name: str,
        dataset: str,
        symbol: str,
        run_id: str,
    ) -> str:
        """保存标准化批次快照（供调试和追溯）。

        与不可变原始响应不同：这里保存的是 provider 标准化后的 DataFrame。
        原始响应留存由各个 provider 内部负责。
        """
        staging_dir = Path(self.config["storage"].get("staging_dir", "data/staging"))
        target_dir = staging_dir / provider_name / dataset
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_symbol = symbol.replace(".", "_") if symbol else "all"
        filename = f"{safe_symbol}_{timestamp}_{run_id}.parquet"
        filepath = target_dir / filename

        df.to_parquet(filepath, index=False, engine="pyarrow")
        logger.info(f"Staging snapshot saved: {filepath} ({len(df)} rows)")

        return str(filepath)

    def _save_quarantine(
        self,
        df: pd.DataFrame,
        provider_name: str,
        dataset: str,
        symbol: str,
        run_id: str,
        reason: str = "",
    ) -> str:
        """保存质量失败的数据到隔离目录。

        隔离数据不进入正式 Parquet 目录，方便事后审计和重处理。
        """
        quarantine_dir = Path(
            self.config["storage"].get("quarantine_dir", "data/quarantine")
        )
        target_dir = quarantine_dir / reason / provider_name
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_symbol = symbol.replace(".", "_") if symbol else "all"
        filename = f"{safe_symbol}_{timestamp}_{run_id}.parquet"
        filepath = target_dir / filename

        df.to_parquet(filepath, index=False, engine="pyarrow")
        logger.warning(
            f"Data quarantined [{reason}]: {filepath} ({len(df)} rows)"
        )

        return str(filepath)

    def _summarize_quality(self, results: list[dict]) -> str:
        """汇总质量检查结果。"""
        statuses = [r["status"] for r in results]
        if "failed" in statuses:
            return "failed"
        if "warning" in statuses:
            return "warning"
        return "passed"
