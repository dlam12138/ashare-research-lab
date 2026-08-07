"""M2 Stage 2K.1R4E.4 — selected secondary provider integration tests.

Covers provider-role resolution, the R4E.3 object promotion, registry v4
(draft -> final), the v2 formal reconciliation, the candidate v2 series, the
economic identity migration, the dual oracle, the R4E.4 manifest and the
product-boundary invariants.  All market objects are synthetic (no real Parquet
is committed) and all tests are offline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ashare_research.pit_valuation import (
    financial_state,
    fixtures,
    provider_roles,
    series_validation,
    valuation_series,
)
from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation import (
    secondary_provider_preflight as spp,
)
from ashare_research.pit_valuation.series_contract import SYMBOL

_REPO_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_V3_PATH = _REPO_ROOT / "events" / "market_data_snapshot_registry_v3.json"
REGISTRY_V3 = json.loads(REGISTRY_V3_PATH.read_text(encoding="utf-8"))

R4E3_TENCENT_SHA = (
    "d760923aae952d9ba400d792d4155b4c6dfa3b728210de64001aa6024c8f7dd7"
)
R4E3_TENCENT_DIGEST = (
    "e6cbee888949b13c0ee47a6193d58026ad6da72a332ffd66948ee4bc4b908cda"
)
PRIMARY_SHA = (
    "c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67"
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dates() -> list[str]:
    """Exactly 1351 synthetic trade dates, 2021-01-04..2026-07-31.

    The real market object has 1351 trading days (holidays excluded) in the
    window.  We generate all weekdays and evenly discard the ~104 holiday
    weekdays so the synthetic series matches the real 1351-row contract
    (``REQUIRED_TRADE_DAYS``) end to end.
    """
    all_days: list[str] = []
    d = date(2021, 1, 4)
    end = date(2026, 7, 31)
    while d <= end:
        if d.weekday() < 5:
            all_days.append(d.isoformat())
        d += timedelta(days=1)
    n = 1351
    if len(all_days) <= n:
        return all_days
    idx = sorted({round(i * (len(all_days) - 1) / (n - 1)) for i in range(n)})
    return [all_days[i] for i in idx]


def _raw_rows(dates: list[str], *, close: str = "5.00") -> list[dict]:
    return [
        {
            "trade_date": d, "open": "4.90", "high": "5.10", "low": "4.80",
            "close": close, "volume": 124659900, "amount": "530000000.0",
            "is_trading": True,
        }
        for d in dates
    ]


def _candidate(cid: str) -> dict:
    cfg = json.loads(
        (_REPO_ROOT / "config" / "pit_valuation_secondary_provider_preflight_v1.json")
        .read_text(encoding="utf-8")
    )
    return next(c for c in cfg["candidates"] if c["candidate_id"] == cid)


def _normalized(dates: list[str], *, endpoint: str = "web.ifzq.gtimg.cn") -> list[dict]:
    cfg = json.loads(
        (_REPO_ROOT / "config" / "pit_valuation_secondary_provider_preflight_v1.json")
        .read_text(encoding="utf-8")
    )
    return spp.normalize_candidate_rows(
        _raw_rows(dates), candidate=_candidate("tencent_via_akshare"),
        contract=cfg, provider_version="1.18.79", endpoint_identity=endpoint,
    )


def _write_object(root: Path, rel_key: str, rows: list[dict]) -> tuple[Path, str]:
    import pandas as pd

    path = root / rel_key
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)
    return path, _sha(path.read_bytes())


def _write_content_addressed(root: Path, rel_dir: str, rows: list[dict]) -> tuple[Path, str]:
    """Write an object at ``<rel_dir>/<content-sha>.parquet`` (name == content)."""
    import pandas as pd

    scratch = root / rel_dir / "scratch.parquet"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(scratch)
    sha = _sha(scratch.read_bytes())
    final = scratch.parent / f"{sha}.parquet"
    if final == scratch:
        return final, sha
    final.write_bytes(scratch.read_bytes())
    scratch.unlink()
    return final, sha


def _loader_rows(dates: list[str], *, close: float = 5.0) -> list[dict]:
    return [
        {"symbol": SYMBOL, "trade_date": d, "close": close, "is_trading": True}
        for d in dates
    ]


def _v4_registry(
    primary_sha: str,
    secondary_sha: str,
    *,
    dates: list[str] | None = None,
    primary_key: str | None = None,
    secondary_key: str | None = None,
    primary_digest: str = "p" * 64,
    secondary_digest: str = R4E3_TENCENT_DIGEST,
    secondary_role: str = "secondary",
) -> dict:
    dates = dates if dates is not None else _dates()
    row_count = len(dates)
    first = dates[0]
    last = dates[-1]
    primary_key = primary_key or f"baostock/{primary_sha}.parquet"
    secondary_key = secondary_key or (
        f"r4e4/tencent_via_akshare/{secondary_sha}.parquet"
    )
    return {
        "contract": "market_data_snapshot_registry_v4",
        "schema_version": "4.0",
        "supersedes_registry": "events/market_data_snapshot_registry_v3.json",
        "supersession_reason": "selected_alternative_secondary_provider_formally_integrated",
        "symbol": SYMBOL,
        "adjustment": "none",
        "required_trade_days": row_count,
        "integration_status": "PENDING_REAL_RECONCILIATION",
        "reconciliation_status": "pending",
        "providers": [
            {
                "provider_id": "baostock_primary",
                "provider_role": "primary",
                "transport_library": "baostock",
                "underlying_provider": "baostock",
                "object_key": primary_key,
                "sha256": primary_sha,
                "table_digest": primary_digest,
                "row_count": row_count,
                "first_trade_date": first,
                "last_trade_date": last,
                "adjustment": "none",
            },
            {
                "provider_id": "tencent_via_akshare",
                "provider_role": secondary_role,
                "transport_library": "akshare",
                "underlying_provider": "tencent",
                "endpoint_identity": "web.ifzq.gtimg.cn",
                "object_key": secondary_key,
                "sha256": secondary_sha,
                "table_digest": secondary_digest,
                "row_count": row_count,
                "first_trade_date": first,
                "last_trade_date": last,
                "adjustment": "none",
            },
        ],
    }


def _two_objects(tmp_path: Path) -> tuple[dict, Path, dict, dict]:
    """Write two identical 1351-row parquet objects and a matching v4 registry."""
    dates = _dates()
    primary_rows = _loader_rows(dates)
    secondary_rows = _loader_rows(dates)
    _, p_sha = _write_content_addressed(tmp_path, "baostock", primary_rows)
    _, s_sha = _write_content_addressed(
        tmp_path, "r4e4/tencent_via_akshare", secondary_rows
    )
    reg = _v4_registry(p_sha, s_sha, dates=dates)
    primary = mkt.load_and_validate_market_object_entry(
        reg, tmp_path, reg["providers"][0]
    )
    secondary = mkt.load_and_validate_market_object_entry(
        reg, tmp_path, reg["providers"][1]
    )
    return reg, tmp_path, primary, secondary


# ── provider-role contract ──────────────────────────────────────────────────


def test_v4_exactly_one_primary_one_secondary(tmp_path):
    reg, _, _, _ = _two_objects(tmp_path)
    primary, secondary = provider_roles.resolve_registry_providers(reg)
    assert provider_roles.entry_role(primary, registry=reg) == "primary"
    assert provider_roles.entry_role(secondary, registry=reg) == "secondary"
    assert provider_roles.entry_provider_id(primary, registry=reg) == "baostock_primary"
    assert provider_roles.entry_provider_id(secondary, registry=reg) == "tencent_via_akshare"


def test_v4_secondary_is_tencent_akshare(tmp_path):
    reg, _, _, _ = _two_objects(tmp_path)
    _, secondary = provider_roles.resolve_registry_providers(reg)
    assert secondary["transport_library"] == "akshare"
    assert secondary["underlying_provider"] == "tencent"
    assert secondary["endpoint_identity"] == "web.ifzq.gtimg.cn"


def test_v4_zero_primary_fails():
    reg = _v4_registry("a" * 64, "b" * 64)
    reg["providers"] = [reg["providers"][1]]
    with pytest.raises(provider_roles.ProviderRoleError):
        provider_roles.resolve_registry_providers(reg)


def test_v4_two_primary_fails():
    reg = _v4_registry("a" * 64, "b" * 64)
    reg["providers"].append(dict(reg["providers"][0]))
    with pytest.raises(provider_roles.ProviderRoleError):
        provider_roles.resolve_registry_providers(reg)


def test_v4_zero_secondary_fails():
    reg = _v4_registry("a" * 64, "b" * 64)
    reg["providers"] = [reg["providers"][0]]
    with pytest.raises(provider_roles.ProviderRoleError):
        provider_roles.resolve_registry_providers(reg)


def test_legacy_v3_adapter_maps_roles():
    # A legacy (pre-v4) registry carries provider *names*; the adapter maps
    # baostock -> primary and akshare -> secondary without modifying the object.
    legacy = {
        "contract": "market_data_snapshot_registry_v3",
        "providers": [
            {"provider": "baostock", "sha256": "b" * 64},
            {"provider": "akshare", "sha256": "a" * 64},
        ],
    }
    primary, secondary = provider_roles.resolve_registry_providers(legacy)
    assert provider_roles.entry_provider_id(primary, registry=legacy) == "baostock"
    assert provider_roles.entry_role(primary, registry=legacy) == "primary"
    assert provider_roles.entry_provider_id(secondary, registry=legacy) == "akshare"
    assert provider_roles.entry_role(secondary, registry=legacy) == "secondary"


def test_real_v3_has_only_primary_baostock():
    # The committed v3 registry was drafted with only the primary baostock
    # source (the akshare secondary was blocked pre-R4E.3).  Resolving it must
    # fail-closed on the missing secondary, never silently fall back.
    assert REGISTRY_V3["providers"][0]["provider"] == "baostock"
    assert len(REGISTRY_V3["providers"]) == 1
    with pytest.raises(provider_roles.ProviderRoleError):
        provider_roles.resolve_registry_providers(REGISTRY_V3)


def test_formal_release_no_hardcoded_akshare():
    src = (_REPO_ROOT / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e_series_preflight.py").read_text(encoding="utf-8")
    # The formal release path must never call load(..., "akshare").
    assert 'load_and_validate_market_object(registry, cache_root, "akshare")' not in src
    assert 'load_and_validate_market_object(reg, cache_root, "akshare")' not in src
    # The R4E.4 formal path must resolve the secondary by ROLE, never by the
    # provider name "akshare".  The name may appear only as a transport_library
    # (the Tencent transport) or in legacy/fixture contexts, never as the
    # role-deciding criterion.
    assert "provider_roles.resolve_registry_providers(registry)" in src
    # The R4E.4 formal function must not name "akshare" as the secondary role.
    pre = src.split("def _cmd_formal_r4e4(")[1].split("def ")[0]
    assert '"akshare"' not in pre
    assert "'akshare'" not in pre


def test_promote_no_sina_fallback(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        promote_selected_tencent,
    )
    # Build a cache with baostock but WITHOUT the tencent object (only sina).
    src = tmp_path / "baostock" / f"{PRIMARY_SHA}.parquet"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"x")
    with pytest.raises(FileNotFoundError):
        promote_selected_tencent(
            r4e3_cache_root=tmp_path, formal_cache_root=tmp_path / "formal"
        )


# ── promotion ──────────────────────────────────────────────────────────────


def test_promote_exact_object_passes(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        verify_object_identity,
    )
    dates = _dates()
    rows = _normalized(dates)
    path, sha = _write_object(tmp_path / "tencent", f"{sha0()}.parquet", rows)
    # The expected sha must be the real content sha (the file name is arbitrary).
    ident = verify_object_identity(
        path,
        expected_sha=sha,
        expected_table_digest=spp.canonical_table_digest(rows),
        expected_row_count=len(dates),
        expected_first="2021-01-04",
        expected_last="2026-07-31",
    )
    assert ident["row_count"] == len(dates)
    assert ident["first_trade_date"] == "2021-01-04"
    assert ident["last_trade_date"] == "2026-07-31"


def sha0() -> str:
    return "0" * 64


def test_promote_sha_error_fails(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        verify_object_identity,
    )
    rows = _normalized(_dates())
    path, _ = _write_object(tmp_path / "t", f"{sha0()}.parquet", rows)
    with pytest.raises(ValueError, match="sha mismatch"):
        verify_object_identity(
            path,
            expected_sha="1" * 64,
            expected_table_digest=spp.canonical_table_digest(rows),
            expected_row_count=len(rows),
            expected_first="2021-01-04",
            expected_last="2026-07-31",
        )


def test_promote_table_digest_error_fails(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        verify_object_identity,
    )
    rows = _normalized(_dates())
    path, sha = _write_object(tmp_path / "t", f"{sha0()}.parquet", rows)
    with pytest.raises(ValueError, match="table digest mismatch"):
        verify_object_identity(
            path,
            expected_sha=sha,
            expected_table_digest="f" * 64,
            expected_row_count=len(rows),
            expected_first="2021-01-04",
            expected_last="2026-07-31",
        )


def test_promote_wrong_endpoint_fails():
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        validate_endpoint_identity,
    )
    # Rows bound to a different endpoint must be rejected by the endpoint guard.
    rows = _normalized(_dates(), endpoint="evil.example.com")
    with pytest.raises(ValueError, match="endpoint identity mismatch"):
        validate_endpoint_identity(rows, "web.ifzq.gtimg.cn")
    # The frozen R4E.3 endpoint passes.
    validate_endpoint_identity(_normalized(_dates()), "web.ifzq.gtimg.cn")


def test_promote_not_selected_provider_fails(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        verify_object_identity,
    )
    # An object whose content differs from the frozen selected-provider identity
    # is NOT the selected provider and must be rejected (sha mismatch).
    dates = _dates()
    rows = _normalized(dates)
    rows[0]["close"] = "9.99"  # tamper the content
    path, _ = _write_object(tmp_path, f"{sha0()}.parquet", rows)
    with pytest.raises(ValueError, match="sha mismatch"):
        verify_object_identity(
            path,
            expected_sha=sha0(),  # the frozen selected-object sha; tampered content differs
            expected_table_digest=spp.canonical_table_digest(rows),
            expected_row_count=len(dates),
            expected_first="2021-01-04",
            expected_last="2026-07-31",
        )


# ── registry v4 ────────────────────────────────────────────────────────────


def test_registry_v3_unchanged():
    assert REGISTRY_V3["contract"] == "market_data_snapshot_registry_v3"
    assert REGISTRY_V3["reconciliation_status"] == "pending_real_reconciliation"
    assert REGISTRY_V3["providers"][0]["provider"] == "baostock"


def test_registry_v4_supersedes_v3(tmp_path):
    reg, _, _, _ = _two_objects(tmp_path)
    assert reg["supersedes_registry"] == "events/market_data_snapshot_registry_v3.json"
    assert reg["supersession_reason"] == (
        "selected_alternative_secondary_provider_formally_integrated"
    )


def test_registry_draft_cannot_prewrite_pass(tmp_path):
    reg, _, _, _ = _two_objects(tmp_path)
    assert reg["integration_status"] == "PENDING_REAL_RECONCILIATION"
    assert reg["reconciliation_status"] == "pending"


def test_registry_object_identity_recomputable(tmp_path):
    reg, _, primary, secondary = _two_objects(tmp_path)
    assert primary["object_sha256"] == reg["providers"][0]["sha256"]
    assert secondary["object_sha256"] == reg["providers"][1]["sha256"]
    assert primary["row_count"] == len(_dates())
    assert secondary["row_count"] == len(_dates())


def test_registry_finalize_after_reconciliation(tmp_path):
    from ashare_research.tools.m2_stage2k1r4e4_secondary_provider_integration import (
        run_formal_reconciliation,
    )
    reg, cache_root, _, _ = _two_objects(tmp_path)
    result = run_formal_reconciliation(registry=reg, cache_root=cache_root)
    assert result["reconciliation"]["common_trade_days"] == len(_dates())
    assert result["report"]["reconciliation_status"] == "pass"
    assert mkt.validate_reconciliation_report_v2(result["report"])["valid"] is True


# ── v2 reconciliation ──────────────────────────────────────────────────────


def test_reconciliation_1351_identical(tmp_path):
    reg, _, primary, secondary = _two_objects(tmp_path)
    rec = mkt.reconcile_market_close_series_v2(primary, secondary)
    assert rec["common_trade_days"] == len(_dates())
    assert rec["primary_only_dates"] == []
    assert rec["secondary_only_dates"] == []
    assert rec["max_abs_difference"] == "0"
    assert rec["differences_over_tolerance_count"] == 0
    assert rec["daily_comparison_digest"]


def test_reconciliation_date_set_mismatch_fails(tmp_path):
    dates = _dates()
    # Find an interior gap of >=4 real days, then substitute an intermediate
    # weekday NOT in the primary set -> same row count, different date set.
    idx = next(
        i for i in range(1, len(dates) - 1)
        if (date.fromisoformat(dates[i]) - date.fromisoformat(dates[i - 1])).days >= 4
    )
    lo = date.fromisoformat(dates[idx - 1])
    hi = date.fromisoformat(dates[idx])
    swap = lo + timedelta(days=1)
    while swap.isoformat() in dates or swap.weekday() >= 5:
        swap += timedelta(days=1)
    assert lo < swap < hi
    sec_dates = list(dates)
    sec_dates[idx] = swap.isoformat()
    primary_rows = _loader_rows(dates)
    secondary_rows = _loader_rows(sec_dates)
    _, p_sha = _write_content_addressed(tmp_path, "baostock", primary_rows)
    _, s_sha = _write_content_addressed(
        tmp_path, "r4e4/tencent_via_akshare", secondary_rows
    )
    reg = _v4_registry(p_sha, s_sha, dates=dates)
    primary = mkt.load_and_validate_market_object_entry(reg, tmp_path, reg["providers"][0])
    secondary = mkt.load_and_validate_market_object_entry(reg, tmp_path, reg["providers"][1])
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series_v2(primary, secondary)


def test_reconciliation_over_tolerance_fails(tmp_path):
    dates = _dates()
    secondary_rows = _loader_rows(dates)
    secondary_rows[-1]["close"] = 5.05  # +0.05 over the 0.01 tolerance
    _, p_sha = _write_content_addressed(tmp_path, "baostock", _loader_rows(dates))
    _, s_sha = _write_content_addressed(
        tmp_path, "r4e4/tencent_via_akshare", secondary_rows
    )
    reg = _v4_registry(p_sha, s_sha, dates=dates)
    primary = mkt.load_and_validate_market_object_entry(reg, tmp_path, reg["providers"][0])
    secondary = mkt.load_and_validate_market_object_entry(reg, tmp_path, reg["providers"][1])
    with pytest.raises(mkt.MarketReconciliationError, match="exceed tolerance"):
        mkt.reconcile_market_close_series_v2(primary, secondary)


def test_v2_digest_binds_provider_identity(tmp_path):
    reg, _, primary, secondary = _two_objects(tmp_path)
    rec1 = mkt.reconcile_market_close_series_v2(primary, secondary)
    d1 = mkt.build_reconciliation_digest_v2(primary, secondary, rec1)
    # Same economic content, different secondary provider_id must change the digest.
    secondary2 = dict(secondary)
    secondary2["provider_id"] = "sina_via_akshare"
    d2 = mkt.build_reconciliation_digest_v2(primary, secondary2, rec1)
    assert d1 != d2


def test_v2_report_validates(tmp_path):
    reg, _, primary, secondary = _two_objects(tmp_path)
    rec = mkt.reconcile_market_close_series_v2(primary, secondary)
    ledger = mkt.build_mismatch_ledger_v2(rec)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    report = mkt.build_reconciliation_report_v2(
        primary, secondary, rec, ledger_digest=ledger_digest
    )
    assert report["schema"] == "petrochina_market_close_reconciliation_v2"
    assert report["secondary_provider"]["provider_role"] == "secondary"
    assert mkt.validate_reconciliation_report_v2(report)["valid"] is True
    # The digest must be independently recomputable.
    assert report["reconciliation_digest"] == mkt.build_reconciliation_digest_v2(
        primary, secondary, rec, ledger_digest=ledger_digest
    )


# ── candidate v2 ───────────────────────────────────────────────────────────


def _market_meta(primary_sha: str, secondary_sha: str, digest: str) -> dict:
    return {
        "primary_provider": "baostock_primary",
        "primary_provider_role": "primary",
        "primary_transport_library": "baostock",
        "primary_underlying_provider": "baostock",
        "primary_object_sha256": primary_sha,
        "primary_object_key": f"baostock/{primary_sha}.parquet",
        "primary_row_count": 1351,
        "secondary_provider": "tencent_via_akshare",
        "secondary_provider_role": "secondary",
        "secondary_transport_library": "akshare",
        "secondary_underlying_provider": "tencent",
        "secondary_endpoint_identity": "web.ifzq.gtimg.cn",
        "secondary_object_sha256": secondary_sha,
        "secondary_object_key": f"r4e4/tencent_via_akshare/{secondary_sha}.parquet",
        "secondary_row_count": 1351,
        "secondary_present": True,
        "secondary_verified": True,
        "reconciliation_status": "pass",
        "market_reconciliation_digest": digest,
        "reconciliation_contract_version": mkt.RECONCILIATION_CONTRACT_VERSION_V2,
        "market_rows": 1351,
        "first_trade_date": "2021-01-04",
        "last_trade_date": "2026-07-31",
    }


def _build_series(market_rows: list[dict], market_meta: dict) -> dict:
    reported, reconciled = fixtures.load_fixture_bundles(Path("."))
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    return valuation_series.build_valuation_series(market_rows, market_meta, timelines)


def test_candidate_4053_observations_and_metrics():
    primary_rows, _, _ = fixtures.load_fixture_dual_market(Path("."))
    market_rows = [{"trade_date": r["trade_date"], "close": r["close"]} for r in primary_rows]
    meta = _market_meta("p" * 64, "s" * 64, "d" * 64)
    series = _build_series(market_rows, meta)
    # 3 metrics (PE_A_TTM, PB_A_MRQ, PS_A_TTM) × one observation per market row.
    assert series["observation_count"] == 3 * len(market_rows)
    assert {o["metric_id"] for o in series["observations"]} == {
        "PE_A_TTM", "PB_A_MRQ", "PS_A_TTM"
    }


def test_observation_binds_both_object_shas_and_v2_digest():
    primary_rows, _, _ = fixtures.load_fixture_dual_market(Path("."))
    market_rows = [{"trade_date": r["trade_date"], "close": r["close"]} for r in primary_rows]
    meta = _market_meta("a" * 64, "b" * 64, "recondigest")
    series = _build_series(market_rows, meta)
    obs = series["observations"][0]
    assert obs["primary_market_object_sha256"] == "a" * 64
    assert obs["secondary_market_object_sha256"] == "b" * 64
    assert obs["market_reconciliation_digest"] == "recondigest"


def test_candidate_non_production_no_percentile():
    primary_rows, _, _ = fixtures.load_fixture_dual_market(Path("."))
    market_rows = [{"trade_date": r["trade_date"], "close": r["close"]} for r in primary_rows]
    series = _build_series(market_rows, _market_meta("p" * 64, "s" * 64, "d" * 64))
    assert series["non_production"] is True
    assert series["percentile_computed"] is False
    for obs in series["observations"]:
        assert obs["non_production"] is True
        assert obs["percentile_computed"] is False
        assert obs["score_eligible"] is False
        assert obs["production_eligible"] is False
        assert "valuation_percentile" not in obs


def test_candidate_ratio_recomputable():
    primary_rows, _, _ = fixtures.load_fixture_dual_market(Path("."))
    market_rows = [{"trade_date": r["trade_date"], "close": r["close"]} for r in primary_rows]
    series = _build_series(market_rows, _market_meta("p" * 64, "s" * 64, "d" * 64))
    verification = series_validation.verify_observations(series)
    assert verification["identity_consistent"] is True
    assert verification["ratio_consistent"] is True


def test_dual_oracle_identical():
    primary_rows, _, _ = fixtures.load_fixture_dual_market(Path("."))
    market_rows = [{"trade_date": r["trade_date"], "close": r["close"]} for r in primary_rows]
    reported, reconciled = fixtures.load_fixture_bundles(Path("."))
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    dual = series_validation.validate_dual_oracle(market_rows, timelines)
    assert dual["all_identical"] is True


def test_no_forward_nearest_join():
    from ashare_research.pit_valuation import temporal_join
    src = Path(temporal_join.__file__).read_text(encoding="utf-8")
    # The join must be backward-only (effective_from <= trade_date).  A forward
    # ("effective_from >= trade_date") or nearest ASOF join is forbidden.  The
    # word "forward cursor" in the docstring describes the sweep's internal
    # cursor, which is legitimate and must not trip this guard.
    assert "effective_from <= trade_date" in src
    assert "effective_from >= trade_date" not in src
    assert "nearest" not in src.lower()


# ── economic identity migration v2 ─────────────────────────────────────────


def _obs(metric_id: str, trade_date: str, *, ratio: str | None, status: str,
         close: str, fs_id: str, obs_id: str) -> dict:
    return {
        "metric_id": metric_id,
        "trade_date": trade_date,
        "ratio_decimal": ratio,
        "status": status,
        "market_close_decimal": close,
        "financial_state_id": fs_id,
        "observation_id": obs_id,
    }


def _series_v1like() -> dict:
    return {"observations": [
        _obs("PE_A_TTM", "2021-01-04", ratio="10.5", status="computed",
             close="6.0", fs_id="old1", obs_id="id1"),
        _obs("PB_A_MRQ", "2021-01-04", ratio="1.25", status="computed",
             close="6.0", fs_id="old2", obs_id="id2"),
    ]}


def test_migration_economic_values_unchanged():
    from ashare_research.tools.m2_stage2k1r4e_series_preflight import (
        _build_identity_migration_v2,
        _economic_migration_trusted,
    )
    old = _series_v1like()
    new = {"observations": [
        # economic values identical; identity fields changed (expected/allowed)
        _obs("PE_A_TTM", "2021-01-04", ratio="10.5", status="computed",
             close="6", fs_id="new1", obs_id="new1"),
        _obs("PB_A_MRQ", "2021-01-04", ratio="1.25", status="computed",
             close="6", fs_id="new2", obs_id="new2"),
    ]}
    mig = _build_identity_migration_v2(old, new)
    assert mig["ratio_changed_count"] == 0
    assert mig["status_changed_count"] == 0
    assert mig["market_close_changed_count"] == 0  # "6.0" == "6" (Decimal-normalized)
    assert mig["financial_state_changed_count"] == 2  # lineage identity change allowed
    assert mig["observation_id_changed_count"] == 2
    assert _economic_migration_trusted(mig) is True


def test_migration_unexplained_ratio_change_fails():
    from ashare_research.tools.m2_stage2k1r4e_series_preflight import (
        _build_identity_migration_v2,
        _economic_migration_trusted,
    )
    old = _series_v1like()
    new = {"observations": [
        _obs("PE_A_TTM", "2021-01-04", ratio="99.0", status="computed",
             close="6.0", fs_id="new1", obs_id="new1"),
        _obs("PB_A_MRQ", "2021-01-04", ratio="1.25", status="computed",
             close="6.0", fs_id="new2", obs_id="new2"),
    ]}
    mig = _build_identity_migration_v2(old, new)
    assert mig["ratio_changed_count"] >= 1
    assert _economic_migration_trusted(mig) is False


def test_migration_status_change_fails():
    from ashare_research.tools.m2_stage2k1r4e_series_preflight import (
        _build_identity_migration_v2,
        _economic_migration_trusted,
    )
    old = _series_v1like()
    new = {"observations": [
        _obs("PE_A_TTM", "2021-01-04", ratio="10.5", status="missing_ttm_input",
             close="6.0", fs_id="new1", obs_id="new1"),
        _obs("PB_A_MRQ", "2021-01-04", ratio="1.25", status="computed",
             close="6.0", fs_id="new2", obs_id="new2"),
    ]}
    mig = _build_identity_migration_v2(old, new)
    assert mig["status_changed_count"] >= 1
    assert _economic_migration_trusted(mig) is False


# ── R4E.4 manifest ─────────────────────────────────────────────────────────


def _write_manifest(out_root: Path, files: list[Path], schema: str) -> Path:
    from ashare_research.scoring import artifact_manifest
    from ashare_research.scoring import content_digest as cd
    entries = []
    for path in sorted(files, key=lambda p: str(p)):
        digest = cd.digest_file(path, algorithm="sha256_lf_normalized_bytes_v1")
        entries.append({
            "path": path.relative_to(out_root).as_posix(),
            "digest_algorithm": digest.algorithm,
            "sha256": digest.sha256,
            "byte_size": digest.byte_size,
        })
    manifest = {"schema": schema, "version": "2.0", "files": entries}
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = out_root / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    return mpath


def test_r4e4_manifest_passes_and_tamper_fails(tmp_path):
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    _write_manifest(tmp_path, [payload], "m2_stage2k1r4e4_artifact_manifest_v2")
    from ashare_research.scoring import artifact_manifest
    res = artifact_manifest.verify_artifact_manifest(
        tmp_path / "manifest.json", repository_root=tmp_path
    )
    assert res.status == "pass"
    payload.write_text('{"x": 2}\n', encoding="utf-8")
    res2 = artifact_manifest.verify_artifact_manifest(
        tmp_path / "manifest.json", repository_root=tmp_path
    )
    assert res2.status == "fail"
    assert res2.hash_mismatches


def test_r4e4_manifest_schema_registered():
    from ashare_research.scoring import artifact_manifest
    assert "m2_stage2k1r4e4_artifact_manifest_v2" in artifact_manifest.ALLOWED_MANIFEST_SCHEMAS
    assert "m2_stage2k1r4e4_artifact_manifest_v2" in artifact_manifest.V2_SCHEMAS


# ── product boundary ───────────────────────────────────────────────────────


def test_no_percentile_no_scoring_no_prod_metric():
    src = (_REPO_ROOT / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e4_secondary_provider_integration.py").read_text(
        encoding="utf-8"
    )
    for needle in ("percentile", "score_eligible", "production_eligible"):
        assert needle in src
    for needle in ("metric_result", "peer", "m3_started", "valuation_shadow"):
        assert needle not in (_REPO_ROOT / "src" / "ashare_research" / "pit_valuation"
                              / "provider_roles.py").read_text(encoding="utf-8").lower()


def test_no_default_db_write():
    for path in (
        _REPO_ROOT / "src" / "ashare_research" / "pit_valuation" / "provider_roles.py",
        _REPO_ROOT / "src" / "ashare_research" / "tools"
        / "m2_stage2k1r4e4_secondary_provider_integration.py",
    ):
        assert "research.duckdb" not in path.read_text(encoding="utf-8")
        assert "duckdb" not in path.read_text(encoding="utf-8").lower()


def test_no_peer_no_m3():
    src = (_REPO_ROOT / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e4_secondary_provider_integration.py").read_text(
        encoding="utf-8"
    )
    assert "peer" not in src.lower()
    assert "m3" not in src.lower()


def test_registry_v3_not_modified_by_cli():
    src = (_REPO_ROOT / "src" / "ashare_research" / "tools"
           / "m2_stage2k1r4e4_secondary_provider_integration.py").read_text(
        encoding="utf-8"
    )
    assert "market_data_snapshot_registry_v3" not in src.replace(
        "events/market_data_snapshot_registry_v3.json", ""
    )
    assert REGISTRY_V3["reconciliation_status"] == "pending_real_reconciliation"


def test_no_absolute_path_no_proxy_no_token():
    for path in (
        _REPO_ROOT / "src" / "ashare_research" / "pit_valuation" / "provider_roles.py",
        _REPO_ROOT / "src" / "ashare_research" / "tools"
        / "m2_stage2k1r4e4_secondary_provider_integration.py",
    ):
        src = path.read_text(encoding="utf-8")
        assert r"D:\\" not in src and r"D:/" not in src
        for needle in ("HTTP_PROXY", "HTTPS_PROXY", "socks5", "set_token", "token="):
            assert needle not in src.lower()
