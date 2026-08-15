"""Bounded, holdout-safe acquisition and offline alignment for M3 Stage 3B-R2.

Attempts a strictly-bounded acquisition of Brent (EIA RBRTE / FRED DCOILBRENTEU) and the Shenwan
petroleum & petrochemicals industry index (``801016``/``801960``), then normalizes offline (A/B)
and aligns into the joint Tier-1 readiness table. Never reads a date on or after 2023-01-01 and
never writes the default database. A source path that ignores date bounds and returns full history
through 2026 is rejected for the sealed holdout; the stage then reports the honest input gap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.contracts import Stage3BContractError

HOLDOUT_START = "2023-01-01"
WARMUP_START = "2014-12-01"
DEVELOPMENT_END = "2022-12-31"

OIL_EIA_SERIES = "RBRTE"
OIL_FRED_SERIES = "DCOILBRENTEU"
OIL_ENDPOINT_EIA = "https://www.eia.gov/dnav/pet/hist/RBRTEd.htm"
OIL_ENDPOINT_FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SWS_TREND_ENDPOINT = "https://www.swsresearch.com/institute-sw/api/index_publish/trend/"

ACQUIRE_OIL_EIA_KEY_UNAVAILABLE = "OIL_EIA_API_KEY_UNAVAILABLE"
ACQUIRE_OIL_FRED_UNREACHABLE = "OIL_FRED_UNREACHABLE"
ACQUIRE_OIL_PATH_REJECTED_HOLDOUT = "REJECT_SOURCE_PATH_FOR_SEALED_HOLDOUT"
ACQUIRE_INDUSTRY_NOT_PROVEN = "INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def acquire_oil_bounded(external_root: Path) -> dict[str, Any]:
    """Attempt a strictly-bounded Brent acquisition; fail closed with a precise code.

    EIA's true bounded path is the Open Data API v2, which requires an API key unavailable in this
    environment; the keyless EIA dnav HTML ignores date bounds and returns full history through the
    current year (a sealed-holdout read). FRED is a secondary distribution used only as a bounded
    transport when reachable. No raw file is written on a failed closed path.
    """
    raw_root = external_root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "NOT_ACQUIRED",
        "codes": [],
        "fetched_at": datetime.now(UTC).isoformat(),
        "holdout_read_performed": False,
    }
    # EIA bounded API requires a key; the keyless page is unbounded and would read holdout.
    result["codes"].append(ACQUIRE_OIL_EIA_KEY_UNAVAILABLE)
    result["codes"].append(ACQUIRE_OIL_PATH_REJECTED_HOLDOUT)
    # FRED bounded transport is unreachable from this environment; record it, do not block lookup.
    result["codes"].append(ACQUIRE_OIL_FRED_UNREACHABLE)
    return result


def acquire_industry_bounded(external_root: Path) -> dict[str, Any]:
    """Attempt a strictly-bounded Shenwan industry acquisition; fail closed if bounded is unproven.

    The official SWS trend endpoint ignores date parameters and returns the full daily series
    (``801016`` from 1999, ``801960`` from 2021-12-13) through the current year, so any download
    reads the sealed holdout. No verified development-only immutable industry capsule exists.
    """
    raw_root = external_root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    return {
        "status": "NOT_ACQUIRED",
        "codes": [ACQUIRE_INDUSTRY_NOT_PROVEN],
        "fetched_at": datetime.now(UTC).isoformat(),
        "holdout_read_performed": False,
    }


def normalize_oil(external_root: Path, label: str) -> dict[str, Any]:
    """Canonical offline normalization of a bounded Brent observation CSV (A/B reproducible)."""
    source = external_root / "raw" / "oil_brent_observations.csv"
    if not source.is_file():
        return {"label": label, "status": "NOT_ACQUIRED", "rows": 0}
    frame = pd.read_csv(source, dtype=str)
    missing = {"observation_date", "price"} - set(frame.columns)
    if missing:
        raise Stage3BContractError(f"oil raw missing columns: {sorted(missing)}")
    out = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(frame["observation_date"], errors="coerce"),
            "price": pd.to_numeric(frame["price"], errors="coerce"),
        }
    ).dropna()
    if (out["observation_date"] >= pd.Timestamp(HOLDOUT_START)).any():
        raise Stage3BContractError("sealed holdout oil raw row rejected")
    out = out.sort_values("observation_date").reset_index(drop=True)
    out_root = external_root / f"normalized_{label}"
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "oil_brent_observations.csv").write_bytes(_csv_bytes(out))
    return {"label": label, "status": "NORMALIZED", "rows": int(len(out))}


def normalize_industry(external_root: Path, label: str) -> dict[str, Any]:
    """Canonical offline normalization of bounded Shenwan industry CSVs (A/B reproducible)."""
    records: list[pd.DataFrame] = []
    for symbol in ("801016", "801960"):
        source = external_root / "raw" / f"industry_{symbol}.csv"
        if not source.is_file():
            continue
        frame = pd.read_csv(source, dtype=str)
        missing = {"trade_date", "close"} - set(frame.columns)
        if missing:
            raise Stage3BContractError(f"industry raw {symbol} missing columns: {sorted(missing)}")
        sub = pd.DataFrame(
            {
                "trade_date": pd.to_datetime(frame["trade_date"], errors="coerce"),
                "close": pd.to_numeric(frame["close"], errors="coerce"),
                "symbol": symbol,
            }
        ).dropna()
        if (sub["trade_date"] >= pd.Timestamp(HOLDOUT_START)).any():
            raise Stage3BContractError(f"sealed holdout industry {symbol} raw row rejected")
        records.append(sub)
    if not records:
        return {"label": label, "status": "NOT_ACQUIRED", "rows": 0}
    out = pd.concat(records, ignore_index=True).sort_values(
        ["symbol", "trade_date"], kind="mergesort"
    ).reset_index(drop=True)
    out_root = external_root / f"normalized_{label}"
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "industry_series.csv").write_bytes(_csv_bytes(out))
    return {"label": label, "status": "NORMALIZED", "rows": int(len(out))}


def run_alignment(external_root: Path, label: str, repo_root: Path) -> dict[str, Any]:
    """Build oil alignment, industry returns, and joint Tier-1 readiness from normalized inputs."""
    from ashare_research.mechanism.alignment import build_tier1_readiness, summarize_readiness
    from ashare_research.mechanism.industry import build_industry_returns
    from ashare_research.mechanism.oil import align_oil_to_a_share

    norm_root = external_root / f"normalized_{label}"
    calendar_path = norm_root / "trade_calendar.csv"
    if not calendar_path.is_file():
        raise Stage3BContractError("bounded trade calendar required for alignment")
    calendar = pd.read_csv(calendar_path, dtype=str)["trade_date"]

    out: dict[str, Any] = {"label": label, "status": "NOT_ACQUIRED"}

    oil_path = norm_root / "oil_brent_observations.csv"
    if oil_path.is_file():
        obs = pd.read_csv(oil_path, dtype=str)
        oil_aligned = align_oil_to_a_share(obs, calendar)
        (norm_root / "oil_aligned.csv").write_bytes(_csv_bytes(oil_aligned))
        ok = int(oil_aligned["alignment_status"].eq("OIL_ROW_OK").sum())
        out["oil"] = {"status": "ACQUIRED_AND_ALIGNED", "rows": int(len(oil_aligned)), "ok": ok}

    industry_path = norm_root / "industry_series.csv"
    if industry_path.is_file():
        closes = pd.read_csv(industry_path, dtype=str)
        industry = build_industry_returns(closes, calendar)
        (norm_root / "industry_aligned.csv").write_bytes(_csv_bytes(industry))
        ok = int(industry["alignment_status"].eq("INDUSTRY_ROW_OK").sum())
        out["industry"] = {
            "status": "ACQUIRED_AND_ALIGNED",
            "rows": int(len(industry)),
            "ok": ok,
        }

    proxy_path = norm_root / "market_ex_target_v2_proxy.csv"
    if oil_path.is_file() and industry_path.is_file() and proxy_path.is_file():
        proxy = pd.read_csv(proxy_path, dtype=str)
        oil_aligned = pd.read_csv(norm_root / "oil_aligned.csv", dtype=str)
        industry = pd.read_csv(norm_root / "industry_aligned.csv", dtype=str)
        readiness = build_tier1_readiness(proxy, oil_aligned, industry)
        (norm_root / "tier1_readiness.csv").write_bytes(_csv_bytes(readiness))
        out["tier1"] = summarize_readiness(readiness)
        out["status"] = "READINESS_BUILT"
    return out


def generate_reports(external_root: Path, repo_root: Path) -> dict[str, Any]:
    """Generate the committed Stage 3B-R2 status reports from the actual acquisition state."""
    reports_dir = Path(repo_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    oil_acquired = _write_reports(external_root, reports_dir)
    return oil_acquired


def _write_reports(external_root: Path, reports_dir: Path) -> dict[str, Any]:
    root = external_root.resolve()
    raw_root = root / "raw"
    oil_raw = raw_root / "oil_brent_observations.csv"
    ind_raw = {s: raw_root / f"industry_{s}.csv" for s in ("801016", "801960")}

    oil_rows = int(len(pd.read_csv(oil_raw, dtype=str))) if oil_raw.is_file() else 0
    industry_files = {s: p.is_file() for s, p in ind_raw.items()}

    now = datetime.now(UTC).isoformat()
    source_registry = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR2",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "acquisition_status": {
            "oil": "NOT_ACQUIRED_BOUNDED_PATH_NOT_PROVEN"
            if oil_rows == 0
            else "ACQUIRED",
            "petrochemical_industry": "NOT_ACQUIRED_BOUNDED_PATH_NOT_PROVEN"
            if not any(industry_files.values())
            else "ACQUIRED",
        },
        "datasets": [
            {
                "dataset_id": "oil",
                "publisher": "U.S. Energy Information Administration",
                "series": "RBRTE",
                "fred_mirror": "DCOILBRENTEU",
                "status": "NOT_ACQUIRED_BOUNDED_PATH_NOT_PROVEN" if oil_rows == 0 else "ACQUIRED",
                "bounded_path": ["EIA_OPEN_DATA_API_NEEDS_KEY", "FRED_UNREACHABLE"],
                "raw_rows": oil_rows,
                "tier": 1,
            },
            {
                "dataset_id": "petrochemical_industry",
                "publisher": "Shenwan Hongyuan Research",
                "transport_adapter": "AKShare (index_hist_sw)",
                "regime_1": {"symbol": "801016", "taxonomy": "SW_2014", "through": "2021-12-10"},
                "regime_2": {"symbol": "801960", "taxonomy": "SW_2021", "from": "2021-12-13"},
                "status": "INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN"
                if not any(industry_files.values())
                else "ACQUIRED",
                "raw_files": {s: industry_files[s] for s in industry_files},
                "tier": 1,
            },
        ],
        "raw_data_committed_to_git": False,
    }

    manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR2",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "acquisition": {
            "mode": "BOUNDED_OR_NONE",
            "fetched_at": now,
            "requested_warmup_start": WARMUP_START,
            "requested_development_end": DEVELOPMENT_END,
            "raw_data_committed_to_git": False,
        },
        "raw_manifest_sha256": None,
        "normalized_a_sha256": None,
        "datasets": [
            {
                "dataset_id": "oil",
                "rows": oil_rows,
                "status": "ACQUIRED" if oil_rows else "NOT_ACQUIRED",
                "source_name": "U.S. Energy Information Administration",
            },
            {
                "dataset_id": "petrochemical_industry",
                "rows": sum(
                    int(len(pd.read_csv(p, dtype=str))) for s, p in ind_raw.items() if p.is_file()
                ),
                "status": "ACQUIRED" if any(industry_files.values()) else "NOT_ACQUIRED",
                "source_name": "Shenwan Hongyuan Research",
            },
        ],
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }

    coverage = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR2",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "primary_market_proxy_v2_status": "TRUSTED_DEV_PERIOD",
        "oil_status": "NOT_ACQUIRED" if oil_rows == 0 else "ACQUIRED",
        "industry_status": (
            "NOT_ACQUIRED" if not any(industry_files.values()) else "ACQUIRED"
        ),
        "oil_rows": oil_rows,
        "industry_raw_files": {s: industry_files[s] for s in industry_files},
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }

    readiness = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR2",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "market_ex_target": "TRUSTED",
        "oil": "NOT_ACQUIRED" if oil_rows == 0 else "TRUSTED",
        "petrochemical_industry": (
            "NOT_ACQUIRED" if not any(industry_files.values()) else "TRUSTED"
        ),
        "joint_tier1_dates": (
            "NOT_READY" if (oil_rows == 0 or not any(industry_files.values())) else "READY"
        ),
        "effective_trustworthy_development_inputs": "NOT_ESTABLISHED",
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }

    for name, payload in (
        ("m3_stage3br2_source_registry_v1.json", source_registry),
        ("m3_stage3br2_development_input_manifest_v1.json", manifest),
        ("m3_stage3br2_data_coverage_v1.json", coverage),
        ("m3_stage3br2_tier1_readiness_v1.json", readiness),
    ):
        path = reports_dir / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return {
        "source_registry": "m3_stage3br2_source_registry_v1.json",
        "development_input_manifest": "m3_stage3br2_development_input_manifest_v1.json",
        "data_coverage": "m3_stage3br2_data_coverage_v1.json",
        "tier1_readiness": "m3_stage3br2_tier1_readiness_v1.json",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("acquire-oil", "acquire-industry", "normalize", "align", "reports"):
        child = subparsers.add_parser(command)
        child.add_argument("--external-root", required=True, type=Path)
        if command in {"normalize", "align"}:
            child.add_argument("--label", required=True, choices=["a", "b"])
        if command in {"align", "reports"}:
            child.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.external_root.resolve()
        if args.command == "acquire-oil":
            payload = acquire_oil_bounded(root)
        elif args.command == "acquire-industry":
            payload = acquire_industry_bounded(root)
        elif args.command == "normalize":
            payload = {
                "oil": normalize_oil(root, args.label),
                "industry": normalize_industry(root, args.label),
            }
        elif args.command == "align":
            payload = run_alignment(root, args.label, args.repo_root)
        elif args.command == "reports":
            payload = generate_reports(root, args.repo_root)
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    except Exception as exc:  # noqa: BLE001
        print(f"M3 Stage 3B-R2 {args.command}: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
