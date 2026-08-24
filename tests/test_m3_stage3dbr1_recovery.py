"""Focused synthetic tests for post-unseal Stage 3D-B-R1 recovery plumbing."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ashare_research.tools.m3_stage3dbr1_market_recovery import (
    ALREADY_ACQUIRED_REQUIRED,
    TRUE_REQUIRED_MISSING,
    RecoveryMetadataError,
    bind_metadata_schema,
    build_holdout_membership,
    build_market_proxy_recovery,
    build_required_series_inventory,
    build_unified_security_master,
    classify_holdout_ever_eligible,
    classify_original_failures,
    repository_relative_digest,
    resolve_capsule_file,
    write_once_overlay,
)


def _current() -> dict[str, pd.DataFrame]:
    return {
        "sh_master_main_a.csv": pd.DataFrame(
            {
                "证券代码": ["600000", "605001", "601857"],
                "上市日期": ["2010-01-01", "2023-01-03", "2007-01-01"],
            }
        ),
        "sh_master_star.csv": pd.DataFrame({"证券代码": ["688001"], "上市日期": ["2019-07-22"]}),
        "sh_master_main_b.csv": pd.DataFrame({"证券代码": ["900001"], "上市日期": ["2010-01-01"]}),
    }


def _delisted() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "公司代码": ["600002", "600003"],
            "上市日期": ["2010-01-01", "2020-01-01"],
            "退市日期": ["2022-12-30", "2023-01-05"],
        }
    )


def _calendar() -> pd.Series:
    return pd.Series(pd.to_datetime(["2022-12-30", "2023-01-03", "2023-01-04", "2023-01-05"]))


def test_schema_binding_uses_actual_columns_and_not_positions(tmp_path: Path) -> None:
    path = tmp_path / "schema.csv"
    path.write_text("证券代码,上市日期\n600000,2020-01-01\n", encoding="utf-8")
    binding = bind_metadata_schema(path, source_kind="current_master")
    assert binding["security_code_column"] == "证券代码"
    assert binding["listing_date_column"] == "上市日期"


def test_schema_binding_rejects_ambiguous_semantic_headers(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text(
        "证券代码,上市日期,首次上市日期\n600000,2020-01-01,2020-01-01\n", encoding="utf-8"
    )
    with pytest.raises(RecoveryMetadataError, match="M3_STAGE3DBR1_METADATA_SCHEMA_AMBIGUOUS"):
        bind_metadata_schema(path, source_kind="current_master")


def test_unified_master_merges_current_and_delisted_without_position_guessing() -> None:
    master = build_unified_security_master(_current(), _delisted())
    assert set(master["symbol"]) == {
        "600000.SH",
        "600002.SH",
        "600003.SH",
        "605001.SH",
        "601857.SH",
        "688001.SH",
        "900001.SH",
    }
    assert master.loc[master["symbol"].eq("600002.SH"), "delisting_date"].iloc[0] == pd.Timestamp(
        "2022-12-30"
    )
    assert master.loc[master["symbol"].eq("900001.SH"), "classification"].iloc[0] == "B_SHARE"


def test_unified_master_rejects_conflicting_duplicate_metadata() -> None:
    conflict = _delisted().copy()
    conflict.loc[1, "公司代码"] = "600002"
    with pytest.raises(RecoveryMetadataError, match="M3_STAGE3DBR1_SECURITY_MASTER_CONFLICT"):
        build_unified_security_master(_current(), conflict)


def test_unified_master_rejects_missing_listing_metadata() -> None:
    missing = _current()["sh_master_main_a.csv"].copy()
    missing.loc[0, "上市日期"] = None
    with pytest.raises(RecoveryMetadataError, match="M3_STAGE3DBR1_METADATA_INSUFFICIENT"):
        build_unified_security_master({"main": missing}, _delisted())


def test_exact_t_minus_one_membership_boundaries() -> None:
    current = {
        "main": pd.DataFrame(
            {
                "证券代码": ["600010", "600011", "600012", "600013"],
                "上市日期": ["2023-01-03", "2023-01-04", "2020-01-01", "2020-01-01"],
            }
        )
    }
    delisted = pd.DataFrame(
        {
            "公司代码": ["600012", "600013"],
            "上市日期": ["2020-01-01", "2020-01-01"],
            "退市日期": ["2023-01-04", "2023-01-05"],
        }
    )
    master = build_unified_security_master(current, delisted)
    marked = classify_holdout_ever_eligible(master, _calendar())
    values = marked.set_index("symbol")["ever_eligible_in_holdout"].to_dict()
    detail = build_holdout_membership(master, _calendar())
    first_day = detail.loc[detail["trade_date"].eq(pd.Timestamp("2023-01-03"))].set_index("symbol")
    assert (
        bool(first_day.loc["600010.SH", "in_expected_universe"]) is False
    )  # listing == current trade date
    assert values["600011.SH"] is True
    assert values["600012.SH"] is True  # delisting == previous day still eligible on t
    assert values["600013.SH"] is True  # delisting > previous day


def test_target_b_share_and_cdr_are_not_required() -> None:
    current = {
        "main": pd.DataFrame(
            {
                "证券代码": ["601857", "900001", "689001", "688001"],
                "上市日期": ["2007-01-01"] * 4,
            }
        )
    }
    delisted = pd.DataFrame({"公司代码": [], "上市日期": [], "退市日期": []})
    master = build_unified_security_master(current, delisted)
    inventory = build_required_series_inventory(master, _calendar(), [])
    assert set(inventory["symbol"]) == {"688001.SH"}


def test_ever_eligible_inventory_is_not_available_file_subset() -> None:
    master = build_unified_security_master(_current(), _delisted())
    inventory = build_required_series_inventory(master, _calendar(), ["600000.SH"])
    statuses = inventory.set_index("symbol")["series_status"].to_dict()
    assert statuses["600000.SH"] == ALREADY_ACQUIRED_REQUIRED
    assert statuses["688001.SH"] == TRUE_REQUIRED_MISSING


def test_original_failed_symbols_are_classified_by_membership() -> None:
    master = classify_holdout_ever_eligible(
        build_unified_security_master(_current(), _delisted()), _calendar()
    )
    classified = classify_original_failures(["600000", "600002", "605001"], master)
    assert "600002" in classified["failed_but_never_eligible"]
    assert "605001" in classified["failed_and_ever_eligible"]
    assert "600000" in classified["failed_and_ever_eligible"]


def test_missing_full_series_stays_in_denominator_and_invalidates_row() -> None:
    master = build_unified_security_master(
        {"main": pd.DataFrame({"证券代码": ["600000", "600002"], "上市日期": ["2020-01-01"] * 2})},
        pd.DataFrame({"公司代码": [], "上市日期": [], "退市日期": []}),
    )
    calendar = _calendar()
    closes = pd.DataFrame(
        {
            "symbol": ["600000.SH"] * 4,
            "trade_date": calendar,
            "close": [10.0, 10.1, 10.2, 10.3],
        }
    )
    proxy, audit = build_market_proxy_recovery(closes, master, calendar)
    row = proxy.loc[proxy["trade_date"].eq(pd.Timestamp("2023-01-03"))].iloc[0]
    assert row["eligible_count"] == 2
    assert row["observable_count"] == 1
    assert row["row_status"] == "PROXY_ROW_INVALID_DATA_GAP"
    assert audit.loc[audit["symbol"].eq("600002.SH"), "in_expected_universe"].any()


def test_base_overlay_prefers_base_and_rejects_conflicting_bytes(tmp_path: Path) -> None:
    base = tmp_path / "base"
    overlay = tmp_path / "overlay"
    (base / "raw").mkdir(parents=True)
    (overlay / "raw").mkdir(parents=True)
    (base / "raw" / "daily_600000.csv").write_bytes(b"base")
    (overlay / "raw" / "daily_600000.csv").write_bytes(b"base")
    resolved = resolve_capsule_file(base, overlay, "raw/daily_600000.csv")
    assert resolved["source"] == "BASE"
    (overlay / "raw" / "daily_600000.csv").write_bytes(b"different")
    with pytest.raises(RecoveryMetadataError, match="M3_STAGE3DBR1_BASE_OVERLAY_CONFLICT"):
        resolve_capsule_file(base, overlay, "raw/daily_600000.csv")


def test_overlay_write_once_is_idempotent_and_immutable(tmp_path: Path) -> None:
    path = tmp_path / "overlay" / "daily_600000.csv"
    assert write_once_overlay(path, b"one")
    assert write_once_overlay(path, b"one")
    with pytest.raises(RecoveryMetadataError, match="M3_STAGE3DBR1_OVERLAY_IMMUTABLE_CONFLICT"):
        write_once_overlay(path, b"two")


def test_recovery_digest_is_repository_relative(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    digest, payload = repository_relative_digest(tmp_path, ["a.txt"])
    assert len(digest) == 64
    assert set(payload["source_hashes"]) == {"a.txt"}
    assert not Path(next(iter(payload["source_hashes"]))).is_absolute()
