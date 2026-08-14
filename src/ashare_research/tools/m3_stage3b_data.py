"""One-shot bounded acquisition and offline audit for M3 Stage 3B.

This tool never reads dates on or after 2023-01-01 and never writes the default database.
The acquisition command refuses to overwrite an existing raw capsule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import akshare as ak
import baostock as bs
import pandas as pd

from ashare_research.mechanism.contracts import Stage3BContractError
from ashare_research.mechanism.normalization import normalize_daily_observations
from ashare_research.mechanism.source_manifest import canonical_frame_digest, verify_raw_manifest

ACQUISITION_START = "2014-12-01"
DEVELOPMENT_END = "2022-12-31"
SNAPSHOT_DATES = ["2015-01-05", "2020-07-21", "2020-07-22", "2022-12-30"]
SHARE_AUDIT_SYMBOLS = ["601857", "600000", "900901"]


def _rows(result: Any, label: str) -> pd.DataFrame:
    if result.error_code != "0":
        raise Stage3BContractError(
            f"Baostock {label} failed: {result.error_code} {result.error_msg}"
        )
    data: list[list[str]] = []
    while result.next():
        data.append(result.get_row_data())
    if not data:
        raise Stage3BContractError(f"Baostock {label} returned no rows")
    return pd.DataFrame(data, columns=result.fields)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists():
        raise Stage3BContractError(f"immutable raw path already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _entry(path: Path, raw_root: Path, sha256: str, dataset_id: str, source: str) -> dict:
    return {
        "dataset_id": dataset_id,
        "raw_file_path": path.relative_to(raw_root).as_posix(),
        "raw_sha256": sha256,
        "source_name": source,
    }


def acquire(external_root: Path) -> dict:
    """Acquire a single immutable, date-bounded feasibility capsule."""
    root = external_root.resolve()
    raw_root = root / "raw"
    manifest_path = root / "manifests" / "acquisition_manifest.json"
    if raw_root.exists() or manifest_path.exists():
        raise Stage3BContractError("acquisition capsule already exists; network rerun refused")

    entries: list[dict] = []
    login = bs.login()
    if login.error_code != "0":
        raise Stage3BContractError(
            f"Baostock login failed: {login.error_code} {login.error_msg}"
        )
    try:
        calendar = _rows(
            bs.query_trade_dates(start_date=ACQUISITION_START, end_date=DEVELOPMENT_END),
            "trade calendar",
        )
        path = raw_root / "baostock" / "trade_calendar.csv"
        entries.append(
            _entry(
                path,
                raw_root,
                _write_once(path, _csv_bytes(calendar)),
                "trade_calendar",
                "Baostock",
            )
        )

        fields = (
            "date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus,isST"
        )
        for adjustment, flag in [("unadjusted", "3"), ("qfq", "2")]:
            target = _rows(
                bs.query_history_k_data_plus(
                    "sh.601857",
                    fields,
                    start_date=ACQUISITION_START,
                    end_date=DEVELOPMENT_END,
                    frequency="d",
                    adjustflag=flag,
                ),
                f"target daily {adjustment}",
            )
            path = raw_root / "baostock" / f"601857_SH_{adjustment}.csv"
            entries.append(
                _entry(
                    path,
                    raw_root,
                    _write_once(path, _csv_bytes(target)),
                    f"target_daily_{adjustment}",
                    "Baostock",
                )
            )

        for snapshot_date in SNAPSHOT_DATES:
            snapshot = _rows(bs.query_all_stock(day=snapshot_date), f"universe {snapshot_date}")
            path = raw_root / "baostock" / f"shanghai_universe_{snapshot_date}.csv"
            entries.append(
                _entry(
                    path,
                    raw_root,
                    _write_once(path, _csv_bytes(snapshot)),
                    "historical_shanghai_pit_universe_feasibility",
                    "Baostock",
                )
            )
    finally:
        bs.logout()

    for symbol in SHARE_AUDIT_SYMBOLS:
        shares = ak.stock_share_change_cninfo(
            symbol=symbol,
            start_date="20000101",
            end_date="20221231",
        )
        path = raw_root / "cninfo" / f"{symbol}_share_changes_to_2022.csv"
        entries.append(
            _entry(
                path,
                raw_root,
                _write_once(path, _csv_bytes(shares)),
                "historical_issued_shares_feasibility",
                "CNINFO via Akshare",
            )
        )

    manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3B",
        "acquisition_mode": "ONE_SHOT_FEASIBILITY_CAPSULE",
        "requested_start": ACQUISITION_START,
        "requested_end": DEVELOPMENT_END,
        "holdout_read_performed": False,
        "fetched_at": datetime.now(UTC).isoformat(),
        "entries": entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _read_csv(raw_root: Path, entry: dict) -> pd.DataFrame:
    return pd.read_csv(raw_root / entry["raw_file_path"], dtype=str)


def audit(external_root: Path, label: str) -> dict:
    """Audit the immutable capsule without network access or mechanism statistics."""
    root = external_root.resolve()
    raw_root = root / "raw"
    manifest_path = root / "manifests" / "acquisition_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_raw_manifest(manifest["entries"], raw_root)

    output_root = root / f"normalized_{label}"
    output_root.mkdir(parents=True, exist_ok=True)
    datasets: list[dict[str, Any]] = []
    normalized_datasets: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        frame = _read_csv(raw_root, entry)
        date_column = next(
            (column for column in ["calendar_date", "date", "变动日期"] if column in frame),
            None,
        )
        dates = pd.to_datetime(frame[date_column], errors="coerce") if date_column else None
        datasets.append(
            {
                "dataset_id": entry["dataset_id"],
                "raw_file_path": entry["raw_file_path"],
                "raw_sha256": entry["raw_sha256"],
                "rows": int(len(frame)),
                "date_start": dates.min().date().isoformat()
                if dates is not None and dates.notna().any()
                else None,
                "date_end": dates.max().date().isoformat()
                if dates is not None and dates.notna().any()
                else None,
                "schema": list(frame.columns),
                "logical_sha256": canonical_frame_digest(frame),
            }
        )
        if entry["dataset_id"] == "trade_calendar":
            normalized = frame.rename(
                columns={"calendar_date": "trade_date", "is_trading_day": "is_open"}
            )
            normalized["trade_date"] = pd.to_datetime(normalized["trade_date"])
            normalized["is_open"] = normalized["is_open"].eq("1")
            normalized["exchange"] = "SH"
            normalized["source_name"] = "Baostock"
            normalized["raw_sha256"] = entry["raw_sha256"]
            normalized["schema_version"] = "1.0.0"
            normalized = normalized[
                [
                    "trade_date",
                    "exchange",
                    "is_open",
                    "source_name",
                    "raw_sha256",
                    "schema_version",
                ]
            ]
        elif entry["dataset_id"] in {"target_daily_unadjusted", "target_daily_qfq"}:
            trade_dates = pd.to_datetime(frame["date"])
            close_time = (
                trade_dates.dt.tz_localize("Asia/Shanghai") + pd.Timedelta(hours=15)
            ).dt.tz_convert("UTC")
            normalization_input = pd.DataFrame(
                {
                    "trade_date": trade_dates,
                    "observation_time": close_time,
                    "available_at": close_time,
                    "value": frame["close"],
                }
            )
            adjustment = "none" if entry["dataset_id"].endswith("unadjusted") else "qfq"
            normalized = normalize_daily_observations(
                normalization_input,
                dataset_id=entry["dataset_id"],
                instrument_id="601857.SH",
                currency="CNY",
                adjustment=adjustment,
                source_name="Baostock",
                source_endpoint="query_history_k_data_plus",
                source_version="00.9.30",
                raw_sha256=entry["raw_sha256"],
            )
        else:
            continue
        normalized_path = output_root / f"{entry['dataset_id']}.csv"
        normalized_path.write_bytes(_csv_bytes(normalized))
        normalized_datasets.append(
            {
                "dataset_id": entry["dataset_id"],
                "rows": int(len(normalized)),
                "schema": list(normalized.columns),
                "logical_sha256": canonical_frame_digest(normalized),
                "normalization_status": "NORMALIZED",
            }
        )

    result = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3B",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "raw_manifest_verified": True,
        "datasets": datasets,
        "normalized_datasets": normalized_datasets,
        "primary_proxy_status": "PRIMARY_PROXY_DATA_GAP",
        "gap_reasons": [
            "CANDIDATE_SHARE_HISTORY_DOES_NOT_PROVE_SECURITY_CLASS_SPECIFIC_APPLICABLE_ISSUED_SHARES_FOR_ALL_ELIGIBLE_A_B_CDR_SECURITIES",
            "NO_COMPLETE_OFFICIAL_CORPORATE_ACTION_AND_DIVISOR_CONTINUITY_INPUT_FOR_2015_2022",
            "DATED_SNAPSHOT_ENDPOINT_MIXES_SECURITIES_WITH_INDICES_AND_DOES_NOT_IDENTIFY_OFFICIAL_INDEX_ELIGIBILITY",
            "COMPLETE_DAILY_MEMBERSHIP_AND_SHARE_COVERAGE_WAS_NOT_OBTAINED",
        ],
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    output = output_root / "offline_audit.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["acquire", "audit"]:
        child = subparsers.add_parser(command)
        child.add_argument("--external-root", required=True, type=Path)
        if command == "audit":
            child.add_argument("--label", required=True, choices=["a", "b"])
    args = parser.parse_args(argv)
    try:
        payload = (
            acquire(args.external_root)
            if args.command == "acquire"
            else audit(args.external_root, args.label)
        )
    except Exception as exc:
        print(f"M3 Stage 3B {args.command}: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
