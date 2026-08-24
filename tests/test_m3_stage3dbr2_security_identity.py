"""Synthetic-only tests for Stage 3D-B-R2 security identity recovery."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ashare_research.tools.m3_stage3dbr2_sse_security_identity import (
    SecurityIdentityRecoveryError,
    load_frozen_compressed_rows,
    parse_sse_response,
    reconcile_frozen_rows,
    request_parameters,
    resolve_security_identities,
    write_standardized_csv,
)


def _payload(stock_type: int, result: list[dict], **page_help: object) -> dict:
    return {
        "result": result,
        "pageHelp": {"pageNo": 1, "pageSize": 500, "pageCount": 1, **page_help},
    }


def _row(
    company: str, security: str, listing: str = "2000-01-01", delisting: str = "2020-01-01"
) -> dict:
    return {
        "COMPANY_CODE": company,
        "A_STOCK_CODE": security,
        "B_STOCK_CODE": security,
        "LIST_DATE": listing,
        "DELIST_DATE": delisting,
        "SEC_NAME_CN": "synthetic",
    }


def _responses(rows1=None, rows2=None, rows8=None):
    return {
        1: _payload(1, rows1 or []),
        2: _payload(2, rows2 or []),
        8: _payload(8, rows8 or []),
    }


def _frozen(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "sh_delist.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_request_types_are_separate_and_type_bound() -> None:
    assert [request_parameters(t)["STOCK_TYPE"] for t in (1, 2, 8)] == ["1", "2", "8"]
    assert request_parameters(1)["COMPANY_STATUS"] == "3"
    with pytest.raises(ValueError):
        request_parameters(128)


def test_company_code_is_never_used_as_security_identity() -> None:
    parsed = resolve_security_identities(_responses(rows1=[_row("600190", "600191")]))
    assert parsed[0]["security_code"] == "600191"
    assert parsed[0]["security_code"] != parsed[0]["company_code"]


def test_type_1_and_8_select_a_stock_code() -> None:
    rows = _responses(rows1=[_row("600001", "600002")], rows8=[_row("600003", "600004")])
    result = resolve_security_identities(rows)
    assert {row["security_code"] for row in result} == {"600002", "600004"}
    assert {row["stock_type_request"] for row in result} == {1, 8}


def test_type_2_selects_b_stock_code() -> None:
    result = resolve_security_identities(_responses(rows2=[_row("600001", "900001")]))
    assert result[0]["security_code"] == "900001"
    assert result[0]["security_type"] == "B_SHARE"


@pytest.mark.parametrize("field", ["A_STOCK_CODE", "COMPANY_CODE", "LIST_DATE", "DELIST_DATE"])
def test_required_raw_schema_missing_fails_closed(field: str) -> None:
    row = _row("600001", "600002")
    row.pop(field)
    with pytest.raises(SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE"):
        parse_sse_response(_payload(1, [row]), stock_type=1)


def test_missing_b_security_code_fails_closed() -> None:
    row = _row("600001", "900001")
    row.pop("B_STOCK_CODE")
    with pytest.raises(SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SSE_RAW_SCHEMA_FAILURE"):
        parse_sse_response(_payload(2, [row]), stock_type=2)


def test_invalid_type_class_fails_closed() -> None:
    with pytest.raises(SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SECURITY_TYPE_CONFLICT"):
        parse_sse_response(_payload(2, [_row("600001", "600002")]), stock_type=2)


def test_pagination_must_be_proven() -> None:
    payload = {"result": [_row("600001", "600002")]}
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN"
    ):
        parse_sse_response(payload, stock_type=1)


def test_pagination_total_must_match() -> None:
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SSE_PAGINATION_NOT_PROVEN"
    ):
        parse_sse_response(_payload(1, [_row("600001", "600002")], total=2), stock_type=1)


def test_same_security_conflicting_listing_fails() -> None:
    responses = _responses(
        rows1=[_row("600001", "600002", "2000-01-01")],
        rows8=[_row("600001", "600002", "2001-01-01")],
    )
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SECURITY_LEVEL_CONFLICT"
    ):
        resolve_security_identities(responses)


def test_same_security_conflicting_delisting_fails() -> None:
    responses = _responses(
        rows1=[_row("600001", "600002", delisting="2020-01-01")],
        rows8=[_row("600001", "600002", delisting="2021-01-01")],
    )
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_SECURITY_LEVEL_CONFLICT"
    ):
        resolve_security_identities(responses)


def test_company_to_a_and_b_one_to_many_is_accepted(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path,
        [
            {
                "公司代码": "600001",
                "公司简称": "x",
                "上市日期": "2000-01-01",
                "暂停上市日期": "2020-01-01",
            },
            {
                "公司代码": "600001",
                "公司简称": "x",
                "上市日期": "2000-01-01",
                "暂停上市日期": "2020-01-01",
            },
        ],
    )
    rows = resolve_security_identities(
        _responses(rows1=[_row("600001", "600002")], rows2=[_row("600001", "900001")])
    )
    result = reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)
    assert {r["security_code"] for r in result["resolved_rows"]} == {"600002", "900001"}
    assert result["matched_frozen_row_count"] == 2


def test_same_dates_multiset_is_not_collapsed(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path,
        [
            {
                "公司代码": "600001",
                "公司简称": "x",
                "上市日期": "2000-01-01",
                "暂停上市日期": "2020-01-01",
            },
            {
                "公司代码": "600001",
                "公司简称": "x",
                "上市日期": "2000-01-01",
                "暂停上市日期": "2020-01-01",
            },
        ],
    )
    rows = resolve_security_identities(
        _responses(rows1=[_row("600001", "600002")], rows8=[_row("600001", "600003")])
    )
    result = reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)
    assert len(result["resolved_rows"]) == 2


def test_missing_frozen_row_fails_closed(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path, [{"公司代码": "600001", "上市日期": "2000-01-01", "暂停上市日期": "2020-01-01"}]
    )
    rows = resolve_security_identities(_responses())
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_FROZEN_ROW_IDENTITY_UNRESOLVED"
    ):
        reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)


def test_extra_current_sse_row_is_ignored(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path, [{"公司代码": "600001", "上市日期": "2000-01-01", "暂停上市日期": "2020-01-01"}]
    )
    rows = resolve_security_identities(
        _responses(rows1=[_row("600001", "600002"), _row("600009", "600010")])
    )
    result = reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)
    assert result["extra_current_sse_rows_ignored"] == 1
    assert len(result["resolved_rows"]) == 1


def test_frozen_set_does_not_expand(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path, [{"公司代码": "600001", "上市日期": "2000-01-01", "暂停上市日期": "2020-01-01"}]
    )
    rows = resolve_security_identities(
        _responses(rows1=[_row("600001", "600002"), _row("600009", "600010")])
    )
    result = reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)
    assert {row["company_code"] for row in result["resolved_rows"]} == {"600001"}


def test_ambiguous_extra_matching_security_fails(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path, [{"公司代码": "600001", "上市日期": "2000-01-01", "暂停上市日期": "2020-01-01"}]
    )
    rows = resolve_security_identities(
        _responses(rows1=[_row("600001", "600002")], rows8=[_row("600001", "600003")])
    )
    with pytest.raises(
        SecurityIdentityRecoveryError, match="M3_STAGE3DBR2_FROZEN_ROW_MULTIPLICITY_AMBIGUOUS"
    ):
        reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)


def test_standardized_output_never_uses_company_code(tmp_path: Path) -> None:
    frozen = _frozen(
        tmp_path, [{"公司代码": "600001", "上市日期": "2000-01-01", "暂停上市日期": "2020-01-01"}]
    )
    rows = resolve_security_identities(_responses(rows1=[_row("600001", "600002")]))
    result = reconcile_frozen_rows(load_frozen_compressed_rows(frozen), rows)
    output = tmp_path / "normalized" / "frozen_delist_security_level.csv"
    write_standardized_csv(result, output)
    frame = pd.read_csv(output, dtype=str)
    assert frame.loc[0, "证券代码"] == "600002"
    assert frame.loc[0, "公司代码"] == "600001"
