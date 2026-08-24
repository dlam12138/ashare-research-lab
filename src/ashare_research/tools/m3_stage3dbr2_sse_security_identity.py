"""Fail-closed SSE security-identity recovery for Stage 3D-B-R2.

This module contains the pre-network contract: raw SSE response validation, the
request-type-to-security-field binding, and reconciliation against the immutable
compressed rows of the frozen ``sh_delist.csv`` snapshot.  It deliberately does
not parse prices, build a market proxy, or execute any statistic.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.proxy_v2 import classify_equity

SSE_ENDPOINT = "https://query.sse.com.cn/commonQuery.do"
SSE_SQL_ID = "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L"
SSE_COMPANY_STATUS = "3"
SSE_STOCK_TYPES = (1, 2, 8)

SECURITY_FIELD_BY_TYPE = {1: "A_STOCK_CODE", 2: "B_STOCK_CODE", 8: "A_STOCK_CODE"}
CLASS_BY_TYPE = {1: "A_SHARE_COMMON", 2: "B_SHARE", 8: "A_SHARE_COMMON"}
REQUIRED_COMMON_FIELDS = ("COMPANY_CODE", "LIST_DATE", "DELIST_DATE")

FROZEN_REQUIRED_COLUMNS = ("公司代码", "上市日期", "暂停上市日期")
KNOWN_CONFLICT_COMPANIES = ("600190", "600555", "600614", "600625", "600680", "600695")


class SecurityIdentityRecoveryError(ValueError):
    """A machine-readable, fail-closed R2 identity error."""


def _fail(code: str, detail: str) -> SecurityIdentityRecoveryError:
    return SecurityIdentityRecoveryError(f"{code}:{detail}")


def request_parameters(
    stock_type: int, *, page_no: int = 1, page_size: int = 500
) -> dict[str, str]:
    """Return the frozen SSE request shape for exactly one security type."""

    if stock_type not in SSE_STOCK_TYPES:
        raise ValueError(f"unsupported STOCK_TYPE: {stock_type}")
    if page_no < 1 or page_size < 1:
        raise ValueError("page_no and page_size must be positive")
    return {
        "sqlId": SSE_SQL_ID,
        "isPagination": "true",
        "STOCK_CODE": "",
        "CSRC_CODE": "",
        "REG_PROVINCE": "",
        "STOCK_TYPE": str(stock_type),
        "COMPANY_STATUS": SSE_COMPANY_STATUS,
        "type": "inParams",
        "pageHelp.cacheSize": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.pageSize": str(page_size),
        "pageHelp.pageNo": str(page_no),
        "pageHelp.endPage": str(page_no),
    }


def _as_object(payload: bytes | str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    try:
        parsed = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", "invalid_json") from exc
    if not isinstance(parsed, Mapping):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", "root_not_object")
    return parsed


def _pagination(payload: Mapping[str, Any], result_count: int) -> dict[str, Any]:
    """Prove that a single raw payload is not a silently truncated page."""

    raw = payload.get("pageHelp", payload.get("pagination"))
    if not isinstance(raw, Mapping):
        raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "missing_pageHelp")

    def pick(*names: str) -> Any:
        for name in names:
            if name in raw:
                return raw[name]
        return None

    page_no = pick("pageNo", "page_no", "currentPage", "current_page")
    page_size = pick("pageSize", "page_size", "size")
    total = pick("total", "totalCount", "total_count", "recordCount", "record_count")
    page_count = pick("pageCount", "page_count", "pages", "pageAll")
    try:
        page_no_i = int(page_no)
        page_size_i = int(page_size)
    except (TypeError, ValueError) as exc:
        raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "invalid_page_numbers") from exc
    if page_no_i < 1 or page_size_i < 1:
        raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "non_positive_page_numbers")

    total_i: int | None = None
    if total is not None:
        try:
            total_i = int(total)
        except (TypeError, ValueError) as exc:
            raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "invalid_total") from exc
        if total_i < result_count:
            raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "result_exceeds_total")

    page_count_i: int | None = None
    if page_count is not None:
        try:
            page_count_i = int(page_count)
        except (TypeError, ValueError) as exc:
            raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "invalid_page_count") from exc
        if page_count_i < 1 or page_no_i > page_count_i:
            raise _fail("M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN", "page_out_of_range")

    complete_by_total = total_i is not None and result_count == total_i
    complete_by_page_count = (
        total_i is None and page_count_i == 1 and page_no_i == 1 and result_count <= page_size_i
    )
    if not (complete_by_total or complete_by_page_count):
        raise _fail(
            "M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN",
            f"count={result_count}:total={total_i}:pages={page_count_i}",
        )
    return {
        "page_no": page_no_i,
        "page_size": page_size_i,
        "total": total_i if total_i is not None else result_count,
        "page_count": page_count_i if page_count_i is not None else 1,
        "complete": True,
    }


def _date(value: Any, field: str) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"missing_{field}")
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"invalid_{field}")
    return pd.Timestamp(parsed).date().isoformat()


def _code(value: Any, field: str) -> str:
    if value is None or pd.isna(value):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"missing_{field}")
    text = str(value).strip()
    if not re.fullmatch(r"\d{6}", text):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"invalid_{field}")
    return text


def parse_sse_response(
    payload: bytes | str | Mapping[str, Any], *, stock_type: int
) -> dict[str, Any]:
    """Parse one complete SSE result page without a company-code fallback."""

    if stock_type not in SSE_STOCK_TYPES:
        raise ValueError(f"unsupported STOCK_TYPE: {stock_type}")
    obj = _as_object(payload)
    result = obj.get("result")
    if not isinstance(result, list):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", "result_not_list")
    page = _pagination(obj, len(result))
    identity_field = SECURITY_FIELD_BY_TYPE[stock_type]
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(result):
        if not isinstance(raw, Mapping):
            raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"row_{index}_not_object")
        missing = [field for field in (*REQUIRED_COMMON_FIELDS, identity_field) if field not in raw]
        if missing:
            raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", f"row_{index}:{missing}")
        company_code = _code(raw["COMPANY_CODE"], "COMPANY_CODE")
        security_code = _code(raw[identity_field], identity_field)
        listing_date = _date(raw["LIST_DATE"], "LIST_DATE")
        delisting_date = _date(raw["DELIST_DATE"], "DELIST_DATE")
        expected_class = CLASS_BY_TYPE[stock_type]
        actual_class = classify_equity(security_code)
        if actual_class != expected_class:
            raise _fail(
                "M3_STAGE3DBR2_SECURITY_TYPE_CONFLICT",
                f"type={stock_type}:code={security_code}:class={actual_class}",
            )
        rows.append(
            {
                "company_code": company_code,
                "security_code": security_code,
                "stock_type_request": stock_type,
                "security_type": expected_class,
                "listing_date": listing_date,
                "delisting_date": delisting_date,
                "raw_fields": dict(raw),
            }
        )
    return {"stock_type": stock_type, "rows": rows, "pagination": page}


def resolve_security_identities(
    responses: Mapping[int, bytes | str | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Parse all three type-bound responses and detect security-level date conflicts."""

    if set(responses) != set(SSE_STOCK_TYPES):
        raise _fail("M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE", "all_three_stock_types_required")
    records: list[dict[str, Any]] = []
    for stock_type in SSE_STOCK_TYPES:
        records.extend(parse_sse_response(responses[stock_type], stock_type=stock_type)["rows"])
    by_security: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_security[record["security_code"]].append(record)
    for code, candidates in by_security.items():
        listing = {row["listing_date"] for row in candidates}
        delisting = {row["delisting_date"] for row in candidates}
        if len(listing) > 1 or len(delisting) > 1:
            raise _fail(
                "M3_STAGE3DBR2_SECURITY_LEVEL_CONFLICT",
                f"{code}:listing={sorted(listing)}:delisting={sorted(delisting)}",
            )
    return sorted(records, key=lambda row: (row["company_code"], row["security_code"]))


def _frozen_date(value: Any, field: str) -> str:
    return _date(value, field)


def load_frozen_compressed_rows(path: str | Path) -> list[dict[str, Any]]:
    """Load the frozen row multiset and never reinterpret its company code as a security."""

    source = Path(path)
    try:
        frame = pd.read_csv(source, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        frame = pd.read_csv(source, dtype=str, encoding="gb18030")
    missing = set(FROZEN_REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise _fail("M3_STAGE3DBR2_FROZEN_SCHEMA_FAILURE", str(sorted(missing)))
    rows: list[dict[str, Any]] = []
    for occurrence, row in frame.iterrows():
        company = _code(row["公司代码"], "公司代码")
        listing = _frozen_date(row["上市日期"], "上市日期")
        delisting = _frozen_date(row["暂停上市日期"], "暂停上市日期")
        rows.append(
            {
                "frozen_occurrence": int(occurrence),
                "company_code": company,
                "listing_date": listing,
                "delisting_date": delisting,
                "compressed_key": (company, listing, delisting),
                "company_name": str(row.get("公司简称", "")),
            }
        )
    return rows


def _logical_digest(rows: Iterable[Mapping[str, Any]]) -> str:
    serializable = []
    for row in rows:
        serializable.append(
            {
                "company_code": row["company_code"],
                "security_code": row["security_code"],
                "security_type": row["security_type"],
                "listing_date": row["listing_date"],
                "delisting_date": row["delisting_date"],
                "source_frozen_compressed_key": list(
                    row.get(
                        "source_frozen_compressed_key",
                        (row["company_code"], row["listing_date"], row["delisting_date"]),
                    )
                ),
            }
        )
    encoded = json.dumps(
        sorted(serializable, key=lambda x: tuple(map(str, x.values()))),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def reconcile_frozen_rows(
    frozen_rows: list[dict[str, Any]], direct_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Reconcile a direct SSE identity list to the frozen compressed-row multiset."""

    frozen_counts = Counter(row["compressed_key"] for row in frozen_rows)
    direct_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in direct_rows:
        key = (row["company_code"], row["listing_date"], row["delisting_date"])
        direct_by_key[key].append(row)

    # A raw row for a known company/security with changed dates is drift, not a new row.
    frozen_company_security = {
        (row["company_code"], candidate["security_code"])
        for key in frozen_counts
        for candidate in direct_by_key.get(key, [])
    }
    for row in direct_rows:
        key = (row["company_code"], row["security_code"])
        if key in frozen_company_security:
            exact = (row["company_code"], row["listing_date"], row["delisting_date"])
            if exact not in frozen_counts:
                raise _fail("M3_STAGE3DBR2_METADATA_DATE_DRIFT", str(key))

    unresolved: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for key, count in sorted(frozen_counts.items()):
        candidates = direct_by_key.get(key, [])
        if len(candidates) < count:
            unresolved.append(
                {"compressed_key": key, "frozen_count": count, "direct_count": len(candidates)}
            )
        elif len(candidates) > count:
            ambiguous.append(
                {
                    "compressed_key": key,
                    "frozen_count": count,
                    "direct_count": len(candidates),
                    "distinct_security_codes": sorted({r["security_code"] for r in candidates}),
                }
            )
        else:
            for occurrence, candidate in enumerate(candidates):
                resolved.append(
                    {
                        "security_code": candidate["security_code"],
                        "company_code": key[0],
                        "security_type": candidate["security_type"],
                        "listing_date": key[1],
                        "delisting_date": key[2],
                        "source_frozen_compressed_key": key,
                        "source_raw_type": candidate["stock_type_request"],
                        "metadata_provenance": json.dumps(
                            {
                                "sse_raw_type": candidate["stock_type_request"],
                                "raw_fields": candidate["raw_fields"],
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        "frozen_occurrence": occurrence,
                    }
                )
    if unresolved:
        raise _fail("M3_STAGE3DBR2_FROZEN_ROW_IDENTITY_UNRESOLVED", json.dumps(unresolved))
    if ambiguous:
        raise _fail("M3_STAGE3DBR2_FROZEN_ROW_MULTIPLICITY_AMBIGUOUS", json.dumps(ambiguous))

    extra = [
        row
        for row in direct_rows
        if (row["company_code"], row["listing_date"], row["delisting_date"]) not in frozen_counts
    ]
    known_summary: dict[str, Any] = {}
    for company in KNOWN_CONFLICT_COMPANIES:
        rows = [row for row in resolved if row["company_code"] == company]
        known_summary[company] = {
            "company_code": company,
            "matching_frozen_row_count": len(rows),
            "resolved_security_codes": sorted({row["security_code"] for row in rows}),
            "stock_types": sorted({row["security_type"] for row in rows}),
            "listing_dates": sorted({row["listing_date"] for row in rows}),
            "delisting_dates": sorted({row["delisting_date"] for row in rows}),
            "same_security_code_with_conflicting_dates": False,
            "status": "RESOLVED_AT_SECURITY_LEVEL" if rows else "UNRESOLVED",
        }
    return {
        "resolved_rows": sorted(
            resolved, key=lambda r: (r["company_code"], r["security_code"], r["frozen_occurrence"])
        ),
        "frozen_compressed_row_count": len(frozen_rows),
        "frozen_compressed_unique_key_count": len(frozen_counts),
        "matched_frozen_row_count": len(resolved),
        "unresolved_frozen_row_count": 0,
        "extra_current_sse_rows_ignored": len(extra),
        "extra_current_sse_row_digest": _logical_digest(extra) if extra else None,
        "normalized_logical_digest": _logical_digest(resolved),
        "known_six_conflict_resolution": known_summary,
        "company_code_as_security_id_count": 0,
    }


def write_standardized_csv(result: Mapping[str, Any], path: str | Path) -> None:
    """Write only rows derived from frozen occurrences plus SSE identity enrichment."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "证券代码",
        "公司代码",
        "证券类型",
        "上市日期",
        "终止上市日期",
        "source_frozen_compressed_key",
        "source_raw_type",
        "metadata_provenance",
    ]
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result["resolved_rows"]:
            writer.writerow(
                {
                    "证券代码": row["security_code"],
                    "公司代码": row["company_code"],
                    "证券类型": row["security_type"],
                    "上市日期": row["listing_date"],
                    "终止上市日期": row["delisting_date"],
                    "source_frozen_compressed_key": "|".join(row["source_frozen_compressed_key"]),
                    "source_raw_type": row["source_raw_type"],
                    "metadata_provenance": row["metadata_provenance"],
                }
            )


def repository_relative_digest(
    root: str | Path, relative_paths: Iterable[str]
) -> tuple[str, dict[str, Any]]:
    """Compute the R2 adapter digest from repository-relative source identities only."""

    root_path = Path(root).resolve()
    source_hashes: dict[str, str] = {}
    for relative in sorted(set(relative_paths)):
        path = root_path / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        source_hashes[relative.replace("\\", "/")] = digest
    payload = {
        "digest_algorithm": "M3_REPOSITORY_RELATIVE_DIGEST_V2",
        "source_hashes": source_hashes,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest(), payload
