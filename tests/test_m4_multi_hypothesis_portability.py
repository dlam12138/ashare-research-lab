"""Focused M4 synthetic acceptance for multiple caller-supplied hypotheses.

The fingerprint deliberately covers only pre-execution identities.  It is therefore useful for
portable specification checks, while the complete execution envelope remains runtime-bound.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from test_m4_bounded_execution import _dates, _execution_inputs, _row_values
from test_m4_synthetic_pipeline_orchestrator import _config_document

from ashare_research.mechanism.contract_compiler import compile_hypothesis_config
from ashare_research.mechanism.hypothesis_config import parse_hypothesis_config
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.pipeline import (
    ORCHESTRATOR_VERSION,
    PIPELINE_SCHEMA_VERSION,
    PipelineError,
    SyntheticPipelineRequestV1,
    bound_inputs_identity_payload,
    run_synthetic_pipeline,
    validate_pipeline_result,
)
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
EXPECTED_FINGERPRINTS = {
    "SYNTH_DAILY_CONTROLLED_001": (
        "f7873a6fae2992f148ad3118fdbe139d418cdb2475205b586a80d12a225e1329"
    ),
    "SYNTH_DAILY_THRESHOLD_002": (
        "0a9e300b9ee2c5953b524d83fce7b6a473a7adb6ed1ae5887a3a9521ede151bb"
    ),
}


def _request(
    identifier: str,
    *,
    operator: str = "LTE",
    threshold: str,
    controls: list[str],
    bootstrap: bool,
):
    document = _config_document()
    document["hypothesis_id"] = identifier
    document["condition"] = {"operator": operator, "threshold": threshold}
    document["controls"] = controls
    document["bootstrap_policy"] = {
        "enabled": bootstrap,
        "method_id": "MOVING_BLOCK_BOOTSTRAP_V1" if bootstrap else "DISABLED",
        "replications": 1000,
        "seed": 42,
        "rng": "PCG64",
        "confidence_level": 0.95,
    }
    config = parse_hypothesis_config(document)
    contract = compile_hypothesis_config(config)
    plan = build_analysis_plan(contract)
    dates = _dates(24)
    control_roles = ("CONTROL_0001",) if len(controls) == 1 else ("CONTROL_0001", "CONTROL_0002")
    roles = ("TARGET_OUTCOME", "FACTOR", *control_roles)
    base = _execution_inputs(dates, _row_values(24, "noisy"), roles=roles)
    digest = canonical_digest(
        bound_inputs_identity_payload(contract, plan, base.domain, base.bindings, base.observations)
    )
    bound = replace(
        base,
        source_contract_digest=contract.contract_digest,
        plan_digest=plan.plan_digest,
        input_digest=digest,
    )
    return SyntheticPipelineRequestV1(
        PIPELINE_SCHEMA_VERSION, ORCHESTRATOR_VERSION, config, bound, None
    )


def _pre_execution_identity_payload(result) -> dict[str, str]:
    return {
        "contract_identity": result.contract.contract_digest,
        "plan_identity": result.plan.plan_digest,
        "dataset_identity": result.preparation.dataset_digest,
        "matrix_identity": result.matrix.matrix_digest,
    }


def _fingerprint(result) -> str:
    return canonical_digest(_pre_execution_identity_payload(result))


def _child_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT / "tests")))
    return env


def test_two_structurally_distinct_requests_are_valid_and_bound() -> None:
    first = _request(
        "SYNTH_DAILY_CONTROLLED_001",
        threshold="-0.0100",
        controls=["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"],
        bootstrap=True,
    )
    second = _request(
        "SYNTH_DAILY_THRESHOLD_002",
        operator="GTE",
        threshold="0.0100",
        controls=["SYNTH_CONTROL_1"],
        bootstrap=False,
    )
    first_result = run_synthetic_pipeline(request=first)
    second_result = run_synthetic_pipeline(request=second)
    validate_pipeline_result(first_result, first)
    validate_pipeline_result(second_result, second)

    assert first_result.contract.contract_digest != second_result.contract.contract_digest
    assert first_result.plan.plan_digest != second_result.plan.plan_digest
    assert first_result.preparation.dataset_digest != second_result.preparation.dataset_digest
    assert first_result.matrix.matrix_digest != second_result.matrix.matrix_digest
    first_plan = plan_to_canonical_dict(first_result.plan)
    second_plan = plan_to_canonical_dict(second_result.plan)
    assert {
        key: first_plan["transform_plan"]["condition"][key] for key in ("operator", "threshold")
    } == {"operator": "LTE", "threshold": "-0.01"}
    assert {
        key: second_plan["transform_plan"]["condition"][key] for key in ("operator", "threshold")
    } == {"operator": "GTE", "threshold": "0.01"}
    assert [x["series_id"] for x in second_plan["dataset_requirements"]["requirements"]] == [
        "SYNTH_TARGET_A",
        "SYNTH_FACTOR_A",
        "SYNTH_CONTROL_1",
    ]
    assert first_result.execution.bootstrap.enabled is True
    assert second_result.execution.bootstrap.enabled is False
    assert _fingerprint(first_result) == EXPECTED_FINGERPRINTS[first.config.hypothesis_id]
    assert _fingerprint(second_result) == EXPECTED_FINGERPRINTS[second.config.hypothesis_id]

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=replace(first, bound_inputs=second.bound_inputs))
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"


def test_pre_execution_fingerprints_reproduce_in_fresh_process_from_other_cwd() -> None:
    source = """import json
from test_m4_multi_hypothesis_portability import _fingerprint, _request
from ashare_research.mechanism.pipeline import run_synthetic_pipeline
items = []
cases = (
    ("SYNTH_DAILY_CONTROLLED_001", "LTE", "-0.0100",
     ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"], True),
    ("SYNTH_DAILY_THRESHOLD_002", "GTE", "0.0100",
     ["SYNTH_CONTROL_1"], False),
)
for identifier, operator, threshold, controls, bootstrap in cases:
    request = _request(identifier, operator=operator, threshold=threshold,
                       controls=controls, bootstrap=bootstrap)
    items.append(_fingerprint(run_synthetic_pipeline(request=request)))
print(json.dumps(items))
"""
    with tempfile.TemporaryDirectory() as cwd:
        completed = subprocess.run(
            [str(PYTHON), "-c", source],
            cwd=cwd,
            env=_child_environment(),
            capture_output=True,
            text=True,
            check=False,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == list(EXPECTED_FINGERPRINTS.values())


def test_fingerprint_excludes_execution_and_environment_fields() -> None:
    request = _request(
        "SYNTH_DAILY_CONTROLLED_001",
        threshold="-0.0100",
        controls=["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"],
        bootstrap=True,
    )
    result = run_synthetic_pipeline(request=request)
    identity_payload = _pre_execution_identity_payload(result)
    assert set(identity_payload) == {
        "contract_identity",
        "plan_identity",
        "dataset_identity",
        "matrix_identity",
    }
    assert all(
        key not in identity_payload
        for key in ("numeric_backend", "runtime_version", "environment", "wall_clock")
    )
    assert _fingerprint(result) != _fingerprint(
        run_synthetic_pipeline(
            request=_request(
                "SYNTH_DAILY_THRESHOLD_002",
                operator="GTE",
                threshold="0.0100",
                controls=["SYNTH_CONTROL_1"],
                bootstrap=False,
            )
        )
    )
