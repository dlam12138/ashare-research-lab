from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfWriter

from ashare_research.facts.identity import build_fact_id
from ashare_research.tools import roic_official_fact_acquisition as stage


def _synthetic_pages() -> dict[int, list[str]]:
    p24 = [""] * 280
    p23 = [""] * 293
    p24[114] = (
        "财务费用 47 (12,552) (18,091) 投资收益 49 11,934 9,554 "
        "公允价值变动收益 50 4,673 2,008 资产处置收益 53 613 498"
    )
    p24[177] = "其中：租赁负债的利息支出 5,165 5,239"
    p24[113] = "少数股东权益 41 194,492 184,211 - -"
    p24[148] = "货币资金中无保证金账户存款作为美元借款质押(2023 年 12 月 31 日：21.40 亿元)"
    p23[112] = "少数股东权益 42 184,211 168,550 - -"
    p23[153] = (
        "货币资金中有账面价值为 21.40 亿元(2022 年 12 月 31 日：25.86 亿元)"
        "的保证金账户存款作为美元借款质押"
    )
    return {2023: p23, 2024: p24}


def _cells(monkeypatch: pytest.MonkeyPatch) -> list[stage.ExtractedCell]:
    monkeypatch.setattr(stage, "_page_texts", lambda _: _synthetic_pages())
    return stage.extract_cells(Path("unused"))


def _small_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)


def test_contract_is_exactly_plan_v3_and_non_production() -> None:
    result = stage.validate_contracts()
    assert result["status"] == "PASS"
    assert result["approved_item_count"] == 11
    assert result["affected_cell_count"] == 16
    assert result["content_object_count"] == 2
    assert {
        "A-2024-finance-core",
        "A-2024-investment-income",
        "A-2024-fair-value",
        "A-2024-asset-disposal",
        "A-2024-operating-tax",
        "B-2024-lease-interest",
        "B-2023-2024-nci",
        "B-2023-2024-associate",
        "B-2023-2024-jv",
        "C-2023-2024-restricted-cash",
        "C-2023-2024-non-operating-financial-assets",
    } == stage.APPROVED_IDS
    assert "roic" not in json.loads(stage.VALUE_PROFILE_PATH.read_text(encoding="utf-8"))


def test_source_registry_has_exact_dual_official_identity_and_aliases() -> None:
    source = json.loads(stage.SOURCE_PATH.read_text(encoding="utf-8"))
    cache = json.loads(stage.CACHE_PATH.read_text(encoding="utf-8"))
    assert {item["source_type"] for item in source["entries"]} == {
        "company_official",
        "exchange_official",
    }
    assert all(item["original_url"].endswith(".pdf") for item in source["entries"])
    assert all(item["publication_date"] == item["available_at"] for item in source["entries"])
    assert all(len(item["content_sha256"]) == 64 for item in source["entries"])
    assert {len(item["evidence_ids"]) for item in cache["objects"]} == {2}
    assert all(not Path(item["object_key"]).is_absolute() for item in cache["objects"])
    assert cache["forbidden_fallbacks"] == [
        "Downloads",
        "browser_cache",
        "repository_tmp",
        "test_capsule",
    ]


def test_cache_verification_fails_closed_for_missing_hash_and_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = tmp_path / "object.pdf"
    _small_pdf(pdf)
    payload = pdf.read_bytes()
    registry = {
        "objects": [
            {
                "object_key": "object.pdf",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "byte_size": len(payload),
                "page_count": 1,
                "evidence_ids": ["issuer", "exchange"],
            }
        ]
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(stage, "CACHE_PATH", registry_path)
    assert stage.verify_official_cache(tmp_path)["status"] == "TRUSTED"
    pdf.write_bytes(payload + b"changed")
    with pytest.raises(ValueError, match="hash/size mismatch"):
        stage.verify_official_cache(tmp_path)
    pdf.unlink()
    with pytest.raises(FileNotFoundError, match="object missing"):
        stage.verify_official_cache(tmp_path)


def test_formal_requires_explicit_external_cache() -> None:
    with pytest.raises(FileNotFoundError, match="official-cache-root"):
        stage.verify_official_cache(None)
    with pytest.raises(ValueError, match="external"):
        stage.verify_official_cache(stage.ROOT / "tmp")


def test_acquire_retries_at_most_three(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.json"
    cache_path = tmp_path / "cache.json"
    source_path.write_text(
        json.dumps(
            {
                "entries": [
                    {"evidence_id": "issuer", "original_url": "https://issuer.invalid/report.pdf"}
                ]
            }
        ),
        encoding="utf-8",
    )
    cache_path.write_text(
        json.dumps(
            {
                "objects": [
                    {
                        "object_key": "objects/a.pdf",
                        "sha256": "a" * 64,
                        "byte_size": 1,
                        "page_count": 1,
                        "evidence_ids": ["issuer"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(stage, "SOURCE_PATH", source_path)
    monkeypatch.setattr(stage, "CACHE_PATH", cache_path)
    attempts = 0

    def fail(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal attempts
        attempts += 1
        raise OSError("blocked")

    monkeypatch.setattr(stage.urllib.request, "urlopen", fail)
    monkeypatch.setattr(stage.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        stage.acquire(tmp_path / "external")
    assert attempts == 3


def test_exact_extraction_uses_decimal_units_signs_and_locators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = _cells(monkeypatch)
    assert len(cells) == 9
    assert all(
        item.locator["pdf_page_index_zero_based"] + 1 == item.locator["pdf_page_number_one_based"]
        for item in cells
    )
    assert all(item.locator["table_title"] and item.locator["row_label"] for item in cells)
    assert all(item.locator["nearby_unit_declaration"] for item in cells)
    assert all(len(item.locator["source_excerpt_sha256"]) == 64 for item in cells)
    assert all(
        item.locator["extraction_method"] == "pypdf_embedded_text_regex_v1" for item in cells
    )
    assert all(item.locator["ocr_used"] is False for item in cells)
    assert all(isinstance(Decimal(item.normalized_value), Decimal) for item in cells)
    assert {item.conversion_multiplier for item in cells} == {"100", "10000"}


def test_finance_lease_composition_is_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    cells = {(item.concept_id, item.fiscal_year): item for item in _cells(monkeypatch)}
    finance = Decimal(cells[("finance_cost_excluding_lease_interest", 2024)].normalized_value)
    lease = Decimal(cells[("lease_interest_expense", 2024)].normalized_value)
    assert finance == Decimal("738700")
    assert lease == Decimal("516500")
    assert finance + lease == Decimal("1255200")
    assert "never contributes independently" in cells[("lease_interest_expense", 2024)].derivation


def test_role_specific_values_and_no_zero_default(monkeypatch: pytest.MonkeyPatch) -> None:
    cells = {(item.concept_id, item.fiscal_year): item for item in _cells(monkeypatch)}
    assert cells[("investment_income", 2024)].normalized_value == "1193400"
    assert cells[("fair_value_net_change", 2024)].normalized_value == "467300"
    assert cells[("asset_disposal_gain_loss", 2024)].normalized_value == "61300"
    assert cells[("non_controlling_interest", 2023)].normalized_value == "18421100"
    assert cells[("non_controlling_interest", 2024)].normalized_value == "19449200"
    assert cells[("restricted_cash", 2023)].normalized_value == "214000.00"
    zero = cells[("restricted_cash", 2024)]
    assert zero.raw_value == "无"
    assert zero.raw_sign_presentation == "explicit_absence"
    assert zero.normalized_value == "0"
    assert "not_default_fill" in zero.sign_normalization_rule
    assert "never freely deductible" in zero.purpose


def test_missing_and_ambiguous_facts_stay_explicit() -> None:
    records = stage._missing_records()
    assert len(records) == 7
    by_role = {(item["role_id"], item["fiscal_year"]): item for item in records}
    assert by_role[("tax.operating_tax_expense", 2024)]["status"] == "missing_official_fact"
    assert "forbidden proxies" in by_role[("tax.operating_tax_expense", 2024)]["why_no_fact"]
    for role in (
        "invested_capital.associate_investment",
        "invested_capital.joint_venture_investment",
    ):
        for year in (2023, 2024):
            assert by_role[(role, year)]["status"] == "ambiguous_scope"
            assert "residual" in by_role[(role, year)]["why_no_fact"]
    for year in (2023, 2024):
        item = by_role[("invested_capital.non_operating_financial_assets", year)]
        assert item["status"] == "missing_official_fact"
        assert "unproven assets remain included" in item["why_no_fact"]


def test_bundle_fact_identity_context_pit_and_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = stage.build_fact_bundle(_cells(monkeypatch))
    assert bundle["economic_fact_count"] == 9
    assert bundle["fact_count"] == 27
    assert bundle["shadow_status"] == "NOT_RUN"
    assert bundle["production_metric_created"] is False
    for fact in bundle["facts"]:
        assert fact["fact_id"] == build_fact_id(fact)
        assert fact["accounting_standard"] == "CAS"
        assert fact["scope"] == "consolidated"
        assert fact["unit"] == "万元"
        assert fact["currency"] == "CNY"
        assert fact["supersedes_fact_id"] is None
        assert fact["fact_version"] == 1
        assert fact["restatement_version"] == "original"
    active = [item for item in bundle["facts"] if item["eligible_for_metrics"]]
    assert len(active) == 9
    assert all(item["verification_status"] == "reconciled" for item in active)
    assert all(len(item["source_evidence"]) == 2 for item in active)
    assert all(item["available_at"] in {"2024-03-26", "2025-03-31"} for item in active)


def test_result_preserves_all_items_cells_and_score_false(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = stage.build_fact_bundle(_cells(monkeypatch))
    result = stage._acquisition_result(bundle, stage._missing_records())
    assert result["cell_count"] == 16
    assert {item["plan_acquisition_id"] for item in result["cells"]} == stage.APPROVED_IDS
    assert result["status_counts"] == {
        "acquired_verified": 9,
        "ambiguous_scope": 4,
        "missing_official_fact": 3,
    }
    assert all(item["score_eligibility"] is False for item in result["cells"])
    assert result["shadow_feasibility"] == "NOT_RUN"
    assert result["production_metric_result_created"] is False


def test_compare_formal_runs_is_path_independent(tmp_path: Path) -> None:
    first, second = tmp_path / "a" / "formal", tmp_path / "different" / "formal"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    for root in (first, second):
        (root / "artifact.json").write_text('{"decimal":"1.00"}\n', encoding="utf-8")
    assert stage.compare_runs(first, second) == {
        "status": "PASS",
        "artifact_count": 1,
        "mismatches": [],
    }
    (second / "artifact.json").write_text('{"decimal":"2.00"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="artifacts differ"):
        stage.compare_runs(first, second)


def test_default_db_registry_graph_plan_and_profile_are_never_write_targets() -> None:
    source = (
        stage.Path(__file__).parents[1]
        / "src"
        / "ashare_research"
        / "tools"
        / "roic_official_fact_acquisition.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "duckdb.connect" not in text
    assert ".write_text(REGISTRY_PATH" not in text
    assert ".write_text(GRAPH_PATH" not in text
    assert ".write_text(PLAN_PATH" not in text
    assert ".write_text(VALUE_PROFILE_PATH" not in text
    assert "float(" not in text
    assert "never calculates ROIC" in text
