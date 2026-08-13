from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "src/ashare_research/tools/m2_stage2k1r4f4b_post_5y_pe_disposition.py"
SPEC = importlib.util.spec_from_file_location("r4f4b", TOOL_PATH)
assert SPEC and SPEC.loader
r4f4b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r4f4b)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_exact_upstream_chain_and_protected_hashes():
    assert r4f4b.verify_upstream() == []
    assert len(r4f4b.UPSTREAM_DECISIONS) == 8
    assert r4f4b.PROTECTED_SHA256.keys() >= {
        "reports/m2_stage2k1r4f_decision.json",
        "config/value_dimension_scoring_registry_v2.json",
        "config/value_dimension_scoring_policy_v2.json",
        "reports/petrochina_dimension_scoring_shadow_v6.json",
        "reports/m2_stage2k1r4f4a_decision.json",
        "reports/m2_stage2k1r4f4a1_decision.json",
    }


def test_frozen_5y_evidence_is_exact_and_future_safe():
    decision = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")
    assert decision["upstream_decision"].endswith("NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY")
    assert decision["frozen_5y_evidence"] == {
        "required_days": 1211,
        "ready_days": 1211,
        "blocked_days": 0,
        "candidate_regimes": 1,
        "observed_onsets": 0,
        "left_censored_regimes": 1,
        "valid_onset_episodes": 0,
        "mature_4q": 0,
        "mature_8q": 0,
        "future_eps_values_read": False,
    }


def test_disposition_matrix_selects_descriptive_pe_only():
    matrix = load("reports/m2_stage2k1r4f4b_pe_method_disposition_matrix_v1.json")
    assert len(matrix["candidates"]) == 4
    selected = [row for row in matrix["candidates"] if row["decision"] == "SELECT"]
    assert [row["candidate"] for row in selected] == [
        "KEEP_PE_DESCRIPTIVE_DEFER_NUMERIC_SCORING"
    ]
    assert matrix["new_economic_fact_acquisition"] is False
    assert matrix["future_outcome_read"] is False
    assert matrix["m3_implementation"] is False
    assert all(row["acquisition_performed"] is False for row in matrix["candidates"])


def test_pe_and_valuation_fail_closed_without_zero_or_renormalization():
    decision = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")
    policy = decision["scoring_policy"]
    assert policy["pe_component_score"] is None
    assert policy["valuation_dimension_score"] is None
    assert policy["pe_zero_imputation"] is False
    assert policy["weight_redistribution"] is False
    assert policy["registered_weight_topology_unchanged"] is True
    shadow = load("reports/petrochina_dimension_scoring_shadow_v6.json")["dimensions"][
        "valuation_attractiveness"
    ]
    assert shadow["score"] is None and shadow["components"]["va_pe"]["score"] is None
    assert shadow["eligible_weight"] == 1.0 and shadow["covered_weight"] == 0.6
    assert shadow["coverage_ratio"] == 0.6


def test_no_production_overall_rank_recommendation_or_target_price():
    policy = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")[
        "scoring_policy"
    ]
    for key in (
        "production_scoring",
        "overall_score",
        "ranking",
        "recommendation",
        "target_price",
    ):
        assert policy[key] is False


def test_m2_conditional_closeout_and_m3_preflight_boundary():
    decision = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")
    assert decision["decision"] == (
        "PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE"
    )
    assert decision["m2_status"] == {
        "milestone": "CONDITIONALLY_CLOSED",
        "scoring_addendum": "CONDITIONAL_CLOSEOUT_ALLOWED",
        "fully_complete": False,
    }
    assert decision["next_stage"] == {
        "stage": "M3_NORTH_STAR_PREFLIGHT",
        "preflight_allowed": True,
        "implementation_authorized": False,
        "automatic_start": False,
    }


def test_reopen_gate_prevents_ex_post_method_search():
    gate = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")[
        "method_reopen_gate"
    ]
    assert gate["allowed_reasons"] == [
        "NEW_PRE_REGISTERED_METHOD",
        "NEW_INDEPENDENT_EVIDENCE_CLASS",
        "NORTH_STAR_MATERIAL_CHANGE",
    ]
    assert gate["prohibited_reasons"] == [
        "MORE_HISTORY_ONLY",
        "THRESHOLD_TUNING_AFTER_RESULT",
        "OUTCOME_DRIVEN_METHOD_SELECTION",
    ]


def test_tool_has_no_network_or_acquisition_implementation():
    source = TOOL_PATH.read_text(encoding="utf-8").lower()
    forbidden_code = (
        "import requests",
        "from requests",
        "urllib.request",
        "httpx",
        "akshare",
        "baostock",
        "download(",
    )
    assert not any(token in source for token in forbidden_code)
    boundary = load("reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json")[
        "scope_boundary"
    ]
    assert not any(boundary.values())


def test_build_is_byte_deterministic_and_matches_committed_artifacts(tmp_path):
    built_a = r4f4b.build_all()
    built_b = r4f4b.build_all()
    assert built_a == built_b
    for name, content in built_a.items():
        a = tmp_path / "a" / name
        b = tmp_path / "b" / name
        a.parent.mkdir(exist_ok=True)
        b.parent.mkdir(exist_ok=True)
        a.write_bytes(content.encode("utf-8"))
        b.write_bytes(content.encode("utf-8"))
        assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
        committed = (ROOT / "reports" / name).read_text(encoding="utf-8")
        assert committed.replace("\r\n", "\n").replace("\r", "\n") == content


def test_artifacts_do_not_leak_local_absolute_paths():
    for name in r4f4b.ARTIFACTS.values():
        text = (ROOT / "reports" / name).read_text(encoding="utf-8").lower()
        assert "d:\\" not in text
        assert "c:\\users\\" not in text
        assert "/home/" not in text
