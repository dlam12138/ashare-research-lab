"""Focused Stage 2G contract and vertical-slice checks."""

# Evidence and observation names are intentionally descriptive.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from ashare_research.events.dividend_v2 import (  # noqa: E402
    event_status_as_of,
    validate_source_evidence,
)
from ashare_research.tools.petrochina_valuation_and_value_profile import (  # noqa: E402
    FORBIDDEN_FIELDS,
    _build_rule007_facts,
    _financial_facts,
    _reconcile_rule007_facts,
    _share_timeline,
    run_formal,
    validate_dividend_evidence,
)

ROOT = Path(__file__).parents[1]
FACT_DB = (
    ROOT
    / "output"
    / "601857.SH"
    / "net_profit_official_facts"
    / "2021_2025"
    / "stage2de_trial"
    / "net_profit.duckdb"
)


def _run_formal(tmp_path: Path, run_id: str):
    return run_formal(output_root=tmp_path, run_id=run_id, fact_db=FACT_DB)


def _source(source_id: str) -> dict:
    data = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )
    return next(item for item in data["entries"] if item["source_evidence_id"] == source_id)


def test_phase_a_has_exact_locators_real_hashes_and_explicit_gaps() -> None:
    result = validate_dividend_evidence()
    assert result["status"] == "pass_with_explicit_gaps"
    assert result["event_count"] == 10
    assert result["source_count"] == 20
    assert result["rule007_eligible_event_count"] == 1
    assert result["real_content_hash_count"] == 11
    assert len(result["gaps"]) == 9


def test_generic_exchange_locator_is_rejected() -> None:
    candidate = deepcopy(_source("2024-interim-exchange"))
    candidate["exact_url"] = "https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/"
    assert "generic_exchange_url" in validate_source_evidence(candidate)


def test_url_hash_cannot_be_content_hash() -> None:
    candidate = deepcopy(_source("2024-interim-exchange"))
    candidate["content_sha256"] = candidate["locator_hash"]
    assert "url_hash_used_as_content_hash" in validate_source_evidence(candidate)


def test_source_type_separation_and_designated_platform_rule() -> None:
    candidate = deepcopy(_source("2024-interim-exchange"))
    candidate["source_type"] = "issuer_official"
    candidate["exact_url"] = "https://www.cninfo.com.cn/new/index"
    candidate["locator_hash"] = hashlib.sha256(candidate["exact_url"].encode()).hexdigest()
    assert "designated_platform_mislabelled_issuer_official" in validate_source_evidence(candidate)


def test_rule007_raw_facts_follow_source_payload_not_event() -> None:
    event_data = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )
    source_data = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )
    validated = validate_dividend_evidence(event_data["events"], source_data["entries"])
    raw = _build_rule007_facts(validated)
    reconciled = _reconcile_rule007_facts(validated, raw)
    eligible_event = validated["eligible"][0]["event"]
    mutated_event = deepcopy(eligible_event)
    mutated_event["cash_dividend_per_share"] = "999.99"
    mutated_evidence = {
        **validated,
        "eligible": [{**validated["eligible"][0], "event": mutated_event}],
    }
    mutated_raw = _build_rule007_facts(mutated_evidence)
    assert [row["value"] for row in mutated_raw] == [row["value"] for row in raw]
    for row in mutated_raw:
        source = _source(row["source_evidence_id"])
        assert row["value"] == source["extracted_values"][row["source_payload_key"]]
    for row in reconciled:
        assert len(row["input_fact_ids"]) == 2
        assert set(row["input_fact_ids"]) == {
            raw_fact["fact_id"]
            for raw_fact in raw
            if raw_fact["event_id"] == row["event_id"]
            and raw_fact["concept_id"] == row["concept_id"]
        }


def test_rule007_source_payload_mismatch_is_ineligible() -> None:
    events = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )["events"]
    sources = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )["entries"]
    mutated_sources = deepcopy(sources)
    exchange = next(item for item in mutated_sources if item["source_evidence_id"] == "2024-interim-exchange")
    exchange["extracted_values"]["cash_dividend_per_share"] = "0.22001"
    result = validate_dividend_evidence(events, mutated_sources)
    assert result["status"] == "fail"
    assert any("numeric_or_scope_conflict" in error for error in result["errors"])
    assert result["rule007_eligible_event_count"] == 0


def test_share_timeline_consumes_evidence_and_rejects_inconsistent_split() -> None:
    events = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )["events"]
    sources = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )["entries"]
    rows, ledger = _share_timeline(events, sources)
    assert rows and all(row["evidence_ids"] for row in rows)
    assert ledger
    changed = deepcopy(sources)
    issuer = next(item for item in changed if item["source_evidence_id"] == "2024-interim-issuer")
    issuer["extracted_values"]["share_capital"] = "183020977817"
    changed_rows, _ = _share_timeline(events, changed)
    assert changed_rows != rows
    inconsistent = deepcopy(changed)
    issuer = next(item for item in inconsistent if item["source_evidence_id"] == "2024-interim-issuer")
    issuer["extracted_values"]["a_shares"] = "1"
    issuer["extracted_values"]["h_shares"] = "2"
    with pytest.raises(ValueError, match="share-capital inconsistency"):
        _share_timeline(events, inconsistent)


def test_prior_authorization_and_announcement_payment_are_distinct() -> None:
    events = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )["events"]
    interim = next(
        item
        for item in events
        if item["source_fiscal_year"] == 2024 and item["event_type"] == "interim"
    )
    assert interim["approval_type"] == "prior_shareholder_authorization"
    assert interim["prior_authorization_is_event_specific"] is False
    assert event_status_as_of(interim, "2024-09-12") == "implementation_announced"
    assert event_status_as_of(interim, "2024-09-18") == "implementation_announced"
    assert event_status_as_of(interim, "2024-09-19") == "payment_completed"


def test_formal_runner_reuses_stock_daily_and_reconciles_two_providers(tmp_path: Path) -> None:
    result = _run_formal(tmp_path, "stage2g-test")
    run_dir = Path(result["run_dir"])
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["network_used"] is False
    assert manifest["market_row_count"] == 1351
    assert manifest["market_date_range"] == {"start": "2021-01-04", "end": "2026-07-31"}
    assert manifest["market_registry"]["reconciliation_status"] == "pass"
    assert (run_dir / "stock_daily_snapshot.parquet").exists()
    assert not (run_dir / "market_observations.parquet").exists()
    prices = pd.read_parquet(run_dir / "stock_daily_snapshot.parquet")
    assert set(prices["adjustment"]) == {"none"}
    assert prices["trade_date"].is_unique


def test_formal_runner_requires_explicit_canonical_fact_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing_input"):
        run_formal(output_root=tmp_path, run_id="missing-fact-db", fact_db=tmp_path / "missing.duckdb")


def test_six_formulas_and_pit_no_future_leakage(tmp_path: Path) -> None:
    result = _run_formal(tmp_path, "formula-test")
    obs = pd.read_parquet(Path(result["run_dir"]) / "valuation_observations.parquet")
    assert set(obs["observation_type"]) == {
        "a_share_price_to_latest_annual_parent_earnings",
        "a_share_price_to_latest_year_end_parent_equity",
        "a_share_price_to_latest_annual_revenue",
        "trailing_12m_announced_dividend_yield",
        "trailing_12m_paid_dividend_yield",
        "latest_annual_fcf_proxy_yield",
    }
    facts = _financial_facts(FACT_DB)
    fact_by_id = {fact["fact_id"]: fact for fact in facts}
    before_2025 = obs[
        (obs["trade_date"] == "2025-03-28")
        & (obs["observation_type"] == "a_share_price_to_latest_annual_parent_earnings")
    ].iloc[0]
    assert all(
        fact_by_id[fact_id]["fiscal_year"] <= 2023
        for fact_id in before_2025["lineage"]["financial_fact_ids"]
    )
    after_2024 = obs[
        (obs["trade_date"] == "2025-04-01")
        & (obs["observation_type"] == "a_share_price_to_latest_annual_parent_earnings")
    ].iloc[0]
    assert all(
        fact_by_id[fact_id]["fiscal_year"] <= 2024
        for fact_id in after_2024["lineage"]["financial_fact_ids"]
    )
    announced = obs[
        (obs["trade_date"] == "2024-09-18")
        & (obs["observation_type"] == "trailing_12m_announced_dividend_yield")
    ].iloc[0]
    paid = obs[
        (obs["trade_date"] == "2024-09-18")
        & (obs["observation_type"] == "trailing_12m_paid_dividend_yield")
    ].iloc[0]
    assert announced["status"] in {"partial_evidence", "missing_input"}
    assert paid["status"] in {"partial_evidence", "missing_input"}
    assert len(announced["lineage"]["dividend_event_ids"]) > len(
        paid["lineage"]["dividend_event_ids"]
    )


def test_percentiles_are_descriptive_and_scenarios_have_no_opinion_fields(tmp_path: Path) -> None:
    result = _run_formal(tmp_path, "profile-test")
    profile = result["profile"]
    assert profile["score_eligible"] is False

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert not (FORBIDDEN_FIELDS & set(value))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(profile)
    assert (
        result["percentiles"]["observations"]["a_share_price_to_latest_annual_parent_earnings"][
            "effective_samples"
        ]["3y"]
        >= 500
    )
    assert all(
        row["sample_end_trade_date"] == "2026-07-31" for row in result["scenarios"]["scenarios"]
    )


def test_offline_formal_run_is_idempotent(tmp_path: Path) -> None:
    first = _run_formal(tmp_path, "idempotent-test")
    run_dir = Path(first["run_dir"])
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in run_dir.iterdir()
        if path.is_file()
    }
    second = _run_formal(tmp_path, "idempotent-test")
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in Path(second["run_dir"]).iterdir()
        if path.is_file()
    }
    assert before == after
