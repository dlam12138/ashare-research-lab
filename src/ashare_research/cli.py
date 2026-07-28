"""命令行入口。

提供以下命令：
    ashare-research init-db               初始化 DuckDB 和数据目录
    ashare-research fetch-stock-basic     获取股票基础信息
    ashare-research fetch-calendar        获取交易日历
    ashare-research fetch-stock-daily     获取个股日线
    ashare-research fetch-index-daily     获取指数日线
    ashare-research inspect               查看已保存数据信息
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ashare_research import __version__
from ashare_research.config import load_config
from ashare_research.exceptions import AshareDataError
from ashare_research.fact_sources.candidates.akshare_financial import (
    AKShareFinancialCandidateProvider,
)
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.providers.akshare_provider import AKShareProvider
from ashare_research.providers.baostock_provider import BaostockProvider
from ashare_research.services.data_service import DataService
from ashare_research.storage.duckdb_store import DuckDBStore


def setup_logging(debug: bool = False) -> None:
    """配置日志。"""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")

    # 减少第三方库日志噪音
    for lib in ["matplotlib", "PIL", "urllib3", "baostock"]:
        logging.getLogger(lib).setLevel(logging.WARNING)


def _create_service(config: dict) -> DataService:
    """创建 DataService 实例并注册提供方。"""
    store = DuckDBStore(config["storage"]["duckdb_path"])
    store.connect()
    store.init_db()

    raw_dir = config["storage"].get("raw_dir", "data/raw")
    service = DataService(store, config)
    service.register_provider("baostock", BaostockProvider(raw_dir=raw_dir))
    service.register_provider("akshare", AKShareProvider(raw_dir=raw_dir))

    return service


def cmd_init_db(args: argparse.Namespace) -> int:
    """初始化数据库和数据目录。"""
    config = load_config(args.config)
    store = DuckDBStore(config["storage"]["duckdb_path"])

    try:
        store.init_db()

        # 创建数据目录
        dirs = [
            config["storage"]["raw_dir"],
            config["storage"]["parquet_dir"],
            Path(config["storage"]["raw_dir"]) / "baostock",
            Path(config["storage"]["raw_dir"]) / "akshare",
            Path(config["storage"]["parquet_dir"]) / "stock_daily",
            Path(config["storage"]["parquet_dir"]) / "index_daily",
            Path(config["storage"]["parquet_dir"]) / "stock_basic",
            Path(config["storage"]["parquet_dir"]) / "trade_calendar",
            "data/reports",
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

        print(f"DuckDB initialized: {config['storage']['duckdb_path']}")
        print("Data directories created.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_fetch_stock_basic(args: argparse.Namespace) -> int:
    """获取股票基础信息。"""
    config = load_config(args.config)
    service = _create_service(config)

    provider_name = args.provider or config["providers"]["stock_basic_primary"]

    try:
        result = service.fetch_and_store(
            provider_name=provider_name,
            method_name="get_stock_basic",
            dataset="stock_basic",
        )
        print(f"Stock basic: {result['row_count']} stocks fetched")
        print(f"  Parquet: {result['parquet_path']}")
        print(f"  Quality: {result['quality_status']}")
        if result["quality_results"]:
            for r in result["quality_results"]:
                status_icon = "OK" if r["status"] == "passed" else "!!"
                print(f"  [{status_icon}] {r['check_name']}: {r['status']}")
        return 0
    except AshareDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        service.store.close()


def cmd_fetch_calendar(args: argparse.Namespace) -> int:
    """获取交易日历。"""
    config = load_config(args.config)
    service = _create_service(config)

    provider_name = args.provider or config["providers"]["trade_calendar_primary"]

    try:
        result = service.fetch_and_store(
            provider_name=provider_name,
            method_name="get_trade_calendar",
            dataset="trade_calendar",
            start_date=args.start,
            end_date=args.end,
        )
        print(f"Trade calendar: {result['row_count']} dates fetched")
        print(f"  Range: {args.start} to {args.end}")
        print(f"  Parquet: {result['parquet_path']}")
        trading_days = result.get("row_count", 0)
        print(f"  Trading days: ~{trading_days}")
        return 0
    except AshareDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        service.store.close()


def cmd_fetch_stock_daily(args: argparse.Namespace) -> int:
    """获取个股日线。"""
    config = load_config(args.config)
    service = _create_service(config)

    provider_name = args.provider or config["providers"]["stock_daily_primary"]
    fallback = config["providers"].get("stock_daily_fallback", "")

    # 提供方登录由 DataService 和 Provider 内部管理
    # 不在 CLI 层提前登录，确保登录失败时也能触发回退
    try:
        if fallback and not args.no_fallback:
            result = service.fetch_with_fallback(
                primary_provider_name=provider_name,
                primary_method="get_stock_daily",
                fallback_provider_name=fallback,
                fallback_method="get_stock_daily",
                dataset="stock_daily",
                symbol=args.symbol,
                start_date=args.start,
                end_date=args.end,
                adjustment=args.adjustment,
            )
        else:
            result = service.fetch_and_store(
                provider_name=provider_name,
                method_name="get_stock_daily",
                dataset="stock_daily",
                symbol=args.symbol,
                start_date=args.start,
                end_date=args.end,
                adjustment=args.adjustment,
            )

        print(f"Stock daily: {args.symbol}")
        print(f"  Rows: {result['row_count']}")
        print(f"  Range: {args.start} to {args.end}")
        print(f"  Adjustment: {args.adjustment}")
        print(f"  Parquet: {result['parquet_path']}")
        print(f"  Quality: {result['quality_status']}")

        if args.verbose:
            for r in result["quality_results"]:
                icon = "[OK]" if r["status"] == "passed" else (
                    "[WARN]" if r["status"] == "warning" else "[FAIL]"
                )
                print(f"  {icon} {r['check_name']}: {r['status']}")

        return 0
    except AshareDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        service.store.close()


def cmd_fetch_index_daily(args: argparse.Namespace) -> int:
    """获取指数日线。"""
    config = load_config(args.config)
    service = _create_service(config)

    provider_name = args.provider or config["providers"]["index_daily_primary"]

    try:
        result = service.fetch_and_store(
            provider_name=provider_name,
            method_name="get_index_daily",
            dataset="index_daily",
            symbol=args.index_code,
            start_date=args.start,
            end_date=args.end,
        )
        print(f"Index daily: {args.index_code}")
        print(f"  Provider: {provider_name}")
        print(f"  Rows: {result['row_count']}")
        print(f"  Range: {args.start} to {args.end}")
        print(f"  Parquet: {result['parquet_path']}")
        print(f"  Quality: {result['quality_status']}")
        return 0
    except AshareDataError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        service.store.close()


def _normalize_dataset(dataset: str) -> str:
    """将 CLI 输入的 dataset 名称标准化为目录名。"""
    return dataset.replace("-", "_")


def cmd_inspect(args: argparse.Namespace) -> int:
    """查看已保存数据信息。"""
    config = load_config(args.config)
    service = _create_service(config)

    dataset = _normalize_dataset(args.dataset)

    try:
        info = service.inspect(dataset, args.symbol)

        if not info.get("exists"):
            print(f"No data found for {args.dataset}/{args.symbol}")
            print(f"  Expected path: {info['path']}")
            return 0

        print(f"Dataset: {args.dataset}")
        if args.symbol:
            print(f"  Symbol: {args.symbol}")
        print(f"  File: {info['path']}")
        print(f"  Rows: {info['rows']}")
        print(f"  Columns: {', '.join(info['columns'])}")
        print(f"  Size: {info['size_bytes']:,} bytes")

        if "date_min" in info:
            print(f"  Date range: {info['date_min']} to {info['date_max']}")
        if "sources" in info:
            print(f"  Sources: {info['sources']}")
        if "adjustments" in info:
            print(f"  Adjustments: {info['adjustments']}")

        if args.show_data:
            df = service.query_stored(args.dataset, args.symbol)
            if not df.empty:
                print(f"\n  Preview ({min(10, len(df))} rows):")
                print(df.head(10).to_string(index=False))

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        service.store.close()


# ── M2 价值评估子命令 ──────────────────────────────────────────


def cmd_build_value_facts(args: argparse.Namespace) -> int:
    """构建价值评估事实数据。

    从候选/官方来源获取财务数据，经 validate-before-write 流程
    写入 DuckDB 事实表。

    退出码：0=passed  2=conditional_pass  1=failed
    """
    config = load_config(args.config)
    store = DuckDBStore(config["storage"]["duckdb_path"])
    store.connect()

    source_mode = getattr(args, "source", "candidate")

    try:
        repo = FactRepository(store)
        repo.ensure_schema()

        registry = FactSourceRegistry()

        if source_mode == "candidate":
            registry.register_candidate(
                args.symbol,
                AKShareFinancialCandidateProvider(
                    raw_dir=config["storage"].get("raw_dir", "data/raw"),
                ),
            )
        elif source_mode == "official":
            # 官方来源尚未实现 → 明确失败
            print(
                "ERROR: Official source mode is not yet implemented. "
                "Use --source candidate for AKShare candidate data.",
                file=sys.stderr,
            )
            return 1

        output_root = config["storage"].get(
            "value_assessment_output_dir", "output/value_assessment"
        )
        service = FactService(
            fact_repository=repo, source_registry=registry, output_root=output_root
        )

        result = service.build_facts(
            args.symbol, args.start_year, args.end_year,
            source_mode=source_mode,
        )

        print(f"run_id:           {result['run_id']}")
        print(f"symbol:           {result['symbol']}")
        print(f"reported_count:   {result['reported_count']}")
        print(f"derived_count:    {result['derived_count']}")
        print(f"total_error_count:{result['total_error_count']}")
        print(f"status:           {result['status']}")
        print(f"checkpoint:       {result['checkpoint_decision']}")

        status = result["status"]
        if status == "passed":
            return 0
        elif status == "conditional_pass":
            return 2
        else:
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_verify_value_facts(args: argparse.Namespace) -> int:
    """重新验证已有事实（从数据库读取事实并重新运行校验）。

    不访问网络，不修改事实本身。
    """
    config = load_config(args.config)
    store = DuckDBStore(config["storage"]["duckdb_path"])
    store.connect()

    try:
        repo = FactRepository(store)
        repo.ensure_schema()

        from datetime import datetime

        from ashare_research.validation.results import summarize_results
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()

        # 按 run_id 查询该运行的事实 ID
        conn = store.connect()
        if args.run_id:
            fact_ids = conn.execute(
                "SELECT fact_id FROM fact_lineage WHERE run_id = ?",
                [args.run_id],
            ).fetchall()
            if not fact_ids:
                print(f"No facts found for run_id: {args.run_id}")
                return 1
            fid_list = [r[0] for r in fact_ids]
            placeholders = ", ".join(["?"] * len(fid_list))
            facts_df = conn.execute(
                f"SELECT * FROM financial_facts "
                f"WHERE symbol = ? AND fact_id IN ({placeholders})",
                [args.symbol] + fid_list,
            ).df()
        else:
            facts_df = repo.get_all_versions_for_audit(args.symbol)

        if facts_df.empty:
            print(f"No facts found for symbol={args.symbol} "
                  f"{'run_id=' + args.run_id if args.run_id else ''}")
            return 1

        facts = facts_df.to_dict("records")
        results = validator.validate_batch(facts)
        summary = summarize_results(results)

        # 创建新的 validation run（事务保护）
        run_id = f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        txn_conn = store.connect()
        txn_conn.execute("BEGIN TRANSACTION")
        try:
            repo.store_validation_run(
                run_id=run_id,
                fact_count=len(facts),
                error_count=summary["error_count"],
                warning_count=summary["warning_count"],
                status=(
                    "passed" if summary["error_count"] == 0
                    else "failed"
                ),
                conn=txn_conn,
            )
            repo.store_validation_results(
                results=[{
                    "target_id": r.target_id,
                    "rule_id": r.rule_id,
                    "rule_version": r.rule_version,
                    "severity": r.severity,
                    "passed": r.passed,
                    "expected": r.expected,
                    "actual": r.actual,
                "message": r.message,
                "checked_at": r.checked_at,
            } for r in results],
            validation_run_id=run_id,
        )

            txn_conn.execute("COMMIT")
        except Exception:
            txn_conn.execute("ROLLBACK")
            raise

        print(f"Verification Run: {run_id}")
        print(f"  Symbol:       {args.symbol}")
        print(f"  Fact count:   {len(facts)}")
        print(f"  Passed:       {summary['passed']}")
        print(f"  Failed:       {summary['failed']}")
        print(f"  Errors:       {summary['error_count']}")
        print(f"  Warnings:     {summary['warning_count']}")

        return 0 if summary["error_count"] == 0 else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_query_value_facts(args: argparse.Namespace) -> int:
    """PIT 查询价值评估事实。

    通过 AsOfQuery 对事实表执行时点查询，
    默认仅返回 verified/reconciled + eligible_for_metrics 的事实。
    """
    config = load_config(args.config)
    store = DuckDBStore(config["storage"]["duckdb_path"])
    store.connect()

    try:
        repo = FactRepository(store)
        as_of = AsOfQuery(repo)

        concept_ids: list[str] | None = args.concept if args.concept else None

        df = as_of.query(
            symbol=args.symbol,
            concept_ids=concept_ids,
            as_of_date=args.as_of,
            include_unverified=args.include_unverified,
        )

        if df.empty:
            print(f"No facts found for {args.symbol} as of {args.as_of}")
            if args.include_unverified:
                print("  (include_unverified=True)")
            return 0

        print(f"Symbol:  {args.symbol}")
        print(f"As of:   {args.as_of}")
        print(f"Rows:    {len(df)}")
        print(f"Concepts:{df['concept_id'].nunique()}")
        print()

        cols = [
            "concept_id", "period_end", "value", "unit",
            "verification_status", "is_derived", "filing_date",
        ]
        available_cols = [c for c in cols if c in df.columns]
        print(df[available_cols].to_string(index=False))

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        prog="ashare-research",
        description="A股研究平台 — 免费数据底座",
    )
    parser.add_argument(
        "--version", action="version", version=f"ashare-research {__version__}"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="配置文件路径"
    )
    parser.add_argument(
        "--debug", action="store_true", help="启用调试日志"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init-db
    p_init = subparsers.add_parser("init-db", help="初始化 DuckDB 和数据目录")
    p_init.set_defaults(func=cmd_init_db)

    # fetch-stock-basic
    p_sb = subparsers.add_parser(
        "fetch-stock-basic", help="获取股票基础信息"
    )
    p_sb.add_argument(
        "--provider", type=str, default=None,
        help="数据提供方 (default: from config)"
    )
    p_sb.set_defaults(func=cmd_fetch_stock_basic)

    # fetch-calendar
    p_cal = subparsers.add_parser("fetch-calendar", help="获取交易日历")
    p_cal.add_argument(
        "--start", type=str, required=True, help="开始日期 YYYY-MM-DD"
    )
    p_cal.add_argument(
        "--end", type=str, required=True, help="结束日期 YYYY-MM-DD"
    )
    p_cal.add_argument(
        "--provider", type=str, default=None, help="数据提供方"
    )
    p_cal.set_defaults(func=cmd_fetch_calendar)

    # fetch-stock-daily
    p_sd = subparsers.add_parser("fetch-stock-daily", help="获取个股日线")
    p_sd.add_argument("symbol", type=str, help="股票代码 (e.g. 601857.SH)")
    p_sd.add_argument("--start", type=str, required=True, help="开始日期 YYYY-MM-DD")
    p_sd.add_argument("--end", type=str, required=True, help="结束日期 YYYY-MM-DD")
    p_sd.add_argument(
        "--provider", type=str, default=None, help="数据提供方"
    )
    p_sd.add_argument(
        "--adjustment", type=str, default="none",
        choices=["none", "qfq", "hfq"], help="复权方式 (default: none)"
    )
    p_sd.add_argument(
        "--no-fallback", action="store_true", help="禁用数据源回退"
    )
    p_sd.add_argument(
        "--verbose", "-v", action="store_true", help="显示质量检查详情"
    )
    p_sd.set_defaults(func=cmd_fetch_stock_daily)

    # fetch-index-daily
    p_id = subparsers.add_parser("fetch-index-daily", help="获取指数日线")
    p_id.add_argument("index_code", type=str, help="指数代码 (e.g. 000001)")
    p_id.add_argument("--start", type=str, required=True, help="开始日期 YYYY-MM-DD")
    p_id.add_argument("--end", type=str, required=True, help="结束日期 YYYY-MM-DD")
    p_id.add_argument(
        "--provider", type=str, default=None, help="数据提供方"
    )
    p_id.set_defaults(func=cmd_fetch_index_daily)

    # inspect
    p_inspect = subparsers.add_parser(
        "inspect", help="查看已保存数据信息"
    )
    p_inspect.add_argument("dataset", type=str, help="数据集类型")
    p_inspect.add_argument("symbol", type=str, nargs="?", default="", help="标的代码")
    p_inspect.add_argument(
        "--show-data", action="store_true", help="显示数据预览"
    )
    p_inspect.set_defaults(func=cmd_inspect)

    # build-value-facts
    p_bvf = subparsers.add_parser(
        "build-value-facts", help="构建价值评估事实数据",
    )
    p_bvf.add_argument(
        "symbol", type=str, help="股票代码 (e.g. 000001.SZ)",
    )
    p_bvf.add_argument(
        "--start-year", type=int, required=True, help="起始年份",
    )
    p_bvf.add_argument(
        "--end-year", type=int, required=True, help="结束年份",
    )
    p_bvf.add_argument(
        "--source", type=str, default="candidate",
        choices=["candidate", "official"],
        help="数据来源类型 (default: candidate)",
    )
    p_bvf.set_defaults(func=cmd_build_value_facts)

    # verify-value-facts
    p_vvf = subparsers.add_parser(
        "verify-value-facts", help="重新验证已有事实运行",
    )
    p_vvf.add_argument(
        "symbol", type=str, help="股票代码 (e.g. 000001.SZ)",
    )
    p_vvf.add_argument(
        "--run-id", type=str, required=True, help="构建运行 ID",
    )
    p_vvf.set_defaults(func=cmd_verify_value_facts)

    # query-value-facts
    p_qvf = subparsers.add_parser(
        "query-value-facts", help="PIT 查询价值评估事实",
    )
    p_qvf.add_argument(
        "symbol", type=str, help="股票代码 (e.g. 000001.SZ)",
    )
    p_qvf.add_argument(
        "--as-of", type=str, required=True, dest="as_of",
        help="PIT 截止日期 YYYY-MM-DD",
    )
    p_qvf.add_argument(
        "--concept", type=str, action="append",
        help="概念 ID（可重复指定）",
    )
    p_qvf.add_argument(
        "--include-unverified", action="store_true",
        help="仅用于审计，不得用于正式指标或历史回测",
    )
    p_qvf.set_defaults(func=cmd_query_value_facts)

    args = parser.parse_args(argv)

    setup_logging(args.debug)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
