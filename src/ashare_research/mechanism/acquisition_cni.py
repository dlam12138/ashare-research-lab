"""Bounded official CNI transport for the pre-outcome 399439 industry control."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

CNI_INDEX_CODE = "399439"
CNI_INDEX_NAME = "CNI Oil & Gas Index"
CNI_INDEX_NAME_ZH = "国证石油天然气指数"
CNI_SHORT_NAME_ZH = "国证油气"
CNI_PUBLISHER = "Shenzhen Securities Information Co., Ltd. / CNI"
CNI_PUBLICATION_DATE = "2014-12-30"
CNI_ENDPOINT = "http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
HOLDOUT_START = date(2023, 1, 1)

STATUS_ACQUIRED = "M3_CNI_OIL_GAS_INDUSTRY_CONTROL_V2_ACQUIRED"
STATUS_WRONG_IDENTITY = "CNI_399439_IDENTITY_NOT_PROVEN"
STATUS_NOT_BOUNDED = "CNI_399439_BOUNDED_TRANSPORT_NOT_PROVEN"
STATUS_RAW_HOLDOUT = "CNI_399439_RAW_HOLDOUT_CONTENT_REJECTED"
STATUS_REQUEST_UNBOUNDED = "CNI_BOUNDED_REQUEST_REQUIRED"
STATUS_INVALID_NUMERIC = "INDUSTRY_INVALID_NUMERIC_OBSERVATION"
STATUS_DUPLICATE = "INDUSTRY_DUPLICATE_OBSERVATION_DATE"
STATUS_SCHEMA = "CNI_RESPONSE_SCHEMA_INVALID"
CNI_STATUS_OK = "INDUSTRY_ROW_OK"
CNI_STATUS_DATA_GAP = "INDUSTRY_ROW_INVALID_DATA_GAP"
CNI_STATUS_NO_PREVIOUS = "INDUSTRY_ROW_NO_PREVIOUS_VALID"

HttpGet = Callable[..., bytes]
_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-/.年](\d{2})[-/.月](\d{2})日?(?!\d)")


def assert_cni_identity(index_code: str, *, expected: str = CNI_INDEX_CODE) -> None:
    if str(index_code).strip() != expected:
        raise Stage3BContractError(STATUS_WRONG_IDENTITY)


def validate_cni_bounds(start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    if not start or not end:
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED)
    try:
        start_ts = pd.Timestamp(start).normalize()
        end_ts = pd.Timestamp(end).normalize()
    except Exception as exc:  # noqa: BLE001
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED) from exc
    if start_ts > end_ts or end_ts >= pd.Timestamp(HOLDOUT_START):
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED)
    return start_ts, end_ts


def inspect_akshare_cni_source(source_text: str | None = None) -> dict[str, Any]:
    """Record the local adapter's transport behavior before any CNI data request."""
    if source_text is None:
        import akshare

        source_text = inspect.getsource(akshare.index_hist_cni)
    required = all(
        token in source_text
        for token in ("startDate", "endDate", "indexCode", "getIndexDailyDataWithDataFormat")
    )
    return {
        "package": "akshare",
        "function": "index_hist_cni",
        "source_inspected": True,
        "underlying_endpoint": CNI_ENDPOINT,
        "request_parameters": ["indexCode", "startDate", "endDate", "frequency"],
        "server_bounds_reach_endpoint": required,
        "pagination_behavior": "single_response",
        "local_filter_only": False,
        "inspection_status": "BOUNDED_ENDPOINT_PARAMETERS_CONFIRMED"
        if required
        else "SOURCE_INSPECTION_FAILED",
    }


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _raw_dates(raw: bytes) -> list[pd.Timestamp]:
    dates: list[pd.Timestamp] = []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gb18030", errors="replace")
    for match in _DATE_RE.finditer(text):
        value = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.notna(parsed):
            dates.append(parsed.normalize())
    return dates


def prove_cni_bounded_raw_response(raw: bytes, *, end: str) -> dict[str, Any]:
    _, end_ts = validate_cni_bounds("1900-01-01", end)
    dates = _raw_dates(raw)
    if not dates:
        raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: no date tokens in raw bytes")
    maximum = max(dates)
    if maximum >= pd.Timestamp(HOLDOUT_START):
        raise Stage3BContractError(STATUS_RAW_HOLDOUT)
    if maximum > end_ts:
        raise Stage3BContractError(STATUS_NOT_BOUNDED)
    return {
        "raw_date_scan": "PASSED",
        "raw_observation_date_min": min(dates).date().isoformat(),
        "raw_observation_date_max": maximum.date().isoformat(),
        "raw_date_tokens": len(dates),
        "raw_sha256": _sha256(raw),
    }


def _row_value(row: Any, index: int, keys: tuple[str, ...]) -> Any:
    if isinstance(row, list):
        return row[index] if len(row) > index else None
    if isinstance(row, dict):
        lowered = {str(k).lower(): v for k, v in row.items()}
        for key in keys:
            if key.lower() in lowered:
                return lowered[key.lower()]
    return None


def parse_cni_response_bytes(raw: bytes, *, index_code: str, start: str, end: str) -> pd.DataFrame:
    assert_cni_identity(index_code)
    start_ts, end_ts = validate_cni_bounds(start, end)
    proof = prove_cni_bounded_raw_response(raw, end=end)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Stage3BContractError(STATUS_SCHEMA) from exc
    rows = payload.get("data", {}).get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise Stage3BContractError(STATUS_SCHEMA)
    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows):
        raw_date = _row_value(row, 0, ("date", "日期", "trade_date"))
        raw_close = _row_value(row, 3, ("close", "收盘价", "收盘"))
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(parsed_date) or parsed_date < start_ts or parsed_date > end_ts:
            raise Stage3BContractError(STATUS_NOT_BOUNDED)
        if raw_close is None or str(raw_close).strip() in {"", ".", "-"}:
            continue
        close_text = str(raw_close).strip().replace(",", "")
        close = pd.to_numeric(close_text, errors="coerce")
        if pd.isna(close) or float(close) <= 0:
            raise Stage3BContractError(
                f"{STATUS_INVALID_NUMERIC}: row={row_number}; "
                f"row_length={len(row) if isinstance(row, list) else 'mapping'}; "
                f"close_type={type(raw_close).__name__}"
            )
        records.append({"trade_date": parsed_date.normalize(), "close": float(close)})
    frame = pd.DataFrame(records)
    if frame["trade_date"].duplicated().any():
        raise DuplicateKeyError(STATUS_DUPLICATE)
    frame = frame.sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    frame["index_code"] = CNI_INDEX_CODE
    frame["source_name"] = CNI_INDEX_NAME
    frame["publisher"] = CNI_PUBLISHER
    frame["raw_sha256"] = proof["raw_sha256"]
    frame["schema_version"] = "m3_stage3br4_cni_v2"
    frame["quality_status"] = "VALID_DEVELOPMENT_OBSERVATION"
    return frame


def _default_http_get(url: str, *, params: dict[str, Any]) -> bytes:
    import requests

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return bytes(response.content)


def acquire_cni_bounded(
    external_root: Path,
    *,
    start: str | None = None,
    end: str | None = None,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    """Acquire one raw, server-bounded CNI response after source inspection."""
    start_ts, end_ts = validate_cni_bounds(start, end)
    inspection = inspect_akshare_cni_source()
    if not inspection["server_bounds_reach_endpoint"]:
        raise Stage3BContractError(STATUS_NOT_BOUNDED)
    fetch = http_get or _default_http_get
    raw = fetch(
        CNI_ENDPOINT,
        params={
            "indexCode": CNI_INDEX_CODE,
            "startDate": start_ts.date().isoformat(),
            "endDate": end_ts.date().isoformat(),
            "frequency": "day",
        },
    )
    if not isinstance(raw, bytes):
        raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: transport did not return raw bytes")
    parsed = parse_cni_response_bytes(
        raw,
        index_code=CNI_INDEX_CODE,
        start=start_ts.date().isoformat(),
        end=end_ts.date().isoformat(),
    )
    raw_dir = external_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / "cni_399439_response.json"
    if destination.exists() and destination.read_bytes() != raw:
        raise Stage3BContractError("immutable raw cache conflict")
    if not destination.exists():
        destination.write_bytes(raw)
    return {
        "status": STATUS_ACQUIRED,
        "index_code": CNI_INDEX_CODE,
        "source_name": CNI_INDEX_NAME,
        "publisher": CNI_PUBLISHER,
        "transport": "CNI_OFFICIAL_BOUNDED_ENDPOINT",
        "requested_start": start_ts.date().isoformat(),
        "requested_end": end_ts.date().isoformat(),
        "source_inspection": inspection,
        "bounded_proof": prove_cni_bounded_raw_response(raw, end=end_ts.date().isoformat()),
        "rows": int(len(parsed)),
        "raw_sha256": _sha256(raw),
        "raw_file": destination.as_posix(),
    }


def normalize_cni(raw_file: Path, output_file: Path, *, start: str, end: str) -> dict[str, Any]:
    raw = raw_file.read_bytes()
    frame = parse_cni_response_bytes(raw, index_code=CNI_INDEX_CODE, start=start, end=end)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_file, index=False, lineterminator="\n")
    return {"status": "NORMALIZED", "rows": int(len(frame)), "raw_sha256": _sha256(raw)}


def build_cni_returns(closes: pd.DataFrame, a_share_calendar: pd.Series) -> pd.DataFrame:
    """Build simple close-to-close returns for one continuous CNI index identity."""
    required = {"trade_date", "index_code", "close"}
    missing = required - set(closes.columns)
    if missing:
        raise Stage3BContractError(f"CNI closes missing columns: {sorted(missing)}")
    frame = closes.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if (
        frame["trade_date"].isna().any()
        or frame["close"].isna().any()
        or frame["close"].le(0).any()
    ):
        raise Stage3BContractError(STATUS_INVALID_NUMERIC)
    if (frame["trade_date"] >= pd.Timestamp(HOLDOUT_START)).any():
        raise Stage3BContractError(STATUS_RAW_HOLDOUT)
    if set(frame["index_code"].astype(str)) != {CNI_INDEX_CODE}:
        raise Stage3BContractError(STATUS_WRONG_IDENTITY)
    if frame.duplicated(["index_code", "trade_date"]).any():
        raise DuplicateKeyError(STATUS_DUPLICATE)
    closes_by_date = frame.set_index("trade_date")["close"]
    calendar = (
        pd.Series(pd.to_datetime(a_share_calendar, errors="coerce"))
        .dropna()
        .drop_duplicates()
        .sort_values()
    )
    if (calendar >= pd.Timestamp(HOLDOUT_START)).any():
        raise Stage3BContractError(STATUS_RAW_HOLDOUT)
    previous_date: pd.Timestamp | None = None
    previous_close: float | None = None
    rows: list[dict[str, Any]] = []
    for trade_date in calendar:
        close = closes_by_date.get(trade_date)
        if close is None:
            status, value = CNI_STATUS_DATA_GAP, None
        elif previous_close is None:
            status, value = CNI_STATUS_NO_PREVIOUS, None
        else:
            status, value = CNI_STATUS_OK, float(close) / previous_close - 1.0
        rows.append(
            {
                "trade_date": trade_date.date().isoformat(),
                "index_code": CNI_INDEX_CODE,
                "close": float(close) if close is not None else None,
                "previous_trade_date": previous_date.date().isoformat()
                if previous_date is not None
                else None,
                "previous_close": previous_close,
                "industry_return": value,
                "alignment_status": status,
            }
        )
        if close is not None:
            previous_date, previous_close = trade_date, float(close)
    return pd.DataFrame(rows)
