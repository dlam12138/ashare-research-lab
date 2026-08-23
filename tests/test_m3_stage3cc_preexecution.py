"""Synthetic-only boundary tests for Stage 3C-C orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.tools.m3_stage3cb_inputs import Stage3CBInputError
from ashare_research.tools.m3_stage3cc_registered_robustness import (
    BH_Q,
    EXPECTED_DATA_MANIFEST_DIGEST,
    EXPECTED_MODEL_DIGEST,
    EXTREME_COUNTS,
    PRIMARY_DECISION,
    THRESHOLDS,
    build_robustness_execution_digest,
    load_execution_plan,
    load_result_schema,
    validate_result_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _minimal_result() -> dict:
    return {
        "stage": "M3_STAGE3CC",
        "canonical_base": "4669eebf2e1837053495d56f68ea414bd76c692d",
        "upstream_inventory_sha": (
            "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
        ),
        "pipeline_digest": "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b",
        "model_digest": EXPECTED_MODEL_DIGEST,
        "execution_adapter_digest": (
            "9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78"
        ),
        "data_manifest_digest": EXPECTED_DATA_MANIFEST_DIGEST,
        "robustness_execution_digest": "a" * 64,
        "primary_anchor": {
            "nobs": 1902,
            "crash_count": 330,
            "gamma": 0.0005072734676652487,
            "gamma_ci_lower": -0.0021987423016553366,
            "gamma_ci_upper": 0.0033325010311833106,
            "primary_decision": PRIMARY_DECISION,
            "reversal_prohibited": True,
        },
        "descriptive": {},
        "conditional": {},
        "threshold_robustness": {
            "results": [
                {"threshold": value, "pvalue_two_sided": 0.5}
                for value in THRESHOLDS
            ],
            "bh_q": BH_Q,
            "bh_adjusted_p_values": [0.5, 0.5, 0.5],
            "bh_reject": [False, False, False],
        },
        "extreme_day": {"remove_top_1": {}, "remove_top_3": {}},
        "calendar_year": {},
        "registered_not_executed": {
            "leave_one_event_out": "NOT_EXECUTED_PREOUTCOME_IMPLEMENTATION_MISSING",
        },
        "development_evidence_ceiling": 2,
        "development_evidence_level": None,
        "evidence_level_status": (
            "NOT_ASSIGNABLE_BECAUSE_DESCRIPTIVE_RELATIONSHIP_CRITERION_NOT_PRELOCKED"
        ),
        "holdout_read": False,
        "same_input_ab": {"exact_match": True},
    }


def test_plan_is_exact_projection_and_prohibits_unregistered_scope() -> None:
    plan = load_execution_plan()
    assert plan["execution"]["thresholds"] == THRESHOLDS
    assert plan["execution"]["benjamini_hochberg_q"] == BH_Q
    assert plan["execution"]["remove_top_extreme_crash_day_counts"] == EXTREME_COUNTS
    assert plan["not_executed"]["leave_one_event_out"] == (
        "NOT_EXECUTED_PREOUTCOME_IMPLEMENTATION_MISSING"
    )
    assert plan["holdout"]["read"] is False


def test_execution_digest_is_repository_relative_and_binds_frozen_sources() -> None:
    digest, payload = build_robustness_execution_digest(
        data_manifest_digest=EXPECTED_DATA_MANIFEST_DIGEST,
        model_digest=EXPECTED_MODEL_DIGEST,
    )
    assert len(digest) == 64
    assert payload["data_manifest_digest"] == EXPECTED_DATA_MANIFEST_DIGEST
    assert payload["model_digest"] == EXPECTED_MODEL_DIGEST
    assert set(payload["source_hashes"]) == {
        "src/ashare_research/tools/m3_stage3cc_registered_robustness.py",
        "src/ashare_research/mechanism/robustness.py",
        "src/ashare_research/mechanism/regression.py",
    }
    assert all(":" not in key and not key.startswith("/") for key in payload["source_hashes"])


def test_result_schema_preserves_primary_and_caps_evidence() -> None:
    schema = load_result_schema()
    assert schema["primary_anchor"]["decision"] == PRIMARY_DECISION
    assert schema["development_evidence"]["ceiling"] == 2
    assert schema["development_evidence"]["level_3_prohibited"] is True
    validate_result_payload(_minimal_result())


def test_result_schema_rejects_primary_reversal_and_primary_threshold_family() -> None:
    result = _minimal_result()
    result["primary_anchor"]["primary_decision"] = (
        "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
    )
    with pytest.raises(Stage3CBInputError, match="PRIMARY_DECISION_IMMUTABLE"):
        validate_result_payload(result)

    result = _minimal_result()
    result["threshold_robustness"]["results"][0]["threshold"] = -0.01
    with pytest.raises(Stage3CBInputError, match="THRESHOLD_FAMILY_MISMATCH"):
        validate_result_payload(result)


def test_same_input_ab_is_canonical_json_deterministic() -> None:
    left = {"thresholds": THRESHOLDS, "counts": EXTREME_COUNTS, "q": BH_Q}
    right = {"q": BH_Q, "counts": EXTREME_COUNTS, "thresholds": THRESHOLDS}
    assert canonical_digest(left) == canonical_digest(right)


def test_runner_does_not_define_prohibited_post_outcome_functions() -> None:
    source = (ROOT / "src/ashare_research/tools/m3_stage3cc_registered_robustness.py").read_text(
        encoding="utf-8"
    )
    assert "def leave_one_event_out" not in source
    assert "requests." not in source
    assert "akshare" not in source
    assert "baostock" not in source
