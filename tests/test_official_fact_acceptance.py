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


def _synthetic_bundle(
    fiscal_year: int,
    *,
    symbol: str = "600519.SH",
    company_name: str = "合成测试股份有限公司",
) -> dict:
    """Synthetic fixture only; not real historical evidence."""
    bundle = copy.deepcopy(_bundle())
    bundle["symbol"] = symbol
    bundle["company_name"] = company_name
    bundle["fiscal_year"] = fiscal_year
    bundle["period_start"], bundle["period_end"] = acceptance.expected_annual_period(
        fiscal_year
    )
    for key, document in bundle["documents"].items():
        document["source_id"] = f"{key}:{symbol}:{fiscal_year}:annual:synthetic"
        document["source_document"] = f"{company_name}{fiscal_year}年年度报告（合成测试）"
        document["landing_url"] = f"https://example.invalid/{key}/landing"
        document["pdf_url"] = f"https://example.invalid/{key}/report.pdf"
        document["final_pdf_url"] = document["pdf_url"]
        document["announcement_date"] = f"{fiscal_year + 1:04d}-03-30"
        document["retrieved_at"] = f"{fiscal_year + 1:04d}-07-01T12:00:00+08:00"
    return bundle


def _scoped_bundle() -> dict:
    bundle = copy.deepcopy(_bundle())
    bundle["documents"]["company"][
        "document_scope"
    ] = acceptance.AUDITED_FINANCIAL_STATEMENTS
    bundle["documents"]["exchange"]["document_scope"] = acceptance.FULL_ANNUAL_REPORT
    bundle[
        "document_relationship"
    ] = "audited_financial_statements_subset_of_full_annual_report"
    return bundle


def _valid_temp_bundle(
    tmp_path: Path,
    bundle: dict | None = None,
) -> tuple[Path, Path, Path, dict]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    bundle = copy.deepcopy(bundle if bundle is not None else _bundle())
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


def _run_success(
    tmp_path: Path,
    bundle: dict | None = None,
    *,
    run_id: str = "test_run",
):
    bundle_path, company, exchange, _ = _valid_temp_bundle(tmp_path, bundle)
    return acceptance.run_acceptance(
        bundle_path, company, exchange, tmp_path / "output", run_id=run_id
    )


# Bundle validation


def test_bundle_accepts_valid_sh_symbol():
    acceptance.validate_bundle(_synthetic_bundle(2024, symbol="600519.SH"))


def test_bundle_accepts_valid_sz_symbol():
    acceptance.validate_bundle(_synthetic_bundle(2024, symbol="000001.SZ"))


@pytest.mark.parametrize(
    "symbol",
    ["601857", "601857.sh", "00700.HK", "AAPL", "SH601857", ""],
)
def test_bundle_rejects_invalid_a_share_symbol(symbol):
    bundle = _bundle()
    bundle["symbol"] = symbol
    _assert_invalid(bundle, "symbol")


def test_bundle_rejects_symbol_without_suffix():
    bundle = _bundle()
    bundle["symbol"] = "601857"
    _assert_invalid(bundle, "symbol")


def test_bundle_rejects_lowercase_suffix():
    bundle = _bundle()
    bundle["symbol"] = "601857.sh"
    _assert_invalid(bundle, "symbol")


def test_bundle_rejects_non_a_share_symbol():
    bundle = _bundle()
    bundle["symbol"] = "00700.HK"
    _assert_invalid(bundle, "symbol")


def test_bundle_rejects_empty_symbol():
    bundle = _bundle()
    bundle["symbol"] = ""
    _assert_invalid(bundle, "symbol")


def test_bundle_rejects_non_string_symbol():
    bundle = _bundle()
    bundle["symbol"] = None
    _assert_invalid(bundle, "symbol")


def test_bundle_accepts_2025_annual_context():
    acceptance.validate_bundle(_bundle())


def test_bundle_accepts_2024_annual_context():
    acceptance.validate_bundle(_synthetic_bundle(2024))


def test_bundle_derives_period_from_fiscal_year():
    assert acceptance.expected_annual_period(2024) == (
        "2024-01-01",
        "2024-12-31",
    )


def test_bundle_rejects_period_start_from_different_year():
    bundle = _synthetic_bundle(2024)
    bundle["period_start"] = "2025-01-01"
    _assert_invalid(bundle, "period_start")


def test_bundle_rejects_period_end_from_different_year():
    bundle = _synthetic_bundle(2024)
    bundle["period_end"] = "2025-12-31"
    _assert_invalid(bundle, "period_end")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("report_type", "quarterly"),
        ("accounting_standard", "IFRS"),
        ("consolidation_scope", "parent_company"),
        ("language", "en-US"),
    ],
)
def test_bundle_rejects_non_annual_context_contract(field, value):
    bundle = _bundle()
    bundle[field] = value
    _assert_invalid(bundle, field)


def test_bundle_rejects_quarterly_report():
    bundle = _bundle()
    bundle["report_type"] = "quarterly"
    _assert_invalid(bundle, "report_type")


def test_bundle_rejects_ifrs():
    bundle = _bundle()
    bundle["accounting_standard"] = "IFRS"
    _assert_invalid(bundle, "accounting_standard")


def test_bundle_rejects_parent_company_scope():
    bundle = _bundle()
    bundle["consolidation_scope"] = "parent_company"
    _assert_invalid(bundle, "consolidation_scope")


def test_bundle_rejects_non_chinese_language():
    bundle = _bundle()
    bundle["language"] = "en-US"
    _assert_invalid(bundle, "language")


@pytest.mark.parametrize("fiscal_year", ["2024", 2024.0, True, 1989, 10000])
def test_bundle_rejects_invalid_fiscal_year(fiscal_year):
    bundle = _bundle()
    bundle["fiscal_year"] = fiscal_year
    _assert_invalid(bundle, "fiscal_year")


def test_bundle_rejects_string_fiscal_year():
    bundle = _bundle()
    bundle["fiscal_year"] = "2024"
    _assert_invalid(bundle, "fiscal_year")


def test_bundle_rejects_boolean_fiscal_year():
    bundle = _bundle()
    bundle["fiscal_year"] = True
    _assert_invalid(bundle, "fiscal_year")


@pytest.mark.parametrize("company_name", ["", "   ", None, 123])
def test_bundle_rejects_invalid_company_name(company_name):
    bundle = _bundle()
    bundle["company_name"] = company_name
    _assert_invalid(bundle, "company_name")


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


def test_legacy_bundle_defaults_to_full_annual_report():
    bundle = _bundle()
    assert "document_scope" not in bundle["documents"]["company"]
    assert (
        acceptance.normalized_document_scope(bundle["documents"]["company"])
        == acceptance.FULL_ANNUAL_REPORT
    )
    acceptance.validate_bundle(bundle)


def test_all_legacy_registered_bundles_remain_valid():
    for fiscal_year in range(2022, 2026):
        path = REAL_BUNDLE.with_name(f"{fiscal_year}_annual.json")
        acceptance.validate_bundle(json.loads(path.read_text(encoding="utf-8")))


def test_audited_statements_and_full_report_are_compatible():
    acceptance.validate_bundle(_scoped_bundle())


def test_subset_relationship_requires_company_audited_statements():
    bundle = _scoped_bundle()
    bundle["documents"]["company"]["document_scope"] = acceptance.FULL_ANNUAL_REPORT
    _assert_invalid(bundle, "hashes and scopes")


def test_subset_relationship_requires_exchange_full_report():
    bundle = _scoped_bundle()
    bundle["documents"]["exchange"][
        "document_scope"
    ] = acceptance.AUDITED_FINANCIAL_STATEMENTS
    _assert_invalid(bundle, "hashes and scopes")


def test_two_audited_statements_cannot_use_subset_relationship():
    bundle = _scoped_bundle()
    bundle["documents"]["exchange"][
        "document_scope"
    ] = acceptance.AUDITED_FINANCIAL_STATEMENTS
    _assert_invalid(bundle, "hashes and scopes")


def test_identical_hashes_cannot_use_subset_relationship():
    bundle = _scoped_bundle()
    bundle["documents"]["exchange"]["sha256"] = bundle["documents"]["company"]["sha256"]
    _assert_invalid(bundle, "hashes and scopes")


def test_different_full_reports_keep_existing_relationship():
    bundle = _bundle()
    bundle["documents"]["company"]["document_scope"] = acceptance.FULL_ANNUAL_REPORT
    bundle["documents"]["exchange"]["document_scope"] = acceptance.FULL_ANNUAL_REPORT
    acceptance.validate_bundle(bundle)


def test_byte_identical_relationship_requires_matching_scope():
    bundle = _bundle()
    bundle["documents"]["exchange"]["sha256"] = bundle["documents"]["company"]["sha256"]
    bundle["document_relationship"] = "byte_identical"
    bundle["documents"]["company"][
        "document_scope"
    ] = acceptance.AUDITED_FINANCIAL_STATEMENTS
    bundle["documents"]["exchange"]["document_scope"] = acceptance.FULL_ANNUAL_REPORT
    _assert_invalid(bundle, "hashes and scopes")


def test_manifest_normalizes_legacy_document_scope():
    bundle = _bundle()
    manifest = acceptance._public_source_manifest(
        bundle,
        {"company": {"verified": True}, "exchange": {"verified": True}},
    )
    assert {
        document["document_scope"] for document in manifest["documents"].values()
    } == {acceptance.FULL_ANNUAL_REPORT}


def test_manifest_preserves_scoped_document_roles():
    manifest = acceptance._public_source_manifest(
        _scoped_bundle(),
        {"company": {"verified": True}, "exchange": {"verified": True}},
    )
    assert manifest["documents"]["company"]["document_scope"] == (
        acceptance.AUDITED_FINANCIAL_STATEMENTS
    )
    assert (
        manifest["documents"]["exchange"]["document_scope"]
        == acceptance.FULL_ANNUAL_REPORT
    )
    assert manifest["independent_content_sources"] is False


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


def test_existing_2025_bundle_remains_backward_compatible():
    bundle = _bundle()
    acceptance.validate_bundle(bundle)
    context = acceptance.build_context(bundle, created_at="test")
    facts = acceptance.build_source_facts(bundle, created_at="test")
    assert context["context_id"] == "601857.SH|2025|annual|consolidated"
    assert len(facts["company"] + facts["exchange"]) == 6


def test_synthetic_2024_bundle_validates():
    acceptance.validate_bundle(_synthetic_bundle(2024))


def test_synthetic_2024_context_uses_2024():
    context = acceptance.build_context(_synthetic_bundle(2024), created_at="test")
    assert context["context_id"] == "600519.SH|2024|annual|consolidated"
    assert context["fiscal_year"] == 2024
    assert context["period_start"] == "2024-01-01"
    assert context["period_end"] == "2024-12-31"
    assert context["source_document"] == "合成测试股份有限公司2024年年度报告"
    assert "2025" not in context["source_document"]


def test_synthetic_2024_facts_use_2024_period():
    facts = acceptance.build_source_facts(_synthetic_bundle(2024), created_at="test")
    for fact in facts["company"] + facts["exchange"]:
        assert fact["fiscal_year"] == 2024
        assert fact["period_start"] == "2024-01-01"
        assert fact["period_end"] == "2024-12-31"
        assert "|2024|" in fact["context_id"]


def test_synthetic_2024_fact_ids_differ_from_2025():
    previous = _bundle()
    synthetic = _synthetic_bundle(
        2024,
        symbol=previous["symbol"],
        company_name=previous["company_name"],
    )
    facts_previous = acceptance.build_source_facts(previous, created_at="test")
    facts_synthetic = acceptance.build_source_facts(synthetic, created_at="test")
    ids_previous = {
        (key, fact["concept_id"]): fact["fact_id"]
        for key, facts in facts_previous.items()
        for fact in facts
    }
    ids_synthetic = {
        (key, fact["concept_id"]): fact["fact_id"]
        for key, facts in facts_synthetic.items()
        for fact in facts
    }
    assert ids_previous.keys() == ids_synthetic.keys()
    assert all(ids_previous[key] != ids_synthetic[key] for key in ids_previous)


def test_runner_is_not_bound_to_601857():
    bundle = _synthetic_bundle(2024, symbol="600519.SH")
    acceptance.validate_bundle(bundle)
    context = acceptance.build_context(bundle, created_at="test")
    assert context["symbol"] == "600519.SH"
    assert "601857" not in context["context_id"]


def test_second_symbol_uses_same_runner(tmp_path: Path):
    result = _run_success(
        tmp_path,
        _synthetic_bundle(2024, symbol="600519.SH"),
        run_id="second_symbol",
    )
    assert result["status"] == "passed"
    assert result["symbol"] == "600519.SH"
    assert "600519.SH" in result["run_directory"].parts


def test_second_symbol_does_not_require_new_python_module():
    path = (
        ROOT
        / "src"
        / "ashare_research"
        / "tools"
        / "company_specific_acceptance.py"
    )
    assert not path.exists()


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
    assert result["run_directory"].parts[-4:] == (
        "601857.SH",
        "annual_official_facts",
        "2025",
        "test_run",
    )
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


def test_synthetic_2024_offline_run_passes(tmp_path: Path):
    result = _run_success(tmp_path, _synthetic_bundle(2024))
    assert result["status"] == "passed"
    assert result["counts"] == {
        "contexts": 1,
        "financial_facts": 9,
        "company_original": 3,
        "exchange_original": 3,
        "reconciled": 3,
        "lineage": 9,
        "pit_before": 0,
        "pit_after": 3,
        "audit": 9,
    }


def test_synthetic_2024_run_directory_contains_year(tmp_path: Path):
    result = _run_success(tmp_path, _synthetic_bundle(2024))
    assert result["run_directory"].parts[-3:] == (
        "annual_official_facts",
        "2024",
        "test_run",
    )


def test_synthetic_2024_manifest_contains_year(tmp_path: Path):
    result = _run_success(tmp_path, _synthetic_bundle(2024))
    manifest = json.loads(
        (result["run_directory"] / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["fiscal_year"] == 2024
    assert manifest["period_start"] == "2024-01-01"
    assert manifest["period_end"] == "2024-12-31"


def test_run_path_is_annual_and_year_scoped(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["run_directory"].parts[-3:] == (
        "annual_official_facts",
        "2025",
        "test_run",
    )
    assert "stage1cb" not in result["run_directory"].parts


def test_2024_and_2025_runs_do_not_share_directory(tmp_path: Path):
    result_2024 = _run_success(
        tmp_path,
        _synthetic_bundle(2024),
        run_id="same_run",
    )
    result_2025 = _run_success(tmp_path, run_id="same_run")
    assert result_2024["run_directory"] != result_2025["run_directory"]
    assert "2024" in result_2024["run_directory"].parts
    assert "2025" in result_2025["run_directory"].parts


def test_manifest_contains_no_absolute_local_paths(tmp_path: Path):
    result = _run_success(tmp_path)
    manifest_text = (result["run_directory"] / "run_manifest.json").read_text(
        encoding="utf-8"
    )
    assert str(tmp_path.resolve()) not in manifest_text
    assert "company.pdf" not in manifest_text
    assert "exchange.pdf" not in manifest_text
    assert "bundle.json" not in manifest_text


def test_summary_contains_symbol_and_fiscal_year(tmp_path: Path):
    result = _run_success(tmp_path, _synthetic_bundle(2024, symbol="600519.SH"))
    summary = (result["run_directory"] / "acceptance_summary.md").read_text(
        encoding="utf-8"
    )
    assert "600519.SH" in summary
    assert "2024" in summary


def test_summary_does_not_contain_stage1cb(tmp_path: Path):
    result = _run_success(tmp_path)
    summary = (result["run_directory"] / "acceptance_summary.md").read_text(
        encoding="utf-8"
    )
    assert "stage1cb" not in summary


def test_manifest_records_bundle_schema_version(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["bundle_schema_version"] == "1.0"


def test_manifest_records_acceptance_contract(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["acceptance_contract"] == "annual_official_facts_v1_1"


def test_manifest_records_fact_schema_version(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["fact_schema_version"] == "2.1"


def test_contract_version_is_distinct_from_fact_schema_version(tmp_path: Path):
    result = _run_success(tmp_path)
    assert result["acceptance_contract"] != result["fact_schema_version"]


def test_build_run_id_is_symbol_year_and_time_scoped():
    run_id = acceptance.build_run_id(
        "600519.SH",
        2024,
        now=acceptance.datetime(2026, 7, 29, 20, 30, 0, 123456),
    )
    assert run_id == "annual_official_600519_SH_2024_20260729_203000_123456"
    assert "stage1cb" not in run_id


def test_acceptance_runner_is_offline():
    tree = ast.parse(Path(acceptance.__file__).read_text(encoding="utf-8"))
    forbidden = {"requests", "httpx", "urllib", "socket", "aiohttp"}
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
        )
    }
    assert imported.isdisjoint(forbidden)


def test_runner_source_contains_no_company_or_year_hardcoding():
    source = Path(acceptance.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "EXPECTED_SYMBOL",
        "601857",
        "2025-01-01",
        "2025-12-31",
        "stage1cb",
        "中国石油",
        "petrochina",
    ):
        assert forbidden not in source


def test_cli_result_is_json_serializable(tmp_path: Path):
    result = _run_success(tmp_path)
    json.dumps(acceptance._jsonable(result))
