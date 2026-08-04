"""M2 Stage 2K.1R3 market observation-set builder.

Builds a valuation observation set from a market frame (real external cache or
synthetic fixture), generating a stable per-trade-date observation_id, applying
the PIT exclusion (trade_date <= market_data_as_of_date), computing the
included/excluded counts and the 3y/5y percentile of the close series, and
computing the observation_set_digest.

Raw provider OHLCV is never committed. The formal report carries only
observation IDs, dates, inclusion/exclusion, normalized-value digests, the
observation-set digest, percentiles, provider object SHA and the calculation
contract.

Real mode requires an explicit external market cache; it never falls back to
synthetic or committed percentiles.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ashare_research.reproducibility.market import MarketSnapshotResolver, read_market_frame

_CANONICAL_SEP = (",", ":")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def _observation_id(
    metric_id: str,
    symbol: str,
    trade_date: str,
    financial_context_id: str,
    numerator_identity: str,
    denominator_identity: str,
    normalized_value_digest: str,
) -> str:
    payload = {
        "metric_id": metric_id,
        "symbol": symbol,
        "trade_date": trade_date,
        "financial_context_id": financial_context_id,
        "numerator_identity": numerator_identity,
        "denominator_identity": denominator_identity,
        "normalized_value_digest": normalized_value_digest,
    }
    return _sha256_bytes(_canonical(payload))


def _close_series_percentile(df_val: list[float], value: float) -> float | None:
    """Percentile rank of `value` within the historical close series."""
    if not df_val:
        return None
    below = sum(1 for x in df_val if x <= value)
    return below / len(df_val)


def _date_window_percentile(
    rows: list[tuple[str, float]], as_of_date: str, years: int
) -> float | None:
    """Percentile of the latest close within the trailing `years`-window of
    trade dates ending at `as_of_date`. Returns None if the window is empty."""
    if not rows:
        return None
    latest_close = rows[-1][1]
    cutoff = f"{int(as_of_date[:4]) - years:04d}{as_of_date[4:]}"
    window = [close for d, close in rows if d >= cutoff]
    if not window:
        return None
    return _close_series_percentile(window, latest_close)


def build_observation_set(
    *,
    registry_path: Path,
    mode: str,
    cache_root: Path | None,
    fixture_root: Path | None,
    symbol: str,
    market_data_as_of_date: str,
    scorecard_formed_at: str,
    metric_id: str = "close",
) -> dict[str, Any]:
    """Build the observation set from the market frame. Real mode requires a
    cache root; synthetic mode requires a fixture root. Never falls back."""
    resolver = MarketSnapshotResolver(
        registry_path, mode=mode, cache_root=cache_root, fixture_root=fixture_root
    )
    resolved, registry = resolver.resolve()
    frame_path, record = resolved[0]
    df = read_market_frame(frame_path)
    if symbol not in set(df["symbol"]):
        raise ValueError(f"market frame missing symbol {symbol}")
    sub = df[df["symbol"] == symbol].copy()
    if "trade_date" not in sub.columns or "close" not in sub.columns:
        raise ValueError("market frame missing trade_date/close")

    sub["trade_date"] = sub["trade_date"].astype(str)
    total_rows = len(sub)
    included = sub[sub["trade_date"] <= market_data_as_of_date].copy()
    excluded = sub[sub["trade_date"] > market_data_as_of_date]
    excluded_count = len(excluded)

    observations: list[dict[str, Any]] = []
    close_values: list[float] = []
    for _, row in included.iterrows():
        trade_date = row["trade_date"]
        close = float(row["close"])
        close_values.append(close)
        context_id = f"financial_context:{symbol}:{market_data_as_of_date}"
        num_identity = f"close:{symbol}"
        den_identity = "1"
        norm_digest = _sha256_bytes(_canonical({"close": close}))
        obs_id = _observation_id(
            metric_id, symbol, trade_date, context_id, num_identity, den_identity, norm_digest
        )
        observations.append(
            {
                "observation_id": obs_id,
                "metric_id": metric_id,
                "symbol": symbol,
                "trade_date": trade_date,
                "available_at": market_data_as_of_date,
                "financial_context_id": context_id,
                "numerator_identity": num_identity,
                "denominator_identity": den_identity,
                "normalized_value_digest": norm_digest,
                "inclusion_status": "included",
                "exclusion_reason": None,
            }
        )

    # 3y / 5y windows from the close series (date-windowed, not full-series).
    rows_sorted = sorted(
        (str(r["trade_date"]), float(r["close"])) for _, r in sub.iterrows()
    )
    rows_included = [r for r in rows_sorted if r[0] <= market_data_as_of_date]
    p3y = _date_window_percentile(rows_included, market_data_as_of_date, 3)
    p5y = _date_window_percentile(rows_included, market_data_as_of_date, 5)
    latest_close = rows_included[-1][1] if rows_included else None

    obs_set = {
        "metric_id": metric_id,
        "symbol": symbol,
        "market_data_as_of_date": market_data_as_of_date,
        "scorecard_formed_at": scorecard_formed_at,
        "provider_object_sha256": record.get("sha256"),
        "provider_object_key": record.get("object_key"),
        "retrieval_status": record.get("retrieval_status"),
        "total_row_count": total_rows,
        "included_observation_count": len(included),
        "excluded_observation_count": excluded_count,
        "exclusion_reasons": ["trade_date > market_data_as_of_date"],
        "percentile_3y_close": p3y,
        "percentile_5y_close": p5y,
        "latest_close": latest_close,
        "observation_ids": [o["observation_id"] for o in observations],
    }
    obs_set["observation_set_digest"] = _sha256_bytes(_canonical(obs_set))

    market_validation_mode = (
        "external_verified_cache" if mode == "real_research" else "synthetic_test_capsule"
    )
    return {
        "schema": "petrochina_valuation_observation_set_manifest_v2",
        "version": "2.0",
        "symbol": symbol,
        "market_validation_mode": market_validation_mode,
        "real_market_verified": mode == "real_research",
        "network_used": False,
        "production_eligible": False,
        "observations": observations,
        "observation_set": obs_set,
    }


def status_for_observation_set() -> dict[str, Any]:
    """Return the synthetic-only status when no real cache is provided."""
    return {
        "market_validation_mode": "synthetic_test_capsule",
        "real_market_verified": False,
        "production_eligible": False,
        "cache_missing": True,
    }
