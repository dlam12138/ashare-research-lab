"""Exact, resumable Stage 3D-B holdout acquisition and offline normalization.

This module is intentionally separate from the historical development adapters.  It only becomes
usable for real requests when the immutable Stage 3D-B unseal marker is present; pre-unseal tests
inject transport fixtures and never call these network functions.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.alignment import build_tier1_readiness
from ashare_research.tools.m3_stage3db_oos_inputs import (
    HOLDOUT_END,
    WARMUP_START,
    align_oil_to_a_share_oos,
    build_cni_returns_oos,
    build_market_ex_target_proxy_v2_oos,
    materialize_target_qfq_oos,
)

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = "DCOILBRENTEU"
CNI_URL = "http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
CNI_INDEX = "399439"
TARGET_CODE = "601857"
TARGET_SYMBOL = "sh.601857"
AK_START = "20221201"
AK_END = "20260813"
RAW_END = "2026-08-13"
_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-/.](\d{2})[-/.](\d{2})(?!\d)")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_once(path: Path, raw: bytes) -> str:
    if path.exists() and path.read_bytes() != raw:
        raise ValueError(f"M3_STAGE3DB_IMMUTABLE_RAW_CONFLICT:{path.name}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return sha256_bytes(raw)


def _request_bytes(url: str, params: dict[str, Any]) -> bytes:
    import requests

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return bytes(response.content)


def _raw_dates(raw: bytes) -> list[pd.Timestamp]:
    values: list[pd.Timestamp] = []
    text = raw.decode("utf-8", errors="replace")
    for match in _DATE_RE.finditer(text):
        parsed = pd.Timestamp(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
        values.append(parsed.normalize())
    return values


def prove_bounded_raw(raw: bytes) -> dict[str, Any]:
    dates = _raw_dates(raw)
    if not dates or max(dates) > HOLDOUT_END:
        raise ValueError("M3_STAGE3DB_UNBOUNDED_RAW_RESPONSE")
    return {
        "raw_date_scan": "PASSED",
        "raw_observation_date_min": min(dates).date().isoformat(),
        "raw_observation_date_max": max(dates).date().isoformat(),
        "raw_date_tokens": len(dates),
        "raw_sha256": sha256_bytes(raw),
    }


def acquire_target(root: Path) -> dict[str, Any]:
    import baostock as bs

    raw_root = root / "raw" / "baostock"
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"M3_STAGE3DB_BAOSTOCK_LOGIN_FAILED:{login.error_msg}")
    try:
        calendar = bs.query_trade_dates(start_date=AK_START, end_date=AK_END)
        calendar_rows = []
        while calendar.next():
            calendar_rows.append(calendar.get_row_data())
        calendar_frame = pd.DataFrame(calendar_rows, columns=calendar.fields)
        calendar_sha = write_once(raw_root / "trade_calendar.csv", csv_bytes(calendar_frame))
        fields = "date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus,isST"
        result = bs.query_history_k_data_plus(
            TARGET_SYMBOL,
            fields,
            start_date=AK_START,
            end_date=AK_END,
            frequency="d",
            adjustflag="2",
        )
        rows = []
        while result.next():
            rows.append(result.get_row_data())
        target = pd.DataFrame(rows, columns=result.fields)
        target_sha = write_once(raw_root / "601857_SH_qfq.csv", csv_bytes(target))
    finally:
        bs.logout()
    return {
        "source": "Baostock",
        "dataset_id": "target_daily_qfq",
        "request": {
            "code": TARGET_SYMBOL,
            "start_date": AK_START,
            "end_date": AK_END,
            "adjustflag": "2",
        },
        "calendar_raw_sha256": calendar_sha,
        "target_raw_sha256": target_sha,
        "rows": int(len(target)),
    }


def _master_frame(root: Path) -> pd.DataFrame:
    return pd.concat(
        [
            pd.read_csv(root / "raw" / "akshare" / f"sh_master_{name}.csv", dtype=str)
            for name in ("主板A股", "科创板", "主板B股")
        ],
        ignore_index=True,
    )


def acquire_market(root: Path) -> dict[str, Any]:
    import akshare as ak

    raw_root = root / "raw" / "akshare"
    entries: list[dict[str, Any]] = []
    for name in ("主板A股", "科创板", "主板B股"):
        frame = ak.stock_info_sh_name_code(symbol=name)
        raw = csv_bytes(frame)
        entries.append(
            {
                "path": f"akshare/sh_master_{name}.csv",
                "sha256": write_once(raw_root / f"sh_master_{name}.csv", raw),
            }
        )
    delist = ak.stock_info_sh_delist()
    entries.append(
        {
            "path": "akshare/sh_delist.csv",
            "sha256": write_once(raw_root / "sh_delist.csv", csv_bytes(delist)),
        }
    )
    frames = [_master_frame(root), pd.read_csv(raw_root / "sh_delist.csv", dtype=str)]
    codes = set(frames[0].iloc[:, 0].astype(str).str.strip()) | set(
        frames[1].iloc[:, 0].astype(str).str.strip()
    )
    eligible = sorted(
        code.zfill(6)
        for code in codes
        if code.zfill(6)[:3] in {"600", "601", "603", "605", "688"} and code.zfill(6) != TARGET_CODE
    )
    failures: list[str] = []
    for code in eligible:
        path = raw_root / f"daily_{code}.csv"
        if path.exists():
            entries.append(
                {"path": f"akshare/daily_{code}.csv", "sha256": sha256_bytes(path.read_bytes())}
            )
            continue
        try:
            frame = ak.stock_zh_a_daily(
                symbol=f"sh{code}", start_date=AK_START, end_date=AK_END, adjust=""
            )
            if frame is None or frame.empty:
                failures.append(f"{code}:EMPTY")
                continue
            entries.append(
                {"path": f"akshare/daily_{code}.csv", "sha256": write_once(path, csv_bytes(frame))}
            )
        except Exception as exc:  # noqa: BLE001 - preserve per-symbol audit and continue
            failures.append(f"{code}:{type(exc).__name__}:{str(exc)[:100]}")
    if failures:
        raise RuntimeError(f"M3_STAGE3DB_MARKET_ACQUISITION_FAILURE:{len(failures)}:{failures[:5]}")
    return {
        "source": "AKShare stock_zh_a_daily",
        "entries": entries,
        "eligible_symbols": len(eligible),
    }


def acquire_oil(root: Path, http_get=None) -> dict[str, Any]:
    fetch = http_get or _request_bytes
    raw = fetch(FRED_URL, {"id": FRED_SERIES, "cosd": AK_START, "coed": AK_END})
    proof = prove_bounded_raw(raw)
    path = root / "raw" / "fred_DCOILBRENTEU.csv"
    digest = write_once(path, raw)
    return {
        "source": "FRED_PUBLIC_GRAPH_CSV",
        "series": FRED_SERIES,
        "request": {"cosd": AK_START, "coed": AK_END},
        "raw_sha256": digest,
        "bounded_proof": proof,
    }


def acquire_industry(root: Path, http_get=None) -> dict[str, Any]:
    fetch = http_get or _request_bytes
    params = {"indexCode": CNI_INDEX, "startDate": AK_START, "endDate": AK_END, "frequency": "day"}
    raw = fetch(CNI_URL, params)
    proof = prove_bounded_raw(raw)
    path = root / "raw" / "cni_399439_response.json"
    digest = write_once(path, raw)
    return {
        "source": "CNI_OFFICIAL_BOUNDED_ENDPOINT",
        "index_code": CNI_INDEX,
        "request": params,
        "raw_sha256": digest,
        "bounded_proof": proof,
    }


def normalize_all(root: Path) -> dict[str, Any]:
    raw = root / "raw"
    normalized = root / "normalized_a"
    normalized.mkdir(parents=True, exist_ok=True)
    target_raw = pd.read_csv(raw / "baostock" / "601857_SH_qfq.csv", dtype=str)
    target = materialize_target_qfq_oos(target_raw)
    target.to_csv(normalized / "target_returns.csv", index=False, lineterminator="\n")
    calendar_raw = pd.read_csv(raw / "baostock" / "trade_calendar.csv", dtype=str)
    date_col = next(
        column for column in calendar_raw.columns if column.lower() in {"calendar_date", "date"}
    )
    flag_col = next(
        (
            column
            for column in calendar_raw.columns
            if column.lower() in {"is_trading_day", "istradingday"}
        ),
        None,
    )
    calendar = pd.to_datetime(
        calendar_raw.loc[calendar_raw[flag_col].astype(str).eq("1"), date_col]
        if flag_col
        else calendar_raw[date_col],
        errors="coerce",
    ).dropna()
    calendar = calendar.loc[calendar.between(WARMUP_START, HOLDOUT_END)].reset_index(drop=True)
    pd.DataFrame({"trade_date": calendar}).to_csv(
        normalized / "trade_calendar.csv", index=False, lineterminator="\n"
    )
    master_raw = _master_frame(root)
    delist_raw = pd.read_csv(raw / "akshare" / "sh_delist.csv", dtype=str)
    master = pd.DataFrame(
        {
            "symbol": master_raw.iloc[:, 0].astype(str).str.strip().str.zfill(6) + ".SH",
            "classification": "A_SHARE_COMMON",
            "listing_date": pd.to_datetime(master_raw.iloc[:, 5], errors="coerce"),
        }
    )
    delist = pd.DataFrame(
        {
            "symbol": delist_raw.iloc[:, 0].astype(str).str.strip().str.zfill(6) + ".SH",
            "delisting_date": pd.to_datetime(delist_raw.iloc[:, 2], errors="coerce"),
        }
    )
    master = master.drop_duplicates("symbol").merge(delist, on="symbol", how="left")
    master["classification"] = (
        master["symbol"]
        .str[:3]
        .map(
            lambda value: "A_SHARE_COMMON"
            if value in {"600", "601", "603", "605", "688"}
            else "OTHER_INSTRUMENT"
        )
    )
    master.to_csv(normalized / "security_master.csv", index=False, lineterminator="\n")
    daily_frames = []
    for path in sorted((raw / "akshare").glob("daily_*.csv")):
        frame = pd.read_csv(path, dtype=str)
        date_column = next(column for column in frame.columns if column.lower() == "date")
        close_column = next(column for column in frame.columns if column.lower() == "close")
        code = path.stem.removeprefix("daily_")
        daily_frames.append(
            pd.DataFrame(
                {
                    "symbol": f"{code}.SH",
                    "trade_date": pd.to_datetime(frame[date_column], errors="coerce"),
                    "close": pd.to_numeric(frame[close_column], errors="coerce"),
                }
            )
        )
    daily = (
        pd.concat(daily_frames, ignore_index=True)
        .dropna()
        .loc[lambda frame: frame["trade_date"].between(WARMUP_START, HOLDOUT_END)]
    )
    daily.to_csv(normalized / "daily_series.csv", index=False, lineterminator="\n")
    proxy, audit = build_market_ex_target_proxy_v2_oos(daily, master, calendar, coverage_gate=0.99)
    proxy.to_csv(normalized / "market_ex_target_v2_proxy.csv", index=False, lineterminator="\n")
    audit.to_csv(normalized / "market_ex_target_v2_audit.csv", index=False, lineterminator="\n")
    fred = pd.read_csv(raw / "fred_DCOILBRENTEU.csv")
    oil_obs = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(fred.iloc[:, 0], errors="coerce"),
            "price": pd.to_numeric(fred.iloc[:, 1], errors="coerce"),
        }
    ).dropna()
    oil = align_oil_to_a_share_oos(oil_obs, calendar)
    oil.to_csv(normalized / "oil_aligned.csv", index=False, lineterminator="\n")
    payload = json.loads((raw / "cni_399439_response.json").read_text(encoding="utf-8"))
    rows = payload.get("data", {}).get("data", [])
    industry = pd.DataFrame(
        {
            "trade_date": pd.to_datetime([row[0] for row in rows], errors="coerce"),
            "index_code": CNI_INDEX,
            "close": pd.to_numeric([row[3] for row in rows], errors="coerce"),
        }
    ).dropna()
    industry = industry.loc[industry["trade_date"].between(WARMUP_START, HOLDOUT_END)]
    industry_aligned = build_cni_returns_oos(industry, calendar)
    industry_aligned.to_csv(normalized / "industry_aligned.csv", index=False, lineterminator="\n")
    readiness = build_tier1_readiness(proxy, oil, industry_aligned)
    readiness.to_csv(normalized / "tier1_readiness.csv", index=False, lineterminator="\n")
    return {
        "target_rows": len(target),
        "market_rows": len(proxy),
        "oil_rows": len(oil),
        "industry_rows": len(industry_aligned),
        "readiness_rows": len(readiness),
    }
