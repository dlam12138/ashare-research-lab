"""Metadata-only boundary runner for Stage 3D-B-R2.

The runner is intentionally separate from the parser.  It will not issue an SSE
request unless an immutable pre-metadata CI marker exists, and it has no imports
for price acquisition, proxy construction, FRED, CNI, regression, or bootstrap.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ashare_research.tools.m3_stage3dbr2_sse_security_identity import (
    SSE_ENDPOINT,
    SSE_STOCK_TYPES,
    _as_object,
    load_frozen_compressed_rows,
    parse_sse_response,
    reconcile_frozen_rows,
    request_parameters,
    resolve_security_identities,
    write_standardized_csv,
)

RawOpener = Callable[..., Any]


def _request_page(stock_type: int, page_no: int, *, opener: RawOpener = urlopen) -> dict[str, Any]:
    params = request_parameters(stock_type, page_no=page_no)
    request = Request(
        f"{SSE_ENDPOINT}?{urlencode(params)}",
        headers={
            "Accept": "*/*",
            "Referer": "https://www.sse.com.cn/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with opener(request, timeout=30) as response:
            raw = response.read()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"M3_STAGE3DBR2_SSE_REQUEST_FAILED:type={stock_type}:page={page_no}"
        ) from exc
    return dict(_as_object(raw))


def _page_count(payload: dict[str, Any], stock_type: int) -> tuple[list[Any], int, int]:
    result = payload.get("result")
    page_help = payload.get("pageHelp")
    if not isinstance(result, list) or not isinstance(page_help, dict):
        raise RuntimeError(f"M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN:type={stock_type}")
    try:
        page_no = int(page_help["pageNo"])
        page_count = int(page_help.get("pageCount", page_help.get("pageAll")))
        total = int(page_help.get("total", page_help.get("totalCount", len(result))))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN:type={stock_type}") from exc
    if page_no < 1 or page_count < 1 or total < len(result) or page_no > page_count:
        raise RuntimeError(f"M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN:type={stock_type}")
    return result, page_count, total


def fetch_complete_sse_type(stock_type: int, *, opener: RawOpener = urlopen) -> dict[str, Any]:
    """Fetch all pages for one type, then parse one completeness-proven aggregate."""

    first = _request_page(stock_type, 1, opener=opener)
    result, page_count, total = _page_count(first, stock_type)
    all_rows = list(result)
    for page_no in range(2, page_count + 1):
        page = _request_page(stock_type, page_no, opener=opener)
        page_rows, observed_page_count, observed_total = _page_count(page, stock_type)
        if observed_page_count != page_count or observed_total != total:
            raise RuntimeError(f"M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN:type={stock_type}")
        all_rows.extend(page_rows)
    if len(all_rows) != total:
        raise RuntimeError(f"M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN:type={stock_type}")
    aggregate = {
        "result": all_rows,
        "pageHelp": {
            "pageNo": 1,
            "pageSize": max(len(all_rows), 1),
            "pageCount": 1,
            "total": total,
        },
        "request": request_parameters(stock_type),
    }
    # parse_sse_response is the final schema/type gate for the complete aggregate.
    parse_sse_response(aggregate, stock_type=stock_type)
    return aggregate


def _write_once_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"M3_STAGE3DBR2_RAW_IMMUTABLE_CONFLICT:{path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def run_metadata_recovery(
    *,
    external_root: str | Path,
    frozen_delist_path: str | Path,
    pre_metadata_marker: str | Path,
    output_repo_root: str | Path,
    opener: RawOpener = urlopen,
) -> dict[str, Any]:
    """Run only the post-CI SSE metadata recovery and frozen-row reconciliation."""

    marker = Path(pre_metadata_marker)
    if not marker.is_file():
        raise RuntimeError("M3_STAGE3DBR2_PRE_METADATA_CI_MARKER_REQUIRED")
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    if marker_payload.get("price_statistic_observed") is not False:
        raise RuntimeError("M3_STAGE3DBR2_STATISTIC_BOUNDARY_VIOLATION")
    root = Path(external_root)
    raw_root = root / "raw" / "sse"
    raw_root.mkdir(parents=True, exist_ok=True)
    responses: dict[int, dict[str, Any]] = {}
    raw_sha256: dict[str, str] = {}
    for stock_type in SSE_STOCK_TYPES:
        payload = fetch_complete_sse_type(stock_type, opener=opener)
        path = raw_root / f"delist_type_{stock_type}.json"
        _write_once_json(path, payload)
        responses[stock_type] = payload
        import hashlib

        raw_sha256[str(stock_type)] = hashlib.sha256(path.read_bytes()).hexdigest()
    frozen_rows = load_frozen_compressed_rows(frozen_delist_path)
    direct_rows = resolve_security_identities(responses)
    reconciliation = reconcile_frozen_rows(frozen_rows, direct_rows)
    normalized_path = root / "normalized" / "frozen_delist_security_level.csv"
    write_standardized_csv(reconciliation, normalized_path)
    manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3DBR2",
        "status": "SSE_SECURITY_LEVEL_IDENTITY_RECOVERED",
        "source_class": "SAME_OFFICIAL_SOURCE_RAW_FIELD_PRESERVATION",
        "endpoint": SSE_ENDPOINT,
        "sql_id": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
        "company_status": "3",
        "stock_type_requests": [1, 2, 8],
        "frozen_sh_delist_sha": _sha256(Path(frozen_delist_path)),
        "type_raw_sha256": raw_sha256,
        "raw_result_counts": {str(t): len(responses[t]["result"]) for t in SSE_STOCK_TYPES},
        "frozen_compressed_row_count": reconciliation["frozen_compressed_row_count"],
        "frozen_compressed_unique_key_count": reconciliation["frozen_compressed_unique_key_count"],
        "matched_frozen_row_count": reconciliation["matched_frozen_row_count"],
        "unresolved_frozen_row_count": reconciliation["unresolved_frozen_row_count"],
        "extra_current_sse_rows_ignored_count": reconciliation["extra_current_sse_rows_ignored"],
        "standardized_security_level_row_count": len(reconciliation["resolved_rows"]),
        "a_share_row_count": sum(
            r["security_type"] == "A_SHARE_COMMON" for r in reconciliation["resolved_rows"]
        ),
        "b_share_row_count": sum(
            r["security_type"] == "B_SHARE" for r in reconciliation["resolved_rows"]
        ),
        "normalized_logical_digest": reconciliation["normalized_logical_digest"],
        "known_six_conflict_resolution": reconciliation["known_six_conflict_resolution"],
        "company_code_as_security_id_count": 0,
        "price_bytes_parsed_after_r2": False,
        "market_proxy": False,
        "fred": False,
        "cni": False,
        "crash": False,
        "ols": False,
        "bootstrap": False,
        "gamma": False,
    }
    report = (
        Path(output_repo_root) / "reports" / "m3_stage3dbr2_sse_security_identity_manifest_v1.json"
    )
    _write_once_json(report, manifest)
    return manifest


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True, type=Path)
    parser.add_argument("--frozen-delist", required=True, type=Path)
    parser.add_argument("--pre-metadata-marker", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(
            json.dumps(
                run_metadata_recovery(
                    external_root=args.external_root,
                    frozen_delist_path=args.frozen_delist,
                    pre_metadata_marker=args.pre_metadata_marker,
                    output_repo_root=args.repo_root,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"M3 Stage 3D-B-R2 metadata recovery: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
