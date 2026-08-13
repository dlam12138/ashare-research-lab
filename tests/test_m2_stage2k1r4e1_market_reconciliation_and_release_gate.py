"""M2 Stage 2K.1R4E.1 — market reconciliation, PB lineage, release-gate tests.

Covers the dual-source market object validation, the daily Decimal close
reconciliation, the PB complete-input lineage, the fail-closed CLI exit codes,
the v2 artifact manifest, and the product-boundary invariants.  All market
objects are synthetic (no real Parquet is committed).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.pit_valuation import (
    financial_state,
    fixtures,
)
from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation.series_contract import (
    SYMBOL,
    canonical_digest,
    parse_decimal,
)
from ashare_research.tools.m2_stage2k1r4e_series_preflight import (
    DECISION_ALLOWED,
    DECISION_GAPS,
    DECISION_NOT_TRUSTED,
    decision_to_exit_code,
)
from ashare_research.tools.m2_stage2k1r4e_series_preflight import (
    main as cli_main,
)

REPORTED, RECONCILED = fixtures.load_fixture_bundles(Path("."))

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_out(name: str) -> Path:
    """A repo-relative output root (manifest paths must be repo-relative)."""
    out = _REPO_ROOT / "tmp" / f"r4e1-test-{name}"
    if out.exists():
        import shutil

        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    return out

# ── helpers ────────────────────────────────────────────────────────────────


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


def _rows(dates: list[str], *, close_start: float = 5.0, symbol: str = SYMBOL) -> list[dict]:
    rows = []
    for i, d in enumerate(dates):
        rows.append(
            {
                "symbol": symbol,
                "trade_date": d,
                "close": round(close_start + i * 0.01, 2),
                "is_trading": True,
            }
        )
    return rows


def _write_object(root: Path, subdir: str, rows: list[dict]) -> tuple[Path, str]:
    import pandas as pd

    path = root / subdir / "object.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)
    return path, _sha(path.read_bytes())


def _registry(*, common: int, max_diff: str, providers: list[dict]) -> dict:
    return {
        "contract": "market_data_snapshot_registry_v2",
        "symbol": SYMBOL,
        "providers": providers,
        "common_trade_days": common,
        "close_max_abs_difference": max_diff,
        "close_differences_within_0_01": True,
        "reconciliation_status": "pass",
    }


def _provider(name: str, sha: str, row_count: int, *, key: str = "") -> dict:
    return {
        "provider": name,
        "object_key": key or f"{name}/object.parquet",
        "sha256": sha,
        "row_count": row_count,
        "adjustment": "none",
        "date_range": {"start": "2021-01-04", "end": "2026-07-31"},
    }


def _two_objects(
    tmp_path: Path,
    *,
    secondary_symbol: str = SYMBOL,
    secondary_invalid_sha: bool = False,
    secondary_rows=None,
) -> tuple[dict, dict, dict]:
    dates = _market_dates()
    primary_rows = _rows(dates)
    secondary_rows = (
        _rows(dates) if secondary_rows is None else secondary_rows
    )
    p_path, p_sha = _write_object(tmp_path, "baostock", primary_rows)
    s_path, s_sha = _write_object(tmp_path, "akshare", secondary_rows)
    if secondary_invalid_sha:
        s_sha = "0" * 64
    reg = _registry(
        common=len(primary_rows),
        max_diff="0.0",
        providers=[
            _provider("baostock", p_sha, len(primary_rows)),
            _provider("akshare", s_sha, len(secondary_rows)),
        ],
    )
    return reg, primary_rows, secondary_rows


# ── single-object validation ───────────────────────────────────────────────


def test_two_correct_objects_reconcile_pass(tmp_path):
    reg, p_rows, s_rows = _two_objects(tmp_path)
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    rec = mkt.reconcile_market_close_series(primary, secondary)
    assert rec["common_trade_days"] == len(p_rows)
    assert rec["differences_over_tolerance_count"] == 0
    assert rec["max_abs_difference"] == "0"


def test_secondary_missing_raises_missing_error(tmp_path):
    reg, p_rows, _ = _two_objects(tmp_path)
    # remove the akshare object
    (tmp_path / "akshare" / "object.parquet").unlink()
    mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    with pytest.raises(mkt.MarketObjectMissingError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_secondary_sha_wrong_raises_invalid(tmp_path):
    reg, _, _ = _two_objects(tmp_path, secondary_invalid_sha=True)
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_missing_required_column_fails(tmp_path):
    reg, p_rows, _ = _two_objects(tmp_path)
    # drop the 'symbol' column from the secondary object
    dates = _market_dates()
    bad = [{"trade_date": d, "close": 5.0, "is_trading": True} for d in dates]
    _write_object(tmp_path, "akshare", bad)
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_wrong_symbol_fails(tmp_path):
    reg, _, _ = _two_objects(tmp_path, secondary_symbol="000001.SZ")
    # rebuild secondary with wrong symbol, keep sha consistent
    dates = _market_dates()
    bad = _rows(dates, symbol="000001.SZ")
    _, s_sha = _write_object(tmp_path, "akshare", bad)
    reg["providers"][1]["sha256"] = s_sha
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_adjustment_not_none_fails(tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    reg["providers"][1]["adjustment"] = "qfq"
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_row_count_mismatch_fails(tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    reg["providers"][1]["row_count"] = 999
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_duplicate_or_nonincreasing_date_fails(tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    dates = _market_dates()
    dup = _rows(dates)
    dup[0]["trade_date"] = dup[1]["trade_date"]  # duplicate / non-increasing
    _, s_sha = _write_object(tmp_path, "akshare", dup)
    reg["providers"][1]["sha256"] = s_sha
    with pytest.raises(mkt.MarketObjectInvalidError):
        mkt.load_and_validate_market_object(reg, tmp_path, "akshare")


def test_one_side_missing_trade_day_fails(tmp_path):
    # Secondary is missing one *middle* trade day -> both objects still load
    # (row count and date range match their own registry entries) but the
    # daily reconciliation sees a date-set disagreement and fails closed.
    dates = _market_dates()
    primary_rows = _rows(dates)
    secondary_rows = _rows(dates[:500] + dates[501:])  # drop one middle day
    p_path, p_sha = _write_object(tmp_path, "baostock", primary_rows)
    s_path, s_sha = _write_object(tmp_path, "akshare", secondary_rows)
    reg = _registry(
        common=len(secondary_rows),
        max_diff="0.0",
        providers=[
            _provider("baostock", p_sha, len(primary_rows)),
            _provider("akshare", s_sha, len(secondary_rows)),
        ],
    )
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series(primary, secondary)


def test_close_over_tolerance_fails(tmp_path):
    dates = _market_dates()
    primary_rows = _rows(dates)
    secondary_rows = [dict(r) for r in primary_rows]
    secondary_rows[-1]["close"] = round(secondary_rows[-1]["close"] + 0.05, 2)
    p_path, p_sha = _write_object(tmp_path, "baostock", primary_rows)
    s_path, s_sha = _write_object(tmp_path, "akshare", secondary_rows)
    reg = _registry(
        common=len(primary_rows),
        max_diff="0.0",
        providers=[
            _provider("baostock", p_sha, len(primary_rows)),
            _provider("akshare", s_sha, len(secondary_rows)),
        ],
    )
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series(primary, secondary)


def test_sha_only_not_enough_for_pass(tmp_path):
    # A SHA match alone must not be treated as a reconciliation: the closes
    # still differ over tolerance and the real reconcile must fail.
    dates = _market_dates()
    primary_rows = _rows(dates)
    secondary_rows = [dict(r) for r in primary_rows]
    secondary_rows[0]["close"] = round(secondary_rows[0]["close"] + 0.02, 2)
    p_path, p_sha = _write_object(tmp_path, "baostock", primary_rows)
    s_path, s_sha = _write_object(tmp_path, "akshare", secondary_rows)
    reg = _registry(
        common=len(primary_rows),
        max_diff="0.0",
        providers=[
            _provider("baostock", p_sha, len(primary_rows)),
            _provider("akshare", s_sha, len(secondary_rows)),
        ],
    )
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    # Both SHAs verify, yet the daily reconciliation must not "pass".
    assert primary["actual_sha256"] == reg["providers"][0]["sha256"]
    assert secondary["actual_sha256"] == reg["providers"][1]["sha256"]
    with pytest.raises(mkt.MarketReconciliationError):
        mkt.reconcile_market_close_series(primary, secondary)


def test_reconciliation_digest_independently_recomputable(tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    rec = mkt.reconcile_market_close_series(primary, secondary)
    ledger = mkt.build_mismatch_ledger(rec)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    report = mkt.build_reconciliation_report(primary, secondary, rec, ledger_digest=ledger_digest)
    # digest recomputed from the same inputs must equal the bound digest.
    assert report["reconciliation_digest"] == mkt.build_reconciliation_digest(
        primary, secondary, rec, ledger_digest=ledger_digest
    )
    # and the report validates.
    assert mkt.validate_reconciliation_report(report)["valid"] is True


# ── Decimal parsing ────────────────────────────────────────────────────────


def test_loader_has_no_float_close():
    src = Path(mkt.__file__).read_text(encoding="utf-8")
    # No line may cast a close via float(); the Decimal must come from str().
    for needle in ("float(r", "float(close", "float(row", "float(c["):
        assert needle not in src


def test_close_parsed_from_source_scalar_string():
    # The Decimal must come from str(source_scalar), never from a binary float.
    for probe in ("7.92", "7.0", "5.01"):
        assert parse_decimal(probe) == Decimal(probe)
        assert str(parse_decimal(probe)) == str(Decimal(probe))


def test_decimal_identity_platform_stable(tmp_path):
    # Canonical string comparison is locale/float-repr independent.
    reg, _, _ = _two_objects(tmp_path)
    primary = mkt.load_and_validate_market_object(reg, tmp_path, "baostock")
    secondary = mkt.load_and_validate_market_object(reg, tmp_path, "akshare")
    rec = mkt.reconcile_market_close_series(primary, secondary)
    d1 = mkt.build_reconciliation_digest(primary, secondary, rec)
    # Rebuild from identical inputs -> identical digest.
    d2 = mkt.build_reconciliation_digest(primary, secondary, rec)
    assert d1 == d2
    for row in rec["daily_comparison"]:
        assert row["baostock_close"] == row["akshare_close"]


# ── PB complete-input lineage ──────────────────────────────────────────────


def _pb_core_fact(concept_id, year, report_type, value, eff, avail, **kw):
    _end = {"q1": "03-31", "half_year": "06-30", "q3": "09-30", "annual": "12-31"}
    return {
        "concept_id": concept_id,
        "symbol": SYMBOL,
        "period_end": f"{year}-{_end[report_type]}",
        "value": value,
        "available_at": avail,
        "effective_from": eff,
        "restatement_version": kw.get("restatement_version", "original"),
        "supersedes_fact_id": kw.get("supersedes_fact_id", ""),
        "source_id": kw.get("source_id", "TEST"),
        "fact_id": kw.get("fact_id", ""),
    }


def _finalize_fact(fact: dict) -> dict:
    payload = {k: v for k, v in fact.items() if k != "fact_id"}
    fact["fact_id"] = canonical_digest(payload)
    return fact


def test_pb_input_fact_ids_include_equity_and_shares():
    reported, reconciled = fixtures.load_fixture_bundles(Path("."))
    pb = financial_state.build_pb_states(reported, reconciled)
    for state in pb:
        assert state["status"] == "computed"
        assert state["equity_fact_id"]
        assert state["period_end_shares_fact_id"]
        assert set(state["input_fact_ids"]) == {
            state["equity_fact_id"],
            state["period_end_shares_fact_id"],
        }


def test_pb_effective_and_available_are_max_of_inputs():
    equity = _finalize_fact(
        _pb_core_fact("equity_attributable_to_parent", 2021, "annual", 1.5e12,
                      "2022-04-28", "2022-04-28")
    )
    share = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      183020977818, "2022-04-28", "2022-04-28")
    )
    pb = financial_state.build_pb_states([equity], [share])
    state = pb[0]
    assert state["effective_from"] == "2022-04-28"
    assert state["available_at_max"] == "2022-04-28"
    assert state["equity_effective_from"] == "2022-04-28"
    assert state["period_end_shares_effective_from"] == "2022-04-28"


def test_pb_share_later_than_equity_not_prematurely_visible():
    equity = _finalize_fact(
        _pb_core_fact("equity_attributable_to_parent", 2021, "annual", 1.5e12,
                      "2022-04-28", "2022-04-28")
    )
    # share fact effective AFTER the equity -> not visible at the equity's eff.
    share = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      183020977818, "2022-05-10", "2022-05-10")
    )
    pb = financial_state.build_pb_states([equity], [share])
    state = pb[0]
    assert state["status"] == "unmatched_equity_share_context"
    assert state["period_end_shares_decimal"] is None


def test_pb_multi_version_shares_order_independent():
    # Two share versions (original superseded by restated), same effective date.
    orig = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      180000000000, "2022-04-28", "2022-04-28",
                      restatement_version="original")
    )
    rest = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      183020977818, "2022-04-28", "2022-04-28",
                      restatement_version="restated_1", supersedes_fact_id=orig["fact_id"])
    )
    equity = _finalize_fact(
        _pb_core_fact("equity_attributable_to_parent", 2021, "annual", 1.5e12,
                      "2022-04-28", "2022-04-28")
    )
    # order A
    a = financial_state.build_pb_states([equity], [orig, rest])[0]
    # order B (reversed list)
    b = financial_state.build_pb_states([equity], [rest, orig])[0]
    assert a["period_end_shares_fact_id"] == rest["fact_id"]
    assert a["period_end_shares_fact_id"] == b["period_end_shares_fact_id"]
    assert a["financial_state_id"] == b["financial_state_id"]


def test_pb_ambiguous_shares_fail_closed():
    # Two share versions, same effective date, no unambiguous supersession.
    s1 = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      180000000000, "2022-04-28", "2022-04-28")
    )
    s2 = _finalize_fact(
        _pb_core_fact("total_ordinary_shares_at_period_end", 2021, "annual",
                      183020977818, "2022-04-28", "2022-04-28")
    )
    equity = _finalize_fact(
        _pb_core_fact("equity_attributable_to_parent", 2021, "annual", 1.5e12,
                      "2022-04-28", "2022-04-28")
    )
    with pytest.raises(ValueError):
        financial_state.build_pb_states([equity], [s1, s2])


# ── CLI exit-code contract ─────────────────────────────────────────────────


def test_decision_to_exit_code_mapping():
    assert decision_to_exit_code(DECISION_ALLOWED) == 0
    assert decision_to_exit_code(DECISION_GAPS) == 1
    assert decision_to_exit_code(DECISION_NOT_TRUSTED) == 2
    assert decision_to_exit_code("UNKNOWN") == 2


def _write_bundles(tmp_path):
    rb = tmp_path / "reported.json"
    cb = tmp_path / "reconciled.json"
    rb.write_text(json.dumps({"facts": REPORTED}), encoding="utf-8")
    cb.write_text(json.dumps({"facts": RECONCILED}), encoding="utf-8")
    return rb, cb


def _run_formal(monkeypatch, tmp_path, cache_root, output_root, reg):
    from ashare_research.pit_valuation import series_contract as sc
    rb, cb = _write_bundles(tmp_path)
    monkeypatch.setattr(sc, "validate_all_contracts", lambda: {"ok": True})
    monkeypatch.setattr(sc, "load_market_snapshot_registry", lambda: reg)
    return cli_main(
        [
            "formal",
            "--market-cache-root", str(cache_root),
            "--output-root", str(output_root),
            "--reported-bundle", str(rb),
            "--reconciled-bundle", str(cb),
        ]
    )


def test_cli_allowed_returns_0(monkeypatch, tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    out = _repo_out("allowed")
    code = _run_formal(monkeypatch, tmp_path, tmp_path, out, reg)
    assert code == 0
    assert (out / "m2_stage2k1r4e1_decision.json").exists()


def test_cli_gaps_returns_1(monkeypatch, tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    (tmp_path / "akshare" / "object.parquet").unlink()
    out = _repo_out("gaps")
    code = _run_formal(monkeypatch, tmp_path, tmp_path, out, reg)
    assert code == 1
    decision = json.loads((out / "m2_stage2k1r4e1_decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == DECISION_GAPS
    # secondary missing -> no candidate v2 published
    assert not (out / "petrochina_pit_valuation_series_candidate_v2.json").exists()


def test_cli_not_trusted_returns_2(monkeypatch, tmp_path):
    reg, _, _ = _two_objects(tmp_path, secondary_invalid_sha=True)
    out = _repo_out("not-trusted")
    code = _run_formal(monkeypatch, tmp_path, tmp_path, out, reg)
    assert code == 2


def test_cli_output_root_does_not_change_exit_code(monkeypatch, tmp_path):
    reg, _, _ = _two_objects(tmp_path)
    code_a = _run_formal(monkeypatch, tmp_path, tmp_path, _repo_out("outA"), reg)
    code_b = _run_formal(monkeypatch, tmp_path, tmp_path, _repo_out("outB"), reg)
    assert code_a == 0
    assert code_b == 0


def test_fixtures_cli_uses_same_mapping(tmp_path):
    # fixtures command must not hard-code 0; real ALLOWED path returns 0.
    out = _repo_out("fixtures-mapping")
    code = cli_main(["fixtures", "--fixture-root", str(Path(".")), "--output-root", str(out)])
    assert code == 0
    decision = json.loads((out / "m2_stage2k1r4e1_decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == DECISION_ALLOWED


# ── manifest v2 ────────────────────────────────────────────────────────────


def _write_manifest(out_root, files):
    from ashare_research.scoring import artifact_manifest
    from ashare_research.scoring import content_digest as cd
    entries = []
    for path in sorted(files, key=lambda p: str(p)):
        digest = cd.digest_file(path, algorithm="sha256_lf_normalized_bytes_v1")
        rel = str(path.resolve().relative_to(out_root.resolve()).as_posix())
        entries.append(
            {
                "path": rel,
                "digest_algorithm": digest.algorithm,
                "sha256": digest.sha256,
                "byte_size": digest.byte_size,
            }
        )
    manifest = {
        "schema": "m2_stage2k1r4e1_artifact_manifest_v2",
        "version": "2.0",
        "files": entries,
    }
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = out_root / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    return mpath


def _verify_manifest(out_root):
    from ashare_research.scoring import artifact_manifest
    return artifact_manifest.verify_artifact_manifest(
        out_root / "manifest.json", repository_root=out_root
    )


def test_manifest_v2_passes(tmp_path):
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    _write_manifest(tmp_path, [payload])
    res = _verify_manifest(tmp_path)
    assert res.status == "pass"


def test_manifest_not_self_included(tmp_path):
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    _write_manifest(tmp_path, [payload])
    res = _verify_manifest(tmp_path)
    assert "manifest.json" not in [e["path"] for e in res.verified_entries]


def test_manifest_tamper_candidate_fails(tmp_path):
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    _write_manifest(tmp_path, [payload])
    assert _verify_manifest(tmp_path).status == "pass"
    payload.write_text('{"x": 2}\n', encoding="utf-8")  # tamper the candidate
    res_fail = _verify_manifest(tmp_path)  # verify the ORIGINAL manifest
    assert res_fail.status == "fail"
    assert res_fail.hash_mismatches


def test_manifest_tamper_hash_fails(tmp_path):
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    entries = [{
        "path": "a.json",
        "digest_algorithm": "sha256_lf_normalized_bytes_v1",
        "sha256": "0" * 64,
        "byte_size": 10,
    }]
    manifest = {
        "schema": "m2_stage2k1r4e1_artifact_manifest_v2",
        "version": "2.0",
        "files": entries,
    }
    from ashare_research.scoring import artifact_manifest
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    res = artifact_manifest.verify_artifact_manifest(mpath, repository_root=tmp_path)
    assert res.status == "fail"
    assert res.hash_mismatches


def test_manifest_missing_path_fails(tmp_path):
    from ashare_research.scoring import artifact_manifest
    entries = [{
        "path": "does_not_exist.json",
        "digest_algorithm": "sha256_lf_normalized_bytes_v1",
        "sha256": "0" * 64,
        "byte_size": 10,
    }]
    manifest = {
        "schema": "m2_stage2k1r4e1_artifact_manifest_v2",
        "version": "2.0",
        "files": entries,
    }
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    res = artifact_manifest.verify_artifact_manifest(mpath, repository_root=tmp_path)
    assert res.status == "fail"
    assert res.missing_files


def test_manifest_duplicate_and_traversal_fail(tmp_path):
    from ashare_research.scoring import artifact_manifest
    payload = tmp_path / "a.json"
    payload.write_text('{"x": 1}\n', encoding="utf-8")
    entries = [
        {"path": "a.json", "digest_algorithm": "sha256_lf_normalized_bytes_v1",
         "sha256": "0" * 64, "byte_size": 10},
        {"path": "a.json", "digest_algorithm": "sha256_lf_normalized_bytes_v1",
         "sha256": "1" * 64, "byte_size": 11},
        {"path": "../escape.json", "digest_algorithm": "sha256_lf_normalized_bytes_v1",
         "sha256": "2" * 64, "byte_size": 12},
    ]
    manifest = {
        "schema": "m2_stage2k1r4e1_artifact_manifest_v2",
        "version": "2.0",
        "files": entries,
    }
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    res = artifact_manifest.verify_artifact_manifest(mpath, repository_root=tmp_path)
    assert res.status == "fail"
    assert res.duplicate_paths
    assert res.invalid_paths


# ── product boundary ───────────────────────────────────────────────────────


def test_no_percentile_no_shadow_no_prod(tmp_path):
    out = _repo_out("boundary")
    cli_main(["fixtures", "--fixture-root", str(Path(".")), "--output-root", str(out)])
    candidate = json.loads(
        (out / "petrochina_pit_valuation_series_candidate_v2.json").read_text(encoding="utf-8")
    )
    assert candidate["percentile_computed"] is False
    for obs in candidate["observations"]:
        assert obs["percentile_computed"] is False
        assert obs["score_eligible"] is False
        assert obs["production_eligible"] is False
        assert "valuation_percentile" not in obs
    assert not list(tmp_path.glob("*.duckdb"))
    assert not list(tmp_path.glob("*.db"))
    shadow = [p for p in out.iterdir() if p.name.startswith("petrochina_dimension_scoring_shadow")]
    assert not shadow
    assert "peer" not in json.dumps(candidate)
    assert "m3" not in json.dumps({k: v for k, v in candidate.items()})


def test_identity_migration_report_generated(tmp_path):
    out = _repo_out("identity")
    cli_main(["fixtures", "--fixture-root", str(Path(".")), "--output-root", str(out)])
    mig = json.loads(
        (out / "petrochina_pit_valuation_series_identity_migration_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert mig["all_pb_state_ids_changed"] is True
    assert mig["all_observation_ids_changed"] is True
    assert mig["ratio_changed_count"] == 0
    assert mig["status_changed_count"] == 0
    assert mig["non_production_unchanged"] is True
