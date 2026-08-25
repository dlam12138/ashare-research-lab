from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/ashare_research/tools/m3_stage3a_preflight.py"
SPEC = importlib.util.spec_from_file_location("m3_stage3a", TOOL)
assert SPEC and SPEC.loader
m3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m3)


def load(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def test_canonical_question_and_primary_hypothesis_are_frozen():
    contract = load(m3.ARTIFACTS["hypothesis"])
    assert "excluding PetroChina" in contract["canonical_question"]
    assert contract["prohibited_question"] == "Is PetroChina used to support the market?"
    assert contract["primary_hypothesis"]["outcome"] == "abnormal_return"
    assert contract["primary_hypothesis"]["raw_positive_return_is_primary_evidence"] is False
    assert contract["interpretation_boundary"]["funding_actor_intent_inference_authorized"] is False


def test_proxy_and_thresholds_fail_closed_without_ex_post_tuning():
    hypothesis = load(m3.ARTIFACTS["hypothesis"])
    data = load(m3.ARTIFACTS["data"])
    condition = hypothesis["market_condition"]
    assert condition == {
        "ex_post_threshold_tuning_allowed": False,
        "operator": "<=",
        "primary_threshold": -0.01,
        "proxy": "SH_MARKET_EX_601857",
        "robustness_thresholds": [-0.005, -0.015, -0.02],
    }
    proxy = data["primary_market_proxy"]
    assert proxy["exact_reproducibility"] == "DATA_ACQUISITION_REQUIRED"
    assert proxy["fallback_to_sse_composite_allowed"] is False


def test_outcomes_and_controls_are_tiered_and_non_production():
    hypothesis = load(m3.ARTIFACTS["hypothesis"])
    protocol = load(m3.ARTIFACTS["protocol"])
    assert hypothesis["outcomes"]["primary"]["id"] == "abnormal_return"
    positive = next(
        item for item in hypothesis["outcomes"]["secondary"]
        if item["id"] == "positive_return_indicator"
    )
    assert positive["role"] == "DESCRIPTIVE_ONLY"
    assert protocol["controls"]["tier_1_required"] == [
        "market_ex_target", "oil", "petrochemical_industry"
    ]
    assert protocol["real_data_execution_authorized"] is False


def test_oil_alignment_and_sample_availability_are_point_in_time_safe():
    data = load(m3.ARTIFACTS["data"])
    oil = data["oil_point_in_time_policy"]
    assert oil["primary"] == "LATEST_OBSERVABLE_BEFORE_A_SHARE_CLOSE"
    assert oil["fallback"] == "OIL_RETURN_T_MINUS_1"
    assert oil["same_day_overseas_close_allowed"] is False
    sample = data["sample_availability_policy"]
    assert sample["effective_primary_start"] == "MAX_TRUSTWORTHY_START_OF_REQUIRED_PRIMARY_INPUTS"
    assert sample["pre_effective_period"] == "DESCRIPTIVE_ONLY"
    assert sample["forward_fill_missing_history_allowed"] is False


def test_bootstrap_multiplicity_and_holdout_are_pre_registered():
    protocol = load(m3.ARTIFACTS["protocol"])
    assert protocol["bootstrap"] == {
        "block_length_rule": "ROUND_N_TO_ONE_THIRD_CAPPED_AT_20_TRADING_DAYS",
        "change_after_results_allowed": False,
        "ci_method": "PERCENTILE_TWO_SIDED_95",
        "iid_is_primary": False,
        "method": "MOVING_BLOCK_BOOTSTRAP",
        "replications": 5000,
        "seed": 20260813,
    }
    assert protocol["multiple_testing"]["primary_inference_count"] == 1
    assert protocol["multiple_testing"]["robustness_family_correction"] == "BENJAMINI_HOCHBERG_FDR"
    assert protocol["out_of_sample"]["holdout_status"] == "SEALED"
    assert protocol["out_of_sample"]["holdout_read_performed"] is False
    assert protocol["out_of_sample"]["unseal_preconditions"] == [
        "PIPELINE_LOCKED", "MODEL_DIGEST_LOCKED"
    ]


def test_extreme_dates_contribution_and_evidence_ceiling_are_bounded():
    protocol = load(m3.ARTIFACTS["protocol"])
    robust = protocol["extreme_date_robustness"]
    assert robust["leave_one_event_out"] is True
    assert robust["remove_top_absolute_abnormal_returns"] == [1, 3]
    assert robust["winsorization_primary_allowed"] is False
    contribution = protocol["index_contribution"]
    assert contribution["separate_from_abnormal_return"] is True
    assert contribution["official_point_attribution_claim_allowed"] is False
    assert protocol["daily_mvp_max_authorized_level"] == 3
    assert protocol["minute_data_required_for_level_4"] is True


def test_decision_authorizes_only_stage3b_and_contains_no_result():
    decision = load(m3.ARTIFACTS["decision"])
    assert decision["decision"] == "M3_MECHANISM_RESEARCH_CONTRACT_FROZEN"
    assert decision["next_stage"] == "M3_STAGE3B_DATA_ACQUISITION_AND_NORMALIZATION_ALLOWED"
    for key in (
        "stage3b_started", "m3_implementation_complete",
        "petrochina_abnormal_support_behavior_confirmed",
        "real_hypothesis_result_produced", "real_data_acquisition_performed",
        "regression_performed", "holdout_read_performed",
    ):
        assert decision[key] is False


def test_build_is_deterministic_and_matches_committed_artifacts(tmp_path):
    built_a = m3.build_all()
    built_b = m3.build_all()
    assert built_a == built_b
    for name, content in built_a.items():
        a = tmp_path / "a" / name
        b = tmp_path / "b" / name
        a.parent.mkdir(exist_ok=True)
        b.parent.mkdir(exist_ok=True)
        a.write_bytes(content.encode("utf-8"))
        b.write_bytes(content.encode("utf-8"))
        assert a.read_bytes() == b.read_bytes()
        committed = (ROOT / "reports" / name).read_text(encoding="utf-8")
        assert committed.replace("\r\n", "\n").replace("\r", "\n") == content


def test_artifacts_have_no_local_paths_or_real_statistics():
    forbidden = ["d:\\", "c:\\users\\", "/home/", '"p_value"', '"coefficient"']
    for name in m3.ARTIFACTS.values():
        text = (ROOT / "reports" / name).read_text(encoding="utf-8").lower()
        assert not any(token in text for token in forbidden)


def test_stage3b_data_layer_remains_intact_after_stage3ca_integration():
    package = ROOT / "src/ashare_research/mechanism"
    assert package.is_dir()
    allowed = {
        "__init__.py",
        "contracts.py",
        "market_proxy.py",
        "normalization.py",
        "source_manifest.py",
        "proxy_v2.py",
        "oil.py",
        "industry.py",
        "alignment.py",
        "acquisition_eia.py",
        "acquisition_shenwan.py",
        "acquisition_fred_public.py",
        "acquisition_cni.py",
        "analysis_contracts.py",
        "analysis_dataset.py",
        "bootstrap.py",
        "crash.py",
        "evidence.py",
        "model_digest.py",
        "regression.py",
        "robustness.py",
    }
    allowed |= {"hypothesis_config.py", "contract_compiler.py"}
    assert {path.name for path in package.glob("*.py")} == allowed
    prohibited = {"conditional_test.py", "evidence_grade.py"}
    assert not any((package / name).exists() for name in prohibited)
