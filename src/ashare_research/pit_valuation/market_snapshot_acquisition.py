"""M2 Stage 2K.1R4E.2 — versioned dual-source market snapshot reacquisition.

This module is the single deterministic home for the content-addressed,
double-source daily market snapshot acquisition.  It:

- ``acquire_baostock_snapshot`` / ``acquire_akshare_snapshot`` fetch one provider's
  daily unadjusted (``adjustflag=3`` / ``adjust=""``) A-share series over the
  frozen window with a bounded retry policy (at most three attempts, no silent
  interface switch, no third-party backfill).  Network access lives only here.
- ``normalize_market_snapshot`` produces the canonical row contract (symbol,
  trade_date, open/high/low/close, volume, amount, is_trading, adjustment,
  provider, provider_version) with strict ascending trade_date, no duplicates,
  no float repr for business identity, and canonical ``Decimal`` strings.
- ``write_content_addressed_snapshot`` writes a deterministic Parquet
  (``index=False``, pyarrow) to ``<cache-root>/<provider>/<sha256>.parquet``
  where the SHA-256 is taken from the final normalized file's raw bytes.
- ``canonical_table_digest`` / ``build_acquisition_receipt`` /
  ``validate_acquisition_receipt`` produce and validate the acquisition receipt,
  whose batch identity is derived only from a canonical payload (never a
  wall-clock timestamp and never an absolute path).

The module never opens the default database and never falls back to another
provider or a web scrape to fill missing data.
"""

from __future__ import annotations

import contextlib
import hashlib
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    SYMBOL,
    canonical_digest,
    parse_decimal,
)

DEFAULT_ATTEMPTS = 3

# Canonical writer contract (mirrors the frozen acquisition config).
CANONICAL_COLUMNS = (
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "is_trading",
    "adjustment",
    "provider",
    "provider_version",
)


class MarketAcquisitionError(RuntimeError):
    """A provider acquisition failed after the bounded retry policy."""


class MarketNormalizationError(ValueError):
    """A provider response failed the canonical normalization contract."""


def _canon_decimal(source_value: Any) -> str:
    """Canonical Decimal string (no exponent, no float repr)."""
    return format(parse_decimal(source_value).normalize(), "f")


def _iso_date(value: Any) -> str:
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "isoformat"):
        return str(value.isoformat())[:10]
    return str(value)[:10]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── acquisition (network only) ─────────────────────────────────────────────


def _baostock_raw_rows(rows: list[list[str]], fields: list[str]) -> list[dict[str, Any]]:
    """Map raw Baostock rows to the intermediate row contract."""
    out: list[dict[str, Any]] = []
    for raw in rows:
        d = dict(zip(fields, raw, strict=False))
        vol = parse_decimal(d.get("volume", "0"))
        out.append(
            {
                "trade_date": _iso_date(d.get("date", "")),
                "open": d.get("open", ""),
                "high": d.get("high", ""),
                "low": d.get("low", ""),
                "close": d.get("close", ""),
                "volume": int(vol),
                "amount": d.get("amount", ""),
                "is_trading": str(d.get("tradestatus", "")) == "1",
            }
        )
    return out


def _akshare_raw_rows(df) -> list[dict[str, Any]]:
    """Map raw AKShare rows (Chinese columns) to the intermediate contract.

    AKShare ``stock_zh_a_hist`` reports volume in lots (``手`` = 100 shares);
    the internal contract requires shares, so the volume is multiplied by 100.
    """
    import pandas as pd

    out: list[dict[str, Any]] = []
    if df is None or df.empty:
        return out
    # Field aliases that have appeared across AKShare versions: canonical name
    # -> the Chinese column actually present in the response.
    aliases = {
        "日期": "trade_date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    }
    col = {canonical: chinese for chinese, canonical in aliases.items() if chinese in df.columns}
    missing = [c for c in ("trade_date", "open", "close", "high", "low", "volume", "amount")
               if c not in col]
    if missing:
        raise MarketNormalizationError(f"AKShare missing required columns: {missing}")
    for _, r in df.iterrows():
        vol = int(pd.to_numeric(r[col["volume"]], errors="coerce") * 100)
        out.append(
            {
                "trade_date": _iso_date(r[col["trade_date"]]),
                "open": r[col["open"]],
                "high": r[col["high"]],
                "low": r[col["low"]],
                "close": r[col["close"]],
                "volume": vol,
                "amount": r[col["amount"]],
                "is_trading": True,
            }
        )
    return out


def acquire_baostock_snapshot(
    contract: dict[str, Any], *, attempts: int = DEFAULT_ATTEMPTS
) -> tuple[list[dict[str, Any]], str]:
    """Fetch the Baostock daily unadjusted series over the frozen window.

    Network only.  Bounded retries; a failed login or query is a provider gap.
    """
    import baostock as bs

    cfg = contract["baostock"]
    fields = (
        "date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus"
    )
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise MarketAcquisitionError(
                    f"baostock login {lg.error_code}: {lg.error_msg}"
                )
            rs = bs.query_history_k_data_plus(
                cfg["code"],
                fields,
                start_date=cfg["start_date"],
                end_date=cfg["end_date"],
                frequency=cfg["frequency"],
                adjustflag=cfg["adjustflag"],
            )
            if rs.error_code != "0":
                raise MarketAcquisitionError(
                    f"baostock query {rs.error_code}: {rs.error_msg}"
                )
            rows: list[list[str]] = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                raise MarketAcquisitionError("baostock returned no rows")
            return _baostock_raw_rows(rows, rs.fields), contract["provider_versions"]["baostock"]
        except Exception as exc:  # noqa: BLE001 - any failure is a bounded retry
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(1.5 * attempt)
        finally:
            with contextlib.suppress(Exception):  # logout must not mask the result
                bs.logout()
    raise MarketAcquisitionError(
        f"baostock acquisition failed after {attempts} attempts: {last_error}"
    )


def acquire_akshare_snapshot(
    contract: dict[str, Any], *, attempts: int = DEFAULT_ATTEMPTS
) -> tuple[list[dict[str, Any]], str]:
    """Fetch the AKShare daily unadjusted series over the frozen window.

    Network only.  Bounded retries; a failed interface call is a provider gap.
    """
    import akshare as ak

    cfg = contract["akshare"]
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            df = ak.stock_zh_a_hist(
                symbol=cfg["symbol"],
                period=cfg["period"],
                start_date=cfg["start_date"],
                end_date=cfg["end_date"],
                adjust=cfg["adjust"],
            )
            if df is None or df.empty:
                raise MarketAcquisitionError("akshare returned no rows")
            return _akshare_raw_rows(df), contract["provider_versions"]["akshare"]
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise MarketAcquisitionError(
        f"akshare acquisition failed after {attempts} attempts: {last_error}"
    )


# ── normalization ──────────────────────────────────────────────────────────


def normalize_market_snapshot(
    raw_rows: list[dict[str, Any]],
    *,
    provider: str,
    provider_version: str,
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    """Produce the canonical row list for one provider.

    Enforces the canonical writer contract: pinned symbol, ISO dates, strict
    ascending ``trade_date`` without duplicates, canonical ``Decimal`` strings
    for OHLC/amount, normalized integer volume in shares.
    """
    if provider not in ("baostock", "akshare"):
        raise MarketNormalizationError(f"unsupported provider {provider!r}")
    symbol = contract.get("symbol", SYMBOL)
    adjustment = contract.get("adjustment", "none")
    rows: list[dict[str, Any]] = []
    for r in raw_rows:
        rows.append(
            {
                "symbol": symbol,
                "trade_date": _iso_date(r["trade_date"]),
                "open": _canon_decimal(r["open"]),
                "high": _canon_decimal(r["high"]),
                "low": _canon_decimal(r["low"]),
                "close": _canon_decimal(r["close"]),
                "volume": int(r["volume"]),
                "amount": _canon_decimal(r["amount"]),
                "is_trading": bool(r["is_trading"]),
                "adjustment": adjustment,
                "provider": provider,
                "provider_version": str(provider_version),
            }
        )
    rows.sort(key=lambda x: x["trade_date"])
    dates = [r["trade_date"] for r in rows]
    if len(set(dates)) != len(dates):
        raise MarketNormalizationError(f"{provider} normalized rows contain duplicate trade_dates")
    if dates != sorted(dates):
        raise MarketNormalizationError(f"{provider} normalized rows are not ascending")
    return rows


def canonical_table_digest(normalized_rows: list[dict[str, Any]]) -> str:
    """Deterministic content digest of the normalized table (recomputable)."""
    return canonical_digest(normalized_rows)


def column_schema_digest() -> str:
    return canonical_digest(list(CANONICAL_COLUMNS))


# ── content-addressed write ────────────────────────────────────────────────


def write_content_addressed_snapshot(
    normalized_rows: list[dict[str, Any]],
    cache_root: Path | str,
    provider: str,
) -> tuple[Path, str]:
    """Write a canonical Parquet to ``<cache-root>/<provider>/<sha256>.parquet``.

    The returned SHA-256 is computed from the final normalized file's raw bytes.
    Writes are atomic (temp file then rename).
    """
    import pandas as pd

    if not normalized_rows:
        raise MarketNormalizationError(f"{provider} has no rows to write")
    df = pd.DataFrame(normalized_rows, columns=list(CANONICAL_COLUMNS))
    df = df.reset_index(drop=True)
    root = Path(cache_root).resolve()
    provider_dir = root / provider
    provider_dir.mkdir(parents=True, exist_ok=True)
    tmp = provider_dir / f".tmp-{uuid.uuid4().hex}.parquet"
    try:
        df.to_parquet(tmp, index=False, engine="pyarrow")
        data = tmp.read_bytes()
        sha = _sha256_bytes(data)
        final = provider_dir / f"{sha}.parquet"
        if not final.is_file():
            tmp.replace(final)
        else:
            tmp.unlink()
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return final, sha


# ── acquisition receipt ────────────────────────────────────────────────────


def build_acquisition_batch_id(
    symbol: str,
    date_range: dict[str, str],
    adjustment: str,
    provider_records: list[dict[str, Any]],
) -> str:
    """Deterministic batch identity from a canonical payload (no wall-clock)."""
    payload = {
        "symbol": symbol,
        "date_range": date_range,
        "adjustment": adjustment,
        "providers": [
            {
                "provider": p.get("provider"),
                "provider_version": p.get("provider_version"),
                "function": p.get("function"),
                "params": p.get("params"),
                "sha256": p.get("sha256"),
            }
            for p in sorted(provider_records, key=lambda x: x.get("provider", ""))
        ],
    }
    return canonical_digest(payload)


def build_acquisition_receipt(
    *,
    contract: dict[str, Any],
    provider_records: list[dict[str, Any]],
    runtime_versions: dict[str, str],
    acquisition_code_commit: str,
    started_at: str,
    finished_at: str,
    acquisition_warnings: list[str],
) -> dict[str, Any]:
    """Assemble the acquisition receipt (no absolute paths, no proxy)."""
    date_range = {
        "requested_start": contract.get("requested_start"),
        "requested_end": contract.get("requested_end"),
        "actual_start": next(
            (p.get("first_trade_date") for p in provider_records if p.get("first_trade_date")),
            None,
        ),
        "actual_end": next(
            (p.get("last_trade_date") for p in provider_records if p.get("last_trade_date")),
            None,
        ),
    }
    batch_id = build_acquisition_batch_id(
        contract.get("symbol", SYMBOL),
        {"start": contract.get("requested_start"), "end": contract.get("requested_end")},
        contract.get("adjustment", "none"),
        provider_records,
    )
    return {
        "schema": "petrochina_market_snapshot_acquisition_receipt_v1",
        "acquisition_batch_id": batch_id,
        "symbol": contract.get("symbol", SYMBOL),
        "date_range": date_range,
        "adjustment": contract.get("adjustment", "none"),
        "frequency": contract.get("frequency"),
        "currency": contract.get("currency"),
        "close_unit": contract.get("close_unit"),
        "providers": provider_records,
        "runtime_versions": runtime_versions,
        "acquisition_code_commit": acquisition_code_commit,
        "started_at": started_at,
        "finished_at": finished_at,
        "acquisition_warnings": acquisition_warnings,
        "evidence_class": "external_real_data_cache",
    }


def validate_acquisition_receipt(
    receipt: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Validate an acquisition receipt against the frozen contract."""
    errors: list[str] = []
    if receipt.get("schema") != "petrochina_market_snapshot_acquisition_receipt_v1":
        errors.append("schema mismatch")
    if receipt.get("symbol") != contract.get("symbol"):
        errors.append("symbol mismatch")
    if receipt.get("adjustment") != contract.get("adjustment"):
        errors.append("adjustment mismatch")
    providers = receipt.get("providers", [])
    names = {p.get("provider") for p in providers}
    if names != {"baostock", "akshare"}:
        errors.append(f"providers mismatch: {names}")
    for p in providers:
        if len(str(p.get("sha256", ""))) != 64:
            errors.append(f"provider {p.get('provider')} missing sha256")
        if not p.get("first_trade_date") or not p.get("last_trade_date"):
            errors.append(f"provider {p.get('provider')} missing date range")
    required_first = contract.get("required_first_trade_date")
    required_last = contract.get("required_last_trade_date")
    for p in providers:
        if p.get("first_trade_date") != required_first:
            errors.append(
                f"{p.get('provider')} first {p.get('first_trade_date')} != {required_first}"
            )
        if p.get("last_trade_date") != required_last:
            errors.append(
                f"{p.get('provider')} last {p.get('last_trade_date')} != {required_last}"
            )
    # batch id must be recomputable from the canonical payload.
    try:
        recomputed = build_acquisition_batch_id(
            receipt.get("symbol"),
            {"start": receipt.get("date_range", {}).get("requested_start"),
             "end": receipt.get("date_range", {}).get("requested_end")},
            receipt.get("adjustment"),
            providers,
        )
        if recomputed != receipt.get("acquisition_batch_id"):
            errors.append("acquisition_batch_id mismatch")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"acquisition_batch_id not recomputable: {exc}")
    return {"valid": not errors, "errors": errors}


def utc_now_iso() -> str:
    """Current UTC timestamp (used only for receipt metadata, never identity)."""
    return datetime.now(UTC).isoformat(timespec="seconds")
