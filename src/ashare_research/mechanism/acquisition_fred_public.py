"""No-credential, raw-byte bounded transport for FRED's Brent CSV distribution."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

FRED_GRAPH_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = "DCOILBRENTEU"
FRED_SERIES_NAME = "Europe Brent Spot Price FOB"
FRED_UNDERLYING_SOURCE = "U.S. Energy Information Administration"
FRED_PUBLISHER = "Federal Reserve Bank of St. Louis FRED"
FRED_FREQUENCY = "daily"
FRED_UNIT = "USD/barrel"
HOLDOUT_START = date(2023, 1, 1)

STATUS_ACQUIRED = "M3_OIL_CONTROL_V3_ACQUIRED"
STATUS_NOT_BOUNDED = "FRED_PUBLIC_CSV_BOUNDED_TRANSPORT_NOT_PROVEN"
STATUS_WRONG_SERIES = "OIL_SOURCE_IDENTITY_NOT_PROVEN"
STATUS_INVALID_NUMERIC = "OIL_INVALID_NUMERIC_OBSERVATION"
STATUS_DUPLICATE = "OIL_DUPLICATE_OBSERVATION_DATE"
STATUS_REQUEST_UNBOUNDED = "FRED_BOUNDED_REQUEST_REQUIRED"
STATUS_RAW_HOLDOUT = "FRED_PUBLIC_CSV_HOLDOUT_CONTENT_REJECTED"

ENDPOINT_TEMPLATE = f"{FRED_GRAPH_CSV_URL}?id={FRED_SERIES}&cosd=<START>&coed=<END>"
HttpGet = Callable[..., bytes]
_DATE_RE = re.compile(rb"(?<!\d)(20\d{2})[-/.](\d{2})[-/.](\d{2})(?!\d)")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_fred_bounds(start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Require an explicit development-only server-side window."""
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


def _raw_dates(raw: bytes) -> list[pd.Timestamp]:
    dates: list[pd.Timestamp] = []
    for match in _DATE_RE.finditer(raw):
        value = f"{match.group(1).decode()}-{match.group(2).decode()}-{match.group(3).decode()}"
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.notna(parsed):
            dates.append(parsed.normalize())
    return dates


def prove_bounded_raw_response(raw: bytes, *, end: str) -> dict[str, Any]:
    """Prove the original response bytes contain no holdout date before parsing/filtering."""
    _, end_ts = validate_fred_bounds("1900-01-01", end)
    dates = _raw_dates(raw)
    if not dates:
        raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: no observation dates in raw bytes")
    maximum = max(dates)
    if maximum >= pd.Timestamp(HOLDOUT_START) or maximum > end_ts:
        raise Stage3BContractError(
            STATUS_RAW_HOLDOUT if maximum >= pd.Timestamp(HOLDOUT_START) else STATUS_NOT_BOUNDED
        )
    return {
        "raw_date_scan": "PASSED",
        "raw_observation_date_min": min(dates).date().isoformat(),
        "raw_observation_date_max": maximum.date().isoformat(),
        "raw_date_tokens": len(dates),
        "raw_sha256": _sha256(raw),
    }


def parse_fred_csv_bytes(raw: bytes, *, start: str, end: str) -> pd.DataFrame:
    """Validate FRED CSV identity and values; missing ``.``/blank values remain gaps."""
    start_ts, end_ts = validate_fred_bounds(start, end)
    proof = prove_bounded_raw_response(raw, end=end)
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: invalid CSV bytes") from exc
    if (
        not rows
        or len(rows[0]) != 2
        or rows[0][0].strip().lower() not in {"date", "observation_date"}
        or rows[0][1].strip() != FRED_SERIES
    ):
        raise Stage3BContractError(STATUS_WRONG_SERIES)
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        if len(row) != 2:
            raise Stage3BContractError(f"{STATUS_INVALID_NUMERIC}: malformed CSV row")
        observation_date, value = row[0].strip(), row[1].strip()
        parsed_date = pd.to_datetime(observation_date, errors="coerce")
        if pd.isna(parsed_date) or parsed_date < start_ts or parsed_date > end_ts:
            raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: invalid observation date")
        if value in {"", "."}:
            continue
        price = pd.to_numeric(value, errors="coerce")
        if pd.isna(price) or float(price) <= 0:
            raise Stage3BContractError(STATUS_INVALID_NUMERIC)
        records.append({"observation_date": parsed_date.normalize(), "price": float(price)})
    frame = pd.DataFrame(records, columns=["observation_date", "price"])
    if frame.empty:
        raise Stage3BContractError(f"{STATUS_INVALID_NUMERIC}: no valid observation")
    if frame["observation_date"].duplicated().any():
        raise DuplicateKeyError(STATUS_DUPLICATE)
    frame = frame.sort_values("observation_date", kind="mergesort").reset_index(drop=True)
    frame["series_id"] = FRED_SERIES
    frame["source_name"] = FRED_SERIES_NAME
    frame["publisher"] = FRED_PUBLISHER
    frame["underlying_source"] = FRED_UNDERLYING_SOURCE
    frame["frequency"] = FRED_FREQUENCY
    frame["unit"] = FRED_UNIT
    frame["raw_sha256"] = proof["raw_sha256"]
    frame["schema_version"] = "m3_stage3br4_oil_v3"
    frame["quality_status"] = "VALID_DEVELOPMENT_OBSERVATION"
    return frame


def _default_http_get(url: str, *, params: dict[str, Any]) -> bytes:
    import requests

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return bytes(response.content)


def acquire_fred_bounded(
    external_root: Path,
    *,
    start: str | None = None,
    end: str | None = None,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    """Fetch one bounded FRED response, validate raw bytes, and cache it immutably."""
    start_ts, end_ts = validate_fred_bounds(start, end)
    fetch = http_get or _default_http_get
    raw = fetch(
        FRED_GRAPH_CSV_URL,
        params={
            "id": FRED_SERIES,
            "cosd": start_ts.date().isoformat(),
            "coed": end_ts.date().isoformat(),
        },
    )
    if not isinstance(raw, bytes):
        raise Stage3BContractError(f"{STATUS_NOT_BOUNDED}: transport did not return raw bytes")
    parsed = parse_fred_csv_bytes(
        raw, start=start_ts.date().isoformat(), end=end_ts.date().isoformat()
    )
    raw_dir = external_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / "fred_DCOILBRENTEU.csv"
    if destination.exists() and destination.read_bytes() != raw:
        raise Stage3BContractError("immutable raw cache conflict")
    if not destination.exists():
        destination.write_bytes(raw)
    return {
        "status": STATUS_ACQUIRED,
        "series_id": FRED_SERIES,
        "source_name": FRED_SERIES_NAME,
        "underlying_source": FRED_UNDERLYING_SOURCE,
        "transport": "FRED_PUBLIC_GRAPH_CSV",
        "requested_start": start_ts.date().isoformat(),
        "requested_end": end_ts.date().isoformat(),
        "bounded_proof": prove_bounded_raw_response(raw, end=end_ts.date().isoformat()),
        "rows": int(len(parsed)),
        "raw_sha256": _sha256(raw),
        "raw_file": destination.as_posix(),
    }


def normalize_fred(raw_file: Path, output_file: Path, *, start: str, end: str) -> dict[str, Any]:
    """Normalize an already cached raw response without another network request."""
    raw = raw_file.read_bytes()
    frame = parse_fred_csv_bytes(raw, start=start, end=end)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_file, index=False, lineterminator="\n")
    return {"status": "NORMALIZED", "rows": int(len(frame)), "raw_sha256": _sha256(raw)}
