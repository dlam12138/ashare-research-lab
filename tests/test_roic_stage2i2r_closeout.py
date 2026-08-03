from decimal import Decimal

from ashare_research.tools import roic_official_fact_acquisition as stage


def test_three_state_gate_fails_closed_for_unknown_and_validator_failure():
    assert (
        stage.decide_acquisition_gate("READY_FOR_SHADOW", {"all": "TRUSTED"})["decision"]
        == "ROIC_SHADOW_ALLOWED"
    )
    assert (
        stage.decide_acquisition_gate("BLOCKED_WITH_EXPLICIT_GAPS", {"all": "TRUSTED"})["decision"]
        == "ROIC_FACT_GAPS_REMAIN"
    )
    assert (
        stage.decide_acquisition_gate("UNKNOWN", {"all": "TRUSTED"})["decision"]
        == "ROIC_ACQUISITION_NOT_TRUSTED"
    )
    assert (
        stage.decide_acquisition_gate("READY_FOR_SHADOW", {"search": "FAILED"})["decision"]
        == "ROIC_ACQUISITION_NOT_TRUSTED"
    )


def test_missing_ledger_has_executed_versioned_records():
    records = stage._missing_records()
    assert len(records) == 7
    assert all(item["search_spec_version"] == "2" for item in records)
    assert all(item["search_completeness"] == "complete" for item in records)
    assert all(len(item["deterministic_id"]) == 64 for item in records)


def test_reconciled_source_semantics_are_derived(monkeypatch):
    monkeypatch.setattr(stage, "_page_texts", lambda _: {2023: [""] * 293, 2024: [""] * 280})
    pages = {2023: [""] * 293, 2024: [""] * 280}
    pages[2024][114] = (
        "财务费用 47 (12,552) (18,091) 投资收益 49 11,934 9,554 "
        "公允价值变动收益 50 4,673 2,008 资产处置收益 53 613 498"
    )
    pages[2024][177] = "其中：租赁负债的利息支出 5,165 5,239"
    pages[2024][113] = "少数股东权益 41 194,492 184,211 - -"
    pages[2023][112] = "少数股东权益 42 184,211 168,550 - -"
    pages[2023][153] = (
        "货币资金中有账面价值为 21.40 亿元(2022 年 12 月 31 日：25.86 亿元)"
        "的保证金账户存款作为美元借款质押"
    )
    pages[2024][148] = "货币资金中无保证金账户存款作为美元借款质押(2023 年 12 月 31 日：21.40 亿元)"
    monkeypatch.setattr(stage, "_page_texts", lambda _: pages)
    bundle = stage.build_fact_bundle(stage.extract_cells(None))
    active = [fact for fact in bundle["facts"] if fact["eligible_for_metrics"]]
    assert active and all(fact["source_type"] == "reconciled_derived" for fact in active)
    assert all("evidence_set_digest" in fact for fact in active)
    assert Decimal(bundle["economic_facts"][0]["normalized_decimal_value"])
