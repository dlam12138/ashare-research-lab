"""Shenwan petroleum & petrochemicals industry-control source-resolution ladder for M3 Stage 3B-R3.

Stage 3B-R2 confirmed the known SWS daily-endpoint families ignore date bounds and return full
history through the current year, so any download reads the sealed holdout. Stage 3B-R3 does not
re-run that same endpoint; instead it resolves the industry source through an ordered ladder:

  Route A - an official SWS bounded transport (historical export / download / pagination /
            date-query / per-period endpoint with a server-side bound <= 2022-12-31).
  Route B - an existing development-only official capsule in an authorized external root.
  Route C - a user-provided official development capsule (only <= 2022-12-31, immutable, hashed).
  Route D - a same-series third-party transport (last resort, only if series identity and
            source lineage are provable; never an industry ETF / CSI energy / THS sector).

The frozen industry identity is the Shenwan Petroleum and Petrochemicals Industry Price Index:
``801016`` (SW_2014, through 2021-12-10) and ``801960`` (SW_2021, from 2021-12-13). Returns are
simple within-regime price returns; the two index levels are never spliced. No holdout (2023+) value
is ever read, parsed, or stored.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

HOLDOUT_START = "2023-01-01"
DEVELOPMENT_END = "2022-12-31"

REGIME_1_SYMBOL = "801016"
REGIME_1_TAXONOMY = "SW_2014"
REGIME_2_SYMBOL = "801960"
REGIME_2_TAXONOMY = "SW_2021"

# Official SWS endpoint families investigated (source inspection of the current AKShare adapter).
# None accepts server-side date bounds; each returns the full daily/minute series through the
# current year, so any download reads the sealed holdout.
INVESTIGATED_SWS_ENDPOINT_FAMILIES = [
    {
        "family": "index_publish/trend/",
        "role": "DAILY_HISTORY",
        "adapter": "AKShare index_hist_sw",
        "date_bounds_accepted": False,
        "reason": "RETURNS_FULL_HISTORY_THROUGH_CURRENT_YEAR",
    },
    {
        "family": "index_publish/details/timelines/",
        "role": "MINUTE_TIMELINES",
        "adapter": "AKShare index_min_sw",
        "date_bounds_accepted": False,
        "reason": "RETURNS_FULL_HISTORY_THROUGH_CURRENT_YEAR",
    },
    {
        "family": "index_analysis/index_analysis_report/",
        "role": "ANALYSIS_REPORT",
        "adapter": "AKShare index_analysis_daily_sw",
        "date_bounds_accepted": False,
        "reason": "NOT_AN_INDEX_LEVEL_SERIES",
    },
]

# Fail-closed status codes.
STATUS_ACQUIRED = "INDUSTRY_ACQUIRED"
STATUS_BOUNDED_NOT_PROVEN = "INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN"
STATUS_AKSHARE_UNBOUNDED_REJECTED = "AKSHARE_SW_UNBOUNDED_TRANSPORT_REJECTED"
STATUS_CAPSULE_REQUIRED = "INDUSTRY_OFFICIAL_DEVELOPMENT_CAPSULE_REQUIRED"
STATUS_UNVERIFIED_MIRROR_REJECTED = "UNVERIFIED_MIRROR_REJECTED"
STATUS_CAPSULE_SCHEMA_INVALID = "INDUSTRY_CAPSULE_SCHEMA_INVALID"
STATUS_CAPSULE_HAS_HOLDOUT = "INDUSTRY_CAPSULE_HAS_HOLDOUT"
STATUS_CAPSULE_SHA_MISMATCH = "INDUSTRY_CAPSULE_SHA_MISMATCH"
STATUS_CAPSULE_MISSING = "INDUSTRY_CAPSULE_MISSING"

CAPSULE_FILES = ("industry_801016.csv", "industry_801960.csv")
CAPSULE_REQUIRED_COLUMNS = {"trade_date", "close"}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_capsule_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str)
    missing = CAPSULE_REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise Stage3BContractError(
            f"{STATUS_CAPSULE_SCHEMA_INVALID}: {path.name} missing columns {sorted(missing)}"
        )
    out = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(frame["trade_date"], errors="coerce"),
            "close": pd.to_numeric(frame["close"], errors="coerce"),
        }
    )
    if out["trade_date"].isna().any():
        raise Stage3BContractError(
            f"{STATUS_CAPSULE_SCHEMA_INVALID}: {path.name} invalid trade_date"
        )
    if out["close"].isna().any():
        raise Stage3BContractError(f"{STATUS_CAPSULE_SCHEMA_INVALID}: {path.name} invalid close")
    if out["close"].le(0).any():
        raise Stage3BContractError(
            f"{STATUS_CAPSULE_SCHEMA_INVALID}: {path.name} non-positive close"
        )
    if (out["trade_date"] >= pd.Timestamp(HOLDOUT_START)).any():
        raise Stage3BContractError(f"{STATUS_CAPSULE_HAS_HOLDOUT}: {path.name}")
    if out["trade_date"].duplicated().any():
        raise DuplicateKeyError(f"{STATUS_CAPSULE_SCHEMA_INVALID}: {path.name} duplicate date")
    return out.sort_values("trade_date").reset_index(drop=True)


def validate_official_capsule(
    capsule_root: Path, expected_sha256: dict[str, str] | None = None
) -> dict[str, Any]:
    """Validate an official development capsule and return its normalized closes and hashes.

    ``capsule_root`` must contain ``industry_801016.csv`` and ``industry_801960.csv``, each with
    columns ``trade_date`` and ``close``, covering only development dates (<= 2022-12-31). Every
    file must be immutable and, when ``expected_sha256`` is supplied, byte-match its locked hash.
    Returns the concatenated closes frame plus per-file SHA-256 and date ranges.
    """
    capsule_root = capsule_root.resolve()
    if not capsule_root.is_dir():
        raise Stage3BContractError(f"{STATUS_CAPSULE_MISSING}: {capsule_root}")
    frames: list[pd.DataFrame] = []
    files: dict[str, dict[str, Any]] = {}
    for symbol, filename in ((REGIME_1_SYMBOL, "industry_801016.csv"),
                             (REGIME_2_SYMBOL, "industry_801960.csv")):
        path = capsule_root / filename
        if not path.is_file():
            raise Stage3BContractError(f"{STATUS_CAPSULE_MISSING}: {filename}")
        expected = (expected_sha256 or {}).get(filename)
        if expected is not None and _file_sha256(path) != expected:
            raise Stage3BContractError(f"{STATUS_CAPSULE_SHA_MISMATCH}: {filename}")
        frame = _read_capsule_csv(path)
        frame["symbol"] = symbol
        frame["taxonomy"] = REGIME_1_TAXONOMY if symbol == REGIME_1_SYMBOL else REGIME_2_TAXONOMY
        frame["source"] = "USER_PROVIDED_OFFICIAL_DEVELOPMENT_CAPSULE"
        frame["raw_sha256"] = _file_sha256(path)
        files[filename] = {
            "raw_sha256": _file_sha256(path),
            "rows": int(len(frame)),
            "first_date": frame["trade_date"].min().strftime("%Y-%m-%d"),
            "last_date": frame["trade_date"].max().strftime("%Y-%m-%d"),
        }
        frames.append(frame)
    closes = pd.concat(frames, ignore_index=True).sort_values(
        ["symbol", "trade_date"], kind="mergesort"
    ).reset_index(drop=True)
    return {
        "status": STATUS_ACQUIRED,
        "source": "USER_PROVIDED_OFFICIAL_DEVELOPMENT_CAPSULE",
        "publisher": "Shenwan Hongyuan Research",
        "files": files,
        "rows": int(len(closes)),
        "closes": closes,
    }


def resolve_industry_source(
    external_root: Path,
    *,
    user_capsule: Path | None = None,
    expected_capsule_sha256: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve the frozen Shenwan industry control through the ordered source ladder.

    Route A (official bounded SWS transport) and the AKShare adapter are recorded as rejected
    because the official endpoint families ignore server-side date bounds. Route B searches the
    authorized external root for an existing official capsule. Route C validates a user-provided
    official development capsule when supplied. Route D is only reachable with a proof-bearing
    same-series transport, which this environment does not provide; without proof it is
    ``UNVERIFIED_MIRROR_REJECTED``. The honest outcome is therefore ``INDUSTRY_OFFICIAL_
    DEVELOPMENT_CAPSULE_REQUIRED`` unless a capsule is supplied and validated.
    """
    result: dict[str, Any] = {
        "status": STATUS_CAPSULE_REQUIRED,
        "codes": [],
        "fetched_at": datetime.now(UTC).isoformat(),
        "holdout_read_performed": False,
        "endpoint_families_investigated": INVESTIGATED_SWS_ENDPOINT_FAMILIES,
    }
    # Route A: the official endpooint families are all unbounded; the AKShare full-history adapter
    # is likewise rejected. Neither is re-invoked (that would read the holdout).
    result["codes"].append(STATUS_BOUNDED_NOT_PROVEN)
    result["codes"].append(STATUS_AKSHARE_UNBOUNDED_REJECTED)

    # Route B: an existing official capsule in the authorized external root.
    for name in CAPSULE_FILES:
        if (external_root / "raw" / name).is_file():
            try:
                found = validate_official_capsule(
                    external_root / "raw", expected_sha256=expected_capsule_sha256
                )
                result["status"] = STATUS_ACQUIRED
                result["route"] = "B_EXISTING_ROCESSED_CAPSULE"
                result["capsule"] = found
                result["codes"].append(STATUS_ACQUIRED)
                return result
            except Stage3BContractError as exc:
                result["codes"].append(str(exc))

    # Route C: a user-provided official development capsule.
    if user_capsule is not None:
        try:
            accepted = validate_official_capsule(
                user_capsule, expected_sha256=expected_capsule_sha256
            )
            result["status"] = STATUS_ACQUIRED
            result["route"] = "C_USER_PROVIDED_OFFICIAL_CAPSULE"
            result["capsule"] = accepted
            result["codes"].append(STATUS_ACQUIRED)
            return result
        except Stage3BContractError as exc:
            result["codes"].append(str(exc))

    # Route D: no same-series third-party transport with provable identity/lineage is available.
    result["codes"].append(STATUS_UNVERIFIED_MIRROR_REJECTED)
    result["status"] = STATUS_CAPSULE_REQUIRED
    return result


def materialize_official_capsule(external_root: Path, capsule: dict[str, Any]) -> dict[str, str]:
    """Persist an accepted official capsule into the external raw root as immutable files.

    Returns the per-file SHA-256 manifest entries. The capsule is never written to Git.
    """
    raw_root = external_root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    closes = capsule["closes"]
    entries: dict[str, str] = {}
    for symbol in (REGIME_1_SYMBOL, REGIME_2_SYMBOL):
        sub = closes.loc[closes["symbol"].eq(symbol), ["trade_date", "close"]].reset_index(
            drop=True
        )
        path = raw_root / f"industry_{symbol}.csv"
        if path.exists():
            raise Stage3BContractError(f"immutable industry raw path exists: {path.name}")
        payload = _csv_bytes(sub)
        path.write_bytes(payload)
        entries[f"industry_{symbol}.csv"] = _sha256_bytes(payload)
    return entries
