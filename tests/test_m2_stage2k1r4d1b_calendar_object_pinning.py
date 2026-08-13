"""M2 Stage 2K.1R4D.1b — Calendar object pinning closeout.

Covers the R4D.1b fix: ``load_market_calendar`` must read the single exact
content-addressed calendar object pinned by the committed market-calendar
registry, and must never scan the cache directory or fall back to another
parquet when the pinned object is absent or corrupt.

Behaviour verified:

- pinned object present with correct content address  -> PASS
- pinned object missing but an older parquet exists    -> FAIL (no fallback)
- filename is the expected sha but content sha differs -> FAIL
- registry row_count mismatch                          -> FAIL
- duplicate or non-increasing trade_date               -> FAIL
- required coverage start not reached                  -> FAIL
- required coverage end not reached                    -> FAIL
- correct object and an older object coexist           -> only the pinned
  object is used

Also covers the registry contract validator (a registry that would allow
scanning/fallback is rejected) and, when the real baostock snapshot is present
locally, an integration check that the committed registry pins the real object.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.pit_valuation.contracts import (
    CalendarCoverageGapError,
    load_market_calendar_registry,
    validate_market_calendar_registry,
)
from ashare_research.pit_valuation.fact_builder import load_market_calendar

ROOT = Path(__file__).resolve().parents[1]

# A representative pinned calendar (matches the real extended object's
# first/last trading day and a May-Day crossing).
TRADE_DATES = [
    "2020-01-02",
    "2020-01-03",
    "2020-04-30",
    "2020-05-06",
    "2020-05-07",
    "2026-08-04",
    "2026-08-05",
]

# The oldest short-range calendar (begins 2021-01-04) that must never be
# selected when the pinned object is absent.
OLD_TRADE_DATES = ["2021-01-04", "2021-01-05", "2026-08-04", "2026-08-05"]

PINNED_SHA = (
    "77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d"
)


def _df(trade_dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": "sh.601857",
            "trade_date": pd.to_datetime(trade_dates),
            "is_trading": [True] * len(trade_dates),
        }
    )


def _registry(**overrides) -> dict:
    """A registry pinned to the real object, overridable per test."""
    reg = {
        "schema": "pit_valuation_market_calendar_registry_v1",
        "provider": "baostock",
        "symbol": "601857.SH",
        "object_sha256": PINNED_SHA,
        "object_key": f"{PINNED_SHA}.parquet",
        "row_count": len(TRADE_DATES),
        "first_trading_day": "2020-01-02",
        "last_trading_day": "2026-08-05",
        "evidence_cutoff": "2026-08-02",
        "resolver_contract": "explicit_content_addressed_object_no_scan_no_fallback",
    }
    reg.update(overrides)
    return reg


def _provision(root: Path, trade_dates: list[str]) -> tuple[Path, dict]:
    """Write a self-consistent content-addressed parquet + matching registry.

    The object is named by its own sha256 so the loader's content-address
    check passes; the registry records that sha and the structural facts.
    """
    df = _df(trade_dates)
    tmp = root / "tmp.parquet"
    df.to_parquet(tmp)
    sha = hashlib.sha256(tmp.read_bytes()).hexdigest()
    path = root / f"{sha}.parquet"
    tmp.rename(path)
    reg = _registry(
        object_sha256=sha,
        object_key=f"{sha}.parquet",
        row_count=len(trade_dates),
        first_trading_day=trade_dates[0],
        last_trading_day=trade_dates[-1],
    )
    return path, reg


def _load(root: Path, registry: dict, **load_kw):
    return load_market_calendar(root, registry=registry, **load_kw)


# ── 1. pinned object present, content address correct -> PASS ──────────────


def test_pinned_object_present_and_correct_passes(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    _, reg = _provision(root, TRADE_DATES)
    cal = _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")
    assert cal["calendar_sha256"] == reg["object_sha256"]
    assert cal["trade_dates"][0] == "2020-01-02"
    assert cal["trade_dates"][-1] == "2026-08-05"
    assert len(cal["trade_dates"]) == len(TRADE_DATES)


# ── 2. pinned object missing, older parquet present -> FAIL (no fallback) ──


def test_pinned_object_missing_does_not_fall_back(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    # Only the older short-range calendar is present; the pinned object is not.
    _df(OLD_TRADE_DATES).to_parquet(root / f"{'a' * 64}.parquet")
    with pytest.raises(CalendarCoverageGapError, match="missing"):
        _load(root, _registry(), required_start="2020-01-02", required_end="2026-08-05")


# ── 3. filename is expected sha, content sha differs -> FAIL ───────────────


def test_content_sha_mismatch_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    path, reg = _provision(root, TRADE_DATES)
    # Overwrite the file with different content, keeping the pinned filename.
    _df(OLD_TRADE_DATES).to_parquet(path)
    with pytest.raises(CalendarCoverageGapError, match="does not match"):
        _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")


# ── 4. registry row_count mismatch -> FAIL ─────────────────────────────────


def test_row_count_mismatch_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    _, reg = _provision(root, TRADE_DATES)
    reg["row_count"] = len(TRADE_DATES) + 1
    with pytest.raises(CalendarCoverageGapError, match="row_count"):
        _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")


# ── 5. duplicate / non-increasing trade_date -> FAIL ───────────────────────


def test_duplicate_trade_date_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    dup = ["2020-01-02", "2020-01-02", "2020-05-06", "2026-08-05"]
    _, reg = _provision(root, dup)
    with pytest.raises(CalendarCoverageGapError, match="duplicate"):
        _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")


def test_non_increasing_trade_date_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    unsorted = ["2020-05-06", "2020-01-02", "2026-08-05"]
    _, reg = _provision(root, unsorted)
    with pytest.raises(CalendarCoverageGapError, match="strictly increasing"):
        _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")


# ── 6. required coverage start not reached -> FAIL ─────────────────────────


def test_coverage_start_not_reached_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    _, reg = _provision(root, TRADE_DATES)
    # required_start is earlier than the calendar's first trading day.
    with pytest.raises(CalendarCoverageGapError, match="coverage gap"):
        _load(root, reg, required_start="2018-01-01", required_end="2026-08-05")


# ── 7. required coverage end not reached -> FAIL ───────────────────────────


def test_coverage_end_not_reached_fails(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    _, reg = _provision(root, TRADE_DATES)
    # required_end is later than the calendar's last trading day.
    with pytest.raises(CalendarCoverageGapError, match="coverage gap"):
        _load(root, reg, required_start="2020-01-02", required_end="2026-12-31")


# ── 8. correct + older object coexist -> only pinned object is used ────────


def test_correct_and_older_object_coexist_uses_pinned(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    # Older short-range calendar present alongside the pinned object.
    _df(OLD_TRADE_DATES).to_parquet(root / f"{'b' * 64}.parquet")
    pinned_path, reg = _provision(root, TRADE_DATES)
    cal = _load(root, reg, required_start="2020-01-02", required_end="2026-08-05")
    # The pinned object (2020 start) is read, never the older 2021 calendar.
    assert cal["calendar_object_id"] == pinned_path.name
    assert cal["trade_dates"][0] == "2020-01-02"


# ── registry contract: scanning/fallback is rejected ───────────────────────


def test_registry_forbidding_fallback_is_rejected():
    with pytest.raises(ValueError, match="forbid scanning"):
        validate_market_calendar_registry(
            _registry(resolver_contract="scan_directory_fallback")
        )


def test_registry_validates():
    validate_market_calendar_registry(_registry())


# ── integration: committed registry pins the real local object (skip if absent)

REAL_CACHE = ROOT / "tmp" / "market_cache" / "baostock"


def test_committed_registry_pins_real_local_object():
    pinned = REAL_CACHE / f"{PINNED_SHA}.parquet"
    if not pinned.is_file():
        pytest.skip("real baostock snapshot not present in repo")
    registry = load_market_calendar_registry()
    validate_market_calendar_registry(registry)
    assert registry["object_sha256"] == PINNED_SHA
    cal = load_market_calendar(
        REAL_CACHE, registry=registry, required_start="2020-04-30"
    )
    assert cal["calendar_sha256"] == PINNED_SHA
    assert cal["trade_dates"][0] == "2020-01-02"
    assert cal["trade_dates"][-1] == "2026-08-05"
    assert len(cal["trade_dates"]) == registry["row_count"]
