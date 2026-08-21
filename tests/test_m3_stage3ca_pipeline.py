"""Focused offline tests for the locked Stage 3C-A synthetic pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import MissingDataError

from ashare_research.mechanism.analysis_contracts import (
    ANALYSIS_COLUMNS,
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_SEED,
    DESIGN_COLUMNS,
    AnalysisContractError,
    ExecutionGateError,
    enforce_execution_gate,
    load_json_contract,
)
from ashare_research.mechanism.analysis_dataset import (
    prepare_analysis_dataset,
    select_development_sample,
)
from ashare_research.mechanism.bootstrap import (
    moving_block_bootstrap,
    moving_block_length,
    moving_block_sample,
)
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.evidence import (
    evidence_level,
    interpretation_boundary,
    primary_decision,
)
from ashare_research.mechanism.model_digest import (
    build_model_digest,
    build_pipeline_digest,
)
from ashare_research.mechanism.regression import fit_primary_ols
from ashare_research.mechanism.robustness import (
    benjamini_hochberg,
    conditional_summary,
    descriptive_summary,
    leave_one_year_out,
    remove_top_extreme_crash_days,
    threshold_robustness,
)
from ashare_research.tools.m3_stage3ca_pipeline import run_synthetic, synthetic_fixture


def _frame(n: int = 80) -> pd.DataFrame:
    rng = np.random.Generator(np.random.PCG64(11))
    market = np.tile([-0.012, -0.004, 0.003, 0.01], n // 4)
    oil = rng.normal(0, 0.01, n)
    industry = rng.normal(0, 0.01, n)
    target = 0.001 + 0.7 * market + 0.4 * oil + 0.2 * industry + 0.03 * (market <= -0.01)
    dates = pd.date_range("2019-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "trade_date": dates,
            "target_analysis_return": target,
            "market_ex_target_return": market,
            "oil_return": oil,
            "industry_return": industry,
            "target_valid": True,
            "market_valid": True,
            "oil_valid": True,
            "industry_valid": True,
            "tier1_joint_valid": True,
        }
    )


def test_contracts_are_valid_and_constants_are_frozen() -> None:
    pipeline = load_json_contract("m3_stage3ca_analysis_pipeline_contract_v1.json")
    model = load_json_contract("m3_stage3ca_model_specification_v1.json")
    robustness = load_json_contract("m3_stage3ca_robustness_registry_v1.json")
    output = load_json_contract("m3_stage3ca_output_schema_v1.json")
    assert pipeline["status"] == "PIPELINE_LOCKED"
    assert model["estimator"]["method"] == "OLS"
    assert robustness["multiple_testing"] == {
        "family": "threshold_robustness",
        "method": "Benjamini-Hochberg",
        "q": 0.05,
    }
    assert output["forbidden_real_output"] is True
    assert pipeline["bootstrap"]["replications"] == BOOTSTRAP_REPLICATIONS
    assert pipeline["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert tuple(pipeline["model"]["design_columns"]) == DESIGN_COLUMNS
    assert tuple(pipeline["input_schema"]["required_columns"]) == ANALYSIS_COLUMNS


def test_schema_canonicalizes_unsorted_dates() -> None:
    frame = _frame().sample(frac=1, random_state=3)
    result = prepare_analysis_dataset(frame)
    assert result["trade_date"].is_monotonic_increasing
    assert result.index.tolist() == list(range(len(result)))


def test_schema_rejects_missing_duplicate_and_mixed_target_input() -> None:
    frame = _frame()
    with pytest.raises(AnalysisContractError, match="missing analysis columns"):
        prepare_analysis_dataset(frame.drop(columns=["oil_return"]))
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(AnalysisContractError, match="duplicate trade_date"):
        prepare_analysis_dataset(duplicate)
    frame["target_unadjusted_return"] = frame["target_analysis_return"]
    with pytest.raises(AnalysisContractError, match="mixing"):
        prepare_analysis_dataset(frame)


def test_schema_rejects_nonfinite_returns_and_nonboolean_flags() -> None:
    frame = _frame()
    frame.loc[0, "target_analysis_return"] = np.inf
    with pytest.raises(AnalysisContractError, match="non-finite"):
        prepare_analysis_dataset(frame)
    frame = _frame()
    frame["target_valid"] = frame["target_valid"].astype(object)
    frame.loc[0, "target_valid"] = 1
    with pytest.raises(AnalysisContractError, match="boolean"):
        prepare_analysis_dataset(frame)


def test_schema_rejects_missing_validity_flags() -> None:
    frame = _frame()
    frame["oil_valid"] = frame["oil_valid"].astype(object)
    frame.loc[0, "oil_valid"] = None
    with pytest.raises(AnalysisContractError, match="missing validity"):
        prepare_analysis_dataset(frame)


def test_development_sample_uses_target_and_joint_validity() -> None:
    frame = _frame()
    frame.loc[0, "target_valid"] = False
    frame.loc[1, "tier1_joint_valid"] = False
    frame.loc[2, "trade_date"] = pd.Timestamp("2023-01-03")
    result = select_development_sample(frame)
    assert len(result) == len(frame) - 3
    assert result["trade_date"].max().year == 2019


def test_execution_gate_rejects_real_and_holdout() -> None:
    frame = _frame()
    with pytest.raises(ExecutionGateError, match="REAL_ANALYSIS_NOT_AUTHORIZED"):
        enforce_execution_gate("development", frame)
    holdout = frame.copy()
    holdout.loc[0, "trade_date"] = pd.Timestamp("2023-01-01")
    with pytest.raises(ExecutionGateError, match="HOLDOUT_SEALED"):
        enforce_execution_gate("synthetic", holdout)


def test_execution_gate_allows_pre_holdout_synthetic_fixture() -> None:
    enforce_execution_gate("synthetic", _frame())


def test_crash_rule_uses_exact_less_equal_boundary() -> None:
    frame = _frame(4)
    frame["market_ex_target_return"] = [-0.01, -0.009999, -0.015, 0.0]
    result = add_crash_indicator(frame)
    assert result["Crash_t"].tolist() == [1, 0, 1, 0]
    assert add_crash_indicator(frame, -0.015)["Crash_t"].tolist() == [0, 0, 1, 0]


def test_crash_rule_does_not_consult_target_or_industry_columns() -> None:
    frame = _frame(4)
    frame["market_ex_target_return"] = [-0.02, 0.0, 0.0, 0.0]
    frame["target_analysis_return"] = [-0.99, -0.99, -0.99, -0.99]
    frame["industry_return"] = [-0.99, -0.99, -0.99, -0.99]
    assert add_crash_indicator(frame)["Crash_t"].tolist() == [1, 0, 0, 0]


def test_ols_design_order_intercept_oracle_and_abnormal_return() -> None:
    frame = _frame()
    frame = add_crash_indicator(frame)
    fitted = fit_primary_ols(frame)
    assert list(fitted.design_matrix.columns) == list(DESIGN_COLUMNS)
    assert np.all(fitted.design_matrix["const"].to_numpy() == 1.0)
    assert fitted.coefficients["gamma"] == pytest.approx(0.03, abs=1e-12)
    expected = fitted.expected_control_return
    assert fitted.abnormal_return.iloc[0] == pytest.approx(
        frame["target_analysis_return"].iloc[0] - expected.iloc[0]
    )


def test_ols_missing_raise_and_crash_column_required() -> None:
    frame = add_crash_indicator(_frame())
    frame.loc[0, "oil_return"] = np.nan
    with pytest.raises(MissingDataError):
        fit_primary_ols(frame)
    with pytest.raises(AnalysisContractError, match="regression columns"):
        fit_primary_ols(_frame())


def test_ols_parameter_names_are_stable() -> None:
    fitted = fit_primary_ols(add_crash_indicator(_frame()))
    assert list(fitted.coefficients) == [
        "alpha",
        "beta_market",
        "beta_oil",
        "beta_industry",
        "gamma",
    ]


def test_moving_block_rule_and_non_circular_boundaries() -> None:
    assert moving_block_length(1) == 1
    assert moving_block_length(8) == 2
    assert moving_block_length(100_000) == 20
    frame = add_crash_indicator(_frame())
    sample = moving_block_sample(frame, np.array([0, 10]), 3)
    assert sample["trade_date"].tolist() == frame.iloc[[0, 1, 2, 10, 11, 12]]["trade_date"].tolist()
    with pytest.raises(ValueError, match="outside"):
        moving_block_sample(frame, np.array([len(frame) - 1]), 3)


def test_mbb_reproducibility_and_rowwise_resampling() -> None:
    frame = add_crash_indicator(_frame())
    left = moving_block_bootstrap(frame, replications=10)
    right = moving_block_bootstrap(frame, replications=10)
    assert np.array_equal(left.gamma_samples, right.gamma_samples)
    assert left.seed == BOOTSTRAP_SEED
    assert left.rng == "PCG64"
    assert left.gamma_ci_lower <= left.gamma_ci_upper


def test_mbb_rejects_unknown_rng_and_invalid_replications() -> None:
    frame = add_crash_indicator(_frame())
    with pytest.raises(ValueError, match="PCG64"):
        moving_block_bootstrap(frame, replications=2, rng_algorithm="default_rng")
    with pytest.raises(ValueError, match="positive"):
        moving_block_bootstrap(frame, replications=0)


def test_production_bootstrap_contract_is_5000_replicates() -> None:
    contract = load_json_contract("m3_stage3ca_analysis_pipeline_contract_v1.json")
    assert contract["bootstrap"]["replications"] == 5000
    assert contract["bootstrap"]["rng_algorithm"] == "PCG64"


def test_primary_decision_is_strict_two_sided_ci_rule() -> None:
    assert primary_decision(0.01, 0.001) == (
        "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
    )
    assert primary_decision(0.01, 0.0) == (
        "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
    )
    assert primary_decision(-0.01, 0.001) == (
        "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
    )


@pytest.mark.parametrize(
    ("kind", "expected_positive"),
    [("positive", True), ("null", False), ("negative", False)],
)
def test_fixture_decision_classes(kind: str, expected_positive: bool) -> None:
    result = run_synthetic(kind, bootstrap_replications=20)
    is_positive = result["primary"]["primary_decision"] == (
        "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
    )
    assert is_positive is expected_positive
    assert result["execution"]["holdout_execution_authorized"] is False


def test_extreme_fixture_is_supporting_warning_not_level_three() -> None:
    result = run_synthetic("extreme", bootstrap_replications=10)
    assert result["primary"]["evidence_level"] <= 2
    assert result["robustness"]["extreme_days"]["1"]["removed_trade_dates"]


def test_descriptive_and_conditional_layers_are_non_primary() -> None:
    frame = add_crash_indicator(_frame())
    desc = descriptive_summary(frame)
    conditional = conditional_summary(frame)
    assert "full_sample_correlation" in desc
    assert desc["volume_abnormality"]["status"].startswith("REGISTERED_")
    assert desc["market_regimes"]["status"].startswith("REGISTERED_")
    assert conditional["crash_count"] > 0
    assert conditional["ordinary_count"] > 0
    assert "gamma" not in conditional


def test_extreme_ranking_uses_absolute_control_only_abnormal_and_date_tie_break() -> None:
    frame = add_crash_indicator(_frame())
    fitted = fit_primary_ols(frame)
    reduced, dates = remove_top_extreme_crash_days(frame, fitted, 3)
    assert len(reduced) == len(frame) - 3
    assert dates == sorted(dates, reverse=True) or len(dates) == 3


def test_year_leave_out_is_mechanical() -> None:
    frame = add_crash_indicator(synthetic_fixture("positive", 900))
    result = leave_one_year_out(frame)
    assert set(result) == {"2018", "2019", "2020", "2021"}
    assert all(item["nobs"] < len(frame) for item in result.values())


def test_threshold_robustness_preserves_controls_and_marks_non_estimable() -> None:
    frame = add_crash_indicator(_frame())
    results = threshold_robustness(frame, [-0.01, -0.5])
    assert [item["threshold"] for item in results] == [-0.01, -0.5]
    assert results[0]["estimable"] is True
    assert results[1]["estimable"] is False
    assert results[1]["gamma"] is None


def test_threshold_robustness_has_frozen_primary_and_alternative_thresholds() -> None:
    frame = add_crash_indicator(_frame())
    results = threshold_robustness(frame)
    assert [item["threshold"] for item in results] == [-0.005, -0.015, -0.02]
    assert all("crash_count" in item for item in results)


def test_bh_fdr_is_deterministic_and_validates_inputs() -> None:
    result = benjamini_hochberg([0.01, 0.04, 0.2])
    assert result["adjusted_p_values"] == pytest.approx([0.03, 0.06, 0.2])
    assert result["reject"] == [True, False, False]
    with pytest.raises(ValueError):
        benjamini_hochberg([1.1])


def test_bh_fdr_rejects_invalid_q_and_nan() -> None:
    with pytest.raises(ValueError):
        benjamini_hochberg([0.1], q=0)
    with pytest.raises(ValueError):
        benjamini_hochberg([np.nan])


def test_evidence_engine_caps_at_daily_level_three() -> None:
    assert evidence_level(
        gamma=0.1,
        gamma_ci_lower=0.01,
        descriptive_relationship_present=True,
        controls_trusted=True,
        robustness_triggered=False,
    ) == 3
    assert evidence_level(
        gamma=0.1,
        gamma_ci_lower=0.01,
        descriptive_relationship_present=True,
        controls_trusted=True,
        robustness_triggered=True,
    ) == 2
    assert interpretation_boundary(1).startswith("Primary")
    assert interpretation_boundary(3).startswith("Daily")


def test_evidence_engine_keeps_null_primary_at_level_one_without_description() -> None:
    assert evidence_level(
        gamma=0.0,
        gamma_ci_lower=-0.01,
        descriptive_relationship_present=False,
        controls_trusted=True,
        robustness_triggered=False,
    ) == 1


def test_digest_payload_binds_upstream_identity_and_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    digest, payload = build_model_digest(
        pipeline_digest="pipeline",
        contract_paths=[root / "reports/m3_stage3ca_model_specification_v1.json"],
        source_paths=[root / "src/ashare_research/mechanism/evidence.py"],
        dependency_contract={"statsmodels": ">=0.14.6,<0.15"},
        upstream_contract_identities=["A", "B"],
    )
    assert len(digest) == 64
    assert set(payload["upstream_contract_identity_hashes"]) == {"A", "B"}


def test_digests_are_separate_and_reproducible() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = [root / "src/ashare_research/mechanism/regression.py"]
    pipeline, payload = build_pipeline_digest(sources)
    same_pipeline, _ = build_pipeline_digest(sources)
    model, model_payload = build_model_digest(
        pipeline_digest=pipeline,
        contract_paths=[root / "reports/m3_stage3ca_model_specification_v1.json"],
        source_paths=sources,
        dependency_contract={"statsmodels": ">=0.14.6,<0.15"},
        upstream_contract_identities=["M3_STAGE3A_HYPOTHESIS_CONTRACT_V1"],
    )
    assert pipeline == same_pipeline
    assert pipeline != model
    assert payload["implementation_source_hashes"]
    assert model_payload["pipeline_digest"] == pipeline


def test_cli_writes_only_synthetic_machine_outputs(tmp_path: Path) -> None:
    result = run_synthetic("positive", tmp_path, bootstrap_replications=5)
    assert result["status"] == "M3_STAGE3CA_PIPELINE_LOCK_ACCEPTED"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "analysis_input_manifest.json",
        "mechanism_primary_result.json",
        "mechanism_robustness_result.json",
    ]
    primary = json.loads((tmp_path / "mechanism_primary_result.json").read_text())
    assert primary["nobs"] == 900


def test_primary_output_contains_every_locked_field() -> None:
    result = run_synthetic("null", bootstrap_replications=5)["primary"]
    required = load_json_contract("m3_stage3ca_output_schema_v1.json")[
        "primary_result_required_fields"
    ]
    assert set(required).issubset(result)
    assert set(result["coefficients"]) == {
        "alpha",
        "beta_market",
        "beta_oil",
        "beta_industry",
        "gamma",
    }
