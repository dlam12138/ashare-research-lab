"""Offline tests for the registered official-fact acceptance runner."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.tools import official_fact_acceptance as acceptance

ROOT = Path(__file__).resolve().parents[1]
REAL_BUNDLE = (
    ROOT
    / "acceptance"
    / "fixtures"
    / "official_facts"
    / "601857.SH"
    / "2025_annual.json"
)
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _bundle() -> dict:
    return json.loads(REAL_BUNDLE.read_text(encoding="utf-8"))


def _valid_temp_bundle(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    bundle = _bundle()
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    for document in bundle["documents"].values():
        document["sha256"] = digest
        document["content_length"] = len(PDF_BYTES)
        document["page_count"] = 1
    bundle["document_relationship"] = "byte_identical"
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    company = tmp_path / "company.pdf"
    exchange = tmp_path / "exchange.pdf"
    company.write_bytes(PDF_BYTES)
    exchange.write_bytes(PDF_BYTES)
    return bundle_path, company, exchange, bundle


def _assert_invalid(bundle: dict, message: str = "") -> None:
    with pytest.raises(acceptance.AcceptanceError, match=message or None):
        acceptance.validate_bundle(bundle)


def _run_success(tmp_path: Path):
    bundle_path, company, exchange, _ = _valid_temp_bundle(tmp_path)
    return acceptance.run_acceptance(
        bundle_path, company, exchange, tmp_path / "output", run_id="test_run"
    )


# Bundle validation


def test_bundle_requires_exact_symbol():
    bundle = _bundle()
    bundle["symbol"] = "000001.SZ"
    _assert_invalid(bundle, "symbol")


def test_bundle_requires_2025_annual_context():
    for field, value in (
        ("fiscal_year", 2024),
        ("report_type", "quarterly"),
        ("period_start", "2025-04-01"),
        ("period_end", "2025-09-30"),
        ("accounting_standard", "IFRS"),
        ("consolidation_scope", "parent_company"),
    ):
        bundle = _bundle()
        bundle[field] = value
        _assert_invalid(bundle, field)


def test_bundle_requires_company_and_exchange_documents():
    bundle = _bundle()
    del bundle["documents"]["exchange"]
    _assert_invalid(bundle, "company and exchange")


def test_bundle_requires_exact_three_concepts():
    bundle = _bundle()
    bundle["facts"][0]["concept_id"] = "net_profit"
    _assert_invalid(bundle, "unsupported concept")


def test_bundle_rejects_duplicate_source_fact():
    bundle = _bundle()
    bundle["facts"][1]["concept_id"] = bundle["facts"][0]["concept_id"]
    _assert_invalid(bundle, "duplicate")


def test_bundle_rejects_missing_announcement_date():
    bundle = _bundle()
    bundle["documents"]["company"]["announcement_date"] = ""
    _assert_invalid(bundle, "announcement_date")


def test_bundle_rejects_missing_source_page():
    bundle = _bundle()
    bundle["facts"][0]["source_page"] = ""
    _assert_invalid(bundle, "source_page")


def test_bundle_rejects_non_sha256_hash():
    bundle = _bundle()
    bundle["documents"]["company"]["sha256"] = "abc"
    _assert_invalid(bundle, "SHA-256")


def test_bundle_rejects_third_party_source_tier():
    bundle = _bundle()
    bundle["documents"]["company"]["source_tier"] = "candidate_aggregator"
    _assert_invalid(bundle, "source_tier")


# Hash verification


def test_local_pdf_hash_must_match_bundle(tmp_path: Path):
    _, company, _, bundle = _valid_temp_bundle(tmp_path)
    result = acceptance.verify_local_pdf(company, bundle["documents"]["company"])
    assert result["verified"] is True
    assert result["sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()


def test_company_pdf_hash_mismatch_fails_before_database_write(tmp_path: Path):
    bundle_path, company, exchange, _ = _valid_temp_bundle(tmp_path)
    company.write_bytes(PDF_BYTES + b"changed")
    result = acceptance.run_acceptance(
        bundle_path, company, exchange, tmp_path / "output", run_id="bad_company"
    )
    assert result["status"] == "failed"
    assert not (result["run_directory"] / "acceptance.duckdb").exists()


def test_exchange_pdf_hash_mismatch_fails_before_database_write(tmp_path: Path):
    bundle_path, company, exchange, _ = _valid_temp_bundle(tmp_path)
    exchange.write_bytes(PDF_BYTES + b"changed")
    result = acceptance.run_acceptance(
        bundle_path, company, exchange, tmp_path / "output", run_id="bad_exchange"
    )
    assert result["status"] == "failed"
    assert not (result["run_directory"] / "acceptance.duckdb").exists()


def test_pdf_magic_header_is_required(tmp_path: Path):
    _, company, _, bundle = _valid_temp_bundle(tmp_path)
    company.write_bytes(b"not a PDF")
    document = bundle["documents"]["company"]
    document["sha256"] = hashlib.sha256(b"not a PDF").hexdigest()
    document["content_length"] = len(b"not a PDF")
    with pytest.raises(acceptance.AcceptanceError, match="magic"):
        acceptance.verify_local_pdf(company, document)


# Normalization


def test_million_rmb_to_ten_thousand_rmb_exact_conversion():
    assert acceptance.normalize_registered_value(_bundle()["facts"][0]) == 286446900


def test_raw_value_is_parsed_with_decimal(monkeypatch):
    calls: list[str] = []
    real_decimal = acceptance.Decimal

    def recording_decimal(value):
        calls.append(value)
        return real_decimal(value)

    monkeypatch.setattr(acceptance, "Decimal", recording_decimal)
    acceptance.normalize_registered_value(_bundle()["facts"][0])
    assert calls == ["2864469", "100"]


def test_fractional_raw_value_is_rejected():
    fact = copy.deepcopy(_bundle()["facts"][0])
    fact["raw_value"] = "1.5"
    _assert_normalization_invalid(fact)


def test_expected_normalized_value_must_match():
    fact = copy.deepcopy(_bundle()["facts"][0])
    fact["expected_normalized_value"] += 1
    _assert_normalization_invalid(fact)


def test_normalization_does_not_use_float():
    source = Path(acceptance.__file__).read_text(encoding="utf-8")
    function = ast.parse(source)
    target = next(
        node
        for node in function.body
        if isinstance(node, ast.FunctionDef) and node.name == "normalize_registered_value"
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
        for node in ast.walk(target)
    )


def test_normalization_does_not_round():
    source = Path(acceptance.__file__).read_text(encoding="utf-8")
    target = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "normalize_registered_value"
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "round"
        for node in ast.walk(target)
    )


def _assert_normalization_invalid(fact: dict) -> None:
    with pytest.raises(acceptance.AcceptanceError):
        acceptance.normalize_registered_value(fact)


# Fact construction


def _facts():
    bundle = _bundle()
    acceptance.validate_bundle(bundle)
    return acceptance.build_source_facts(bundle, created_at="2026-07-29T20:00:00")


def test_company_facts_use_company_official():
    assert {fact["source_tier"] for fact in _facts()["company"]} == {"company_official"}


def test_exchange_facts_use_exchange_official():
    assert {fact["source_tier"] for fact in _facts()["exchange"]} == {"exchange_official"}


def test_source_ids_are_distinct():
    facts = _facts()
    assert {fact["source_id"] for fact in facts["company"]}.isdisjoint(
        {fact["source_id"] for fact in facts["exchange"]}
    )


def test_same_document_hash_does_not_merge_source_identity():
    bundle = _bundle()
    bundle["documents"]["exchange"]["sha256"] = bundle["documents"]["company"]["sha256"]
    bundle["document_relationship"] = "byte_identical"
    facts = acceptance.build_source_facts(bundle, created_at="2026-07-29T20:00:00")
    assert len({fact["fact_id"] for group in facts.values() for fact in group}) == 6


def test_all_six_facts_have_canonical_ids():
    facts = [fact for group in _facts().values() for fact in group]
    assert len(facts) == 6
    assert all(fact["fact_id"] == build_fact_id(fact) for fact in facts)


def test_original_facts_are_verified_and_ineligible():
    facts = [fact for group in _facts().values() for fact in group]
    assert all(fact["verification_status"] == "verified" for fact in facts)
    assert all(fact["eligible_for_metrics"] is False for fact in facts)


# Reconciliation


def test_three_real_fixture_pairs_match_offline():
    facts = _facts()
    by_source = {
        key: {fact["concept_id"]: fact for fact in values}
        for key, values in facts.items()
    }
    results = [
        ReconciliationEngine().reconcile_pair(
            by_source["company"][concept], by_source["exchange"][concept]
        )
        for concept in sorted(acceptance.EXPECTED_CONCEPTS)
    ]
    assert [result.status for result in results] == [ReconciliationStatus.matched] * 3


def test_any_mismatch_blocks_entire_acceptance_persistence(tmp_path: Path):
    bundle_path, company, exchange, bundle = _valid_temp_bundle(tmp_path)
    target = next(
        fact
        for fact in bundle["facts"]
        if fact["source_key"] == "exchange" and fact["concept_id"] == "revenue"
    )
    target["raw_value"] = "2864470"
    target["expected_normalized_value"] = 286447000
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    result = acceptance.run_acceptance(
        bundle_path, company, exchange, tmp_path / "output", run_id="mismatch"
    )
    assert result["status"] == "failed"
    conn = duckdb.connect(str(result["run_directory"] / "acceptance.duckdb"), read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0] == 0
    finally:
        conn.close()


def test_reconciliation_creates_three_reconciled_facts(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["status"] == "passed"
    assert result["counts"]["reconciled"] == 3


def test_reconciled_facts_are_eligible(tmp_path: Path):
    result = _run_success(tmp_path)
    facts = json.loads(
        (result["run_directory"] / "reconciled_facts.json").read_text(encoding="utf-8")
    )
    assert all(fact["eligible_for_metrics"] is True for fact in facts)


def test_reconciled_available_at_uses_later_source(tmp_path: Path):
    result = _run_success(tmp_path)
    facts = json.loads(
        (result["run_directory"] / "reconciled_facts.json").read_text(encoding="utf-8")
    )
    assert {fact["available_at"] for fact in facts} == {"2026-03-30"}


def test_default_pit_before_availability_returns_zero(tmp_path: Path):
    assert _run_success(tmp_path)["counts"]["pit_before"] == 0


def test_default_pit_after_availability_returns_three(tmp_path: Path):
    assert _run_success(tmp_path)["counts"]["pit_after"] == 3


def test_audit_returns_all_nine_facts(tmp_path: Path):
    assert _run_success(tmp_path)["counts"]["audit"] == 9


def test_lineage_contains_nine_role_rows(tmp_path: Path):
    result = _run_success(tmp_path)
    rows = json.loads(
        (result["run_directory"] / "lineage_summary.json").read_text(encoding="utf-8")
    )
    assert len(rows) == 9
    assert {row["role"] for row in rows} == {
        "reconciliation_input_company",
        "reconciliation_input_exchange",
        "reconciliation_output",
    }


# Isolation


def test_acceptance_uses_run_scoped_database(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["run_directory"].parts[-3:] == ("601857.SH", "stage1cb", "test_run")
    assert (result["run_directory"] / "acceptance.duckdb").is_file()


def test_acceptance_does_not_modify_default_research_database(tmp_path: Path):
    default_db = tmp_path / "data" / "research.duckdb"
    default_db.parent.mkdir()
    default_db.write_bytes(b"sentinel")
    before = default_db.read_bytes()
    _run_success(tmp_path)
    assert default_db.read_bytes() == before


def test_acceptance_output_contains_no_absolute_paths(tmp_path: Path):
    result = _run_success(tmp_path)
    forbidden = str(tmp_path.resolve()).replace("\\", "\\\\")
    for path in result["run_directory"].glob("*.json"):
        assert forbidden not in path.read_text(encoding="utf-8")


def test_acceptance_runner_is_offline():
    tree = ast.parse(Path(acceptance.__file__).read_text(encoding="utf-8"))
    forbidden = {"requests", "httpx", "urllib", "socket", "aiohttp"}
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (
            node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
        )
    }
    assert imported.isdisjoint(forbidden)


def test_cli_result_is_json_serializable(tmp_path: Path):
    result = _run_success(tmp_path)
    json.dumps(acceptance._jsonable(result))
