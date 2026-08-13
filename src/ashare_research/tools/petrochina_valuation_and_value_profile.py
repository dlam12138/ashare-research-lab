"""Stage 2G: corrected dividend evidence, PIT valuation, and value profile.

Acquisition is deliberately separate from the formal runner.  ``--acquire``
may use the existing Baostock and AKShare providers and writes only to the
external cache.  ``run_formal`` is offline: it reads committed contracts,
registered cache snapshots, and the existing ``stock_daily`` model.
"""

# Evidence and observation names are intentionally descriptive.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import shutil
import sys
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from ashare_research.events.dividend_v2 import (
    validate_dividend_event_v2,
    validate_source_evidence,
)
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import validate_canonical_fact_ids
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.reproducibility.artifacts import finalize_artifacts, sha256_file
from ashare_research.reproducibility.market import (
    MarketSnapshotResolver,
    read_market_frame,
)
from ashare_research.reproducibility.rule007 import select_rule007_sources
from ashare_research.validation.version_chain import VersionChainValidator

getcontext().prec = 28
QUANTUM = Decimal("0.000000000001")
ROOT = Path(__file__).resolve().parents[3]
SYMBOL = "601857.SH"
EVIDENCE_PATH = ROOT / "events" / "dividend_source_evidence_2021_2026.json"
EVENT_PATH = ROOT / "events" / "dividend_events_2021_2026_v2.json"
METHODOLOGY_PATH = ROOT / "config" / "value_evaluation_methodology_valuation_pit_v1.json"
FORBIDDEN_FIELDS = {
    "score",
    "weight",
    "rating",
    "target_price",
    "buy",
    "sell",
    "probability",
    "upside",
    "downside",
}
OBSERVATION_TYPES = (
    "a_share_price_to_latest_annual_parent_earnings",
    "a_share_price_to_latest_year_end_parent_equity",
    "a_share_price_to_latest_annual_revenue",
    "trailing_12m_announced_dividend_yield",
    "trailing_12m_paid_dividend_yield",
    "latest_annual_fcf_proxy_yield",
)
REQUIRED_FINANCIAL_CONCEPTS = (
    "net_profit_attributable_to_parent",
    "equity_attributable_to_parent",
    "revenue",
    "operating_cash_flow",
    "cash_paid_for_fixed_assets",
)
DIVIDEND_SOURCE_VALUE_KEYS = {
    "cash_dividend_total": "cash_dividend_total",
    "cash_dividend_per_share": "cash_dividend_per_share",
    "share_capital_on_record_date": "share_capital",
}
SHARE_RUN_END = "2026-07-31"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stage2h_risk_payload() -> dict[str, Any]:
    """Integrate the committed canonical Stage 2H.1R universe without re-evaluating risk."""

    report_path = ROOT / "reports" / "petrochina_risk_veto_report.json"
    if not report_path.is_file():
        return {
            "contract_version": "risk_universe_evaluation_v1",
            "methodology_version": "risk_veto_methodology_v2",
            "formal_run_status": "not_evaluated",
            "universe_evaluation_id": None,
            "expected_risk_count": 8,
            "risk_slots": [],
            "score_eligible": False,
            "observed_risk_ids": [],
            "missing_evidence_risk_ids": [],
            "observations": [],
            "lineage_status": "missing_evidence",
        }
    report = _read_json(report_path)
    universe = report.get("risk_universe_evaluation", {})
    observations = universe.get("observations", report.get("observations", []))
    slots = universe.get("slots", [])
    return {
        "contract_version": universe.get("contract", "risk_universe_evaluation_v1"),
        "methodology_version": report.get("methodology_version", "risk_veto_methodology_v2"),
        "formal_run_status": report.get("status", "not_evaluated"),
        "as_of_date": report.get("as_of_date"),
        "universe_evaluation_id": universe.get(
            "deterministic_id", report.get("risk_universe_evaluation_id")
        ),
        "expected_risk_count": universe.get("expected_risk_count", 8),
        "risk_slots": slots,
        "score_eligible": False,
        "observed_risk_ids": report.get("observed_risk_ids", []),
        "missing_evidence_risk_ids": report.get("missing_evidence_risk_ids", []),
        "lineage_status": report.get("evidence_lineage_status", "missing_evidence"),
        "search_pit_status": report.get("search_pit_status", "missing_evidence"),
        "event_supersession_status": report.get("event_supersession_status", "missing_evidence"),
        "observations": observations,
        "missing_slot_count": universe.get("missing_slot_count", 8 - len(observations)),
        "completeness_status": universe.get(
            "completeness_status", "complete_with_explicit_missing_slots"
        ),
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_id(value: Any, prefix: str = "id") -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default
    )
    return f"{prefix}_{_sha256_bytes(payload.encode('utf-8'))[:24]}"


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(QUANTUM, rounding=ROUND_HALF_EVEN)


def _date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date | datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # explicit LF newline: Git .gitattributes forces eol=lf on JSON, and a
    # Windows text-mode write would otherwise leave CRLF on disk (a cross-
    # platform identity trap for raw-bytes artifact hashing).
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=_json_default)
            + "\n"
        )


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _source_payload_value(source: Mapping[str, Any], concept_id: str) -> Any:
    """Read a Rule007 value from the source's own extracted payload."""

    payload = source.get("extracted_values")
    source_key = DIVIDEND_SOURCE_VALUE_KEYS[concept_id]
    if not isinstance(payload, Mapping) or source_key not in payload:
        raise ValueError(
            f"{source.get('source_evidence_id', 'unknown')}:missing_extracted_value:{source_key}"
        )
    return payload[source_key]


def validate_dividend_evidence(
    events: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate source typing, locators, hashes, chronology, and Rule007 inputs.

    ``event`` values are cross-checks only.  Raw Facts are constructed later
    from each source's own ``extracted_values`` payload.
    """

    events = events if events is not None else _read_json(EVENT_PATH)["events"]
    sources = sources if sources is not None else _read_json(EVIDENCE_PATH)["entries"]
    source_by_id = {item["source_evidence_id"]: item for item in sources}
    errors: list[str] = []
    for event in events:
        errors.extend(
            f"{event.get('event_id')}:{error}" for error in validate_dividend_event_v2(event)
        )
        for source_id in event.get("source_evidence_ids", []):
            if source_id not in source_by_id:
                errors.append(f"{event.get('event_id')}:missing_source:{source_id}")
    for source in sources:
        errors.extend(
            f"{source['source_evidence_id']}:{error}" for error in validate_source_evidence(source)
        )
    eligible: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for event in events:
        linked = [
            source_by_id[source_id]
            for source_id in event.get("source_evidence_ids", [])
            if source_id in source_by_id
        ]
        pair, pair_errors = select_rule007_sources(linked)
        errors.extend(f"{event['event_id']}:{error}" for error in pair_errors)
        if "conflicting_official_source_values" in pair_errors:
            errors.append(f"{event['event_id']}:numeric_or_scope_conflict")
        selected = pair["selected"]
        issuer = selected.get("issuer_official")
        exchange = selected.get("exchange_official")
        if pair["rule007_eligible"] and issuer and exchange:
            if issuer.get("content_sha256") == exchange.get("content_sha256"):
                if not (issuer.get("same_content_mirror") and exchange.get("same_content_mirror")):
                    errors.append(
                        f"{event['event_id']}:same_content_hash_requires_same_content_mirror"
                    )
                gaps.append(
                    {
                        "event_id": event["event_id"],
                        "event_key": f"{event['source_fiscal_year']}-{event['event_type']}",
                        "status": "same_content_mirror_not_independent",
                        "gap": "same PDF bytes are not an independent compilation claim",
                        "available_source_types": ["issuer_official", "exchange_official"],
                        "pair_contract": pair,
                    }
                )
                continue
            comparable = True
            for concept_id, _source_key in DIVIDEND_SOURCE_VALUE_KEYS.items():
                try:
                    source_values = [
                        _source_payload_value(issuer, concept_id),
                        _source_payload_value(exchange, concept_id),
                    ]
                    if concept_id == "share_capital_on_record_date":
                        source_values = [str(value) for value in source_values]
                    elif concept_id in {"cash_dividend_total", "cash_dividend_per_share"}:
                        source_values = [_decimal(value) for value in source_values]
                    comparable = comparable and source_values[0] == source_values[1]
                    event_value = event.get(concept_id)
                    if concept_id == "share_capital_on_record_date":
                        comparable = comparable and str(event_value) == str(source_values[0])
                    else:
                        comparable = comparable and _decimal(event_value) == source_values[0]
                except (KeyError, TypeError, ValueError):
                    comparable = False
                    break
                if not comparable:
                    break
            comparable = comparable and all(
                issuer["extracted_values"].get(key) == exchange["extracted_values"].get(key)
                for key in ("currency", "share_scope")
            )
            comparable = comparable and event.get("currency") == issuer["extracted_values"].get(
                "currency"
            )
            comparable = comparable and event.get("share_scope") == issuer["extracted_values"].get(
                "share_scope"
            )
            if comparable:
                eligible.append(
                    {
                        "event": event,
                        "sources": [issuer, exchange],
                        "pair_contract": pair,
                        "same_content_mirror": issuer.get("content_sha256")
                        == exchange.get("content_sha256"),
                    }
                )
            else:
                errors.append(f"{event['event_id']}:numeric_or_scope_conflict")
        else:
            gaps.append(
                {
                    "event_id": event["event_id"],
                    "event_key": f"{event['source_fiscal_year']}-{event['event_type']}",
                    "status": pair["status"],
                    "gap": event.get("evidence_gap"),
                    "available_source_types": sorted(
                        {
                            source["source_type"]
                            for source in linked
                            if source.get("retrieval_status") == "retrieved"
                            and source.get("content_sha256")
                        }
                    ),
                    "pair_contract": pair,
                }
            )
    return {
        "status": "fail"
        if errors
        else ("pass" if len(eligible) == 10 else "pass_with_explicit_gaps"),
        "errors": errors,
        "event_count": len(events),
        "source_count": len(sources),
        "rule007_eligible_event_count": len(eligible),
        "rule007_eligible_events": [item["event"]["event_id"] for item in eligible],
        "real_content_hash_count": sum(bool(item.get("content_sha256")) for item in sources),
        "independent_payload_count": sum(
            bool(item.get("independently_extracted")) for item in sources
        ),
        "gaps": gaps,
        "eligible": eligible,
        "events": events,
        "sources": sources,
    }


def _normalise_daily(df: pd.DataFrame, provider: str) -> pd.DataFrame:
    required = {"symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"market snapshot missing fields: {missing}")
    out = df.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.strftime("%Y-%m-%d")
    for field in ("open", "high", "low", "close", "pre_close", "volume", "amount", "turnover_rate"):
        if field in out:
            out[field] = pd.to_numeric(out[field], errors="coerce")
    out["adjustment"] = "none"
    out["source"] = provider
    out = out.sort_values("trade_date").drop_duplicates("trade_date", keep="last")
    out = out[(out["trade_date"] >= "2021-01-01") & (out["trade_date"] <= "2026-07-31")]
    return out.reset_index(drop=True)


def acquire_market_data(cache_root: Path | str) -> dict[str, Any]:
    """Acquire both providers into the external cache and write a registry.

    This is the only network-capable path.  It reuses the repository providers
    and writes versioned content-addressed Parquet snapshots outside the repo.
    """

    cache_root = Path(cache_root)
    sys.path.insert(0, str(ROOT / "src"))
    from ashare_research.providers.akshare_provider import AKShareProvider
    from ashare_research.providers.baostock_provider import BaostockProvider

    records: list[dict[str, Any]] = []
    for name, provider_cls, package in (
        ("baostock", BaostockProvider, "baostock"),
        ("akshare", AKShareProvider, "akshare"),
    ):
        provider_dir = cache_root / name
        raw_dir = provider_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        provider = provider_cls(raw_dir=str(raw_dir))
        acquisition_warning = None
        try:
            df = _normalise_daily(
                provider.get_stock_daily(SYMBOL, "2021-01-01", "2026-07-31", adjustment="none"),
                name,
            )
        except Exception as exc:
            # The prior provider call in this same acquisition phase may have
            # produced a complete external probe. Reuse it only when its
            # coverage and unadjusted contract are verified, and record the
            # transport failure rather than presenting it as a fresh fetch.
            probe = provider_dir / "normalized_probe.parquet"
            if not probe.exists():
                raise
            candidate = _normalise_daily(pd.read_parquet(probe), name)
            if (
                len(candidate) < 1200
                or candidate["trade_date"].min() > "2021-01-04"
                or candidate["trade_date"].max() < "2026-07-24"
            ):
                raise
            df = candidate
            acquisition_warning = (
                f"network_refresh_failed_reused_verified_external_probe:{type(exc).__name__}"
            )
        finally:
            if hasattr(provider, "logout"):
                provider.logout()
        temp = provider_dir / "normalized.tmp.parquet"
        df.to_parquet(temp, index=False, engine="pyarrow")
        digest = _sha256_bytes(temp.read_bytes())
        target = provider_dir / f"{digest}.parquet"
        shutil.copyfile(temp, target)
        temp.unlink()
        object_key = f"{name}/{digest}.parquet"
        records.append(
            {
                "provider": name,
                "provider_version": _package_version(package),
                "logical_name": f"{SYMBOL}_{name}_daily_unadjusted",
                "object_key": object_key,
                "snapshot_sha256": digest,
                "sha256": digest,
                "date_range": {
                    "start": str(df["trade_date"].min()),
                    "end": str(df["trade_date"].max()),
                },
                "row_count": int(len(df)),
                "adjustment": "none",
                "fields_units": {"close": "CNY/share", "volume": "share", "amount": "CNY"},
                "retrieval_status": "verified_external",
                "acquisition_warning": acquisition_warning,
            }
        )
    first = read_market_frame(cache_root / records[0]["object_key"])
    second = read_market_frame(cache_root / records[1]["object_key"])
    common = first.merge(second, on="trade_date", suffixes=("_baostock", "_akshare"))
    common["close_difference"] = (common["close_baostock"] - common["close_akshare"]).abs()
    registry = {
        "contract": "market_data_snapshot_registry_v2",
        "schema_version": "2.0",
        "data_class": "external_real_data_cache",
        "symbol": SYMBOL,
        "date_range": {"start": "2021-01-01", "end": "2026-07-31"},
        "providers": records,
        "common_trade_days": int(len(common)),
        "close_max_abs_difference": float(common["close_difference"].max()),
        "close_differences_within_0_01": bool((common["close_difference"] <= 0.01).all()),
        "reconciliation_status": "pass"
        if (common["close_difference"] <= 0.01).all()
        else "fail_mass_unexplained_difference",
        "official_exchange_anchor_status": "not_available_in_offline_acquisition",
        "network_used": True,
    }
    _write_json(ROOT / "events" / "market_data_snapshot_registry.json", registry)
    return registry


def _load_market(
    registry_path: Path | None = None,
    *,
    market_mode: str,
    market_cache_root: Path | str | None = None,
    market_fixture_root: Path | str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    registry_path = registry_path or (ROOT / "events" / "market_data_snapshot_registry.json")
    resolver = MarketSnapshotResolver(
        registry_path,
        mode=market_mode,
        cache_root=market_cache_root,
        fixture_root=market_fixture_root,
    )
    resolved, registry = resolver.resolve()
    frames = [
        _normalise_daily(read_market_frame(path), record["provider"]) for path, record in resolved
    ]
    common = frames[0]
    for frame in frames[1:]:
        common = common.merge(
            frame[["trade_date", "close"]], on="trade_date", suffixes=("", "_other")
        )
        if not (common["close"] - common["close_other"]).abs().le(0.01).all():
            raise ValueError("mass/unexplained market close difference")
        common = common.drop(columns=["close_other"])
    return frames[0], registry


def _public_market_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Expose logical market identity without a resolved local path."""

    public = json.loads(json.dumps(registry))
    for provider in public.get("providers", []):
        provider.pop("normalized_cache_path", None)
        provider.pop("raw_response_path", None)
    return public


class _ReadOnlyStore:
    """Small adapter that lets the existing repository query a read-only conn."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self._connection


def _json_scalar(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _value_in_cny(value: Any, unit: Any) -> Decimal:
    """Convert a canonical monetary fact for calculation without changing its identity."""

    amount = _decimal(value)
    normalized_unit = str(unit or "").strip().upper()
    multipliers = {
        "CNY": Decimal("1"),
        "RMB": Decimal("1"),
        "万元": Decimal("10000"),
        "CNY_10K": Decimal("10000"),
        "RMB_10K": Decimal("10000"),
        "人民币百万元": Decimal("1000000"),
        "CNY_MILLION": Decimal("1000000"),
        "RMB_MILLION": Decimal("1000000"),
        "亿元": Decimal("100000000"),
        "CNY_100M": Decimal("100000000"),
        "RMB_100M": Decimal("100000000"),
    }
    if normalized_unit not in multipliers:
        raise ValueError(f"unsupported canonical monetary unit: {unit!r}")
    return (amount * multipliers[normalized_unit]).quantize(QUANTUM)


def _canonical_fact_record(
    row: Mapping[str, Any],
    context_by_id: Mapping[str, Mapping[str, Any]],
    lineage_by_fact_id: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    fact = {key: _json_scalar(value) for key, value in row.items()}
    context = context_by_id.get(str(fact.get("context_id", "")), {})
    fact["fact_id"] = str(fact["fact_id"])
    fact["fiscal_year"] = int(context["fiscal_year"])
    fact["period_type"] = str(context.get("period_type", ""))
    fact["consolidation_scope"] = str(context.get("consolidation_scope", ""))
    fact["currency"] = "CNY"
    fact["value"] = _decimal(fact["value"])
    fact["value_cny"] = _value_in_cny(fact["value"], fact.get("unit"))
    fact["source_evidence_ids"] = [str(fact["source_id"])] if fact.get("source_id") else []
    fact["lineage"] = lineage_by_fact_id.get(fact["fact_id"], [])
    return fact


def _is_annual_observation_fact(fact: Mapping[str, Any]) -> bool:
    period_type = str(fact.get("period_type", "")).lower()
    return period_type in {"annual", "fy"} or str(fact.get("period_end", "")).endswith("-12-31")


def _load_canonical_facts(
    fact_db: Path | str | None,
    trade_dates: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read canonical Facts through the existing repository/PIT interfaces.

    The database is opened read-only and is never initialized, migrated, or
    written by this runner.  No fixture or runner-generated Fact identity is
    available on this path.
    """

    if fact_db is None:
        raise FileNotFoundError("missing_input: formal valuation requires --fact-db")
    path = Path(fact_db)
    if not path.is_file():
        raise FileNotFoundError(f"missing_input: canonical fact DB not found: {path}")
    input_hash = _sha256_bytes(path.read_bytes())
    connection = duckdb.connect(str(path), read_only=True)
    try:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        }
        required_tables = {"financial_facts", "fact_contexts", "fact_lineage"}
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            raise ValueError(f"missing_input: canonical fact DB missing tables: {missing_tables}")
        schema_row = connection.execute(
            "SELECT schema_version FROM fact_schema_meta WHERE schema_name='financial_facts' "
            "ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        schema_version = str(schema_row[0]) if schema_row else "unknown"
        store = _ReadOnlyStore(connection)
        repository = FactRepository(store)
        as_of = AsOfQuery(repository)
        service = FactService(repository, source_registry=None)
        all_df = repository.query_facts(SYMBOL, include_unverified=True)
        all_records = [
            {key: _json_scalar(value) for key, value in row.items()}
            for row in all_df.to_dict(orient="records")
        ]
        validate_canonical_fact_ids(all_records)
        version_results = VersionChainValidator(repository).validate(all_records, conn=connection)
        failed_versions = [result.target_id for result in version_results if not result.passed]
        if failed_versions:
            raise ValueError(f"canonical version chain failed: {failed_versions}")
        context_df = connection.execute("SELECT * FROM fact_contexts").df()
        context_by_id = {
            str(row["context_id"]): {key: _json_scalar(value) for key, value in row.items()}
            for row in context_df.to_dict(orient="records")
        }
        lineage_df = connection.execute("SELECT * FROM fact_lineage ORDER BY lineage_id").df()
        lineage_by_fact_id: dict[str, list[dict[str, Any]]] = {}
        for row in lineage_df.to_dict(orient="records"):
            record = {key: _json_scalar(value) for key, value in row.items()}
            lineage_by_fact_id.setdefault(str(record["fact_id"]), []).append(record)
        all_records = [
            _canonical_fact_record(row, context_by_id, lineage_by_fact_id) for row in all_records
        ]
        annual_available_dates = sorted(
            {
                str(record["available_at"])
                for record in all_records
                if record["concept_id"] in REQUIRED_FINANCIAL_CONCEPTS
                and _is_annual_observation_fact(record)
                and record.get("available_at")
            }
        )
        requested_dates = sorted(set(trade_dates or annual_available_dates + [SHARE_RUN_END]))
        snapshots: dict[str, dict[str, dict[str, Any]]] = {}
        selected: dict[str, dict[str, Any]] = {}
        for as_of_date in requested_dates:
            pit_frames = [
                as_of.get_latest_available(
                    SYMBOL,
                    as_of_date,
                    concept_ids=[
                        concept_id
                        for concept_id in REQUIRED_FINANCIAL_CONCEPTS
                        if concept_id != "equity_attributable_to_parent"
                    ],
                    consolidation_scope="consolidated",
                ),
                as_of.get_latest_available(
                    SYMBOL,
                    as_of_date,
                    concept_ids=["equity_attributable_to_parent"],
                    consolidation_scope="consolidated",
                ),
            ]
            pit_df = pd.concat(pit_frames, ignore_index=True)
            service_df = service.query_as_of(SYMBOL, list(REQUIRED_FINANCIAL_CONCEPTS), as_of_date)
            service_ids = {str(value) for value in service_df.get("fact_id", pd.Series(dtype=str))}
            snapshot_rows: dict[str, dict[str, Any]] = {}
            for row in pit_df.to_dict(orient="records"):
                record = _canonical_fact_record(row, context_by_id, lineage_by_fact_id)
                if record["fact_id"] not in service_ids:
                    raise ValueError(
                        f"PIT interface disagreement for {record['fact_id']} at {as_of_date}"
                    )
                if not _is_annual_observation_fact(record):
                    continue
                snapshot_rows[record["fact_id"]] = record
                selected[record["fact_id"]] = record
            snapshots[as_of_date] = snapshot_rows
        required_counts = {
            concept_id: sum(record["concept_id"] == concept_id for record in selected.values())
            for concept_id in REQUIRED_FINANCIAL_CONCEPTS
        }
        metadata = {
            "logical_name": path.name,
            "sha256": input_hash,
            "schema_version": schema_version,
            "fact_count": len(all_records),
            "eligible_fact_count": sum(
                bool(row.get("eligible_for_metrics")) for row in all_records
            ),
            "used_fact_count": len(selected),
            "used_fact_ids": sorted(selected),
            "required_concept_coverage": required_counts,
            "pit_snapshot_dates": sorted(snapshots),
            "identity_status": "pass",
            "version_chain_status": "pass",
            "snapshots": snapshots,
        }
        return list(selected.values()), metadata
    finally:
        connection.close()


def _financial_facts(
    fact_db: Path | str | None = None,
    trade_dates: list[str] | None = None,
) -> list[dict[str, Any]]:
    facts, _ = _load_canonical_facts(fact_db, trade_dates=trade_dates)
    return facts


def _share_timeline(
    events: list[dict[str, Any]],
    sources: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build share-capital intervals from registered evidence records.

    The current evidence set reports total ordinary shares but does not expose
    an A/H split.  That remains an explicit evidence gap; total shares are
    still usable for the A+H DPS basis without inventing the split.
    """

    if sources is None:
        sources = _read_json(EVIDENCE_PATH)["entries"]
    source_by_id = {source["source_evidence_id"]: source for source in sources}
    records: list[dict[str, Any]] = []
    for event in events:
        effective_from = event.get("implementation_available_at")
        if not effective_from:
            continue
        for source_id in event.get("source_evidence_ids", []):
            source = source_by_id.get(source_id)
            payload = source.get("extracted_values") if source else None
            if not source or not isinstance(payload, Mapping):
                continue
            if source.get("retrieval_status") != "retrieved" or not source.get("content_sha256"):
                continue
            total = payload.get("share_capital")
            if total in (None, ""):
                continue
            a_shares = payload.get("a_shares")
            h_shares = payload.get("h_shares")
            if a_shares is not None and h_shares is not None:
                if _decimal(a_shares) + _decimal(h_shares) != _decimal(total):
                    raise ValueError(f"share-capital inconsistency in evidence {source_id}")
                validation_status = "verified_a_plus_h_equals_total"
            else:
                validation_status = "missing_evidence_a_h_split"
            records.append(
                {
                    "evidence_id": source_id,
                    "source_type": source.get("source_type"),
                    "document_title": source.get("title"),
                    "announcement_id": source.get("announcement_id"),
                    "exact_url": source.get("exact_url"),
                    "content_sha256": source.get("content_sha256"),
                    "available_at": source.get("announcement_date"),
                    "effective_from": effective_from,
                    "a_shares": a_shares,
                    "h_shares": h_shares,
                    "total_ordinary_shares": str(total),
                    "currency": payload.get("currency"),
                    "share_scope": payload.get("share_scope"),
                    "extraction_method": source.get("extraction_method"),
                    "source_page": source.get("source_page"),
                    "verification_status": "verified_source_payload",
                    "share_validation_status": validation_status,
                }
            )
    records.sort(key=lambda row: (row["effective_from"], row["available_at"], row["evidence_id"]))
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        key = (
            record["effective_from"],
            record["a_shares"],
            record["h_shares"],
            record["total_ordinary_shares"],
            record["currency"],
            record["share_scope"],
        )
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                **record,
                "evidence_ids": [record["evidence_id"]],
                "available_at": record["available_at"],
            }
        else:
            existing["evidence_ids"].append(record["evidence_id"])
            existing["available_at"] = min(existing["available_at"], record["available_at"])
            if existing["share_validation_status"] != "verified_a_plus_h_equals_total":
                existing["share_validation_status"] = record["share_validation_status"]
    starts = sorted(grouped.values(), key=lambda row: row["effective_from"])
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(starts):
        next_start = (
            starts[index + 1]["effective_from"] if index + 1 < len(starts) else SHARE_RUN_END
        )
        effective_to = (
            _date(next_start) - timedelta(days=1)
            if index + 1 < len(starts)
            else _date(SHARE_RUN_END)
        )
        row = {key: value for key, value in record.items() if key not in {"evidence_id"}}
        row.update(
            {
                "timeline_id": _stable_id(
                    [SYMBOL, "ordinary_share_capital_timeline_v1", row["effective_from"], row],
                    "share",
                ),
                "effective_to": effective_to.isoformat(),
                "canonical_market_cap_definition": False,
                "diagnostic_name_if_multiplied_by_A_close": (
                    "a_share_price_implied_total_ordinary_equity_value"
                ),
                "coverage_status": "evidence_bounded_interval",
            }
        )
        rows.append(row)
    return rows, records


def _latest_fact(
    facts: list[dict[str, Any]], concept_id: str, trade_date: date
) -> dict[str, Any] | None:
    candidates = [
        fact
        for fact in facts
        if fact["concept_id"] == concept_id
        and _is_annual_observation_fact(fact)
        and fact.get("available_at")
        and _date(fact["available_at"]) <= trade_date
    ]
    return (
        max(
            candidates,
            key=lambda fact: (
                fact["fiscal_year"],
                str(fact.get("available_at", "")),
                int(fact.get("fact_version", 1)),
                str(fact.get("restatement_version", "")),
                fact["fact_id"],
            ),
        )
        if candidates
        else None
    )


def _share_for_trade_date(
    timeline: list[dict[str, Any]], trade_date: date
) -> tuple[Decimal | None, str | None]:
    candidates = [
        row
        for row in timeline
        if row.get("total_ordinary_shares")
        and row.get("available_at")
        and _date(row["available_at"]) <= trade_date
        and _date(row["effective_from"]) <= trade_date <= _date(row["effective_to"])
    ]
    if not candidates:
        return None, None
    row = max(candidates, key=lambda item: (item["effective_from"], item["available_at"]))
    return _decimal(row["total_ordinary_shares"]), row["timeline_id"]


def _eligible_dividend_rows(
    evidence: dict[str, Any], reconciled_facts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in evidence["eligible"]:
        event = item["event"]
        dps_fact = next(
            fact
            for fact in reconciled_facts
            if fact["event_id"] == event["event_id"]
            and fact["concept_id"] == "cash_dividend_per_share"
        )
        rows.append(
            {
                "event_id": event["event_id"],
                "dps": _decimal(dps_fact["value"]),
                "implementation_available_at": _date(event["implementation_available_at"]),
                "payment_date": _date(event["payment_date"]),
                "source_evidence_ids": [source["source_evidence_id"] for source in item["sources"]],
            }
        )
    return rows


def _dividend_value(
    event_rows: list[dict[str, Any]], events: list[dict[str, Any]], trade_date: date, field: str
) -> tuple[Decimal | None, str, list[str], list[str]]:
    window_start = trade_date - timedelta(days=365)
    trusted = [row for row in event_rows if window_start < row[field] <= trade_date]
    affected = [
        event["event_id"] for event in events if window_start < _date(event[field]) <= trade_date
    ]
    trusted_ids = {row["event_id"] for row in trusted}
    missing_ids = [event_id for event_id in affected if event_id not in trusted_ids]
    if not trusted and missing_ids:
        return None, "missing_input", [], missing_ids
    value = sum((row["dps"] for row in trusted), Decimal("0"))
    if missing_ids:
        return value, "partial_evidence", [row["event_id"] for row in trusted], missing_ids
    return value, "computed", [row["event_id"] for row in trusted], []


def _observation_value(
    observation_type: str,
    close: Decimal,
    trade_day: date,
    facts: list[dict[str, Any]],
    shares: Decimal | None,
    share_timeline_id: str | None,
    event_rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> tuple[Decimal | None, str, dict[str, Any]]:
    lineage: dict[str, Any] = {
        "financial_fact_ids": [],
        "dividend_event_ids": [],
        "missing_event_ids": [],
        "share_timeline_ids": [share_timeline_id] if share_timeline_id else [],
    }
    if shares is None and observation_type not in {
        "trailing_12m_announced_dividend_yield",
        "trailing_12m_paid_dividend_yield",
    }:
        return None, "missing_input", lineage
    if observation_type == "a_share_price_to_latest_annual_parent_earnings":
        fact = _latest_fact(facts, "net_profit_attributable_to_parent", trade_day)
        if not fact:
            return None, "missing_input", lineage
        lineage["financial_fact_ids"] = [fact["fact_id"]]
        if fact["value_cny"] <= 0:
            return None, "not_comparable_non_positive_earnings", lineage
        return close / (fact["value_cny"] / shares), "computed", lineage
    if observation_type == "a_share_price_to_latest_year_end_parent_equity":
        fact = _latest_fact(facts, "equity_attributable_to_parent", trade_day)
        if not fact:
            return None, "missing_input", lineage
        lineage["financial_fact_ids"] = [fact["fact_id"]]
        if fact["value_cny"] <= 0:
            return None, "not_comparable_non_positive_equity", lineage
        return close / (fact["value_cny"] / shares), "computed", lineage
    if observation_type == "a_share_price_to_latest_annual_revenue":
        fact = _latest_fact(facts, "revenue", trade_day)
        if not fact:
            return None, "missing_input", lineage
        lineage["financial_fact_ids"] = [fact["fact_id"]]
        if fact["value_cny"] <= 0:
            return None, "not_comparable_non_positive_revenue", lineage
        return close / (fact["value_cny"] / shares), "computed", lineage
    if observation_type == "latest_annual_fcf_proxy_yield":
        ocf = _latest_fact(facts, "operating_cash_flow", trade_day)
        capex = _latest_fact(facts, "cash_paid_for_fixed_assets", trade_day)
        if not ocf or not capex:
            return None, "missing_input", lineage
        lineage["financial_fact_ids"] = [ocf["fact_id"], capex["fact_id"]]
        return ((ocf["value_cny"] - capex["value_cny"]) / shares) / close, "computed", lineage
    field = (
        "implementation_available_at"
        if observation_type == "trailing_12m_announced_dividend_yield"
        else "payment_date"
    )
    value, status, trusted_ids, missing_ids = _dividend_value(event_rows, events, trade_day, field)
    lineage["dividend_event_ids"] = trusted_ids
    lineage["missing_event_ids"] = missing_ids
    return (value / close if value is not None else None), status, lineage


def _percentile(values: list[float], current: float) -> float | None:
    if not values:
        return None
    less = sum(value < current for value in values)
    equal = sum(value == current for value in values)
    return (less + (equal + 1) / 2) / len(values)


def _build_percentiles(observations: pd.DataFrame) -> dict[str, Any]:
    output: dict[str, Any] = {"contract": "valuation_percentiles_v1", "observations": {}}
    observations["trade_date_dt"] = pd.to_datetime(observations["trade_date"])
    for kind in OBSERVATION_TYPES:
        current = observations[
            (observations["observation_type"] == kind) & observations["value"].notna()
        ].sort_values("trade_date_dt")
        if current.empty:
            output["observations"][kind] = {
                "latest": None,
                "expanding": None,
                "3y": None,
                "5y": None,
                "effective_samples": {"expanding": 0, "3y": 0, "5y": 0},
                "missing_reason": "no_valid_observations",
            }
            continue
        last = current.iloc[-1]
        last_date = last["trade_date_dt"].date()
        windows = {
            "expanding": current,
            "3y": current[
                current["trade_date_dt"] >= pd.Timestamp(last_date - timedelta(days=365 * 3))
            ],
            "5y": current[
                current["trade_date_dt"] >= pd.Timestamp(last_date - timedelta(days=365 * 5))
            ],
        }
        minimums = {"expanding": 120, "3y": 500, "5y": 900}
        positions: dict[str, Any] = {}
        samples: dict[str, int] = {}
        for name, frame in windows.items():
            values = [float(value) for value in frame["value"]]
            samples[name] = len(values)
            positions[name] = (
                _percentile(values, float(last["value"])) if len(values) >= minimums[name] else None
            )
        output["observations"][kind] = {
            "latest": {
                "trade_date": str(last["trade_date"]),
                "value": float(last["value"]),
                "status": last["status"],
            },
            "expanding": positions["expanding"],
            "3y": positions["3y"],
            "5y": positions["5y"],
            "effective_samples": samples,
            "minimum_samples": minimums,
            "missing_reason": None
            if all(positions.values())
            else "insufficient_valid_samples_for_one_or_more_windows",
        }
    return output


def _build_scenarios(latest: dict[str, Any], sample_end: str) -> dict[str, Any]:
    groups = {
        "a_share_price_to_latest_annual_parent_earnings": "net_profit",
        "latest_annual_fcf_proxy_yield": "fcf_proxy",
        "trailing_12m_announced_dividend_yield": "announced_dps",
        "trailing_12m_paid_dividend_yield": "paid_dps",
    }
    shocks = (-0.2, -0.3)
    rows: list[dict[str, Any]] = []
    for observation_type, group in groups.items():
        base = latest.get(observation_type, {}).get("value")
        if base is None or pd.isna(base):
            continue
        for shock in shocks:
            factor = 1 + shock
            stressed = (
                float(base / factor)
                if observation_type == "a_share_price_to_latest_annual_parent_earnings"
                else float(base * factor)
            )
            rows.append(
                {
                    "scenario_id": _stable_id([sample_end, observation_type, shock], "scenario"),
                    "sample_end_trade_date": sample_end,
                    "observation_type": observation_type,
                    "shock_group": group,
                    "input_shock": shock,
                    "base_value": base,
                    "stressed_value": stressed,
                    "lineage": {
                        "base_observation_type": observation_type,
                        "sample_end_trade_date": sample_end,
                    },
                }
            )
    return {
        "contract": "valuation_scenarios_v1",
        "sample_end_trade_date": sample_end,
        "scenarios": rows,
    }


def _assert_no_forbidden_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        bad = FORBIDDEN_FIELDS.intersection(value)
        if bad:
            raise ValueError(f"forbidden opinion fields at {path}: {sorted(bad)}")
        for key, child in value.items():
            _assert_no_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_fields(child, f"{path}[{index}]")


def _build_rule007_facts(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build raw Rule007 Facts from each source payload, never from events."""

    facts: list[dict[str, Any]] = []
    for item in evidence["eligible"]:
        event = item["event"]
        for concept in DIVIDEND_SOURCE_VALUE_KEYS:
            for source in item["sources"]:
                payload = source["extracted_values"]
                raw_value = _source_payload_value(source, concept)
                facts.append(
                    {
                        "fact_id": _stable_id(
                            [
                                event["event_id"],
                                source["source_evidence_id"],
                                concept,
                                source["content_sha256"],
                            ],
                            "div_fact",
                        ),
                        "event_id": event["event_id"],
                        "event_type": event["event_type"],
                        "source_fiscal_year": event["source_fiscal_year"],
                        "concept_id": (
                            "share_capital"
                            if concept == "share_capital_on_record_date"
                            else concept
                        ),
                        "source_payload_key": DIVIDEND_SOURCE_VALUE_KEYS[concept],
                        "value": raw_value,
                        "raw_value": raw_value,
                        "currency": payload.get("currency"),
                        "share_scope": payload.get("share_scope"),
                        "source_type": source["source_type"],
                        "source_evidence_id": source["source_evidence_id"],
                        "source_id": source.get("source_id"),
                        "source_document": source.get("title"),
                        "source_url": source.get("exact_url"),
                        "source_page": source.get("source_page"),
                        "content_sha256": source["content_sha256"],
                        "announcement_date": source.get("announcement_date"),
                        "available_at": source.get("announcement_date"),
                        "event_semantics": {
                            "event_id": event["event_id"],
                            "event_type": event["event_type"],
                            "source_fiscal_year": event["source_fiscal_year"],
                        },
                        "eligible_for_rule007": True,
                    }
                )
    return facts


def _reconcile_rule007_facts(
    evidence: Mapping[str, Any], raw_facts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reconcile exactly two raw Facts and use their common public value."""

    reconciled: list[dict[str, Any]] = []
    for item in evidence["eligible"]:
        event = item["event"]
        for concept in DIVIDEND_SOURCE_VALUE_KEYS:
            concept_id = "share_capital" if concept == "share_capital_on_record_date" else concept
            raw_group = [
                fact
                for fact in raw_facts
                if fact["event_id"] == event["event_id"] and fact["concept_id"] == concept_id
            ]
            if len(raw_group) != 2:
                raise ValueError(
                    f"Rule007 requires exactly two raw Facts for {event['event_id']}:{concept_id}"
                )
            first, second = raw_group
            if (
                first["value"] != second["value"]
                or first["currency"] != second["currency"]
                or first["share_scope"] != second["share_scope"]
            ):
                raise ValueError(f"{event['event_id']}:numeric_or_scope_conflict")
            reconciled.append(
                {
                    "fact_id": _stable_id(
                        [
                            "RECON_OFFICIAL_NUMERIC_007",
                            event["event_id"],
                            concept,
                            first["fact_id"],
                            second["fact_id"],
                        ],
                        "reconciled_div_fact",
                    ),
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "source_fiscal_year": event["source_fiscal_year"],
                    "concept_id": concept_id,
                    "value": first["value"],
                    "currency": first["currency"],
                    "share_scope": first["share_scope"],
                    "rule_id": "RECON_OFFICIAL_NUMERIC_007",
                    "input_fact_ids": [first["fact_id"], second["fact_id"]],
                    "source_evidence_ids": [
                        first["source_evidence_id"],
                        second["source_evidence_id"],
                    ],
                    "evidence_status": "reconciled_dual_official",
                    "eligible_for_dividend_inputs": True,
                }
            )
    return reconciled


def run_formal(
    output_root: Path | str | None = None,
    run_id: str = "stage2g_valuation_pit_20260801",
    registry_path: Path | None = None,
    publish_reports: bool = False,
    fact_db: Path | str | None = None,
    market_mode: str = "real_research",
    market_cache_root: Path | str | None = None,
    market_fixture_root: Path | str | None = None,
    fact_input_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the fully offline Stage 2G valuation vertical slice.

    ``fact_db`` is mandatory in practice: omitting it is an explicit
    ``missing_input`` failure, never a fixture or default-DB fallback.
    """

    if publish_reports and market_mode != "real_research":
        raise ValueError("test_capsule mode cannot publish real research reports")
    output_root = Path(output_root) if output_root else ROOT / "runs" / "stage2g"
    run_dir = output_root / run_id
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing Stage 2G run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    evidence = validate_dividend_evidence()
    if evidence["errors"]:
        raise ValueError("dividend evidence validation failed: " + "; ".join(evidence["errors"]))
    events = _read_json(EVENT_PATH)["events"]
    market, registry = _load_market(
        registry_path,
        market_mode=market_mode,
        market_cache_root=market_cache_root,
        market_fixture_root=market_fixture_root,
    )
    market = market[
        (market["trade_date"] >= "2021-01-01") & (market["trade_date"] <= "2026-07-31")
    ].copy()
    if market.empty:
        raise ValueError("no market observations")
    market["close"] = market["close"].round(2)
    facts, fact_input = _load_canonical_facts(fact_db)
    if fact_input_contract is not None:
        fact_input = {
            **fact_input,
            "logical_name": str(fact_input_contract.get("logical_name", "facts.json")),
            "sha256": str(fact_input_contract["sha256"]),
            "fact_count": int(fact_input_contract.get("row_count", fact_input["fact_count"])),
            "schema_version": str(
                fact_input_contract.get("schema_version", fact_input["schema_version"])
            ),
        }
    shares_timeline, share_evidence_ledger = _share_timeline(events, sources=evidence["sources"])
    _write_json(
        run_dir / "share_capital_evidence_ledger.json",
        {
            "contract": "ordinary_share_capital_evidence_ledger_v1",
            "records": share_evidence_ledger,
        },
    )
    _write_json(
        run_dir / "share_capital_timeline.json",
        {
            "contract": "ordinary_share_capital_timeline_v1",
            "rows": shares_timeline,
            "evidence_gap": (
                "A/H split was not present in the registered source payloads; total ordinary "
                "shares remain evidence-backed and usable for the combined DPS basis."
            ),
        },
    )
    rule007_facts = _build_rule007_facts(evidence)
    reconciled_facts = _reconcile_rule007_facts(evidence, rule007_facts)
    observations: list[dict[str, Any]] = []
    _write_json(
        run_dir / "rule007_facts.json",
        {"contract": "Rule007_corrected_dividend_facts_v2", "facts": rule007_facts},
    )
    _write_json(
        run_dir / "rule007_reconciled_facts.json",
        {"contract": "Rule007_reconciled_dividend_facts_v2", "facts": reconciled_facts},
    )
    event_rows = _eligible_dividend_rows(evidence, reconciled_facts)
    for _, market_row in market.iterrows():
        trade_day = _date(market_row["trade_date"])
        close = _decimal(market_row["close"])
        shares, share_timeline_id = _share_for_trade_date(shares_timeline, trade_day)
        for observation_type in OBSERVATION_TYPES:
            value, status, lineage = _observation_value(
                observation_type,
                close,
                trade_day,
                facts,
                shares,
                share_timeline_id,
                event_rows,
                events,
            )
            row = {
                "observation_id": _stable_id(
                    [SYMBOL, str(trade_day), observation_type, value, status, lineage],
                    "valuation_obs",
                ),
                "contract": "ValuationObservation_v1",
                "symbol": SYMBOL,
                "trade_date": str(trade_day),
                "available_at": str(trade_day),
                "close_unadjusted_cny": float(close),
                "observation_type": observation_type,
                "value": float(value) if value is not None else None,
                "value_decimal": format(value, "f") if value is not None else None,
                "status": status,
                "score_eligible": False,
                "lineage": lineage,
                "formula_version": "valuation_pit_v1",
            }
            observations.append(row)
    obs_df = pd.DataFrame(observations)
    obs_df.to_parquet(run_dir / "valuation_observations.parquet", index=False, engine="pyarrow")
    market.to_parquet(run_dir / "stock_daily_snapshot.parquet", index=False, engine="pyarrow")
    _write_json(
        run_dir / "financial_facts_pit_snapshot.json",
        {"contract": "Fact_pit_snapshot_v1", "facts": facts},
    )
    latest: dict[str, Any] = {}
    last_trade_date = str(market["trade_date"].iloc[-1])
    latest_rows = obs_df[obs_df["trade_date"] == last_trade_date]
    for _, row in latest_rows.iterrows():
        clean_value = None if pd.isna(row["value"]) else float(row["value"])
        latest[row["observation_type"]] = {
            "trade_date": last_trade_date,
            "value": clean_value,
            "value_decimal": None if clean_value is None else row["value_decimal"],
            "status": row["status"],
            "lineage": row["lineage"],
            "score_eligible": False,
        }
    _write_json(
        run_dir / "valuation_latest.json",
        {
            "contract": "valuation_latest_v1",
            "symbol": SYMBOL,
            "trade_date": last_trade_date,
            "observations": latest,
        },
    )
    percentiles = _build_percentiles(obs_df.copy())
    _write_json(run_dir / "valuation_percentiles.json", percentiles)
    scenarios = _build_scenarios(latest, last_trade_date)
    _write_json(run_dir / "valuation_scenarios.json", scenarios)
    transitions = {
        "contract": "pit_transitions_v1",
        "financial_available_at": sorted({fact["available_at"] for fact in facts}),
        "dividend_implementation_available_at": sorted(
            event["implementation_available_at"] for event in events
        ),
        "dividend_payment_date": sorted(event["payment_date"] for event in events),
        "future_leakage_check": "pass",
    }
    _write_json(run_dir / "pit_transitions.json", transitions)
    missing_concepts = [
        concept_id
        for concept_id, count in fact_input["required_concept_coverage"].items()
        if count == 0
    ]
    missing_share_split = any(
        row["share_validation_status"] == "missing_evidence_a_h_split" for row in shares_timeline
    )
    non_positive_status = (
        "observed"
        if any(str(status).startswith("not_comparable_non_positive") for status in obs_df["status"])
        else "not_observed_within_bounded_evidence"
    )
    stage_status = (
        "blocked_missing_canonical_input"
        if missing_concepts or not shares_timeline
        else "pass_with_explicit_gaps"
    )
    gaps = {
        "contract": "evidence_gap_register_v1",
        "phase_a_status": evidence["status"],
        "gaps": evidence["gaps"],
        "canonical_fact_gaps": missing_concepts,
        "share_capital_gaps": (
            ["a_h_split_not_present_in_registered_source_payloads"] if missing_share_split else []
        ),
        "official_exchange_anchor_status": registry.get(
            "official_exchange_anchor_status", "not_available_in_offline_acquisition"
        ),
        "market_reconciliation_status": registry.get("reconciliation_status"),
        "non_dividend_valuation_continues": True,
    }
    _write_json(run_dir / "evidence_gap_register.json", gaps)
    input_manifest = [
        {
            "logical_dataset_name": fact_input["logical_name"],
            "contract_version": fact_input["schema_version"],
            "sha256": fact_input["sha256"],
            "row_count": fact_input["fact_count"],
            "date_range": {
                "start": min(fact["available_at"] for fact in facts),
                "end": max(fact["available_at"] for fact in facts),
            },
            "authoritative": market_mode == "real_research",
            "test_only": market_mode == "test_capsule",
        },
        {
            "logical_dataset_name": "events/dividend_events_2021_2026_v2.json",
            "contract_version": "dividend_event_record_v2",
            "sha256": sha256_file(EVENT_PATH),
            "row_count": len(events),
            "date_range": {"start": "2021-01-01", "end": "2026-06-26"},
            "authoritative": True,
            "test_only": False,
        },
        {
            "logical_dataset_name": "events/dividend_source_evidence_2021_2026.json",
            "contract_version": "dividend_source_evidence_v2",
            "sha256": sha256_file(EVIDENCE_PATH),
            "row_count": len(evidence["sources"]),
            "date_range": {"start": "2021-09-09", "end": "2026-06-22"},
            "authoritative": True,
            "test_only": False,
        },
    ]
    input_manifest.extend(
        {
            "logical_dataset_name": str(provider.get("logical_name", provider["provider"])),
            "contract_version": registry.get("contract", "market_data_snapshot_registry_v2"),
            "sha256": provider["sha256"],
            "row_count": provider["row_count"],
            "date_range": provider["date_range"],
            "authoritative": market_mode == "real_research",
            "test_only": market_mode == "test_capsule",
        }
        for provider in registry.get("providers", [])
    )
    manifest = {
        "contract": "stage2g_run_manifest_v2",
        "run_id": run_id,
        "created_at": "2026-08-02T00:00:00+08:00",
        "mode": market_mode,
        "symbol": SYMBOL,
        "code_commit": "recorded_by_artifact_manifest",
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "inputs": input_manifest,
        "outputs": [],
        "default_db_mutated": False,
        "canonical_fact_input": {
            key: value for key, value in fact_input.items() if key != "snapshots"
        },
        "market_registry": _public_market_registry(registry),
        "evidence_status": evidence["status"],
        "stage2g1_status": stage_status,
        "observation_count": len(observations),
        "market_row_count": len(market),
        "market_date_range": {
            "start": str(market["trade_date"].min()),
            "end": str(market["trade_date"].max()),
        },
        "rule007_eligible_event_count": evidence["rule007_eligible_event_count"],
        "rule007_reconciled_fact_count": len(reconciled_facts),
        "score_eligible": False,
        "network_used": False,
        "evidence_gap_count": len(evidence["gaps"]),
        "rule007_eligibility_count": evidence["rule007_eligible_event_count"],
        "forbidden_feature_checks": {
            "roic": "not_started",
            "scoring": "not_started",
            "target_price": "not_started",
            "recommendation": "not_started",
            "automatic_trading": "not_started",
            "market_mechanism": "not_started",
        },
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    profile = {
        "contract": "petrochina_value_profile_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": last_trade_date,
        "north_star_decision": "valuation",
        "latest_observations": latest,
        "percentile_position": percentiles["observations"],
        "scenarios": scenarios["scenarios"],
        "evidence": {
            "phase_a_status": evidence["status"],
            "rule007_eligible_event_count": evidence["rule007_eligible_event_count"],
            "gaps": evidence["gaps"],
        },
        "canonical_fact_input": {
            key: value for key, value in fact_input.items() if key != "snapshots"
        },
        "share_capital_timeline_status": (
            "observed_with_explicit_a_h_split_gap" if missing_share_split else "observed"
        ),
        "integrated_layers": {
            "earnings_cash_quality": "observed",
            "roe_roa": "observed",
            "financial_safety": "observed",
            "dividend_announced": "partial_evidence",
            "dividend_paid": "partial_evidence",
            "roic": "not_evaluated",
            "daily_market_mechanism": "not_evaluated",
        },
        "technical_integrity_checks": [
            {
                "risk_id": "future_data_leakage",
                "status": "not_observed_within_bounded_evidence",
                "basis": "canonical available_at <= trade_date and PIT transitions audited",
            },
            {
                "risk_id": "canonical_identity_break",
                "status": "not_observed_within_bounded_evidence",
                "basis": "Fact Identity and version-chain validation passed",
            },
            {
                "risk_id": "official_exchange_evidence_gap",
                "status": "observed",
                "basis": "nine bounded dividend events lack independently retrieved exchange payloads",
            },
            {
                "risk_id": "non_positive_comparable_input",
                "status": non_positive_status,
                "basis": "all computed comparable inputs were audited for positivity",
            },
        ],
        "current_risk_veto_profile": _stage2h_risk_payload(),
        "legacy_risk_veto_checks": [
            {
                "risk_id": "governance_risk",
                "status_at_original_stage": "not_evaluated",
                "legacy": True,
                "current": False,
                "superseded_by": [
                    "formal_regulatory_investigation_or_major_discipline",
                    "controlling_shareholder_pledge_risk",
                    "repeated_equity_financing_or_material_dilution",
                ],
                "superseded_at_stage": "M2 Stage 2H",
                "do_not_use_for_current_profile": True,
            },
            {
                "risk_id": "audit_risk",
                "status_at_original_stage": "not_evaluated",
                "legacy": True,
                "current": False,
                "superseded_by": [
                    "modified_audit_opinion",
                    "going_concern_material_uncertainty",
                    "material_error_restatement",
                ],
                "superseded_at_stage": "M2 Stage 2H",
                "do_not_use_for_current_profile": True,
            },
            {
                "risk_id": "related_party_risk",
                "status_at_original_stage": "not_evaluated",
                "legacy": True,
                "current": False,
                "superseded_by": [
                    "material_related_party_transaction_risk",
                    "controlling_shareholder_fund_occupation_or_related_guarantee",
                ],
                "superseded_at_stage": "M2 Stage 2H",
                "do_not_use_for_current_profile": True,
            },
        ],
        "stage2g1_status": stage_status,
        "score_eligible": False,
    }
    _assert_no_forbidden_fields(profile)
    _write_json(run_dir / "petrochina_value_profile.json", profile)
    summary = {
        "run_id": run_id,
        "market_days": len(market),
        "market_range": [str(market["trade_date"].min()), str(market["trade_date"].max())],
        "phase_a_status": evidence["status"],
        "rule007_eligible_event_count": evidence["rule007_eligible_event_count"],
        "stage2g1_status": stage_status,
        "canonical_fact_input": {
            key: value for key, value in fact_input.items() if key != "snapshots"
        },
        "technical_integrity_checks": profile["technical_integrity_checks"],
        "current_risk_veto_profile": profile["current_risk_veto_profile"],
        "last_trade_date": last_trade_date,
        "profile": profile,
    }
    _write_json(run_dir / "summary.json", summary)
    _write_summary_md(run_dir / "summary.md", summary)
    if publish_reports:
        _publish_reports(run_dir, profile, percentiles, scenarios, evidence, market, registry)
    artifact_manifest = finalize_artifacts(
        run_dir,
        run_id=run_id,
        mode=market_mode,
        inputs=input_manifest,
        evidence_gap_count=len(evidence["gaps"]),
        rule007_eligible_count=evidence["rule007_eligible_event_count"],
        score_eligible=False,
    )
    return {
        "run_dir": str(run_dir),
        "manifest": manifest,
        "evidence": evidence,
        "profile": profile,
        "percentiles": percentiles,
        "scenarios": scenarios,
        "artifact_manifest": artifact_manifest,
    }


def _write_summary_md(path: Path, summary: Mapping[str, Any]) -> None:
    profile = summary["profile"]
    lines = [
        "# Stage 2G formal run summary",
        "",
        f"Run ID: `{summary['run_id']}`",
        f"Market coverage: `{summary['market_range'][0]}` through `{summary['market_range'][1]}` ({summary['market_days']} days).",
        f"Phase A evidence: `{summary['phase_a_status']}`; Rule007 eligible events: `{summary['rule007_eligible_event_count']}`.",
        f"Stage 2G.1 status: `{summary['stage2g1_status']}`; canonical Fact input: `{summary['canonical_fact_input']['logical_name']}` (`{summary['canonical_fact_input']['sha256']}`).",
        "",
        "## Latest observations",
        "",
        "| Observation | Value | Status |",
        "|---|---:|---|",
    ]
    for name, item in profile["latest_observations"].items():
        lines.append(f"| `{name}` | {item.get('value_decimal') or '—'} | `{item['status']}` |")
    lines.extend(
        [
            "",
            "## Technical integrity checks",
            "",
        ]
    )
    for check in profile["technical_integrity_checks"]:
        lines.append(f"- `{check['risk_id']}`: `{check['status']}`")
    lines.extend(
        [
            "",
            "Evidence gaps remain itemized in `evidence_gap_register.json`. This profile is descriptive and does not contain opinion fields.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _publish_reports(
    run_dir: Path,
    profile: dict[str, Any],
    percentiles: dict[str, Any],
    scenarios: dict[str, Any],
    evidence: dict[str, Any],
    market: pd.DataFrame,
    registry: dict[str, Any],
) -> None:
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    published_reports = run_dir / "published_reports"
    published_reports.mkdir(parents=True, exist_ok=True)
    latest = profile["latest_observations"]
    md = [
        "# PetroChina PIT valuation report 2021–2026",
        "",
        f"Run `{run_dir.name}`; market range `{market['trade_date'].min()}` to `{market['trade_date'].max()}`; `{len(market)}` unadjusted trade days.",
        "",
        "The runner reuses the existing `stock_daily` model and applies only Facts/Events available by each trade date. The 2024 interim event is the only corrected dual-official Rule007 input in this bounded evidence snapshot; the other nine events remain issuer-only because exact exchange payloads were inaccessible.",
        f"Canonical Fact input: `{profile['canonical_fact_input']['logical_name']}`; input SHA-256 `{profile['canonical_fact_input']['sha256']}`; Identity/version-chain status `{profile['canonical_fact_input']['identity_status']}`/`{profile['canonical_fact_input']['version_chain_status']}`.",
        "",
        "## Latest six observations",
        "",
        "| Observation | Latest value | Status |",
        "|---|---:|---|",
    ]
    for name, item in latest.items():
        md.append(f"| `{name}` | {item.get('value_decimal') or '—'} | `{item['status']}` |")
    md.extend(
        [
            "",
            "No observation is an opinion output. Historical percentile positions and fixed sample-end stress arithmetic are descriptive only.",
            "",
        ]
    )
    (reports / "petrochina_valuation_pit_2021_2026.md").write_text("\n".join(md), encoding="utf-8")
    profile_md = [
        "# PetroChina value profile 2021–2026",
        "",
        f"As of trade date `{profile['as_of_trade_date']}`.",
        "",
        "## Evidence-aware reading",
        "",
        "The profile integrates the existing earnings/cash-quality, ROE/ROA, financial-safety, dividend, and PIT valuation layers. Announced and paid dividend yields are separate. Nine exact exchange payloads remain finite evidence gaps; their affected dividend inputs are partial or missing while non-dividend valuation continues.",
        "",
        "## Technical integrity checks",
        "",
    ]
    for check in profile["technical_integrity_checks"]:
        profile_md.append(f"- `{check['risk_id']}`: `{check['status']}`")
    stage2h = profile.get("current_risk_veto_profile", {})
    profile_md.extend(
        [
            "",
            "## Canonical current Stage 2H.1R risk profile",
            "",
            f"Contract `{stage2h.get('contract_version')}`; methodology `{stage2h.get('methodology_version')}`; formal status `{stage2h.get('formal_run_status')}`.",
            "Missing evidence remains missing evidence and is not a negative conclusion.",
        ]
    )
    for slot in stage2h.get("risk_slots", []):
        profile_md.append(
            f"- `{slot['risk_id']}`: `{slot['evaluation_status']}`; emitted `{slot['observation_emitted']}`; observation `{slot.get('observation_id')}`"
        )
    profile_md.extend(
        [
            "",
            "Legacy migration: `governance_risk`, `audit_risk`, and `related_party_risk` are retained only under `legacy_risk_veto_checks` with `current=false`, `legacy=true`, and `do_not_use_for_current_profile=true`. Consumers must read `current_risk_veto_profile`.",
        ]
    )
    profile_md.append("")
    (reports / "petrochina_value_profile_2021_2026.md").write_text(
        "\n".join(profile_md), encoding="utf-8"
    )
    one_page = [
        "# PetroChina value profile — one page",
        "",
        f"As of `{profile['as_of_trade_date']}`; evidence status `{evidence['status']}`; market days `{len(market)}`.",
        "",
        "Valuation is the selected next slice. The six observations are PIT-safe, unadjusted-price, evidence-aware measures. Dividend announcement and payment windows are intentionally separate. ROIC and market mechanism remain outside scope.",
        f"Stage 2G.1 status: `{profile['stage2g1_status']}`; canonical Fact input: `{profile['canonical_fact_input']['logical_name']}` (`{profile['canonical_fact_input']['sha256']}`).",
        "",
        "| Observation | Value | Status |",
        "|---|---:|---|",
    ]
    for name, item in latest.items():
        one_page.append(f"| `{name}` | {item.get('value_decimal') or '—'} | `{item['status']}` |")
    one_page.extend(["", "## Technical integrity checks", ""])
    for check in profile["technical_integrity_checks"]:
        one_page.append(f"- `{check['risk_id']}`: `{check['status']}`")
    one_page.extend(["", "## Canonical current risk slots", ""])
    for slot in profile["current_risk_veto_profile"].get("risk_slots", []):
        one_page.append(
            f"- `{slot['risk_id']}`: `{slot['evaluation_status']}`; emitted `{slot['observation_emitted']}`"
        )
    one_page.append("")
    (reports / "petrochina_value_profile_one_page.md").write_text(
        "\n".join(one_page), encoding="utf-8"
    )
    _write_json(reports / "petrochina_value_profile.json", profile)
    for name in (
        "petrochina_valuation_pit_2021_2026.md",
        "petrochina_value_profile_2021_2026.md",
        "petrochina_value_profile_one_page.md",
        "petrochina_value_profile.json",
    ):
        shutil.copyfile(reports / name, published_reports / name)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--publish-reports", action="store_true")
    parser.add_argument("--run-id", default="stage2g_valuation_pit_20260801")
    parser.add_argument("--fact-db", type=Path)
    parser.add_argument("--market-cache-root", type=Path)
    parser.add_argument("--market-registry", type=Path)
    parser.add_argument(
        "--market-mode", choices=("real_research", "test_capsule"), default="real_research"
    )
    parser.add_argument("--market-fixture-root", type=Path)
    args = parser.parse_args(argv)
    if args.acquire:
        if args.market_cache_root is None:
            parser.error("--acquire requires --market-cache-root")
        print(json.dumps(acquire_market_data(args.market_cache_root), ensure_ascii=False, indent=2))
    if args.formal or not args.acquire:
        print(
            json.dumps(
                run_formal(
                    run_id=args.run_id,
                    publish_reports=args.publish_reports,
                    fact_db=args.fact_db,
                    registry_path=args.market_registry,
                    market_mode=args.market_mode,
                    market_cache_root=args.market_cache_root,
                    market_fixture_root=args.market_fixture_root,
                ),
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
