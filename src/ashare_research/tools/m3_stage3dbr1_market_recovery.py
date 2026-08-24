"""Post-unseal Stage 3D-B-R1 market-universe recovery helpers.

This module is deliberately independent from the original Stage 3D-B adapters.  The
metadata path is safe to run before a new price byte is parsed; the price/proxy path is
exposed separately and delegates to the already frozen OOS proxy builder.  In particular,
missing provider files never remove a security from the denominator.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.proxy_v2 import TARGET_SYMBOL, classify_equity
from ashare_research.tools.m3_stage3db_oos_inputs import (
    HOLDOUT_END,
    HOLDOUT_START,
    WARMUP_START,
    build_market_ex_target_proxy_v2_oos,
)

RECOVERY_CLASS = "POST_UNSEAL_TECHNICAL_ADAPTER_RECOVERY"
MISSING_PROVIDER_DATA = "MISSING_PROVIDER_DATA"
ALREADY_ACQUIRED_REQUIRED = "ALREADY_ACQUIRED_REQUIRED"
TRUE_REQUIRED_MISSING = "TRUE_REQUIRED_MISSING"
TARGET_EXCLUDED = "TARGET_EXCLUDED"
METADATA_INSUFFICIENT = "METADATA_INSUFFICIENT"

_CODE_ALIASES = ("证券代码", "公司代码", "股票代码", "代码", "symbol", "code")
_LISTING_ALIASES = ("上市日期", "首次上市日期", "listing_date")
_DELISTING_ALIASES = (
    "退市日期",
    "终止上市日期",
    # AKShare's stock_info_sh_delist endpoint calls this boundary
    # "暂停上市日期".  It is accepted only for that explicitly bound source.
    "暂停上市日期",
    "delisting_date",
)


class RecoveryMetadataError(ValueError):
    """Fail-closed metadata error carrying a machine-readable recovery code."""


def _error(code: str, detail: str) -> RecoveryMetadataError:
    return RecoveryMetadataError(f"{code}:{detail}")


def _read_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="gb18030", newline="") as handle:
            header = next(csv.reader(handle))
    if not header or any(not str(column).strip() for column in header):
        raise _error("M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS", str(path))
    if len(set(header)) != len(header):
        raise _error("M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS", f"duplicate headers: {path}")
    return [str(column).strip() for column in header]


def _pick_column(
    columns: Iterable[str], aliases: tuple[str, ...], semantic: str, source: str
) -> str:
    matches = [column for column in columns if column in aliases]
    if len(matches) != 1:
        raise _error(
            "M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS",
            f"{source}:{semantic}:matches={matches}",
        )
    return matches[0]


def bind_metadata_schema(path: str | Path, *, source_kind: str) -> dict[str, Any]:
    """Bind metadata semantics to actual CSV headers; never use positional columns."""

    source = Path(path)
    columns = _read_header(source)
    code = _pick_column(columns, _CODE_ALIASES, "security_code_column", str(source))
    listing = _pick_column(columns, _LISTING_ALIASES, "listing_date_column", str(source))
    binding: dict[str, Any] = {
        "source_file": source.name,
        "source_kind": source_kind,
        "actual_column_names": columns,
        "security_code_column": code,
        "listing_date_column": listing,
    }
    if source_kind == "delisted_history":
        binding["delisting_date_column"] = _pick_column(
            columns, _DELISTING_ALIASES, "delisting_date_column", str(source)
        )
    return binding


def _encoding(path: Path) -> str:
    try:
        path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return "gb18030"
    return "utf-8-sig"


def _load_bound_frame(path: Path, binding: dict[str, Any]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, encoding=_encoding(path))
    expected = set(binding["actual_column_names"])
    if set(frame.columns) != expected:
        raise _error("M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS", f"header changed: {path}")
    return frame


def _normalise_code(value: Any) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.zfill(6)


def _normalise_date(value: Any) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    return None if pd.isna(parsed) else pd.Timestamp(parsed).normalize()


def _source_rows(frame: pd.DataFrame, binding: dict[str, Any], source: str) -> list[dict[str, Any]]:
    code_col = binding["security_code_column"]
    listing_col = binding["listing_date_column"]
    delisting_col = binding.get("delisting_date_column")
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        code = _normalise_code(row.get(code_col))
        if not code:
            raise _error("M3_STAGE3DBR1_METADATA_INSUFFICIENT", f"missing code:{source}")
        rows.append(
            {
                "symbol": f"{code}.SH",
                "code": code,
                "listing_date": _normalise_date(row.get(listing_col)),
                "delisting_date": _normalise_date(row.get(delisting_col))
                if delisting_col
                else None,
                "metadata_provenance": source,
            }
        )
    return rows


def _as_bound_source(
    source: Any, *, source_kind: str, label: str
) -> tuple[str, pd.DataFrame, dict[str, Any]]:
    if isinstance(source, str | Path):
        path = Path(source)
        binding = bind_metadata_schema(path, source_kind=source_kind)
        return label or path.name, _load_bound_frame(path, binding), binding
    if not isinstance(source, pd.DataFrame):
        raise TypeError("metadata source must be a path or DataFrame")
    columns = [str(column) for column in source.columns]
    binding = {
        "source_file": label,
        "source_kind": source_kind,
        "actual_column_names": columns,
        "security_code_column": _pick_column(columns, _CODE_ALIASES, "security_code_column", label),
        "listing_date_column": _pick_column(
            columns, _LISTING_ALIASES, "listing_date_column", label
        ),
    }
    if source_kind == "delisted_history":
        binding["delisting_date_column"] = _pick_column(
            columns, _DELISTING_ALIASES, "delisting_date_column", label
        )
    return label, source.copy(), binding


def _iter_current_sources(sources: Any) -> list[tuple[str, Any]]:
    if isinstance(sources, Mapping):
        return [(str(label), source) for label, source in sources.items()]
    if isinstance(sources, str | Path | pd.DataFrame):
        return [(str(sources) if not isinstance(sources, pd.DataFrame) else "current", sources)]
    return [(f"current_{index}", source) for index, source in enumerate(sources)]


def build_unified_security_master(
    current_sources: Mapping[str, Any] | Iterable[Any],
    delisted_source: Any,
) -> pd.DataFrame:
    """Build CURRENT_LISTED UNION DELISTED_HISTORY with conflict fail-closed."""

    records: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for label, source in _iter_current_sources(current_sources):
        name, frame, binding = _as_bound_source(source, source_kind="current_master", label=label)
        bindings.append(binding)
        records.extend(_source_rows(frame, binding, name))
    name, frame, binding = _as_bound_source(
        delisted_source, source_kind="delisted_history", label="sh_delist.csv"
    )
    bindings.append(binding)
    records.extend(_source_rows(frame, binding, name))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["symbol"], []).append(record)
    output: list[dict[str, Any]] = []
    for symbol, candidates in sorted(grouped.items()):
        listing_values = {
            value for value in (item["listing_date"] for item in candidates) if value is not None
        }
        delisting_values = {
            value for value in (item["delisting_date"] for item in candidates) if value is not None
        }
        if len(listing_values) > 1 or len(delisting_values) > 1:
            raise _error(
                "M3_STAGE3DBR1_SECURITY_MASTER_CONFLICT",
                f"{symbol}:listing={sorted(map(str, listing_values))}:"
                f"delisting={sorted(map(str, delisting_values))}",
            )
        listing = next(iter(listing_values), None)
        delisting = next(iter(delisting_values), None)
        if listing is None:
            raise _error("M3_STAGE3DBR1_METADATA_INSUFFICIENT", f"{symbol}:listing_date")
        if delisting is not None and delisting < listing:
            raise _error(
                "M3_STAGE3DBR1_SECURITY_MASTER_CONFLICT", f"{symbol}:delisting_before_listing"
            )
        code = symbol.removesuffix(".SH")
        output.append(
            {
                "symbol": symbol,
                "classification": classify_equity(code),
                "listing_date": listing,
                "delisting_date": delisting,
                "metadata_provenance": "|".join(
                    sorted({str(item["metadata_provenance"]) for item in candidates})
                ),
            }
        )
    return pd.DataFrame(
        output,
        columns=[
            "symbol",
            "classification",
            "listing_date",
            "delisting_date",
            "metadata_provenance",
        ],
    )


def _calendar(values: Iterable[Any]) -> pd.DatetimeIndex:
    dates = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .dropna()
        .unique()
        .sort_values()
    )
    if len(dates) == 0 or dates.min() < WARMUP_START or dates.max() > HOLDOUT_END:
        raise _error("M3_STAGE3DBR1_CALENDAR_ENVELOPE_FAILURE", "calendar outside frozen envelope")
    return dates


def _expected_mask(
    row: pd.Series, analysis_dates: pd.DatetimeIndex, previous: pd.Series
) -> pd.Series:
    if row["classification"] != "A_SHARE_COMMON" or row["symbol"] == TARGET_SYMBOL:
        return pd.Series(False, index=analysis_dates)
    listing = _normalise_date(row["listing_date"])
    if listing is None:
        raise _error("M3_STAGE3DBR1_METADATA_INSUFFICIENT", f"{row['symbol']}:listing_date")
    delisting = _normalise_date(row.get("delisting_date"))
    return (listing <= previous) & (
        pd.Series(True, index=analysis_dates) if delisting is None else (delisting > previous)
    )


def classify_holdout_ever_eligible(master: pd.DataFrame, calendar: Iterable[Any]) -> pd.DataFrame:
    """Mark securities eligible on at least one formal holdout date using t-1."""

    detail = build_holdout_membership(master, calendar)
    ever = detail.groupby("symbol", sort=False)["in_expected_universe"].any()
    output = master.copy()
    output["ever_eligible_in_holdout"] = output["symbol"].map(ever).fillna(False).astype(bool)
    output["metadata_status"] = "OK"
    return output


def build_holdout_membership(master: pd.DataFrame, calendar: Iterable[Any]) -> pd.DataFrame:
    """Return exact date-level expected membership for formal holdout dates."""

    required = {"symbol", "classification", "listing_date", "delisting_date"}
    if required - set(master.columns):
        raise _error("M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS", "master columns")
    dates = _calendar(calendar)
    analysis_dates = dates[(dates >= HOLDOUT_START) & (dates <= HOLDOUT_END)]
    positions = [dates.get_loc(date) for date in analysis_dates]
    previous = pd.Series(
        [dates[position - 1] if position > 0 else pd.NaT for position in positions],
        index=analysis_dates,
    )
    rows: list[dict[str, Any]] = []
    for _, row in master.iterrows():
        mask = _expected_mask(row, analysis_dates, previous)
        for date, expected in mask.items():
            rows.append(
                {
                    "trade_date": date,
                    "symbol": row["symbol"],
                    "classification": row["classification"],
                    "in_expected_universe": bool(expected),
                }
            )
    return pd.DataFrame(rows)


def build_required_series_inventory(
    master: pd.DataFrame,
    calendar: Iterable[Any],
    available_symbols: Iterable[str],
) -> pd.DataFrame:
    """Freeze required market series from membership, then attach file status."""

    marked = classify_holdout_ever_eligible(master, calendar)
    available = {str(symbol).strip() for symbol in available_symbols}
    required = marked.loc[
        marked["ever_eligible_in_holdout"]
        & marked["symbol"].ne(TARGET_SYMBOL)
        & marked["classification"].eq("A_SHARE_COMMON")
    ].copy()
    required["series_status"] = required["symbol"].map(
        lambda symbol: ALREADY_ACQUIRED_REQUIRED if symbol in available else TRUE_REQUIRED_MISSING
    )
    return required.reset_index(drop=True)


def classify_original_failures(
    failed_symbols: Iterable[str],
    marked_master: pd.DataFrame,
) -> dict[str, list[str]]:
    """Classify historical failed requests without inspecting price bytes."""

    failed = {str(symbol).strip().zfill(6) for symbol in failed_symbols}
    lookup = {
        str(row.symbol).removesuffix(".SH"): row for row in marked_master.itertuples(index=False)
    }
    result = {
        "failed_but_never_eligible": [],
        "failed_and_ever_eligible": [],
        "failed_metadata_insufficient": [],
    }
    for code in sorted(failed):
        row = lookup.get(code)
        if row is None or getattr(row, "metadata_status", "OK") == METADATA_INSUFFICIENT:
            result["failed_metadata_insufficient"].append(code)
        elif bool(getattr(row, "ever_eligible_in_holdout", False)):
            result["failed_and_ever_eligible"].append(code)
        else:
            result["failed_but_never_eligible"].append(code)
    return result


def build_market_proxy_recovery(
    closes: pd.DataFrame,
    master: pd.DataFrame,
    calendar: Iterable[Any],
    *,
    coverage_gate: float = 0.99,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Delegate real/synthetic proxy construction to the frozen OOS semantics."""

    return build_market_ex_target_proxy_v2_oos(
        closes, master, pd.Series(list(calendar)), coverage_gate=coverage_gate
    )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_capsule_file(
    base_root: str | Path, overlay_root: str | Path, relative_path: str
) -> dict[str, Any]:
    """Resolve BASE + OVERLAY with immutable-base precedence and conflict detection."""

    base = Path(base_root) / relative_path
    overlay = Path(overlay_root) / relative_path
    base_exists, overlay_exists = base.is_file(), overlay.is_file()
    if not base_exists and not overlay_exists:
        return {"source": "MISSING", "path": relative_path, "sha256": None}
    if base_exists and overlay_exists:
        base_sha, overlay_sha = sha256_file(base), sha256_file(overlay)
        if base_sha != overlay_sha:
            raise _error("M3_STAGE3DBR1_BASE_OVERLAY_CONFLICT", relative_path)
        return {"source": "BASE", "path": relative_path, "sha256": base_sha}
    path = base if base_exists else overlay
    return {
        "source": "BASE" if base_exists else "OVERLAY",
        "path": relative_path,
        "sha256": sha256_file(path),
    }


def write_once_overlay(path: str | Path, raw: bytes) -> str:
    """Write a recovery file once; never overwrite a prior overlay response."""

    target = Path(path)
    digest = hashlib.sha256(raw).hexdigest()
    if target.exists():
        if target.read_bytes() != raw:
            raise _error("M3_STAGE3DBR1_OVERLAY_IMMUTABLE_CONFLICT", str(target))
        return digest
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return digest


def repository_relative_digest(
    root: str | Path, relative_paths: Iterable[str]
) -> tuple[str, dict[str, Any]]:
    """Digest source/test artifacts using repository-relative logical paths only."""

    root_path = Path(root).resolve()
    source_hashes: dict[str, str] = {}
    for relative in sorted(set(relative_paths)):
        path = root_path / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        source_hashes[relative.replace("\\", "/")] = sha256_file(path)
    payload = {
        "digest_algorithm": "M3_REPOSITORY_RELATIVE_DIGEST_V2",
        "source_hashes": source_hashes,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest(), payload
