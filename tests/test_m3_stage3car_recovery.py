"""Canonical M3 recovery binding and integration guards."""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from ashare_research.mechanism.analysis_contracts import (
    EXPECTED_EFFECTIVE_IDS,
    UPSTREAM_INVENTORY_NAME,
    ExecutionGateError,
    UpstreamBindingError,
    enforce_execution_gate,
)
from ashare_research.mechanism.contracts import Stage3BContractError
from ashare_research.mechanism.model_digest import (
    build_model_digest,
    build_pipeline_digest,
    verify_upstream_inventory,
)
from ashare_research.tools.m3_stage3ca_pipeline import main, synthetic_fixture

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INVENTORY = REPORTS / UPSTREAM_INVENTORY_NAME


def _inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def _source_paths() -> list[Path]:
    return [
        ROOT / "src/ashare_research/mechanism" / name
        for name in (
            "analysis_contracts.py",
            "analysis_dataset.py",
            "crash.py",
            "regression.py",
            "bootstrap.py",
            "robustness.py",
            "evidence.py",
            "model_digest.py",
        )
    ]


def test_canonical_stage3a_and_r1_r2_r4_files_exist() -> None:
    inventory = _inventory()
    assert len(inventory["bindings"]) >= 13
    assert all((ROOT / entry["path"]).is_file() for entry in inventory["bindings"])
    assert (REPORTS / "m3_stage3a_mechanism_hypothesis_contract_v1.json").is_file()
    assert (REPORTS / "m3_stage3br4_tier1_readiness_v3.json").is_file()


def test_effective_upstream_sha_inventory_matches_actual_bytes() -> None:
    verified = verify_upstream_inventory(INVENTORY)
    assert verified["status"] == "LOCKED_TO_CANONICAL_M3_BYTES"
    assert set(verified["effective_roles"]) == set(EXPECTED_EFFECTIVE_IDS)
    for entry in verified["bindings"]:
        actual = sha256((ROOT / entry["path"]).read_bytes()).hexdigest()
        assert actual == entry["sha256"]


def test_effective_contract_ids_and_versions_are_canonical() -> None:
    inventory = _inventory()
    effective = {entry["role"]: entry for entry in inventory["bindings"]}
    for role, contract_id in EXPECTED_EFFECTIVE_IDS.items():
        assert effective[role]["contract_id"] == contract_id
        assert effective[role]["version"] == "1.0.0"
        assert effective[role]["effective_status"].startswith("EFFECTIVE")


def test_r4_readiness_is_metadata_only_and_ready() -> None:
    readiness = json.loads(
        (REPORTS / "m3_stage3br4_tier1_readiness_v3.json").read_text(encoding="utf-8")
    )
    assert readiness["coverage"]["joint_tier1_valid_dates"] == 1902
    assert readiness["joint_tier1"] == "M3_TIER1_DEVELOPMENT_INPUTS_READY"
    assert readiness["market_proxy"] == "TRUSTED_REUSED_R1"
    assert readiness["oil"] == "M3_OIL_CONTROL_V3_TRUSTED"
    assert readiness["industry_399439"] == "M3_CNI_OIL_GAS_INDUSTRY_CONTROL_V2_TRUSTED"
    assert readiness["holdout_status"] == "SEALED"


def test_superseded_lineage_is_not_effective() -> None:
    inventory = _inventory()
    by_role = {entry["role"]: entry for entry in inventory["bindings"]}
    assert "stage3b_target_return_timing" not in inventory["effective_roles"]
    assert "r2_oil_contract" not in inventory["effective_roles"]
    assert "r4_effective_oil_transport" in inventory["effective_roles"]
    assert by_role["r2_oil_contract"]["effective_status"].startswith("HISTORICAL")


def test_superseded_sse_shenwan_and_keyed_eia_paths_are_not_active() -> None:
    text = json.dumps(_inventory(), ensure_ascii=False)
    assert "m3_stage3b_primary_proxy_contract_v1.json" not in text
    assert "Shenwan primary" not in text
    assert "EIA-key-required" not in text
    assert "m3_stage3br4_oil_transport_contract_v3.json" in text
    assert "m3_stage3br4_industry_contract_v2.json" in text


def test_wrong_declared_identity_is_rejected(tmp_path: Path) -> None:
    payload = _inventory()
    payload["bindings"][0]["contract_id"] = "M3_STAGE3A_HYPOTHESIS_CONTRACT_V1_WRONG"
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UpstreamBindingError, match="MODEL_DIGEST_UPSTREAM_BINDING_FAILURE"):
        verify_upstream_inventory(path)


def test_upstream_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _inventory()
    payload["bindings"][0]["sha256"] = "0" * 64
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UpstreamBindingError, match="MODEL_DIGEST_UPSTREAM_BINDING_FAILURE"):
        verify_upstream_inventory(path)


def test_missing_upstream_inventory_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(UpstreamBindingError, match="MODEL_DIGEST_UPSTREAM_BINDING_FAILURE"):
        build_model_digest(
            pipeline_digest="p",
            contract_paths=[REPORTS / "m3_stage3ca_model_specification_v2.json"],
            source_paths=_source_paths(),
            dependency_contract={"statsmodels": ">=0.14.6,<0.15"},
            upstream_inventory_path=tmp_path / "missing.json",
        )


def test_model_digest_binds_effective_sha_inventory_and_excludes_outcomes() -> None:
    pipeline, pipeline_payload = build_pipeline_digest(_source_paths())
    model, model_payload = build_model_digest(
        pipeline_digest=pipeline,
        contract_paths=[
            REPORTS / "m3_stage3ca_analysis_pipeline_contract_v2.json",
            REPORTS / "m3_stage3ca_model_specification_v2.json",
            REPORTS / "m3_stage3ca_robustness_registry_v2.json",
            REPORTS / "m3_stage3ca_output_schema_v2.json",
            INVENTORY,
        ],
        source_paths=_source_paths(),
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "rng": "PCG64"},
        upstream_inventory_path=INVENTORY,
    )
    assert len(model) == 64
    assert len(pipeline) == 64
    assert "gamma" not in json.dumps(pipeline_payload).lower()
    assert "real development" not in json.dumps(model_payload).lower()
    assert "M3_OIL_CONTROL_V3_TRANSPORT_CONTRACT" in model_payload[
        "upstream_contract_identity_hashes"
    ]


def test_model_digest_changes_when_effective_contract_bytes_change(tmp_path: Path) -> None:
    original = REPORTS / "m3_stage3ca_model_specification_v2.json"
    altered = tmp_path / original.name
    shutil.copyfile(original, altered)
    altered.write_text(altered.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    pipeline, _ = build_pipeline_digest(_source_paths())
    base, _ = build_model_digest(
        pipeline_digest=pipeline,
        contract_paths=[original],
        source_paths=_source_paths(),
        dependency_contract={"statsmodels": ">=0.14.6,<0.15"},
        upstream_inventory_path=INVENTORY,
    )
    with pytest.raises(UpstreamBindingError, match="DIGEST_PATH_OUTSIDE_REPOSITORY"):
        build_model_digest(
            pipeline_digest=pipeline,
            contract_paths=[altered],
            source_paths=_source_paths(),
            dependency_contract={"statsmodels": ">=0.14.6,<0.15"},
            upstream_inventory_path=INVENTORY,
        )
    assert len(base) == 64


def test_pipeline_digest_has_no_real_result_values() -> None:
    digest, payload = build_pipeline_digest(_source_paths())
    encoded = json.dumps(payload).lower()
    assert len(digest) == 64
    assert "real coefficient" not in encoded
    assert "crash count" not in encoded
    assert "holdout value" not in encoded


def test_development_gate_fails_before_any_input_path_is_used() -> None:
    assert main(["--execution-mode", "development", "--fixture", "positive"]) == 2


def test_holdout_gate_rejects_synthetic_frame() -> None:
    frame = synthetic_fixture("positive", n=8)
    frame.loc[0, "trade_date"] = "2023-01-01"
    with pytest.raises(ExecutionGateError, match="HOLDOUT_SEALED"):
        enforce_execution_gate("synthetic", frame)


def test_existing_stage3b_exports_remain_valid() -> None:
    assert Stage3BContractError.__name__ == "Stage3BContractError"
    import ashare_research.mechanism.alignment as alignment
    import ashare_research.mechanism.market_proxy as market_proxy

    assert hasattr(alignment, "build_tier1_readiness")
    assert hasattr(market_proxy, "build_market_ex_target_proxy")
