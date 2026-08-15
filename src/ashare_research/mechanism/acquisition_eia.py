"""Bounded, holdout-safe EIA Open Data API v2 transport for the Brent oil control.

Stage 3B-R3 unblocks the Stage 3B-R2 oil gap by adding the EIA Open Data API v2 as the primary
bounded transport for Europe Brent Spot Price FOB (EIA ``RBRTE``). The API key is read only from the
process environment via ``os.environ.get("EIA_API_KEY")`` and is never persisted, logged, echoed, or
written to any manifest or report. The request is server-side bounded to ``2014-12-01`` (warm-up) ..
``2022-12-31`` (development) and never reads 2023+. The provider response is validated for series
identity, unit, frequency, and date bounds; a response that claims a date on or after 2023-01-01
fails closed with ``OIL_BOUNDED_RESPONSE_CONTRACT_VIOLATION``. Every exception and debug output
passes through secret redaction.

The transport is fully deterministic and testable offline: every HTTP call is routed through an
injectable ``http_get`` so the secret-redaction and bounded-acquisition tests never touch the
network and never use a real key.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

EIA_API_V2_BASE = "https://api.eia.gov/v2"
BOUNDED_START = "2014-12-01"
DEVELOPMENT_END = "2022-12-31"
HOLDOUT_START = "2023-01-01"

OIL_SERIES = "RBRTE"
OIL_SERIES_NAME = "Europe Brent Spot Price FOB"
# EIA v2 metadata reports the petroleum spot-price unit as "Dollars per Barrel".
OIL_SERIES_UNIT_TOKENS = ("dollars", "per barrel")

# Fail-closed status codes.
STATUS_ACQUIRED = "OIL_ACQUIRED"
STATUS_KEY_REQUIRED = "OIL_EIA_API_KEY_REQUIRED"
STATUS_REQUEST_UNBOUNDED = "OIL_EIA_REQUEST_UNBOUNDED"
STATUS_BOUNDED_RESPONSE_VIOLATION = "OIL_BOUNDED_RESPONSE_CONTRACT_VIOLATION"
STATUS_WRONG_SERIES = "OIL_EIA_WRONG_SERIES_IDENTITY"
STATUS_WRONG_UNIT = "OIL_EIA_WRONG_UNITS"
STATUS_DUPLICATE_DATE = "OIL_EIA_DUPLICATE_DATE"
STATUS_MALFORMED_NUMERIC = "OIL_EIA_MALFORMED_NUMERIC"
STATUS_TRANSPORT_ERROR = "OIL_EIA_TRANSPORT_ERROR"
STATUS_ROUTE_DISCOVERY_ERROR = "OIL_EIA_ROUTE_DISCOVERY_ERROR"

# Stable, secret-free endpoint template committed to manifests (never contains a key).
ENDPOINT_TEMPLATE_REDACTED = (
    "https://api.eia.gov/v2/<discovered-route>/data/?frequency=daily&start=2014-12-01"
    "&end=2022-12-31&api_key=<REDACTED>"
)

# The bounded metadata walk never descends more than this many category levels.
MAX_ROUTE_DISCOVERY_DEPTH = 4

SecretProvider = Callable[[], str | None]
HttpGet = Callable[..., dict[str, Any]]


def get_eia_api_key() -> str | None:
    """Return the EIA API key from the process environment, or ``None`` if absent/blank."""
    value = os.environ.get("EIA_API_KEY")
    if value is None or not value.strip():
        return None
    return value.strip()


def redact(text: str, secret: str | None) -> str:
    """Replace every occurrence of ``secret`` in ``text`` with a fixed redaction token."""
    if not secret:
        return text
    return text.replace(secret, "<REDACTED>")


def _redact_exception(exc: BaseException, secret: str | None) -> str:
    return redact(f"{type(exc).__name__}: {exc}", secret)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def discover_eia_route(
    http_get: HttpGet,
    key: str,
    *,
    base: str = EIA_API_V2_BASE,
    max_depth: int = MAX_ROUTE_DISCOVERY_DEPTH,
) -> dict[str, Any]:
    """Walk the official EIA v2 metadata tree to locate the RBRTE data route.

    The route is not hard-coded from memory; it is discovered from the live metadata tree so the
    series identity, name, and unit come from the official provider. A bounded breadth-first walk
    descends from the root category, following child ``id`` links, until a category response lists
    a series whose ``series_id`` contains ``RBRTE``. Returns the discovered data route path plus the
    official series metadata. Fails closed if the series is not found within ``max_depth``.
    """
    candidate_child = _find_rbrte_category_chain(http_get, key, base=base, max_depth=max_depth)
    if candidate_child is None:
        raise Stage3BContractError(STATUS_ROUTE_DISCOVERY_ERROR)

    # The category whose response contained the RBRTE series gives the data route and metadata.
    route, series_meta = candidate_child
    return {
        "data_route": f"{route}/data",
        "series_id": series_meta.get("series_id", ""),
        "series_name": series_meta.get("name", ""),
        "units": series_meta.get("units", ""),
        "frequency": str(series_meta.get("frequency", "")).lower(),
        "base": base,
    }


def _find_rbrte_category_chain(
    http_get: HttpGet, key: str, *, base: str, max_depth: int
) -> tuple[str, dict[str, Any]] | None:
    """Iterative bounded BFS over EIA v2 categories; return (route, metadata) when RBRTE is found.

    A category response carries either child ``categories`` (branch) or a ``series`` list (leaf). A
    leaf whose series list contains ``RBRTE`` names the data route. The walk is bounded by depth and
    never fetches the data series itself (only metadata), so no holdout value is read during
    discovery.
    """
    queue: deque[tuple[str, int]] = deque([("", 0)])
    while queue:
        endpoint, depth = queue.popleft()
        if depth > max_depth:
            continue
        url = f"{base}/{endpoint}" if endpoint else f"{base}/"
        try:
            payload = http_get(url, params={"api_key": key})
        except Exception as exc:  # noqa: BLE001 - a single metadata failure fails discovery closed
            raise Stage3BContractError(
                f"{STATUS_ROUTE_DISCOVERY_ERROR}: {_redact_exception(exc, key)}"
            ) from exc
        response = payload.get("response", {})
        series_list = response.get("series") or []
        for series in series_list:
            if str(series.get("series_id", "")).upper().find(OIL_SERIES) != -1:
                return endpoint, series
        for child in response.get("categories") or []:
            child_id = str(child.get("id", "")).strip()
            if child_id:
                queue.append((child_id if not endpoint else f"{endpoint}/{child_id}", depth + 1))
    return None


def validate_request_bounds(start: str, end: str) -> None:
    """Reject any request that is not server-side bounded to the development window."""
    if not end or not start:
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED)
    end_ts = pd.Timestamp(end)
    if end_ts >= pd.Timestamp(HOLDOUT_START):
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED)
    start_ts = pd.Timestamp(start)
    if start_ts > end_ts:
        raise Stage3BContractError(STATUS_REQUEST_UNBOUNDED)


def fetch_eia_bounded_data(
    key: str,
    route: dict[str, Any],
    http_get: HttpGet,
    *,
    start: str = BOUNDED_START,
    end: str = DEVELOPMENT_END,
) -> dict[str, Any]:
    """Issue the server-side bounded data request and return the raw provider payload."""
    try:
        validate_request_bounds(start, end)
    except Stage3BContractError as exc:
        raise Stage3BContractError(redact(str(exc), key)) from exc
    data_url = f"{route['base']}/{route['data_route']}"
    params = {
        "frequency": "daily",
        "data[0]": "value",
        "start": start,
        "end": end,
        "api_key": key,
    }
    try:
        payload = http_get(data_url, params=params)
    except Exception as exc:  # noqa: BLE001
        raise Stage3BContractError(
            f"{STATUS_TRANSPORT_ERROR}: {_redact_exception(exc, key)}"
        ) from exc
    return payload


def parse_eia_data_payload(payload: dict[str, Any], *, end: str = DEVELOPMENT_END) -> pd.DataFrame:
    """Convert a validated EIA v2 data payload into a canonical observation frame.

    Validates provider-claimed date bounds (a claim on or after 2023-01-01 fails closed), numeric
    well-formedness, and duplicate dates. Returns columns ``observation_date``, ``price``.
    """
    response = payload.get("response", {})
    rows = response.get("data") or []
    records: list[dict[str, Any]] = []
    for row in rows:
        period = str(row.get("period", "")).strip()
        value = row.get("value")
        if not period:
            raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: missing period")
        if value is None or str(value).strip() == "":
            raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: missing value on {period}")
        records.append({"observation_date": period, "price": value})
    if not records:
        raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: empty data payload")

    frame = pd.DataFrame(records)
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    if frame["observation_date"].isna().any():
        raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: invalid period")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    if frame["price"].isna().any():
        raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: non-numeric price")
    if frame["price"].le(0).any():
        raise Stage3BContractError(f"{STATUS_MALFORMED_NUMERIC}: non-positive price")
    if (frame["observation_date"] >= pd.Timestamp(HOLDOUT_START)).any():
        raise Stage3BContractError(STATUS_BOUNDED_RESPONSE_VIOLATION)
    if (frame["observation_date"] > pd.Timestamp(end)).any():
        raise Stage3BContractError(STATUS_BOUNDED_RESPONSE_VIOLATION)
    if frame["observation_date"].duplicated().any():
        raise DuplicateKeyError(STATUS_DUPLICATE_DATE)
    return frame[["observation_date", "price"]].sort_values("observation_date").reset_index(
        drop=True
    )


def validate_series_metadata(route: dict[str, Any]) -> None:
    """Reject a discovered route whose official series identity/unit is not RBRTE USD/barrel."""
    series_id = str(route.get("series_id", "")).upper()
    name = str(route.get("series_name", ""))
    units = str(route.get("units", ""))
    if OIL_SERIES not in series_id:
        raise Stage3BContractError(STATUS_WRONG_SERIES)
    if "brent" not in name.lower():
        raise Stage3BContractError(STATUS_WRONG_SERIES)
    unit_lower = units.lower()
    if not all(token in unit_lower for token in OIL_SERIES_UNIT_TOKENS):
        raise Stage3BContractError(STATUS_WRONG_UNIT)
    if str(route.get("frequency", "")).lower() not in {"daily", "1d", "d"}:
        raise Stage3BContractError(STATUS_WRONG_UNIT)


def acquire_oil_bounded(
    external_root: Path,
    *,
    http_get: HttpGet | None = None,
    key_provider: SecretProvider = get_eia_api_key,
) -> dict[str, Any]:
    """Run the bounded EIA acquisition and write the immutable raw observation CSV on success.

    When no API key is present, returns ``OIL_EIA_API_KEY_REQUIRED`` without writing any raw file
    and without any network call. When a key is present, discovers the official RBRTE route, issues
    a server-side bounded request, validates the response, and writes an immutable raw CSV under
    ``raw/`` with its SHA-256. The FRED secondary distribution is not part of this gate.
    """
    result: dict[str, Any] = {
        "status": STATUS_KEY_REQUIRED,
        "codes": [],
        "fetched_at": datetime.now(UTC).isoformat(),
        "holdout_read_performed": False,
        "raw_sha256": None,
        "ephemeral": None,
    }
    key = key_provider()
    if key is None:
        result["codes"].append(STATUS_KEY_REQUIRED)
        return result

    try:
        route = discover_eia_route(http_get or _requests_get, key)
        validate_series_metadata(route)
        payload = fetch_eia_bounded_data(key, route, http_get or _requests_get)
        frame = parse_eia_data_payload(payload)
    except Stage3BContractError as exc:
        result["status"] = redact(str(exc), key)
        result["codes"].append(redact(str(exc), key))
        return result
    except DuplicateKeyError:
        result["status"] = STATUS_DUPLICATE_DATE
        result["codes"].append(STATUS_DUPLICATE_DATE)
        return result

    raw_root = external_root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    raw = raw_root / "oil_brent_observations.csv"
    if raw.exists():
        raise Stage3BContractError("immutable oil raw path already exists; refuse to overwrite")
    payload = _csv_bytes(frame)
    raw.write_bytes(payload)
    result["status"] = STATUS_ACQUIRED
    result["raw_sha256"] = _sha256_bytes(payload)
    result["codes"].append(STATUS_ACQUIRED)
    result["rows"] = int(len(frame))
    result["first_observation"] = frame["observation_date"].min().strftime("%Y-%m-%d")
    result["last_observation"] = frame["observation_date"].max().strftime("%Y-%m-%d")
    return result


def _requests_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Default HTTP transport using ``requests``; raises on non-2xx or JSON decode failure."""
    import requests

    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        raise Stage3BContractError(f"EIA HTTP {response.status_code}")
    return json.loads(response.text)


def redacted_endpoint_template() -> str:
    """Return the stable, secret-free endpoint template for manifests."""
    return ENDPOINT_TEMPLATE_REDACTED
