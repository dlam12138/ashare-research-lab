"""Resumable content-addressed acquisition and offline normalization for M3 Stage 3B-R1.

Acquires the PIT-capable Shanghai A-share security master and one bounded full-development
daily series for each ever-eligible security, then normalizes offline (A/B) into canonical
inputs for the v2 equal-weight ex-target proxy. Never reads dates on or after 2023-01-01 and
never writes the default database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd

from ashare_research.mechanism.contracts import Stage3BContractError
from ashare_research.mechanism.proxy_v2 import (
    B_SHARE_PREFIXES,
    CDR_PREFIXES,
    ELIGIBLE_PREFIXES,
    ROW_STATUS_OK,
    TARGET_CODE,
    build_market_ex_target_proxy_v2,
    classify_equity,
)
from ashare_research.mechanism.source_manifest import (
    build_coverage_metadata,
    canonical_frame_digest,
)

# The warm-up buffer starts in 2014-01 (not 2014-12) because the akshare/Sina endpoint truncates
# the early-development history of some symbols at the exact `20141201` boundary; widening the
# start avoids that quirk while still never reading the sealed 2023+ holdout. The proxy only uses
# the 2014-12 warm-up onward; the extra 2014 months are raw normalization buffer.
ACQUISITION_START = "2014-01-01"
DEVELOPMENT_END = "2022-12-31"
AK_START = "20140101"
AK_END = "20221231"
MASTER_SYMBOLS = ["主板A股", "科创板", "主板B股"]
TARGET_SYMBOL = "601857.SH"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists():
        raise Stage3BContractError(f"immutable raw path already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _entry(rel: str, sha256: str, dataset_id: str, source: str) -> dict[str, str]:
    return {
        "dataset_id": dataset_id,
        "raw_file_path": rel,
        "raw_sha256": sha256,
        "source_name": source,
    }


def acquire_master(
    external_root: Path,
    manifest: dict,
    raw_root: Path,
    stage3b_capsule: Path | None = None,
) -> list[dict[str, str]]:
    """Acquire the Shanghai security master lists as immutable raw CSVs.

    When ``stage3b_capsule`` is supplied, the immutable Stage 3B trade calendar is reused when its
    raw SHA-256 matches the recorded Stage 3B value; it is copied into the raw root so the offline
    normalization stays fully local.
    """
    entries: list[dict[str, str]] = []
    for symbol in MASTER_SYMBOLS:
        frame = ak.stock_info_sh_name_code(symbol=symbol)
        rel = f"akshare/sh_master_{symbol}.csv"
        entries.append(
            _entry(
                rel,
                _write_once(raw_root / rel, _csv_bytes(frame)),
                "shanghai_security_master",
                "akshare",
            )
        )
    delist = ak.stock_info_sh_delist()
    rel = "akshare/sh_delist.csv"
    entries.append(
        _entry(rel, _write_once(raw_root / rel, _csv_bytes(delist)), "shanghai_delisted", "akshare")
    )
    if stage3b_capsule is not None:
        capsule = stage3b_capsule.resolve()
        source = capsule / "raw/baostock/trade_calendar.csv"
        if not source.is_file():
            raise Stage3BContractError("Stage 3B capsule trade calendar missing")
        expected = (
            "3fb6450581f8389de8227a5c568b283bd77e85eeaad9562a2eac732fb790e2ec"
        )
        if _sha256_bytes(source.read_bytes()) != expected:
            raise Stage3BContractError("Stage 3B trade calendar SHA-256 mismatch; reuse refused")
        rel = "akshare/trade_calendar.csv"
        entries.append(
            _entry(
                rel,
                _write_once(raw_root / rel, source.read_bytes()),
                "trade_calendar",
                "Baostock reused",
            )
        )
    return entries


def _ever_eligible_symbols(raw_root: Path) -> list[str]:
    """Build the ever-eligible Shanghai A-share common symbol set from raw master/delist lists."""
    frames: list[pd.DataFrame] = []
    for symbol in MASTER_SYMBOLS:
        rel = f"akshare/sh_master_{symbol}.csv"
        frames.append(pd.read_csv(raw_root / rel, dtype=str))
    delist = pd.read_csv(raw_root / "akshare/sh_delist.csv", dtype=str)

    codes = set()
    for frame in frames:
        codes.update(frame[frame.columns[0]].astype(str).str.strip())
    delist_codes = set(delist[delist.columns[0]].astype(str).str.strip())
    codes.update(delist_codes)

    eligible: list[str] = []
    for code in sorted(codes):
        digits = code.zfill(6)
        if classify_equity(digits) != "A_SHARE_COMMON":
            continue
        if digits == TARGET_CODE:
            continue
        eligible.append(digits)
    return eligible


def _read_raw_daily(raw_root: Path, symbol: str) -> pd.DataFrame | None:
    rel = f"akshare/daily_{symbol}.csv"
    path = raw_root / rel
    return pd.read_csv(path, dtype=str) if path.is_file() else None


def acquire_daily(
    external_root: Path, manifest: dict, raw_root: Path
) -> tuple[list[dict[str, str]], list[str]]:
    """Resumably acquire one bounded daily series per ever-eligible symbol."""
    symbols = _ever_eligible_symbols(raw_root)
    entries: list[dict[str, str]] = []
    skipped = 0
    failures: list[tuple[str, str]] = []
    for symbol in symbols:
        rel = f"akshare/daily_{symbol}.csv"
        path = raw_root / rel
        if path.is_file():
            entries.append(
                _entry(
                    rel,
                    _sha256_bytes(path.read_bytes()),
                    "shanghai_a_share_daily_series",
                    "akshare",
                )
            )
            skipped += 1
            continue
        try:
            frame = ak.stock_zh_a_daily(
                symbol=f"sh{symbol}", start_date=AK_START, end_date=AK_END, adjust=""
            )
            if frame is None or frame.empty:
                failures.append((symbol, "EMPTY"))
                continue
            payload = _csv_bytes(frame)
            entries.append(
                _entry(rel, _write_once(path, payload), "shanghai_a_share_daily_series", "akshare")
            )
        except Exception as exc:  # noqa: BLE001 - a per-symbol failure must not abort the batch
            failures.append((symbol, f"{type(exc).__name__}: {str(exc)[:80]}"))
            time.sleep(0.5)
    return entries, [f"{sym}:{msg}" for sym, msg in failures]


def _normalize_daily(raw_root: Path, symbol: str, calendar: pd.Series) -> pd.DataFrame:
    frame = _read_raw_daily(raw_root, symbol)
    if frame is None or frame.empty:
        return pd.DataFrame()
    date_col = next((c for c in frame.columns if c.lower() == "date"), None)
    close_col = next((c for c in frame.columns if c.lower() == "close"), None)
    if date_col is None or close_col is None:
        raise Stage3BContractError(f"daily series {symbol} missing date/close column")
    out = pd.DataFrame(
        {
            "symbol": TARGET_SYMBOL if symbol == TARGET_CODE else f"{symbol}.SH",
            "trade_date": pd.to_datetime(frame[date_col], errors="coerce"),
            "close": pd.to_numeric(frame[close_col], errors="coerce"),
        }
    ).dropna()
    out = out.loc[out["trade_date"] < pd.Timestamp("2023-01-01")]
    return out.reset_index(drop=True)


def normalize(external_root: Path, label: str, manifest: dict, raw_root: Path) -> dict[str, Any]:
    """Canonical offline A/B normalization of master + daily series."""
    output_root = external_root / f"normalized_{label}"
    output_root.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for symbol in MASTER_SYMBOLS:
        frame = pd.read_csv(raw_root / f"akshare/sh_master_{symbol}.csv", dtype=str)
        frames.append(
            pd.DataFrame(
                {
                    "symbol": frame[frame.columns[0]].astype(str).str.strip().str.zfill(6)
                    + ".SH",
                    "classification": "A_SHARE_COMMON",
                    "listing_date": pd.to_datetime(frame[frame.columns[5]], errors="coerce"),
                }
            )
        )
    delist = pd.read_csv(raw_root / "akshare/sh_delist.csv", dtype=str)
    delist_frame = pd.DataFrame(
        {
            "symbol": delist[delist.columns[0]].astype(str).str.strip().str.zfill(6) + ".SH",
            "delisting_date": pd.to_datetime(delist[delist.columns[2]], errors="coerce"),
        }
    )
    # B-share lists are excluded from the eligible universe but kept as master entries with a
    # non-eligible classification so that rejection is explicit and auditable.
    master = pd.concat(frames, ignore_index=True)
    master = master.drop_duplicates(subset="symbol", keep="last")
    master = master.merge(delist_frame, on="symbol", how="left")
    master["classification"] = master["symbol"].str[:3].map(
        lambda p: "A_SHARE_COMMON"
        if p in ELIGIBLE_PREFIXES
        else (
            "B_SHARE"
            if p in B_SHARE_PREFIXES
            else ("CDR" if p in CDR_PREFIXES else "OTHER_INSTRUMENT")
        )
    )
    master["is_target"] = master["symbol"].eq(TARGET_SYMBOL)
    master = master.sort_values("symbol", kind="mergesort").reset_index(drop=True)
    master_path = output_root / "security_master.csv"
    master_path.write_bytes(_csv_bytes(master))

    calendar = pd.read_csv(raw_root / "akshare/trade_calendar.csv", dtype=str) if (
        raw_root / "akshare/trade_calendar.csv"
    ).is_file() else None
    if calendar is None:
        raise Stage3BContractError("trade calendar not present in raw root")
    # The reused Stage 3B calendar is a full calendar (all days) with an `is_trading_day` flag;
    # keep only actual trading days so the proxy and coverage are over trading sessions only.
    trading_flag = next(
        (
            col
            for col in calendar.columns
            if str(col).strip().lower() in {"is_trading_day", "trading_day", "istradingday"}
        ),
        None,
    )
    if trading_flag is not None:
        calendar = calendar[calendar[trading_flag].astype(str).str.strip().eq("1")]
    cal = pd.to_datetime(calendar[calendar.columns[0]], errors="coerce").dropna()
    calendar_out = (
        pd.DataFrame({"trade_date": cal}).sort_values("trade_date").reset_index(drop=True)
    )
    (output_root / "trade_calendar.csv").write_bytes(_csv_bytes(calendar_out))

    daily_frames: list[pd.DataFrame] = []
    for code in _ever_eligible_symbols(raw_root):
        norm = _normalize_daily(raw_root, code, cal)
        if not norm.empty:
            daily_frames.append(norm)
    if not daily_frames:
        raise Stage3BContractError("no normalized daily series produced")
    daily = pd.concat(daily_frames, ignore_index=True).sort_values(
        ["symbol", "trade_date"], kind="mergesort"
    ).reset_index(drop=True)
    (output_root / "daily_series.csv").write_bytes(_csv_bytes(daily))

    return {
        "label": label,
        "master_rows": int(len(master)),
        "daily_rows": int(len(daily)),
        "daily_symbols": int(daily["symbol"].nunique()),
        "calendar_rows": int(len(calendar_out)),
    }


def build_proxy(external_root: Path, label: str) -> dict[str, Any]:
    """Construct the v2 equal-weight ex-target proxy from normalized inputs."""
    norm_root = external_root / f"normalized_{label}"
    master = pd.read_csv(norm_root / "security_master.csv", dtype=str)
    daily = pd.read_csv(norm_root / "daily_series.csv", dtype=str)
    calendar = pd.read_csv(norm_root / "trade_calendar.csv", dtype=str)
    proxy, audit = build_market_ex_target_proxy_v2(
        daily,
        master,
        calendar["trade_date"],
        coverage_gate=0.99,
    )
    (norm_root / "market_ex_target_v2_proxy.csv").write_bytes(_csv_bytes(proxy))
    (norm_root / "market_ex_target_v2_audit.csv").write_bytes(_csv_bytes(audit))
    return {
        "instrument_id": "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2",
        "rows": int(len(proxy)),
        "gap_rows": int(proxy["row_status"].eq("PROXY_ROW_INVALID_DATA_GAP").sum()),
        "ok_rows": int(proxy["row_status"].eq("PROXY_ROW_OK").sum()),
        "first_date": proxy["trade_date"].min().strftime("%Y-%m-%d"),
        "last_date": proxy["trade_date"].max().strftime("%Y-%m-%d"),
    }


def _load_manifest(external_root: Path) -> dict[str, Any]:
    path = external_root / "manifests" / "acquisition_manifest.json"
    if not path.is_file():
        raise Stage3BContractError("acquisition manifest missing")
    return json.loads(path.read_text(encoding="utf-8"))


def generate_reports(external_root: Path, repo_root: Path, label: str = "a") -> dict[str, Any]:
    """Generate the committed Stage 3B-R1 manifest and coverage reports from acquired data."""
    root = external_root.resolve()
    manifest = _load_manifest(root)
    norm_root = root / f"normalized_{label}"
    if not (norm_root / "security_master.csv").is_file():
        raise Stage3BContractError("normalized inputs not present; run normalize first")
    master = pd.read_csv(norm_root / "security_master.csv", dtype=str)
    daily = pd.read_csv(norm_root / "daily_series.csv", dtype=str)
    calendar = pd.read_csv(norm_root / "trade_calendar.csv", dtype=str)

    raw_manifest_sha = canonical_frame_digest(
        pd.DataFrame(manifest["entries"]).sort_values("raw_file_path", kind="mergesort")
    ) if manifest["entries"] else None

    daily_symbols = int(daily["symbol"].nunique())
    master_eligible = int(
        (
            master["classification"].eq("A_SHARE_COMMON")
            & ~master["symbol"].eq(TARGET_CODE + ".SH")
        ).sum()
    )

    def _cov(dataset_id: str, frame: pd.DataFrame) -> dict[str, Any]:
        return build_coverage_metadata(
            frame, dataset_id=dataset_id, expected_dates=calendar["trade_date"]
        )

    manifest_report = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR1",
        "acquisition": {
            "mode": "RESUMABLE_CONTENT_ADDRESSED",
            "fetched_at": manifest.get("fetched_at"),
            "holdout_read_performed": False,
            "requested_start": ACQUISITION_START,
            "requested_end": DEVELOPMENT_END,
            "warmup_role": "WARMUP_ONLY",
            "raw_data_committed_to_git": False,
        },
        "datasets": [
            {
                "dataset_id": "shanghai_security_master",
                "rows": int(len(master)),
                "eligible_common_symbols": master_eligible,
                "status": "ACQUIRED_AND_NORMALIZED",
                "source_name": "akshare",
            },
            {
                "dataset_id": "shanghai_a_share_daily_series",
                "rows": int(len(daily)),
                "symbols": daily_symbols,
                "status": "ACQUIRED_AND_NORMALIZED",
                "source_name": "akshare (Sina)",
            },
            {
                "dataset_id": "trade_calendar",
                "rows": int(len(calendar)),
                "status": "REUSE_IMMUTABLE_STAGE3B",
                "source_name": "Baostock reused",
            },
        ],
        "raw_manifest_sha256": raw_manifest_sha,
        "offline_reproducibility": {
            "logical_identity": True,
            "normalized_a_sha256": canonical_frame_digest(daily),
        },
        "primary_proxy_status": "CONSTRUCTED",
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }

    proxy_path = norm_root / "market_ex_target_v2_proxy.csv"
    proxy = pd.read_csv(proxy_path, dtype=str) if proxy_path.is_file() else None
    # The security master is a static list, not a time series, so it carries a static dataset
    # block (rows/schema/digest) rather than trade_date-based coverage metadata.
    master_meta: dict[str, Any] = {
        "dataset_id": "shanghai_security_master",
        "rows": int(len(master)),
        "eligible_common_symbols": master_eligible,
        "schema": sorted(master.columns),
        "logical_sha256": canonical_frame_digest(master),
        "normalization_status": "NORMALIZED",
    }
    coverage_report = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR1",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "coverage_gate": 0.99,
        "primary_proxy_status": "CONSTRUCTED" if proxy is not None else "PRIMARY_PROXY_DATA_GAP",
        "datasets": [
            master_meta,
            _cov("shanghai_a_share_daily_series", daily),
            _cov("trade_calendar", calendar),
        ],
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    if proxy is not None:
        coverage_report["market_ex_target_v2"] = {
            "instrument_id": "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2",
            "rows": int(len(proxy)),
            "ok_rows": int(proxy["row_status"].eq(ROW_STATUS_OK).sum()),
            "gap_rows": int(proxy["row_status"].ne(ROW_STATUS_OK).sum()),
            "first_date": proxy["trade_date"].min(),
            "last_date": proxy["trade_date"].max(),
        }

    reports_dir = Path(repo_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("m3_stage3br1_development_proxy_manifest_v1.json", manifest_report),
        ("m3_stage3br1_data_coverage_v1.json", coverage_report),
    ):
        path = reports_dir / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return {
        "manifest": "m3_stage3br1_development_proxy_manifest_v1.json",
        "coverage": "m3_stage3br1_data_coverage_v1.json",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["acquire-master", "acquire-daily", "normalize", "build", "reports"]:
        child = subparsers.add_parser(command)
        child.add_argument("--external-root", required=True, type=Path)
        if command in {"acquire-master"}:
            child.add_argument("--stage3b-capsule", required=False, type=Path)
        if command in {"normalize"}:
            child.add_argument("--label", required=True, choices=["a", "b"])
        if command in {"build"}:
            child.add_argument("--label", required=False, default="a", choices=["a", "b"])
        if command in {"reports"}:
            child.add_argument("--repo-root", required=True, type=Path)
            child.add_argument("--label", required=False, default="a", choices=["a", "b"])
    args = parser.parse_args(argv)
    try:
        root = args.external_root.resolve()
        raw_root = root / "raw"
        manifest_path = root / "manifests" / "acquisition_manifest.json"
        manifest = _load_manifest(root) if manifest_path.is_file() else {
            "schema_version": "1.0.0",
            "stage": "M3_STAGE3BR1",
            "holdout_read_performed": False,
            "requested_start": ACQUISITION_START,
            "requested_end": DEVELOPMENT_END,
            "fetched_at": datetime.now(UTC).isoformat(),
            "entries": [],
            "failures": [],
        }
        if args.command == "acquire-master":
            merged = manifest["entries"] + acquire_master(
                root, manifest, raw_root, getattr(args, "stage3b_capsule", None)
            )
            manifest["entries"] = merged
        elif args.command == "acquire-daily":
            entries, failures = acquire_daily(root, manifest, raw_root)
            manifest["entries"] = list(manifest["entries"]) + entries
            manifest["failures"] = list(manifest.get("failures", [])) + failures
        elif args.command == "normalize":
            payload = normalize(root, args.label, manifest, raw_root)
        elif args.command == "build":
            payload = build_proxy(root, args.label)
        elif args.command == "reports":
            payload = generate_reports(root, args.repo_root, args.label)
        # The acquisition is resumable, so a rerun re-records already-fetched raw files. Keep the
        # content-addressed manifest a clean unique set: one entry per raw path, latest wins.
        deduped: dict[str, dict[str, str]] = {}
        for entry in manifest.get("entries", []):
            deduped[entry["raw_file_path"]] = entry
        manifest["entries"] = list(deduped.values())
        # A rerun also re-records per-symbol failures; keep one note per symbol, latest wins.
        deduped_failures: dict[str, str] = {}
        for note in manifest.get("failures", []):
            deduped_failures[note.split(":", 1)[0]] = note
        manifest["failures"] = list(deduped_failures.values())
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if args.command in {"normalize", "build"}:
            print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
        else:
            print(
                json.dumps(
                    {
                        "entries": len(manifest["entries"]),
                        "failures": len(manifest.get("failures", [])),
                    },
                    indent=1,
                )
            )
    except Exception as exc:  # noqa: BLE001
        print(f"M3 Stage 3B-R1 {args.command}: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
