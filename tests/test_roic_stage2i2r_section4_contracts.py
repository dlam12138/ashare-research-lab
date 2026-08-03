from decimal import Decimal

import pytest

from ashare_research.tools import roic_official_fact_acquisition as stage


def test_search_classification_is_match_content_driven():
    assert (
        stage.classify_search_match(term="所得税费用", excerpt="税率调节", acquisition_id="x")[0]
        == "tax_proxy_only"
    )
    assert (
        stage.classify_search_match(term="合营企业", excerpt="合计单项不重大", acquisition_id="x")[
            0
        ]
        == "aggregate_only_disclosure"
    )
    assert (
        stage.classify_search_match(term="非经营金融资产", excerpt="利息收入", acquisition_id="x")[
            0
        ]
        == "acceptable_exact_fact"
    )
    assert (
        stage.classify_search_match(
            term="其他权益工具投资", excerpt="金融资产", acquisition_id="x"
        )[0]
        == "purpose_income_linkage_missing"
    )
    assert (
        stage.classify_search_match(term="未知", excerpt="无关", acquisition_id="x")[0]
        == "irrelevant"
    )


def test_gate_whitelist_fails_closed_for_each_validator():
    for status in ("FAILED", "UNKNOWN", None):
        assert (
            stage.decide_acquisition_gate("READY_FOR_SHADOW", {"validator": status})["decision"]
            == "ROIC_ACQUISITION_NOT_TRUSTED"
        )
    assert (
        stage.decide_acquisition_gate("BLOCKED_WITH_EXPLICIT_GAPS", {"all": "TRUSTED"})["decision"]
        == "ROIC_FACT_GAPS_REMAIN"
    )


def test_search_specs_cover_all_cells_and_rejection_codes():
    records = stage._missing_records()
    assert len(records) == 7
    assert all(item["acceptance_patterns"] and item["exclusion_patterns"] for item in records)
    assert all("TAX_PROXY_ONLY" in item["rejection_reason_codes"] for item in records)


def test_search_validator_rejects_missing_object_and_bad_pit():
    record = stage._missing_records()[0]
    with pytest.raises(ValueError):
        stage.validate_search_results([record] * 6)
    record["content_object_ids"] = []
    with pytest.raises(ValueError):
        stage.validate_search_results([record] + stage._missing_records()[1:])


def test_decimal_and_identity_helpers_are_non_float():
    assert isinstance(Decimal("1.20"), Decimal)
    assert "float(" not in stage.Path(stage.__file__).read_text(encoding="utf-8")


def test_plan_and_artifact_contracts_remain_complete():
    result = stage.validate_contracts()
    assert result["approved_item_count"] == 11
    assert result["affected_cell_count"] == 16
