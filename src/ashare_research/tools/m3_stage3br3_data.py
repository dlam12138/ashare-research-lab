"""Bounded Tier-1 acquisition unblock and data closeout for M3 Stage 3B-R3.

Adds the EIA Open Data API v2 bounded transport (oil) and the Shenwan official-source-resolution
ladder (petrochemical industry) on top of the already-tested Stage 3B-R2 normalize/align/readiness
logic. The EIA API key is read only from the process environment and never persisted or logged.
Real bounded acquisition is attempted once; the offline normalize (A/B) and align pipeline reuse the
R2 functions unchanged. Never reads a date on or after 2023-01-01 and never writes the default
database. A source path that ignores date bounds stays rejected; the honest gap is reported.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.acquisition_eia import (
    ENDPOINT_TEMPLATE_REDACTED,
    STATUS_KEY_REQUIRED,
    acquire_oil_bounded,
    get_eia_api_key,
)
from ashare_research.mechanism.acquisition_shenwan import (
    REGIME_1_SYMBOL,
    REGIME_2_SYMBOL,
    STATUS_CAPSULE_REQUIRED,
    materialize_official_capsule,
    resolve_industry_source,
)
from ashare_research.mechanism.acquisition_shenwan import (
    STATUS_ACQUIRED as INDUSTRY_ACQUIRED,
)
from ashare_research.mechanism.contracts import (
    assert_no_restricted_research_outputs,
)
from ashare_research.mechanism.source_manifest import canonical_frame_digest
from ashare_research.tools.m3_stage3br2_data import (
    normalize_industry,
    normalize_oil,
    run_alignment,
)

HOLDOUT_START = "2023-01-01"
DEVELOPMENT_END = "2022-12-31"
WARMUP_START = "2014-12-01"


def _write_report(reports_dir: Path, name: str, payload: dict[str, Any]) -> None:
    assert_no_restricted_research_outputs(payload)
    path = reports_dir / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_oil_raw(external_root: Path) -> pd.DataFrame | None:
    path = external_root / "raw" / "oil_brent_observations.csv"
    return pd.read_csv(path, dtype=str) if path.is_file() else None


def _read_industry_raw(external_root: Path) -> dict[str, pd.DataFrame | None]:
    return {
        symbol: (
            pd.read_csv(external_root / "raw" / f"industry_{symbol}.csv", dtype=str)
            if (external_root / "raw" / f"industry_{symbol}.csv").is_file()
            else None
        )
        for symbol in (REGIME_1_SYMBOL, REGIME_2_SYMBOL)
    }


def _rows(frame: pd.DataFrame | None) -> int:
    return int(len(frame)) if frame is not None else 0


def generate_reports(external_root: Path, repo_root: Path, label: str = "a") -> dict[str, Any]:
    """Generate the six committed Stage 3B-R3 reports from the actual acquisition state."""
    root = external_root.resolve()
    reports_dir = Path(repo_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()

    oil_raw = _read_oil_raw(root)
    oil_status = "ACQUIRED_AND_SEALED" if oil_raw is not None else STATUS_KEY_REQUIRED
    ind_raw = _read_industry_raw(root)
    industry_files_present = any(v is not None for v in ind_raw.values())
    industry_status = "ACQUIRED_AND_SEALED" if industry_files_present else STATUS_CAPSULE_REQUIRED

    norm_root = root / f"normalized_{label}"
    oil_aligned = (
        pd.read_csv(norm_root / "oil_aligned.csv", dtype=str)
        if (norm_root / "oil_aligned.csv").is_file()
        else None
    )
    industry_aligned = (
        pd.read_csv(norm_root / "industry_aligned.csv", dtype=str)
        if (norm_root / "industry_aligned.csv").is_file()
        else None
    )
    readiness = (
        pd.read_csv(norm_root / "tier1_readiness.csv", dtype=str)
        if (norm_root / "tier1_readiness.csv").is_file()
        else None
    )

    # --- source_resolution -------------------------------------------------
    source_resolution = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "oil": {
            "transport": "EIA_OPEN_DATA_API_V2",
            "benchmark": "Europe Brent Spot Price FOB",
            "series": "RBRTE",
            "unit": "USD_PER_BARREL",
            "auth_method": "ENVIRONMENT_API_KEY",
            "api_key_present": bool(oil_raw is not None or get_eia_api_key() is not None),
            "endpoint_template": ENDPOINT_TEMPLATE_REDACTED,
            "status": oil_status,
            "bounded_start": WARMUP_START,
            "bounded_end": DEVELOPMENT_END,
            "fred_status": "OPTIONAL_SECONDARY_DISTRIBUTION_CROSSCHECK",
        },
        "industry": {
            "publisher": "Shenwan Hongyuan Research",
            "name": "Shenwan Petroleum and Petrochemicals Industry Price Index",
            "regime_1": {"symbol": REGIME_1_SYMBOL, "taxonomy": "SW_2014", "through": "2021-12-10"},
            "regime_2": {"symbol": REGIME_2_SYMBOL, "taxonomy": "SW_2021", "from": "2021-12-13"},
            "transition_gap": "2021-12-13 INDUSTRY_TAXONOMY_TRANSITION_GAP",
            "status": industry_status,
            "route_required": "USER_PROVIDED_OFFICIAL_DEVELOPMENT_CAPSULE",
        },
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(
        reports_dir, "m3_stage3br3_source_resolution_v1.json", source_resolution
    )

    # --- oil_development_manifest ------------------------------------------
    oil_manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "acquisition": {
            "mode": "BOUNDED_EIA_V2",
            "fetched_at": now,
            "requested_warmup_start": WARMUP_START,
            "requested_development_end": DEVELOPMENT_END,
            "auth_method": "ENVIRONMENT_API_KEY",
            "api_key_present": oil_raw is not None,
            "endpoint_template": ENDPOINT_TEMPLATE_REDACTED,
            "raw_data_committed_to_git": False,
        },
        "status": oil_status,
        "raw_sha256": (
            canonical_frame_digest(oil_raw) if oil_raw is not None else None
        ),
        "rows": int(len(oil_raw)) if oil_raw is not None else 0,
        "first_observation": (
            pd.to_datetime(oil_raw["observation_date"]).min().strftime("%Y-%m-%d")
            if oil_raw is not None
            else None
        ),
        "last_observation": (
            pd.to_datetime(oil_raw["observation_date"]).max().strftime("%Y-%m-%d")
            if oil_raw is not None
            else None
        ),
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(
        reports_dir, "m3_stage3br3_oil_development_manifest_v1.json", oil_manifest
    )

    # --- industry_development_manifest -------------------------------------
    industry_manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "acquisition": {
            "mode": "SOURCE_RESOLUTION_LADDER",
            "fetched_at": now,
            "route_required": "USER_PROVIDED_OFFICIAL_DEVELOPMENT_CAPSULE",
            "raw_data_committed_to_git": False,
        },
        "status": industry_status,
        "regime_1": {
            "symbol": REGIME_1_SYMBOL,
            "taxonomy": "SW_2014",
            "through": "2021-12-10",
            "raw_file_present": ind_raw[REGIME_1_SYMBOL] is not None,
            "rows": _rows(ind_raw[REGIME_1_SYMBOL]),
        },
        "regime_2": {
            "symbol": REGIME_2_SYMBOL,
            "taxonomy": "SW_2021",
            "from": "2021-12-13",
            "raw_file_present": ind_raw[REGIME_2_SYMBOL] is not None,
            "rows": _rows(ind_raw[REGIME_2_SYMBOL]),
        },
        "transition_gap": "2021-12-13 INDUSTRY_TAXONOMY_TRANSITION_GAP",
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(
        reports_dir, "m3_stage3br3_industry_development_manifest_v1.json", industry_manifest
    )

    # --- data_coverage ------------------------------------------------------
    data_coverage = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "primary_market_proxy_v2": "TRUSTED_DEV_PERIOD",
        "oil_status": oil_status,
        "industry_status": industry_status,
        "oil_raw_rows": int(len(oil_raw)) if oil_raw is not None else 0,
        "industry_raw_rows": {
            s: (int(len(v)) if v is not None else 0) for s, v in ind_raw.items()
        },
        "oil_aligned_rows": int(len(oil_aligned)) if oil_aligned is not None else 0,
        "industry_aligned_rows": (
            int(len(industry_aligned)) if industry_aligned is not None else 0
        ),
        "readiness_rows": int(len(readiness)) if readiness is not None else 0,
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(reports_dir, "m3_stage3br3_data_coverage_v1.json", data_coverage)

    # --- tier1_readiness_v2 -------------------------------------------------
    oil_ready = oil_aligned is not None and int(
        oil_aligned["alignment_status"].eq("OIL_ROW_OK").sum()
    ) > 0
    industry_ready = industry_aligned is not None and int(
        industry_aligned["alignment_status"].eq("INDUSTRY_ROW_OK").sum()
    ) > 0
    joint_ready = readiness is not None and int(readiness["tier1_joint_valid"].sum()) > 0
    readiness_v2 = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "market_ex_target": "TRUSTED",
        "oil": "TRUSTED" if oil_ready else "NOT_ACQUIRED",
        "petrochemical_industry": "TRUSTED" if industry_ready else "NOT_ACQUIRED",
        "joint_tier1_dates": "READY" if joint_ready else "NOT_READY",
        "joint_outcome": "READY" if joint_ready else (
            "OIL_AUTH_INPUT_REQUIRED" if oil_raw is None else "INDUSTRY_CAPSULE_REQUIRED"
        ),
        "effective_trustworthy_development_inputs": (
            "ESTABLISHED" if joint_ready else "NOT_ESTABLISHED"
        ),
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(reports_dir, "m3_stage3br3_tier1_readiness_v2.json", readiness_v2)

    # --- joint_input_manifest ----------------------------------------------
    joint_manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR3",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "inputs": {
            "market_proxy_v2": "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2",
            "oil": {
                "status": oil_status,
                "raw_rows": int(len(oil_raw)) if oil_raw is not None else 0,
                "logical_sha256": canonical_frame_digest(oil_raw) if oil_raw is not None else None,
            },
            "petrochemical_industry": {
                "status": industry_status,
                "raw_rows": {
                    s: (int(len(v)) if v is not None else 0) for s, v in ind_raw.items()
                },
            },
        },
        "readiness": "NOT_READY" if not joint_ready else "READY",
        "no_holdout_rows": True,
        "stage3c_status": "M3_STAGE3C_NOT_ALLOWED",
    }
    _write_report(reports_dir, "m3_stage3br3_joint_input_manifest_v1.json", joint_manifest)

    return {
        "source_resolution": "m3_stage3br3_source_resolution_v1.json",
        "oil_manifest": "m3_stage3br3_oil_development_manifest_v1.json",
        "industry_manifest": "m3_stage3br3_industry_development_manifest_v1.json",
        "data_coverage": "m3_stage3br3_data_coverage_v1.json",
        "tier1_readiness_v2": "m3_stage3br3_tier1_readiness_v2.json",
        "joint_input_manifest": "m3_stage3br3_joint_input_manifest_v1.json",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "acquire-oil",
        "acquire-industry",
        "normalize",
        "align",
        "reports",
    ):
        child = subparsers.add_parser(command)
        child.add_argument("--external-root", required=True, type=Path)
        if command == "acquire-industry":
            child.add_argument("--user-capsule", required=False, type=Path)
        if command in {"normalize", "align"}:
            child.add_argument("--label", required=True, choices=["a", "b"])
        if command == "align":
            child.add_argument("--repo-root", required=True, type=Path)
        if command == "reports":
            child.add_argument("--repo-root", required=True, type=Path)
            child.add_argument("--label", required=False, default="a", choices=["a", "b"])
    args = parser.parse_args(argv)
    try:
        root = args.external_root.resolve()
        if args.command == "acquire-oil":
            payload = acquire_oil_bounded(root)
        elif args.command == "acquire-industry":
            resolved = resolve_industry_source(
                root, user_capsule=getattr(args, "user_capsule", None)
            )
            if resolved.get("status") == INDUSTRY_ACQUIRED:
                if resolved.get("route") == "C_USER_PROVIDED_OFFICIAL_CAPSULE":
                    materialize_official_capsule(root, resolved["capsule"])
                files = (resolved.get("capsule") or {}).get("files", {})
                payload = {
                    "status": resolved.get("status"),
                    "route": resolved.get("route"),
                    "raw_sha256": {
                        name: files[name]["raw_sha256"] for name in sorted(files)
                    },
                    "codes": resolved.get("codes"),
                }
            else:
                payload = {
                    "status": resolved.get("status"),
                    "codes": resolved.get("codes"),
                    "holdout_read_performed": False,
                }
        elif args.command == "normalize":
            payload = {
                "oil": normalize_oil(root, args.label),
                "industry": normalize_industry(root, args.label),
            }
        elif args.command == "align":
            payload = run_alignment(root, args.label, args.repo_root)
        elif args.command == "reports":
            payload = generate_reports(root, args.repo_root, args.label)
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    except Exception as exc:  # noqa: BLE001
        print(f"M3 Stage 3B-R3 {args.command}: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
