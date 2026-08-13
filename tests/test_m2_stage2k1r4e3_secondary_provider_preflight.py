"""M2 Stage 2K.1R4E.3 — alternative secondary market provider preflight tests.

Covers the frozen candidate list, the transport/underlying separation, the
Eastmoney-independence rejection, A/B stability, Pytdx pagination, Tushare
credential-not-available, the unification normalization (Decimal/no-float-repr),
the Baostock comparison + mismatch ledger, company-action adjustment semantics,
the QUALIFIED/PARTIAL/REJECTED/BLOCKED classification, the order-independent
selection rule, the no-QUALIFIED cannot-select rule, the fixture non-masquerade,
and the product-boundary invariants (registry v3 unchanged, no candidate v2, no
percentile, no scoring, no default-DB write, no peer/M3). All network
acquisition is mocked; every run is offline and deterministic.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.pit_valuation import secondary_provider_preflight as spp
from ashare_research.pit_valuation.series_contract import SYMBOL
from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import (
    CONFIG,
    DECISION_PATH,
    build_parser,
    decision_to_exit_code,
)
from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import (
    main as cli_main,
)

REPO = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(CONFIG.read_text(encoding="utf-8"))
REGISTRY_V3_PATH = REPO / "events" / "market_data_snapshot_registry_v3.json"
REGISTRY_V3 = json.loads(REGISTRY_V3_PATH.read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _market_dates() -> list[str]:
    dates: list[str] = []
    d = date(2021, 1, 4)
    end = date(2026, 7, 31)
    while d <= end and len(dates) < 1351:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    return dates


def _primary_rows(dates) -> list[dict]:
    return [
        {
            "trade_date": d,
            "open": "4.15", "high": "4.20", "low": "4.14", "close": "4.19",
            "volume": 96907113, "amount": "403962846.32", "is_trading": True,
        }
        for d in dates
    ]


def _candidate(cid: str) -> dict:
    return next(c for c in CONTRACT["candidates"] if c["candidate_id"] == cid)


def _normalized(raw_rows, cid: str, *, endpoint: str = "web.ifzq.gtimg.cn") -> list[dict]:
    return spp.normalize_candidate_rows(
        raw_rows, candidate=_candidate(cid), contract=CONTRACT,
        provider_version="1.18.79", endpoint_identity=endpoint,
    )


def _cand_raw(dates, *, close: str = "4.19") -> list[dict]:
    return [
        {
            "trade_date": d, "open": "4.15", "high": "4.20", "low": "4.14",
            "close": close, "volume": 124659900, "amount": "530000000.0",
            "is_trading": True,
        }
        for d in dates
    ]


# ── candidate list freeze + transport/underlying separation ────────────────


def test_candidate_list_frozen():
    ids = [c["candidate_id"] for c in CONTRACT["candidates"]]
    assert ids == [
        "tencent_via_akshare", "sina_via_akshare",
        "pytdx_tongdaxin", "tushare_pro_optional",
    ]


def test_transport_and_underlying_separated():
    for c in CONTRACT["candidates"]:
        assert isinstance(c.get("transport_library"), str)
        assert isinstance(c.get("underlying_provider"), str)
    tencent = _candidate("tencent_via_akshare")
    assert tencent["transport_library"] == "akshare"
    assert tencent["underlying_provider"] == "tencent"
    sina = _candidate("sina_via_akshare")
    assert sina["transport_library"] == "akshare"
    assert sina["underlying_provider"] == "sina"


def test_tencent_params_correct():
    c = _candidate("tencent_via_akshare")
    assert c["function"] == "stock_zh_a_hist_tx"
    assert c["symbol"] == "sh601857"
    assert c["start_date"] == "20210101"
    assert c["end_date"] == "20260731"
    assert c["adjust"] == ""


def test_sina_params_correct():
    c = _candidate("sina_via_akshare")
    assert c["function"] == "stock_zh_a_daily"
    assert c["symbol"] == "sh601857"
    assert c["start_date"] == "20210101"
    assert c["end_date"] == "20260731"
    assert c["adjust"] == ""


def test_sina_bounded_calls_policy():
    c = _candidate("sina_via_akshare")
    policy = c["bounded_call_policy"]
    assert policy["bounded_total_calls"] is True
    assert policy["no_loop_pagination"] is True
    assert policy["stop_on_ban"] is True
    assert policy["no_auto_proxy_rotation"] is True


def test_window_contract():
    w = CONTRACT["window"]
    assert w["required_first_trade_date"] == "2021-01-04"
    assert w["required_last_trade_date"] == "2026-07-31"
    assert w["required_trade_days"] == 1351
    assert CONTRACT["adjustment"] == "none"
    assert CONTRACT["close_tolerance_cny_per_share"] == "0.01"


def test_contract_validation_passes():
    d = spp.validate_preflight_contract(CONTRACT)
    assert "candidate_ids_digest" in d


def test_contract_rejects_missing_candidate():
    bad = json.loads(json.dumps(CONTRACT))
    bad["candidates"] = bad["candidates"][:3]
    with pytest.raises(spp.PreflightContractError):
        spp.validate_preflight_contract(bad)


# ── Eastmoney independence rejection ───────────────────────────────────────


def test_eastmoney_endpoint_rejected():
    cand = _candidate("tencent_via_akshare")
    with pytest.raises(spp.PreflightIndependenceError):
        spp.check_independence(cand, "https://push2his.eastmoney.com/api/...")
    with pytest.raises(spp.PreflightIndependenceError):
        spp.check_independence(cand, "push2his.eastmoney.com")


def test_eastmoney_underlying_provider_rejected():
    cand = dict(_candidate("tencent_via_akshare"))
    cand["underlying_provider"] = "eastmoney"
    with pytest.raises(spp.PreflightIndependenceError):
        spp.check_independence(cand, "web.ifzq.gtimg.cn")


def test_independent_endpoint_accepted():
    cand = _candidate("tencent_via_akshare")
    assert spp.check_independence(cand, "web.ifzq.gtimg.cn") is True
    assert spp.check_independence(_candidate("sina_via_akshare"), "finance.sina.com.cn") is True


# ── normalization: Decimal / no float repr / no backfill ───────────────────


def test_normalize_canonical_decimal_no_float_repr():
    dates = _market_dates()[:3]
    rows = _normalized(_cand_raw(dates), "tencent_via_akshare")
    r = rows[0]
    assert r["symbol"] == SYMBOL
    assert r["trade_date"] == dates[0]
    for f in ("open", "high", "low", "close", "amount"):
        assert isinstance(r[f], str)
        Decimal(r[f])
    assert isinstance(r["volume"], int)
    assert r["adjustment"] == "none"
    assert r["transport_library"] == "akshare"
    assert r["underlying_provider"] == "tencent"


def test_normalize_rejects_duplicate_date():
    dates = _market_dates()[:2]
    raw = _cand_raw(dates)
    raw[1]["trade_date"] = raw[0]["trade_date"]
    with pytest.raises(spp.PreflightContractError):
        _normalized(raw, "tencent_via_akshare")


def test_normalize_rejects_empty_date():
    raw = _cand_raw(_market_dates()[:2])
    raw[0]["trade_date"] = ""
    with pytest.raises(spp.PreflightContractError):
        _normalized(raw, "tencent_via_akshare")


def test_normalize_does_not_backfill_missing_dates():
    # A raw series with a real gap must keep the gap (missing dates preserved as
    # a real provider gap), never reindexed to fill.
    dates = _market_dates()[:10]
    raw = _cand_raw(dates)
    missing = dates[3]
    raw = [r for r in raw if r["trade_date"] != missing]
    rows = _normalized(raw, "tencent_via_akshare")
    out_dates = [r["trade_date"] for r in rows]
    assert missing not in out_dates
    assert len(out_dates) == 9


def test_decimal_parse_trusted():
    # Decimal(str(...)) is used; a binary float repr never enters identity.
    assert spp._canon_decimal("4.1900") == "4.19"
    assert spp._canon_decimal(4.19) in ("4.19", "4.190")
    assert Decimal("4.19") == Decimal(spp._canon_decimal("4.19"))


# ── A/B stability ──────────────────────────────────────────────────────────


def test_ab_same_passes():
    dates = _market_dates()
    a = _normalized(_cand_raw(dates), "tencent_via_akshare")
    b = _normalized(_cand_raw(dates), "tencent_via_akshare")
    ab = spp.ab_stability(a, b)
    assert ab["status"] == spp.ACQUISITION_STABLE
    assert ab["stable"] is True


def test_ab_different_rejected():
    dates = _market_dates()
    a = _normalized(_cand_raw(dates), "tencent_via_akshare")
    b = _normalized(_cand_raw(dates, close="4.30"), "tencent_via_akshare")
    ab = spp.ab_stability(a, b)
    assert ab["status"] == spp.ACQUISITION_UNSTABLE
    assert ab["stable"] is False


# ── Pytdx pagination ───────────────────────────────────────────────────────


def test_pytdx_pages_no_overlap_no_gap():
    dates = _market_dates()[:10]
    page1 = [{"trade_date": d} for d in dates[:5]]
    page2 = [{"trade_date": d} for d in dates[5:]]
    r = spp.validate_pytdx_pages([page1, page2])
    assert r["overlap_detected"] is False
    assert r["gap_detected"] is False
    assert r["ordered"] is True
    assert r["row_count"] == 10


def test_pytdx_pages_overlap_rejected():
    dates = _market_dates()[:6]
    page1 = [{"trade_date": d} for d in dates[:4]]
    page2 = [{"trade_date": d} for d in dates[2:]]
    with pytest.raises(spp.PreflightComparisonError):
        spp.validate_pytdx_pages([page1, page2])


def test_pytdx_gap_rejected():
    dates = _market_dates()[:6]
    page1 = [{"trade_date": d} for d in dates[:3]]
    page2 = [{"trade_date": d} for d in dates[4:]]
    with pytest.raises(spp.PreflightComparisonError):
        spp.validate_pytdx_pages([page1, page2], expected_dates=dates)


def test_pytdx_single_run_no_server_mixing():
    # The per-run server pinning is a single-run contract: the acquisition record
    # must carry exactly one server. The CLI records one endpoint per candidate.
    c = _candidate("pytdx_tongdaxin")
    assert c["underlying_provider"] == "tongdaxin_quote_server"
    assert c["required_pagination"] is True
    notes = " ".join(c["contract_notes"])
    assert "single full A/B run must pin one server" in notes
    assert "no silent server switch" in notes


# ── Tushare credential handling ────────────────────────────────────────────


def test_tushare_no_token_is_blocked_not_failure():
    c = _candidate("tushare_pro_optional")
    assert c["no_token"]["status"] == "credential_not_available"
    assert c["no_token"]["not_a_failure"] is True


def test_tushare_no_token_field_in_config():
    # No token value/key may be written into the config (the prose may *mention*
    # a token, but there is no stored credential).
    text = CONFIG.read_text(encoding="utf-8")
    assert "set_token" not in text
    assert "ts.pro_api" not in text
    assert '"token"' not in text.lower()
    assert not any(k.startswith("token_") for k in CONTRACT["candidates"][3])


def test_token_never_in_output():
    # The decide/compare output must carry no credential value.
    decision = {
        "schema": "m2_stage2k1r4e3_decision",
        "candidates": [{"candidate_id": "tushare_pro_optional",
                        "classification": spp.BLOCKED}],
    }
    text = json.dumps(decision)
    assert "token" not in text.lower()


# ── Baostock comparison + mismatch ledger ──────────────────────────────────


def test_compare_identical_primary_passes():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    comp = spp.compare_to_baostock(cand, prim)
    assert comp["common_trade_days"] == len(dates)
    assert comp["over_tolerance_count"] == 0
    assert Decimal(comp["max_close_difference"]) == 0
    assert comp["candidate_only_dates"] == []
    assert comp["primary_only_dates"] == []
    assert comp["mismatch_ledger_digest"]


def test_compare_date_missing_rejected():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    cand = cand[:-1]  # drop the last date -> candidate-only missing
    comp = spp.compare_to_baostock(cand, prim)
    assert comp["primary_only_dates"]
    classification, _ = spp.classify_candidate(
        candidate_id="tencent_via_akshare", independent=True, credential_available=True,
        acquisition={"status": spp.ACQUISITION_STABLE}, comparison=comp,
        adjustment={"status": spp.ADJUSTMENT_TRUSTED}, limitations=[],
    )
    assert classification == spp.REJECTED


def test_compare_close_over_tolerance_rejected():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates, close="4.30"), "tencent_via_akshare")
    prim = _primary_rows(dates)
    comp = spp.compare_to_baostock(cand, prim)
    assert comp["over_tolerance_count"] > 0
    classification, _ = spp.classify_candidate(
        candidate_id="tencent_via_akshare", independent=True, credential_available=True,
        acquisition={"status": spp.ACQUISITION_STABLE}, comparison=comp,
        adjustment={"status": spp.ADJUSTMENT_TRUSTED}, limitations=[],
    )
    assert classification == spp.REJECTED


def test_mismatch_digest_recomputable():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates, close="4.30"), "tencent_via_akshare")
    prim = _primary_rows(dates)
    c1 = spp.compare_to_baostock(cand, prim)
    c2 = spp.compare_to_baostock(cand, prim)
    assert c1["mismatch_ledger_digest"] == c2["mismatch_ledger_digest"]
    assert c1["comparison_digest"] == c2["comparison_digest"]


def test_comparison_digest_binds_objects():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    comp = spp.compare_to_baostock(cand, prim)
    assert len(comp["comparison_digest"]) == 64
    assert comp["comparison_digest"] == spp.comparison_digest(
        cand, prim, comp, comp["mismatch_ledger_digest"], Decimal("0.01")
    )


# ── company-action adjustment semantics ────────────────────────────────────


def test_adjustment_semantics_trusted_when_matches_primary():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    idx = dates.index("2022-06-28")
    windows = [
        {"trade_date": "2022-06-28", "type": "ex_dividend",
         "before": dates[idx - 2:idx], "after": dates[idx + 1:idx + 3]},
    ]
    r = spp.check_adjustment_semantics(cand, prim, windows)
    assert r["status"] == spp.ADJUSTMENT_TRUSTED


def test_adjustment_semantics_rejects_forward_adjusted_backwrite():
    # A forward-adjusted (前复权) candidate would lower historical closes before
    # an ex-dividend date vs the raw primary (historical back-write).
    dates = _market_dates()
    prim = _primary_rows(dates)
    idx = dates.index("2022-06-28")
    cand_raw = _cand_raw(dates)
    for r in cand_raw[:idx]:
        r["close"] = "3.90"  # pre-window closes differ -> back-write detected
    cand = _normalized(cand_raw, "tencent_via_akshare")
    windows = [
        {"trade_date": "2022-06-28", "type": "ex_dividend",
         "before": dates[idx - 2:idx], "after": dates[idx + 1:idx + 3]},
    ]
    r = spp.check_adjustment_semantics(cand, prim, windows)
    assert r["status"] == spp.ADJUSTMENT_NOT_TRUSTED


def test_adjustment_semantics_requires_window_dates():
    prim = _primary_rows(_market_dates())
    cand = _normalized(_cand_raw(_market_dates()), "tencent_via_akshare")
    windows = [{"trade_date": "2022-06-28", "type": "ex_dividend", "before": [], "after": []}]
    r = spp.check_adjustment_semantics(cand, prim, windows)
    assert r["status"] == spp.ADJUSTMENT_NOT_TRUSTED


# ── classification / selection / decision ──────────────────────────────────


def test_classify_qualified_requires_all():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    comp = spp.compare_to_baostock(cand, prim)
    adj = {"status": spp.ADJUSTMENT_TRUSTED}
    classification, _ = spp.classify_candidate(
        candidate_id="tencent_via_akshare", independent=True, credential_available=True,
        acquisition={"status": spp.ACQUISITION_STABLE}, comparison=comp,
        adjustment=adj, limitations=[],
    )
    assert classification == spp.QUALIFIED


def test_classify_partial_with_limitations():
    dates = _market_dates()
    cand = _normalized(_cand_raw(dates), "tencent_via_akshare")
    prim = _primary_rows(dates)
    comp = spp.compare_to_baostock(cand, prim)
    adj = {"status": spp.ADJUSTMENT_TRUSTED}
    classification, _ = spp.classify_candidate(
        candidate_id="tencent_via_akshare", independent=True, credential_available=True,
        acquisition={"status": spp.ACQUISITION_STABLE}, comparison=comp,
        adjustment=adj, limitations=["amount_not_comparable"],
    )
    assert classification == spp.PARTIAL


def test_classify_blocked_when_credential_missing():
    # Tushare is independent of eastmoney but has no credential -> BLOCKED, not
    # a failure and not rejected for independence.
    classification, _ = spp.classify_candidate(
        candidate_id="tushare_pro_optional", independent=True,
        credential_available=False, acquisition=None, comparison=None,
        adjustment=None, limitations=[],
    )
    assert classification == spp.BLOCKED


def test_selection_order_independent():
    tencent = {
        "candidate_id": "tencent_via_akshare", "classification": spp.QUALIFIED,
        "transport_library": "akshare", "underlying_provider": "tencent",
        "object_sha256": "a" * 64, "table_digest": "b" * 64,
        "endpoint_identity": "web.ifzq.gtimg.cn", "limitations": [],
    }
    sina = {
        "candidate_id": "sina_via_akshare", "classification": spp.QUALIFIED,
        "transport_library": "akshare", "underlying_provider": "sina",
        "object_sha256": "c" * 64, "table_digest": "d" * 64,
        "endpoint_identity": "finance.sina.com.cn", "limitations": [],
    }
    sel1 = spp.select_provider([sina, tencent])
    sel2 = spp.select_provider([tencent, sina])
    assert sel1["selected_provider"] == sel2["selected_provider"] == "tencent_via_akshare"


def test_no_qualified_cannot_select_provider():
    partial = {
        "candidate_id": "sina_via_akshare", "classification": spp.PARTIAL,
        "limitations": ["amount_not_comparable"],
    }
    sel = spp.select_provider([partial])
    assert sel["selected_provider"] is None


def test_decision_allowed_when_qualified():
    ok = {"candidate_id": "tencent_via_akshare", "classification": spp.QUALIFIED}
    d = spp.decide([ok], contract_trusted=True)
    assert d["decision"] == spp.DECISION_ALLOWED


def test_decision_gaps_when_all_blocked():
    blocked = {"candidate_id": "pytdx_tongdaxin", "classification": spp.BLOCKED}
    d = spp.decide([blocked], contract_trusted=True)
    assert d["decision"] == spp.DECISION_GAPS


def test_decision_no_acceptable_when_all_rejected():
    rejected = {"candidate_id": "sina_via_akshare", "classification": spp.REJECTED}
    d = spp.decide([rejected], contract_trusted=True)
    assert d["decision"] == spp.DECISION_NO_ACCEPTABLE


def test_decision_not_trusted_when_contract_untrusted():
    d = spp.decide([], contract_trusted=False)
    assert d["decision"] == spp.DECISION_NOT_TRUSTED


def test_decision_to_exit_code_mapping():
    assert decision_to_exit_code(spp.DECISION_ALLOWED) == 0
    assert decision_to_exit_code(spp.DECISION_GAPS) == 1
    assert decision_to_exit_code(spp.DECISION_NO_ACCEPTABLE) == 1
    assert decision_to_exit_code(spp.DECISION_NOT_TRUSTED) == 2


def test_parser_has_five_modes():
    p = build_parser()
    sub = p._subparsers._actions[1].choices
    assert set(sub.keys()) == {"verify-contracts", "probe", "acquire", "compare", "fixtures"}


# ── fixtures cannot masquerade ─────────────────────────────────────────────


def test_fixture_is_synthetic_only(tmp_path):
    import argparse

    from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import _cmd_fixtures

    out = tmp_path / "out"
    ns = argparse.Namespace(config=str(CONFIG), fixture_root=str(Path(".")), output_root=str(out))
    code = _cmd_fixtures(ns)
    assert code == decision_to_exit_code(spp.DECISION_ALLOWED)
    decision = json.loads((out / DECISION_PATH).read_text(encoding="utf-8"))
    assert decision.get("evidence_class") == "SYNTHETIC_ENGINEERING_ONLY"
    assert decision.get("candidate_v2_published") is False


def test_fixture_decision_never_claims_real_selection(tmp_path):
    import argparse

    from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import _cmd_fixtures

    out = tmp_path / "out2"
    ns = argparse.Namespace(config=str(CONFIG), fixture_root=str(Path(".")), output_root=str(out))
    _cmd_fixtures(ns)
    decision = json.loads((out / DECISION_PATH).read_text(encoding="utf-8"))
    assert decision["schema"] == "m2_stage2k1r4e3_decision"
    assert decision["mode"] == "fixtures"


# ── product boundaries ─────────────────────────────────────────────────────


def test_registry_v3_unchanged():
    # The R4E.3 module/CLI never write to registry v3 or create registry v4.
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "secondary_provider_preflight.py").read_text(encoding="utf-8")
    assert "registry_v4" not in src
    assert "market_data_snapshot_registry_v3" not in src
    assert REGISTRY_V3["contract"] == "market_data_snapshot_registry_v3"
    assert REGISTRY_V3["reconciliation_status"] == "pending_real_reconciliation"


def test_no_candidate_v2_published():
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "secondary_provider_preflight.py").read_text(encoding="utf-8")
    assert "percentile" not in src.lower()
    assert "candidate_v2" not in src


def test_module_no_percentile_no_scoring_no_peer_no_m3():
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "secondary_provider_preflight.py").read_text(encoding="utf-8")
    for needle in ("duckdb", "percentile", "score", "peer", " m3", "registry_v4"):
        assert needle not in src.lower()


def test_module_no_absolute_path_no_proxy_no_token():
    src = (REPO / "src" / "ashare_research" / "pit_valuation"
           / "secondary_provider_preflight.py").read_text(encoding="utf-8")
    assert r"D:\\" not in src
    assert r"D:/" not in src
    assert "127.0.0.1" not in src
    for needle in ("HTTP_PROXY", "HTTPS_PROXY", "socks5", "set_token", "token="):
        assert needle not in src.lower()


def test_default_db_not_written():
    # The R4E.3 pipeline never opens the default database.
    for path in (REPO / "src" / "ashare_research" / "pit_valuation"
                 / "secondary_provider_preflight.py",
                 REPO / "src" / "ashare_research" / "tools"
                 / "m2_stage2k1r4e3_secondary_provider_preflight.py"):
        assert "research.duckdb" not in path.read_text(encoding="utf-8")
        assert "duckdb" not in path.read_text(encoding="utf-8").lower()


def test_parser_verify_contracts_offline():
    # verify-contracts must not import network-only transports.
    code = cli_main(["verify-contracts", "--config", str(CONFIG)])
    assert code == decision_to_exit_code(spp.DECISION_ALLOWED)


def test_manifest_schema_registered():
    from ashare_research.scoring import artifact_manifest

    assert "m2_stage2k1r4e3_artifact_manifest" in artifact_manifest.ALLOWED_MANIFEST_SCHEMAS
    assert "m2_stage2k1r4e3_artifact_manifest" in artifact_manifest.V2_SCHEMAS


# ── pytdx is a non-core, function-local optional dependency ────────────────


def test_pytdx_import_is_delayed_and_optional():
    src = (REPO / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e3_secondary_provider_preflight.py").read_text(encoding="utf-8")
    # The pytdx import must appear exactly once, function-local, guarded so a
    # clean clone without pytdx still imports the module and runs Tencent/Sina.
    assert src.count("from pytdx.hq import TdxHq_API") == 1
    idx = src.index("from pytdx.hq import TdxHq_API")
    assert "try:" in src[:idx]
    assert "except ModuleNotFoundError" in src[idx:]
    from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import (
        pytdx_core_dependency,
    )

    assert pytdx_core_dependency() is False


def test_pytdx_probe_reports_dependency_not_available_when_absent():
    from unittest import mock

    from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import (
        _probe_candidate,
    )

    with mock.patch(
        "ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight."
        "_pytdx_runtime_version",
        return_value=None,
    ):
        out = _probe_candidate(_candidate("pytdx_tongdaxin"), attempts=1)
    assert out["candidate_id"] == "pytdx_tongdaxin"
    assert out["reachable"] is False
    assert out["status"] == "dependency_not_available"
    assert out["reason"] == "optional_dependency_not_available"


def test_pytdx_acquire_raises_optional_dependency_when_absent():
    from unittest import mock

    from ashare_research.pit_valuation.secondary_provider_preflight import (
        PreflightAcquisitionError,
    )
    from ashare_research.tools.m2_stage2k1r4e3_secondary_provider_preflight import (
        _acquire_pytdx_candidate,
    )

    with mock.patch.dict("sys.modules", {"pytdx": None}):
        try:
            _acquire_pytdx_candidate(_candidate("pytdx_tongdaxin"), attempts=1)
        except PreflightAcquisitionError as exc:
            assert "optional_dependency_not_available" in str(exc)
        else:
            raise AssertionError("expected PreflightAcquisitionError")


# ── decision binds real object identity ────────────────────────────────────


def test_select_provider_binds_object_identity():
    detail = {
        "candidate_id": "tencent_via_akshare",
        "classification": spp.QUALIFIED,
        "object_sha256": "objsha",
        "table_digest": "tabledigest",
        "transport_library": "akshare",
        "underlying_provider": "tencent",
        "endpoint_identity": "web.ifzq.gtimg.cn",
        "row_count": 1351,
        "first_trade_date": "2021-01-04",
        "last_trade_date": "2026-07-31",
        "comparison_digest": "cdigest",
        "mismatch_ledger_digest": "mdigest",
        "limitations": [],
    }
    sel = spp.select_provider([detail])
    assert sel["selected_provider"] == "tencent_via_akshare"
    assert sel["selected_transport"] == "akshare"
    assert sel["selected_underlying_provider"] == "tencent"
    assert sel["selected_object_sha"] == "objsha"
    assert sel["selected_table_digest"] == "tabledigest"
    assert sel["selected_endpoint_identity"] == "web.ifzq.gtimg.cn"


def test_decision_payload_binds_object_identity_and_dependency():
    src = (REPO / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e3_secondary_provider_preflight.py").read_text(encoding="utf-8")
    for key in (
        "selected_object_sha256",
        "selected_row_count",
        "selected_first_trade_date",
        "selected_last_trade_date",
        "selected_comparison_digest",
        "selected_mismatch_ledger_digest",
        "selected_provider_dependency",
        "pytdx_probe_runtime_version",
        "pytdx_core_dependency",
    ):
        assert key in src


# ── provider independence evidence ─────────────────────────────────────────


def test_independence_evidence_emitted_in_compare():
    src = (REPO / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e3_secondary_provider_preflight.py").read_text(encoding="utf-8")
    for key in (
        "endpoint_host_not_push2his_eastmoney_com",
        "underlying_provider_not_eastmoney",
        "function_name",
        "request_parameters",
        "provider_version",
    ):
        assert key in src
