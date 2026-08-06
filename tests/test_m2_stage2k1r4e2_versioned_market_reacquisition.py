"""M2 Stage 2K.1R4E.2 — versioned dual-source market snapshot reacquisition tests.

Covers the frozen acquisition contract, the canonical normalization + content
addressing, A/B stability, the acquisition receipt, the registry-v3 supersession
contract, the old/new Baostock revision diff, the real reconciliation reuse,
the explicit-registry formal release, and the product-boundary invariants.
All network acquisition is mocked; every run is offline and deterministic.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation import (
    market_snapshot_acquisition as acq,
)
from ashare_research.pit_valuation.series_contract import SYMBOL
from ashare_research.tools.m2_stage2k1r4e2_reacquire_market_snapshots import (
    DECISION_ALLOWED,
    DECISION_GAPS,
    DECISION_NOT_TRUSTED,
    _build_registry_v3,
    _revision_diff,
    build_parser,
    decision_to_exit_code,
)
from ashare_research.tools.m2_stage2k1r4e2_reacquire_market_snapshots import (
    main as cli_main,
)

REPO = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (REPO / "config" / "pit_valuation_market_snapshot_acquisition_v1.json")
    .read_text(encoding="utf-8")
)
REGISTRY_V2 = json.loads(
    (REPO / "events" / "market_data_snapshot_registry.json").read_text(encoding="utf-8")
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _market_dates() -> list[str]:
    from datetime import date, timedelta

    dates: list[str] = []
    d = date(2021, 1, 4)
    end = date(2026, 7, 31)
    while d <= end:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    return dates


def _baostock_raw(dates) -> list[dict]:
    return [
        {
            "trade_date": d,
            "open": "4.15", "high": "4.20", "low": "4.14", "close": "4.19",
            "volume": 96907113, "amount": "403962846.32", "is_trading": True,
        }
        for d in dates
    ]


def _akshare_raw(dates) -> list[dict]:
    return [
        {
            "trade_date": d,
            "open": "4.15", "high": "4.20", "low": "4.14", "close": "4.19",
            "volume": 969071, "amount": "403962848.0", "is_trading": True,
        }
        for d in dates
    ]


def _registry_v3(baostock_sha: str, akshare_sha: str, *, status: str = "pass",
                 row_count: int = 1351, ak_dates=None) -> dict:
    ak_count = len(ak_dates) if ak_dates is not None else row_count
    return {
        "contract": "market_data_snapshot_registry_v3",
        "schema_version": "3.0",
        "supersedes_registry": "events/market_data_snapshot_registry.json",
        "supersession_reason": "pinned_secondary_object_unrecoverable_versioned_reacquisition",
        "data_class": "external_real_data_cache",
        "acquisition_batch_id": "b" * 64,
        "symbol": SYMBOL,
        "date_range": {"actual_start": "2021-01-04", "actual_end": "2026-07-31"},
        "adjustment": "none",
        "providers": [
            {
                "provider": "baostock", "provider_version": "0.9.3",
                "object_key": f"baostock/{baostock_sha}.parquet", "sha256": baostock_sha,
                "row_count": row_count, "adjustment": "none",
                "date_range": {"start": "2021-01-04", "end": "2026-07-31"},
            },
            {
                "provider": "akshare", "provider_version": "1.18.79",
                "object_key": f"akshare/{akshare_sha}.parquet", "sha256": akshare_sha,
                "row_count": ak_count, "adjustment": "none",
                "date_range": {"start": "2021-01-04", "end": "2026-07-31"},
            },
        ],
        "ab_stability": "ACQUISITION_STABLE",
        "reconciliation_status": status,
    }


def _write_object(root: Path, provider: str, rows: list[dict]) -> str:
    rec = acq.normalize_market_snapshot(
        rows, provider=provider, provider_version=CONTRACT["provider_versions"][provider],
        contract=CONTRACT,
    )
    path, sha = acq.write_content_addressed_snapshot(rec, root, provider)
    return sha


# ── acquisition contract freeze ────────────────────────────────────────────


def test_akshare_param_freeze():
    ak = CONTRACT["akshare"]
    assert ak["function"] == "ak.stock_zh_a_hist"
    assert ak["symbol"] == "601857"
    assert ak["period"] == "daily"
    assert ak["start_date"] == "20210101"
    assert ak["end_date"] == "20260731"
    assert ak["adjust"] == ""


def test_baostock_param_freeze():
    bs = CONTRACT["baostock"]
    assert bs["function"] == "bs.query_history_k_data_plus"
    assert bs["code"] == "sh.601857"
    assert bs["frequency"] == "d"
    assert bs["start_date"] == "2021-01-01"
    assert bs["end_date"] == "2026-07-31"
    assert bs["adjustflag"] == "3"


def test_adjustment_none_registered():
    assert CONTRACT["adjustment"] == "none"
    assert CONTRACT["akshare"]["adjust"] == ""
    assert CONTRACT["baostock"]["adjustflag"] == "3"
    assert CONTRACT["close_unit"] == "CNY/share"


def test_provider_versions_frozen():
    assert CONTRACT["provider_versions"]["baostock"] == "0.9.3"
    assert CONTRACT["provider_versions"]["akshare"] == "1.18.79"


# ── canonical normalization ────────────────────────────────────────────────


def test_normalize_baostock_canonical():
    dates = _market_dates()[:3]
    rows = acq.normalize_market_snapshot(
        _baostock_raw(dates), provider="baostock", provider_version="0.9.3", contract=CONTRACT
    )
    assert rows[0]["symbol"] == SYMBOL
    assert rows[0]["trade_date"] == dates[0]
    assert rows[0]["close"] == "4.19"
    assert rows[0]["amount"] == "403962846.32"
    assert rows[0]["volume"] == 96907113
    assert rows[0]["provider"] == "baostock"
    assert rows[0]["provider_version"] == "0.9.3"


def test_akshare_volume_mapped_to_shares():
    import pandas as pd
    df = pd.DataFrame([{
        "日期": "2021-01-04", "股票代码": "601857", "开盘": 4.15, "收盘": 4.19,
        "最高": 4.20, "最低": 4.14, "成交量": 969071, "成交额": 403962848.0,
    }])
    mapped = acq._akshare_raw_rows(df)
    assert mapped[0]["volume"] == 96907100  # 手 -> shares (x100)
    assert mapped[0]["close"] == 4.19


def test_normalize_duplicate_date_fails():
    dates = _market_dates()[:2]
    rows = _baostock_raw(dates)
    rows[1]["trade_date"] = rows[0]["trade_date"]
    with pytest.raises(acq.MarketNormalizationError):
        acq.normalize_market_snapshot(rows, provider="baostock", provider_version="0.9.3",
                                      contract=CONTRACT)


def test_normalize_ascending_order():
    dates = _market_dates()[:3]
    rows = _baostock_raw(dates)
    rows.reverse()
    norm = acq.normalize_market_snapshot(rows, provider="baostock", provider_version="0.9.3",
                                         contract=CONTRACT)
    dates_out = [r["trade_date"] for r in norm]
    assert dates_out == sorted(dates_out)


def test_canonical_table_digest_recomputable():
    dates = _market_dates()
    a = acq.normalize_market_snapshot(_baostock_raw(dates), provider="baostock",
                                      provider_version="0.9.3", contract=CONTRACT)
    b = acq.normalize_market_snapshot(_baostock_raw(dates), provider="baostock",
                                      provider_version="0.9.3", contract=CONTRACT)
    assert acq.canonical_table_digest(a) == acq.canonical_table_digest(b)


def test_object_sha_matches_filename(tmp_path):
    dates = _market_dates()[:5]
    rows = acq.normalize_market_snapshot(_baostock_raw(dates), provider="baostock",
                                         provider_version="0.9.3", contract=CONTRACT)
    path, sha = acq.write_content_addressed_snapshot(rows, tmp_path, "baostock")
    assert path.name == f"{sha}.parquet"
    assert _sha(path.read_bytes()) == sha


def test_no_float_repr_in_normalized_identity():
    dates = _market_dates()[:2]
    rows = acq.normalize_market_snapshot(_baostock_raw(dates), provider="baostock",
                                         provider_version="0.9.3", contract=CONTRACT)
    for r in rows:
        for f in ("open", "high", "low", "close", "amount"):
            assert isinstance(r[f], str)
            Decimal(r[f])
        assert isinstance(r["volume"], int)


# ── A/B stability ──────────────────────────────────────────────────────────


def test_ab_same_passes(tmp_path, monkeypatch):
    from ashare_research.tools.m2_stage2k1r4e2_reacquire_market_snapshots import _stable_record
    dates = _market_dates()
    raw = _baostock_raw(dates)

    def fake_acquire(contract, attempts=3):
        return raw, contract["provider_versions"]["baostock"]

    monkeypatch.setattr(acq, "acquire_baostock_snapshot", fake_acquire)
    rec = _stable_record("baostock", CONTRACT, tmp_path, attempts=3)
    assert rec["ab_stability"] == "ACQUISITION_STABLE"
    assert len(rec["sha256"]) == 64
    assert rec["table_digest"] == acq.canonical_table_digest(
        acq.normalize_market_snapshot(raw, provider="baostock",
                                      provider_version="0.9.3", contract=CONTRACT)
    )


def test_ab_different_blocks(tmp_path, monkeypatch):
    from ashare_research.tools.m2_stage2k1r4e2_reacquire_market_snapshots import _stable_record
    dates = _market_dates()
    raw_a = _baostock_raw(dates)
    raw_b = [dict(r, close="4.20") for r in raw_a]
    calls = {"n": 0}

    def fake_acquire(contract, attempts=3):
        calls["n"] += 1
        return (raw_a if calls["n"] % 2 == 1 else raw_b), "0.9.3"

    monkeypatch.setattr(acq, "acquire_baostock_snapshot", fake_acquire)
    with pytest.raises(acq.MarketAcquisitionError):
        _stable_record("baostock", CONTRACT, tmp_path, attempts=1)


# ── acquisition receipt ────────────────────────────────────────────────────


def test_receipt_records_provider_version():
    recs = [
        {
            "provider": "baostock", "provider_version": "0.9.3", "sha256": "a" * 64,
            "first_trade_date": "2021-01-04", "last_trade_date": "2026-07-31",
            "function": "bs.query_history_k_data_plus", "params": CONTRACT["baostock"],
        },
        {
            "provider": "akshare", "provider_version": "1.18.79", "sha256": "b" * 64,
            "first_trade_date": "2021-01-04", "last_trade_date": "2026-07-31",
            "function": "ak.stock_zh_a_hist", "params": CONTRACT["akshare"],
        },
    ]
    receipt = acq.build_acquisition_receipt(
        contract=CONTRACT, provider_records=recs, runtime_versions={"python": "3.13"},
        acquisition_code_commit="BASE", started_at="2026-08-06T00:00",
        finished_at="2026-08-06T00:01", acquisition_warnings=[],
    )
    assert receipt["providers"][0]["provider_version"] == "0.9.3"
    assert receipt["providers"][1]["provider_version"] == "1.18.79"
    assert receipt["acquisition_code_commit"] == "BASE"
    assert acq.validate_acquisition_receipt(receipt, CONTRACT)["valid"] is True


def test_batch_id_deterministic_no_wall_clock():
    recs = [
        {"provider": "baostock", "provider_version": "0.9.3", "function": "f",
         "params": {}, "sha256": "a" * 64},
        {"provider": "akshare", "provider_version": "1.18.79", "function": "f",
         "params": {}, "sha256": "b" * 64},
    ]
    rng = {"start": "2021-01-01", "end": "2026-07-31"}
    id1 = acq.build_acquisition_batch_id(SYMBOL, rng, "none", recs)
    id2 = acq.build_acquisition_batch_id(SYMBOL, rng, "none", recs)
    assert id1 == id2
    assert "2026-" not in id1


# ── registry v3 supersession ───────────────────────────────────────────────


def test_registry_v3_supersedes_v2():
    recs = [
        {"provider": "baostock", "sha256": "a" * 64, "first_trade_date": "2021-01-04",
         "last_trade_date": "2026-07-31", "provider_version": "0.9.3"},
        {"provider": "akshare", "sha256": "b" * 64, "first_trade_date": "2021-01-04",
         "last_trade_date": "2026-07-31", "provider_version": "1.18.79"},
    ]
    reg = _build_registry_v3(CONTRACT, recs, [])
    assert reg["supersedes_registry"] == "events/market_data_snapshot_registry.json"
    reason = "pinned_secondary_object_unrecoverable_versioned_reacquisition"
    assert reg["supersession_reason"] == reason
    assert reg["contract"] == "market_data_snapshot_registry_v3"


def test_registry_does_not_prewrite_pass():
    recs = [
        {"provider": "baostock", "sha256": "a" * 64, "first_trade_date": "2021-01-04",
         "last_trade_date": "2026-07-31", "provider_version": "0.9.3"},
        {"provider": "akshare", "sha256": "b" * 64, "first_trade_date": "2021-01-04",
         "last_trade_date": "2026-07-31", "provider_version": "1.18.79"},
    ]
    reg = _build_registry_v3(CONTRACT, recs, [])
    assert reg["reconciliation_status"] == "pending_real_reconciliation"
    assert "common_trade_days" not in reg
    assert "close_max_abs_difference" not in reg


def test_old_registry_v2_unmodified():
    assert REGISTRY_V2["contract"] == "market_data_snapshot_registry_v2"
    assert REGISTRY_V2["providers"][0]["provider"] == "baostock"
    assert REGISTRY_V2["providers"][1]["provider"] == "akshare"
    assert len(REGISTRY_V2["providers"][0]["sha256"]) == 64
    assert len(REGISTRY_V2["providers"][1]["sha256"]) == 64


def test_old_akshare_object_missing_recorded():
    assert "203ddfd7" in REGISTRY_V2["providers"][1]["sha256"]


# ── old/new Baostock revision diff ─────────────────────────────────────────


def test_revision_diff_recomputable(tmp_path):
    dates = _market_dates()
    old_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    new_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    diff = _revision_diff(
        tmp_path / "baostock" / f"{old_sha}.parquet", old_sha, "0.9.3",
        tmp_path / "baostock" / f"{new_sha}.parquet", new_sha, "0.9.3",
    )
    assert diff["change_classification"] == "NO_HISTORICAL_DATA_CHANGE"
    assert diff["changed_row_count"] == 0
    assert diff["max_close_difference"] == "0"
    assert diff["old_akshare_byte_comparison"] == "NOT_POSSIBLE_OLD_OBJECT_MISSING"


def test_revision_diff_detects_close_change(tmp_path):
    dates = _market_dates()[:20]
    old_rows = _baostock_raw(dates)
    new_rows = [dict(r) for r in old_rows]
    new_rows[-1]["close"] = "4.30"
    old_sha = _write_object(tmp_path, "baostock", old_rows)
    new_sha = _write_object(tmp_path, "baostock", new_rows)
    diff = _revision_diff(
        tmp_path / "baostock" / f"{old_sha}.parquet", old_sha, "0.9.3",
        tmp_path / "baostock" / f"{new_sha}.parquet", new_sha, "0.9.3",
    )
    assert diff["change_classification"] == "HISTORICAL_DATA_CHANGE"
    assert diff["changed_row_count"] >= 1
    assert Decimal(diff["max_close_difference"]) > 0


# ── real reconciliation reuse (fail-closed) ────────────────────────────────


def test_date_set_mismatch_fails(tmp_path):
    dates = _market_dates()
    bs_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    ak_dates = dates[:500] + dates[501:]
    ak_sha = _write_object(tmp_path, "akshare", _akshare_raw(ak_dates))
    reg = _registry_v3(bs_sha, ak_sha, row_count=len(dates), ak_dates=ak_dates)
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series(primary, secondary)


def test_close_over_tolerance_fails(tmp_path):
    dates = _market_dates()
    bs_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    ak_rows = [dict(r, close="4.30") for r in _akshare_raw(dates)]
    ak_sha = _write_object(tmp_path, "akshare", ak_rows)
    reg = _registry_v3(bs_sha, ak_sha, row_count=len(dates))
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series(primary, secondary)


def test_reconciliation_reuses_market_reconciliation_module(tmp_path):
    dates = _market_dates()
    bs_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    ak_sha = _write_object(tmp_path, "akshare", _akshare_raw(dates))
    reg = _registry_v3(bs_sha, ak_sha, row_count=len(dates))
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    rec = mkt.reconcile_market_close_series(primary, secondary)
    assert rec["differences_over_tolerance_count"] == 0
    assert rec["common_trade_days"] == len(dates)


# ── formal release: explicit registry + observation binding ────────────────


def test_formal_requires_passed_registry(tmp_path, monkeypatch):
    from ashare_research.pit_valuation import series_contract as sc
    dates = _market_dates()
    bs_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    ak_sha = _write_object(tmp_path, "akshare", _akshare_raw(dates))
    reg = _registry_v3(bs_sha, ak_sha, status="pending_real_reconciliation")
    reg_path = tmp_path / "registry_v3.json"
    reg_path.write_text(json.dumps(reg), encoding="utf-8")
    monkeypatch.setattr(sc, "validate_all_contracts", lambda: {"ok": True})
    out = tmp_path / "out"
    code = cli_main(["formal", "--registry", str(reg_path), "--cache-root", str(tmp_path),
                     "--output-root", str(out)])
    assert code == decision_to_exit_code(DECISION_GAPS)


def test_candidate_observations_bind_two_new_shas(tmp_path):
    from ashare_research.pit_valuation import financial_state, fixtures, valuation_series
    dates = _market_dates()
    bs_sha = _write_object(tmp_path, "baostock", _baostock_raw(dates))
    ak_sha = _write_object(tmp_path, "akshare", _akshare_raw(dates))
    reg = _registry_v3(bs_sha, ak_sha, status="pass", row_count=len(dates))
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    rec = mkt.reconcile_market_close_series(primary, secondary)
    ledger = mkt.build_mismatch_ledger(rec)
    digest = mkt.build_mismatch_ledger_digest(ledger)
    meta = {
        "primary_provider": "baostock", "primary_object_sha256": bs_sha,
        "primary_object_key": f"baostock/{bs_sha}.parquet",
        "secondary_provider": "akshare", "secondary_object_sha256": ak_sha,
        "secondary_object_key": f"akshare/{ak_sha}.parquet",
        "secondary_present": True, "secondary_verified": True,
        "reconciliation_status": "pass", "market_reconciliation_digest": digest,
        "market_rows": primary["row_count"],
        "first_trade_date": primary["first_trade_date"],
        "last_trade_date": primary["last_trade_date"], "reconciliation": rec,
    }
    reported, reconciled = fixtures.load_fixture_bundles(Path("."))
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    series = valuation_series.build_valuation_series(primary["rows"], meta, timelines)
    for obs in series["observations"]:
        assert obs["primary_market_object_sha256"] == bs_sha
        assert obs["secondary_market_object_sha256"] == ak_sha
        assert obs["percentile_computed"] is False
        assert obs["score_eligible"] is False
        assert obs["production_eligible"] is False


def test_fixture_cannot_masquerade_as_formal():
    import argparse

    from ashare_research.pit_valuation import fixtures
    from ashare_research.tools.m2_stage2k1r4e2_reacquire_market_snapshots import _cmd_fixtures

    rows, _, meta = fixtures.load_fixture_dual_market(Path("."))
    assert meta["primary_object_sha256"].startswith("synthetic")
    assert len(rows) > 0
    out = REPO / "tmp" / "r4e2-fixtures-test"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    ns = argparse.Namespace(fixture_root=str(Path(".")), output_root=str(out))
    code = _cmd_fixtures(ns)
    assert code == decision_to_exit_code(DECISION_ALLOWED)
    # the synthetic fixture objects are never mistaken for real content.
    assert meta["primary_object_sha256"].startswith("synthetic")
    # fixtures output is explicitly marked synthetic-only so it cannot be read
    # as a real dual-source reconciliation from acquired external data.
    recon = json.loads(
        (out / "petrochina_market_close_reconciliation_v2.json").read_text(encoding="utf-8")
    )
    assert recon.get("evidence_class") == "SYNTHETIC_ENGINEERING_ONLY"


# ── decision gate mapping ──────────────────────────────────────────────────


def test_decision_to_exit_code_mapping():
    assert decision_to_exit_code(DECISION_ALLOWED) == 0
    assert decision_to_exit_code(DECISION_GAPS) == 1
    assert decision_to_exit_code(DECISION_NOT_TRUSTED) == 2
    assert decision_to_exit_code("UNKNOWN") == 2


def test_parser_has_five_modes():
    p = build_parser()
    sub = p._subparsers._actions[1].choices
    assert set(sub.keys()) == {"acquire", "verify", "reconcile", "formal", "fixtures"}


# ── product boundary ───────────────────────────────────────────────────────


def test_acquisition_module_no_percentile_no_prod():
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "market_snapshot_acquisition.py").read_text(encoding="utf-8")
    for needle in ("duckdb", "percentile", "score_eligible", "peer", " m3"):
        assert needle not in src.lower()


def test_acquisition_module_no_absolute_path_no_proxy():
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "market_snapshot_acquisition.py").read_text(encoding="utf-8")
    assert r"D:\\" not in src
    assert r"D:/" not in src
    # no hard-coded proxy endpoint or loopback proxy address.
    assert "127.0.0.1" not in src
    for needle in ("HTTP_PROXY", "HTTPS_PROXY", "socks5", "PROXY_MANAGED"):
        assert needle not in src
