"""Contracts for the Stage 2C-A value methodology baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.tools.official_cashflow_metric_extension import (
    STAGE2A_METRIC_RESULT_ID_SET_SHA256,
    STAGE2BA_FACT_ID_SET_SHA256,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "value_evaluation_methodology_v1.json"
METHODOLOGY = ROOT / "docs" / "value_evaluation_methodology_v1.md"
ROADMAP = ROOT / "docs" / "value_fact_coverage_roadmap.md"
GATES = ROOT / "docs" / "value_scoring_readiness_gates.md"

EXPECTED_METRICS = {
    "revenue_yoy",
    "net_profit_attributable_to_parent_yoy",
    "operating_cash_flow_yoy",
    "operating_cash_flow_to_attributable_net_profit",
    "cash_based_free_cash_flow_proxy",
    "cash_paid_for_fixed_assets_to_revenue",
}
EXPECTED_GAPS = {
    "扣非净利润",
    "毛利率和一般净利率",
    "非经常性损益",
    "ROE / ROA / ROIC",
    "财务安全",
    "分红与回购",
    "估值",
}
FORBIDDEN_KEYS = {
    "weight",
    "score",
    "rating",
    "grade",
    "buy_threshold",
    "sell_threshold",
    "target_price",
}
PROTECTED_BLOBS = {
    "src/ashare_research/metrics/definitions.py":
        "bb06f1e5d0358624fec8fb59863e9e2915a0bf6e",
    "src/ashare_research/metrics/cashflow_definitions.py":
        "4539bd36f306b821dd7f6accab05da8b23749e84",
    "src/ashare_research/metrics/models.py":
        "16e36169c29087fb02685aba65c7fd49d5e7840c",
    "src/ashare_research/metrics/engine.py":
        "7505cccc2b51df1fd73b30ea59c7ae1bb15bfee1",
    "src/ashare_research/facts/concepts.py":
        "f3a9d425c75a19a54313508d9b0f73b459a467f2",
    "src/ashare_research/tools/official_fact_metric_foundation.py":
        "e30f1a9b00b2ef07384bcc27c68d5df9762f3b23",
    "src/ashare_research/tools/official_capex_cash_fact_foundation.py":
        "08e2745eda9e584232e7c86b611bb02207eb7c35",
    "src/ashare_research/tools/official_cashflow_metric_extension.py":
        "66e6b97a5adf1530551dbd835cf81b30594204ce",
    "acceptance/m2_stage2a_petrochina_minimal_transparent_metrics.md":
        "d61b48db73a344a0759572d249a0594ba945f50e",
    "acceptance/m2_stage2ba_petrochina_capex_cash_fact_coverage.md":
        "6f76fb259fb6d1621550fda3e8f7473cf4a69b29",
    "acceptance/m2_stage2bb_petrochina_cashflow_metric_extension.md":
        "1e6ae316c8a79b0a48deaa2b2316b17f559f543e",
}


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _git_blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(  # noqa: S324
        f"blob {len(content)}\0".encode() + content
    ).hexdigest()


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for nested in value.values()
            for key in _all_keys(nested)
        }
    if isinstance(value, list):
        return {key for nested in value for key in _all_keys(nested)}
    return set()


def test_registry_is_parseable_and_versioned():
    registry = _registry()
    assert registry["schema_version"] == "1.0"
    assert registry["methodology_id"] == "ashare_value_evaluation_v1"
    assert registry["methodology_version"] == "1.0"


def test_all_and_only_code_registry_metrics_are_registered():
    registry_ids = {item["metric_id"] for item in _registry()["metrics"]}
    code_ids = {
        *MetricDefinitionRegistry.DEFINITIONS,
        *CashFlowMetricDefinitionRegistry.DEFINITIONS,
    }
    assert registry_ids == code_ids == EXPECTED_METRICS


def test_each_metric_has_a_complete_non_scoring_contract():
    required = {
        "metric_id",
        "methodology_version",
        "dimension",
        "interpretation_role",
        "supports_questions",
        "does_not_support",
        "industry_context_required",
        "multi_year_required",
        "peer_comparison_required",
        "pit_required",
        "restatement_sensitive",
        "score_eligible",
        "score_blockers",
        "references",
    }
    for metric in _registry()["metrics"]:
        assert required <= metric.keys()
        assert metric["score_eligible"] is False
        assert metric["supports_questions"]
        assert metric["does_not_support"]
        assert metric["references"]
        assert isinstance(metric["pit_required"], bool)
        assert isinstance(metric["restatement_sensitive"], bool)


def test_gap_inventory_is_fully_carried_into_the_roadmap():
    text = ROADMAP.read_text(encoding="utf-8")
    assert all(gap in text for gap in EXPECTED_GAPS)
    registry_gaps = {item["label"] for item in _registry()["fact_gaps"]}
    assert registry_gaps == {
        "扣非净利润",
        "利润率",
        "非经常性损益",
        "ROE / ROA / ROIC",
        "财务安全",
        "分红回购",
        "估值",
    }


def test_registry_has_no_forbidden_fields_or_trade_output():
    registry = _registry()
    assert _all_keys(registry).isdisjoint(FORBIDDEN_KEYS)
    serialized = json.dumps(registry, ensure_ascii=False)
    assert "建议买入" not in serialized
    assert "建议卖出" not in serialized
    assert "上涨概率" not in serialized


def test_methodology_freezes_fixed_interpretation_boundaries():
    text = METHODOLOGY.read_text(encoding="utf-8")
    assert "事实 ≠ 指标" in text
    assert "指标 ≠ 评价" in text
    assert "评价 ≠ 评分" in text
    assert "评分 ≠ 买卖建议" in text
    assert "不能把比率 1 机械设为绝对好坏边界" in text
    assert "不是完整 FCFF 或 FCFE" in text
    assert "不能无条件称为完整资本开支强度" in text
    assert all(metric in text for metric in EXPECTED_METRICS)


def test_scoring_remains_blocked_with_all_twelve_gates():
    registry = _registry()
    assert registry["scoring_readiness"] == "blocked"
    assert len(registry["score_readiness_gates"]) == 12
    text = GATES.read_text(encoding="utf-8")
    assert "Scoring readiness: BLOCKED" in text
    assert "分值、权重、数值阈值" in text


def test_frozen_fact_and_metric_result_id_digests_are_unchanged():
    frozen = _registry()["frozen_baseline"]
    assert frozen == {
        "financial_fact_count": 75,
        "financial_fact_id_set_sha256": (
            "7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1"
        ),
        "metric_result_count": 38,
        "metric_result_id_set_sha256": (
            "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
        ),
    }
    assert STAGE2BA_FACT_ID_SET_SHA256 == (
        "7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1"
    )
    assert STAGE2A_METRIC_RESULT_ID_SET_SHA256 == (
        "671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf"
    )


def test_fact_metric_code_runners_and_upstream_reports_are_frozen():
    for relative, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relative) == expected_blob, relative
