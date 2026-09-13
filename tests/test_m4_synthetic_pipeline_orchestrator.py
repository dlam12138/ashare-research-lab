"""Acceptance coverage for the M4 synthetic end-to-end pipeline orchestrator (AC-01..AC-30).

Normative sources (both frozen):

* ``docs/m4_synthetic_end_to_end_pipeline_design_v1.md``
* ``docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md``

Every test is synthetic-only.  Nothing here reads real data, a provider, the database, holdout,
literature or M4-B state; nothing writes to the worktree; no test asserts a research, significance,
economic-validity, tradability or A-share mechanism conclusion.

Reachability labels follow acceptance section 1.2:

* ``COMPOSED_ENTRY`` -- drive the public ``run_synthetic_pipeline`` request layer;
* ``ENVELOPE_LAYER`` -- drive the public ``validate_pipeline_result(forged_result, request)``;
* ``STAGE_LEVEL_PROBE`` -- explicitly a probe of an existing stage validator, *not* an assertion
  about the composed entry;
* ``INTERNAL_PROJECTION_PROBE`` -- explicitly a probe of an existing *private* projection helper
  (design section 6.3 forbids the orchestrator from calling it; the acceptance tests may, once
  annotated).

Frozen facts from the corrected design that these tests depend on:

* the S0 forbidden-content scan surface (corrected design section 7.1) is exactly the
  entry-available registry-record projection; the contract and plan do not exist until S1/S2, and
  V5 scans the whole canonical envelope (which embeds both projections verbatim);
* the replication gate (corrected design G11 / R17.2) is a resampling bound evaluated only when
  ``bootstrap_plan.enabled is True`` -- AC-28d states this explicitly;
* the measured successful-call ceilings (corrected design section 11.3, acceptance section 10.7)
  are ``build_analysis_plan <= 12``, ``materialize_analysis_dataset <= 11`` and ``_execute <= 3``;
  they are asserted against the measured profile and never relaxed.
"""

from __future__ import annotations

import ast
import dataclasses
import datetime
import decimal
import hashlib
import inspect
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from dataclasses import FrozenInstanceError, fields, replace
from functools import cache
from pathlib import Path
from typing import NamedTuple

import pytest
from test_m4_bounded_execution import POSITIVE_ROWS, _dates, _execution_inputs, _row_values
from test_m4_stage4a1_typed_contract import _document

import ashare_research.mechanism as mechanism_package
import ashare_research.mechanism.datasets as datasets_package
import ashare_research.mechanism.execution as execution_package
import ashare_research.mechanism.planning as planning_package
import ashare_research.mechanism.registry as registry_package
from ashare_research.mechanism import pipeline as pipeline_package
from ashare_research.mechanism.contract_compiler import (
    ContractCompilationError,
    FrozenMechanismContract,
    compile_hypothesis_config,
    compute_contract_digest,
    contract_to_canonical_dict,
    validate_contract,
)
from ashare_research.mechanism.datasets import (
    AdapterError,
    DatasetPreparationV1,
    ExpectedDomainV1,
    ObservationV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    validate_dataset,
)
from ashare_research.mechanism.datasets.synthetic import _input_payload
from ashare_research.mechanism.execution import (
    FORBIDDEN_KEYS,
    INTERPRETATION_BOUNDARY,
    ExecutionArtifactV1,
    ExecutionError,
    Float64ValueV1,
    execution_artifact_to_canonical_dict,
    prepare_registered_robustness_dispatch,
    serialize_execution_artifact,
    validate_execution_artifact,
)
from ashare_research.mechanism.hypothesis_config import (
    FrozenJSONList,
    FrozenJSONObject,
    HoldoutPolicy,
    canonical_decimal,
    parse_hypothesis_config,
)
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.pipeline import (
    ORCHESTRATOR_VERSION,
    PIPELINE_DIGEST_ALGORITHM,
    PIPELINE_SCHEMA_VERSION,
    PIPELINE_STAGE_SEQUENCE,
    PIPELINE_STATE,
    REGISTRY_BINDING_ABSENT,
    REGISTRY_BINDING_DIGEST_ALGORITHM,
    REGISTRY_BINDING_PRESENT,
    REQUIRED_STAGES_COMPLETED,
    SYNTHETIC_PIPELINE_MODE,
    PipelineError,
    PipelineMetadataV1,
    RegistryMetadataBindingV1,
    SyntheticPipelineRequestV1,
    SyntheticPipelineResultV1,
    bound_inputs_identity_payload,
    pipeline_result_to_canonical_dict,
    run_synthetic_pipeline,
    serialize_pipeline_result,
    validate_pipeline_result,
)
from ashare_research.mechanism.planning import (
    DeterministicAnalysisPlan,
    build_analysis_plan,
    plan_to_canonical_dict,
    validate_analysis_plan,
)
from ashare_research.mechanism.planning import matrix as matrix_module
from ashare_research.mechanism.planning.matrix import (
    MatrixError,
    MatrixPreparationV1,
    materialize_design_matrix,
    matrix_to_canonical_dict,
    validate_design_matrix,
)
from ashare_research.mechanism.registry import (
    RECORD_SCHEMA_VERSION,
    StateTransitionRequestV1,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    parse_hypothesis_record,
    serialize_hypothesis_record,
    transition_hypothesis_record,
    validate_hypothesis_record,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "src" / "ashare_research" / "mechanism" / "pipeline"
ORCHESTRATOR_PATH = PIPELINE_DIR / "orchestrator.py"
INIT_PATH = PIPELINE_DIR / "__init__.py"
ORCHESTRATOR_SOURCE = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
INIT_SOURCE = INIT_PATH.read_text(encoding="utf-8")
NEW_SOURCES = ((ORCHESTRATOR_PATH, ORCHESTRATOR_SOURCE), (INIT_PATH, INIT_SOURCE))
ORCHESTRATOR_MODULE = sys.modules["ashare_research.mechanism.pipeline.orchestrator"]

HYPOTHESIS_ID = "SYNTH_DAILY_CONTROLLED_001"
UNAVAILABLE = object()

FROZEN_PUBLIC_SYMBOLS = (
    "ORCHESTRATOR_VERSION",
    "PIPELINE_DIGEST_ALGORITHM",
    "PIPELINE_SCHEMA_VERSION",
    "PIPELINE_STAGE_SEQUENCE",
    "PIPELINE_STATE",
    "REGISTRY_BINDING_ABSENT",
    "REGISTRY_BINDING_DIGEST_ALGORITHM",
    "REGISTRY_BINDING_PRESENT",
    "REQUIRED_STAGES_COMPLETED",
    "SYNTHETIC_PIPELINE_MODE",
    "PipelineError",
    "PipelineMetadataV1",
    "RegistryMetadataBindingV1",
    "SyntheticPipelineRequestV1",
    "SyntheticPipelineResultV1",
    "bound_inputs_identity_payload",
    "pipeline_result_to_canonical_dict",
    "run_synthetic_pipeline",
    "serialize_pipeline_result",
    "validate_pipeline_result",
)

CLOSED_PIPELINE_CODES = frozenset(
    {
        "PIPELINE_REQUEST_TYPE_INVALID",
        "PIPELINE_VERSION_UNSUPPORTED",
        "PIPELINE_CONFIG_TYPE_INVALID",
        "PIPELINE_INPUT_TYPE_INVALID",
        "PIPELINE_REGISTRY_RECORD_INVALID",
        "PIPELINE_INPUT_SCHEMA_UNSUPPORTED",
        "PIPELINE_UNSUPPORTED_MODE",
        "PIPELINE_INPUT_BINDING_MISMATCH",
        "PIPELINE_QUALITY_NOT_READY",
        "PIPELINE_REPLICATIONS_EXCEED_LIMIT",
        "PIPELINE_REGISTRY_STATUS_NOT_BINDABLE",
        "PIPELINE_REGISTRY_IDENTITY_MISMATCH",
        "PIPELINE_DIGEST_MISMATCH",
        "PIPELINE_INTERNAL_SOURCE_UNMAPPED",
    }
)

FROZEN_PACKAGE_EXPORTS = {
    "mechanism": ("Stage3BContractError",),
    "planning": (
        "DeterministicAnalysisPlan",
        "build_analysis_plan",
        "compute_plan_digest",
        "plan_to_canonical_dict",
        "serialize_analysis_plan",
        "validate_analysis_plan",
    ),
    "datasets": (
        "AdapterError",
        "AuditCellV1",
        "AuditRowV1",
        "BoundDatasetInputsV1",
        "DatasetPreparationV1",
        "ExpectedDomainV1",
        "ObservationV1",
        "QualityReportV1",
        "RoleBindingV1",
        "dataset_to_canonical_dict",
        "materialize_analysis_dataset",
        "serialize_dataset",
        "validate_dataset",
    ),
    "execution": (
        "ALLOWED_ANALYSIS_METHODS",
        "ALLOWED_BOOTSTRAP_METHODS",
        "ALLOWED_BOOTSTRAP_RNGS",
        "ARTIFACT_SCHEMA_VERSION",
        "BLOCK_LENGTH_POLICY_ID",
        "BOOTSTRAP_MIN_REPLICATIONS",
        "BootstrapBlockV1",
        "CoefficientV1",
        "DISPOSITIONS",
        "ESTIMATOR_CONTRACT_ID",
        "EVIDENCE_DIRECTIONS",
        "EXECUTOR_VERSION",
        "EstimatorBlockV1",
        "EvidenceBlockV1",
        "ExecutionArtifactV1",
        "ExecutionError",
        "FORBIDDEN_KEYS",
        "Float64ValueV1",
        "INTERCEPT_TERM_ROLE",
        "INTERPRETATION_BOUNDARY",
        "MAX_ABS_CELL_DECIMAL",
        "MODEL_FAMILY",
        "MethodConfigurationV1",
        "NUMERIC_BACKEND",
        "PRIMARY_TERM_ROLE",
        "PROVENANCE_CLASS",
        "ProvenanceV1",
        "REASONS",
        "REQUIRED_EVIDENCE_STATISTIC_ROLES",
        "ROBUSTNESS_ARTIFACT_SCHEMA_VERSION",
        "RobustnessArtifactV1",
        "RobustnessDispatchV1",
        "RobustnessEntryDispatchV1",
        "SYNTHETIC_DATASET_MODE",
        "SampleBlockV1",
        "SourceChainV1",
        "StatisticValueV1",
        "TermRefV1",
        "execute_bounded_analysis",
        "execution_artifact_to_canonical_dict",
        "prepare_registered_robustness_dispatch",
        "robustness_artifact_to_canonical_dict",
        "serialize_execution_artifact",
        "serialize_robustness_artifact",
        "validate_execution_artifact",
        "validate_robustness_artifact",
    ),
    "registry": (
        "AShareDataFeasibility",
        "CITATION_MAX_LEN",
        "DIGEST_ALGORITHM_ID",
        "EvidenceKind",
        "ExpectedDirection",
        "FreeDataFeasibility",
        "HYPOTHESIS_ID_MAX_LEN",
        "HypothesisRecordV1",
        "HypothesisRegistrySnapshotV1",
        "HypothesisState",
        "INTERPRETATION_BOUNDARY",
        "LEGAL_TRANSITIONS",
        "LONG_TEXT_MAX_LEN",
        "MAX_HYPOTHESIS_VERSION",
        "MAX_IDENTITY_DIGEST_LEN",
        "MAX_REAL_DEMO_CANDIDATES",
        "MAX_RECORDS_PER_SNAPSHOT",
        "NOTES_MAX_LEN",
        "RECORD_SCHEMA_VERSION",
        "REGISTRY_VERSION",
        "RegistryError",
        "SHORT_TEXT_MAX_LEN",
        "SNAPSHOT_SCHEMA_VERSION",
        "SOURCE_VERSION_MAX_LEN",
        "SourceType",
        "StateTransitionRequestV1",
        "StateTransitionV1",
        "TARGET_HORIZON_MAX_LEN",
        "TERMINAL_STATES",
        "TransitionReasonCode",
        "UNKNOWN_SENTINEL",
        "build_hypothesis_registry_snapshot",
        "count_real_demo_candidates",
        "hypothesis_record_digest",
        "hypothesis_record_identity_digest",
        "hypothesis_record_to_canonical_dict",
        "parse_hypothesis_record",
        "registry_snapshot_to_canonical_dict",
        "serialize_hypothesis_record",
        "serialize_hypothesis_registry_snapshot",
        "transition_hypothesis_record",
        "validate_hypothesis_record",
        "validate_hypothesis_registry_snapshot",
        "validate_state_transition",
    ),
}

FROZEN_BLOBS = {
    "docs/m4_synthetic_end_to_end_pipeline_design_v1.md": (
        "6c2bd048f4f7e74bb4a8015b53c9a6e76fd483cd"
    ),
    "docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md": (
        "2393b4723ef8ac4aa883a34386b7618fb2cd9025"
    ),
    "docs/m4_bounded_execution_and_evidence_design_v1.md": (
        "9617f64360b6c3d9a6148ec08c25fa0209a0f9f4"
    ),
    "docs/m4_bounded_execution_acceptance_cases_v1.md": (
        "f857b9948c7f396a855a1e0f6506752f0065d667"
    ),
    "docs/m4b_hypothesis_registry_design_v1.md": (
        "6d9c292001c09a4b1a8e895e54619dc1e8826f3d"
    ),
    "docs/m4b_hypothesis_registry_acceptance_cases_v1.md": (
        "4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2"
    ),
    "reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json": (
        "dfd41eaafc099e7748499f72de7ddd800bf97f69"
    ),
}

BANNED_IMPORTS = frozenset(
    {
        "asyncio",
        "concurrent",
        "contextlib",
        "datetime",
        "duckdb",
        "glob",
        "http",
        "io",
        "logging",
        "multiprocessing",
        "numpy",
        "os",
        "pandas",
        "pathlib",
        "random",
        "requests",
        "scipy",
        "shutil",
        "socket",
        "statsmodels",
        "subprocess",
        "tempfile",
        "threading",
        "time",
        "urllib",
    }
)
BANNED_INTERNAL_MODULES = frozenset(
    {
        "analysis_contracts",
        "analysis_dataset",
        "bootstrap",
        "crash",
        "evidence",
        "regression",
        "robustness",
    }
)
ALLOWED_TOP_LEVEL_IMPORTS = frozenset(
    {"__future__", "dataclasses", "decimal", "hashlib", "json", "re", "typing"}
)

# Corrected design J4/R11 freezes **no** total ``record_bytes_hex`` ceiling and forbids any
# orchestrator-layer size gate: the existing M4-B schema caps individual text fields but not tuple
# cardinality, ``state_history`` length, ``authorization_ref`` or ``schema_version``.  The J4 test
# therefore measures one bounded *text skeleton* only, with a ceiling derived from the frozen
# per-field limits it actually fills (never presented as a schema guarantee).


class _Chain(NamedTuple):
    config: object
    contract: object
    plan: object
    bound_inputs: object
    request: object


def _code(exc: BaseException) -> str:
    """The only correct extraction (design section 8.6): ``getattr(exc, "code", str(exc))``."""

    return getattr(exc, "code", str(exc))


def _git_blob_hash(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _child_environment() -> dict:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")])
    return environment


def _cross_process_result_sha256() -> str:
    """Child-process entry: rebuild the fixture, run the pipeline and hash the envelope bytes."""

    return hashlib.sha256(serialize_pipeline_result(_result())).hexdigest()


def _run_child(source: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=_child_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _walk_keys(payload) -> list[str]:
    found: list[str] = []
    if type(payload) is dict:
        for key, value in payload.items():
            found.append(key)
            found.extend(_walk_keys(value))
    elif type(payload) is list:
        for item in payload:
            found.extend(_walk_keys(item))
    return found


def _config_document(
    *,
    bootstrap: dict | None = None,
    quality: dict | None = None,
    evidence: dict | None = None,
    registry: list | None = None,
    holdout: object = UNAVAILABLE,
) -> dict:
    document = _document()
    document["development"] = {"start": "2020-01-01", "end": "2022-12-31"}
    document["condition"] = {"operator": "LTE", "threshold": "-0.0100"}
    if bootstrap is not None:
        document["bootstrap_policy"].update(bootstrap)
    if quality is not None:
        document["data_quality_gates"].update(quality)
    if evidence is not None:
        document["evidence_rule"].update(evidence)
    if registry is not None:
        document["robustness_registry"] = registry
    if holdout is not UNAVAILABLE:
        document["holdout_policy"] = holdout
    return document


def _chain(
    *,
    document: dict | None = None,
    missing=None,
    rows: int = POSITIVE_ROWS,
    observations=None,
) -> _Chain:
    """Build the two-pass request fixture with the public identity-payload function."""

    document = _config_document() if document is None else document
    config = parse_hypothesis_config(document)
    contract = compile_hypothesis_config(config)
    plan = build_analysis_plan(contract)
    dates = _dates(rows)
    base = _execution_inputs(dates, _row_values(rows, "noisy"), missing=missing)
    if observations is not None:
        base = replace(base, observations=tuple(observations))
    digest = canonical_digest(
        bound_inputs_identity_payload(
            contract, plan, base.domain, base.bindings, base.observations
        )
    )
    bound_inputs = replace(
        base,
        source_contract_digest=contract.contract_digest,
        plan_digest=plan.plan_digest,
        input_digest=digest,
    )
    request = SyntheticPipelineRequestV1(
        PIPELINE_SCHEMA_VERSION,
        ORCHESTRATOR_VERSION,
        config,
        bound_inputs,
        None,
    )
    return _Chain(config, contract, plan, bound_inputs, request)


@cache
def _base_chain() -> _Chain:
    return _chain()


@cache
def _result() -> SyntheticPipelineResultV1:
    return run_synthetic_pipeline(request=_base_chain().request)


@cache
def _result_bytes() -> bytes:
    return serialize_pipeline_result(_result())


@cache
def _discovered_record():
    return _record()


@cache
def _bound_result() -> SyntheticPipelineResultV1:
    return run_synthetic_pipeline(request=_request(registry_record=_discovered_record()))


def _request(**changes) -> SyntheticPipelineRequestV1:
    return replace(_base_chain().request, **changes)


def _rehash_dataset(preparation):
    payload = dataset_to_canonical_dict(preparation)
    payload.pop("dataset_digest")
    return replace(preparation, dataset_digest=canonical_digest(payload))


def _rehash_matrix(matrix):
    return replace(matrix, matrix_digest=canonical_digest(matrix_to_canonical_dict(matrix)))


def _rehash_artifact(artifact):
    return replace(
        artifact, artifact_digest=canonical_digest(execution_artifact_to_canonical_dict(artifact))
    )


def _resign(result: SyntheticPipelineResultV1) -> SyntheticPipelineResultV1:
    return replace(
        result,
        metadata=replace(
            result.metadata,
            pipeline_digest=canonical_digest(pipeline_result_to_canonical_dict(result)),
        ),
    )


def _record_document(identifier: str = HYPOTHESIS_ID, version: int = 1, **changes) -> dict:
    document = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "hypothesis_id": identifier,
        "hypothesis_version": version,
        "source_type": "TEXTBOOK_THEORY",
        "source_title": "SYNTHETIC_EXAMPLE_TITLE",
        "authors_or_issuer": "SYNTHETIC_EXAMPLE_ISSUER",
        "source_date": "2000-01-01",
        "citation_or_source_identity": "SYNTHETIC_EXAMPLE_IDENTITY",
        "source_version": "SYNTHETIC_EXAMPLE_EDITION",
        "source_notes": "",
        "theory": "SYNTHETIC_EXAMPLE_THEORY",
        "original_market": "SYNTHETIC_EXAMPLE_MARKET",
        "original_sample": "SYNTHETIC_EXAMPLE_SAMPLE",
        "expected_direction": "POSITIVE",
        "candidate_signal": "SYNTHETIC_EXAMPLE_SIGNAL_TEXT",
        "target_horizon": "SYNTHETIC_EXAMPLE_HORIZON",
        "known_controls": ("SYNTHETIC_EXAMPLE_CONTROL",),
        "known_alternative_explanations": ("SYNTHETIC_EXAMPLE_ALT",),
        "known_replications": ("SYNTHETIC_EXAMPLE_REPLICATION",),
        "known_failures_or_decay": (),
        "a_share_data_feasibility": "FEASIBLE_FREE",
        "free_data_feasibility": "SUFFICIENT",
        "status": "DISCOVERED",
        "state_history": (
            {
                "ordinal": 1,
                "from_state": None,
                "to_state": "DISCOVERED",
                "reason_code": "SOURCE_REVIEWED",
                "authorization_ref": None,
                "evidence_kind": None,
            },
        ),
        "identity_digest": "0" * 64,
        "record_digest": "0" * 64,
    }
    document.update(changes)
    document["identity_digest"] = hypothesis_record_identity_digest(document)
    document["record_digest"] = hypothesis_record_digest(document)
    return document


def _record(**changes):
    return parse_hypothesis_record(_record_document(**changes))


def _advance(record, to_state: str, reason: str, *, auth=None, evidence=None):
    return transition_hypothesis_record(
        record,
        StateTransitionRequestV1(
            record.hypothesis_id,
            record.hypothesis_version,
            record.status,
            to_state,
            reason,
            auth,
            evidence,
        ),
    )


def _executed_record(target: str):
    """A legal record in one of the six execution-carrying states (claim-boundary fixture)."""

    record = _record()
    for state, reason, auth, evidence in (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED", None, None),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED", None, None),
        ("NOT_TESTED", "CANDIDATE_REGISTERED", None, None),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED", None, None),
        (
            "DEVELOPMENT_EXECUTED",
            "DEVELOPMENT_COMPLETED",
            "synthetic-development-ref",
            "FROZEN_DEVELOPMENT_EVIDENCE",
        ),
        (
            "ROBUSTNESS_EXECUTED",
            "ROBUSTNESS_COMPLETED",
            "synthetic-robustness-ref",
            "REGISTERED_ROBUSTNESS_EVIDENCE",
        ),
        ("OOS_EXECUTED", "OOS_COMPLETED", "synthetic-oos-ref", "INDEPENDENT_OOS_EVIDENCE"),
    ):
        if record.status == target:
            return record
        record = _advance(record, state, reason, auth=auth, evidence=evidence)
    if record.status == target:
        return record
    reason = {
        "NOT_ESTABLISHED": "EVIDENCE_NOT_SUPPORTED",
        "ESTABLISHED": "EVIDENCE_SUPPORTED",
        "INCONCLUSIVE": "EVIDENCE_INCONCLUSIVE",
    }[target]
    return _advance(record, target, reason)


def _imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif (
            isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0
        ):
            found.add(node.module.split(".")[0])
    return found


def _imported_from_modules(source: str) -> set[str]:
    return {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0
    }


# A standalone mutable-container name in a field annotation.  A bare substring test would falsely
# match immutable stage type names such as ``DatasetPreparationV1``.
MUTABLE_HINT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(dict|list|set|frozenset|bytearray|Dict|List|Set)\b"
)


def _raised_literals(source: str, name: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
            and node.args
        ):
            argument = node.args[0]
            assert isinstance(argument, ast.Constant) and isinstance(argument.value, str), argument
            found.add(argument.value)
    return found


# ==============================================================================================
# 2. Normal cases
# ==============================================================================================


def test_ac01_composed_entry_returns_complete_synthetic_envelope():
    """AC-01 (COMPOSED_ENTRY): the positive synthetic chain produces the full frozen envelope."""

    result = _result()
    assert type(result) is SyntheticPipelineResultV1
    assert result.metadata.pipeline_state == "SYNTHETIC_PIPELINE_COMPLETED"
    assert result.metadata.stages_completed == REQUIRED_STAGES_COMPLETED
    assert len(result.metadata.stages_completed) == 6
    assert result.metadata.orchestrator_version == "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1"
    assert result.metadata.pipeline_schema_version == "M4_SYNTHETIC_PIPELINE_RESULT_V1"
    assert type(result.contract) is FrozenMechanismContract
    assert type(result.plan) is DeterministicAnalysisPlan
    assert type(result.preparation) is DatasetPreparationV1
    assert type(result.matrix) is MatrixPreparationV1
    assert type(result.execution) is ExecutionArtifactV1
    assert result.preparation.status == "READY_SYNTHETIC"
    assert result.execution.statistics_computed is True
    assert result.execution.outcome_read is True
    assert result.execution.execution_authorized is False
    assert result.preparation.execution_authorized is False
    assert result.matrix.execution_authorized is False
    validate_pipeline_result(result, _base_chain().request)
    provenance = result.execution.provenance
    assert provenance.provenance_class == "SYNTHETIC_TEST_ONLY"
    assert provenance.synthetic_test_only is True
    assert provenance.real_data_used is False
    assert provenance.holdout_accessed is False


def test_ac02_envelope_immutability_and_exact_public_export_surface():
    """AC-02: deep immutability plus a machine-counted 20-symbol export surface."""

    result = _result()
    with pytest.raises(FrozenInstanceError):
        result.metadata.pipeline_state = "X"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.execution = None  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.metadata.registry_binding = None  # type: ignore[misc]

    assert type(result.metadata.stages_completed) is tuple
    if result.metadata.registry_binding is not None:
        assert type(result.metadata.registry_binding) is RegistryMetadataBindingV1
    assert result.metadata.registry_binding is None
    validate_pipeline_result(result, _base_chain().request)
    assert _bound_result().metadata.registry_binding is not None
    assert type(_bound_result().metadata.registry_binding) is RegistryMetadataBindingV1
    for frozen_type in (
        SyntheticPipelineRequestV1,
        SyntheticPipelineResultV1,
        PipelineMetadataV1,
        RegistryMetadataBindingV1,
    ):
        assert frozen_type.__dataclass_params__.frozen is True
        for field in fields(frozen_type):
            assert type(field.type) is str  # string annotations, never mutable containers
            assert MUTABLE_HINT_RE.search(str(field.type)) is None, (frozen_type, field)

    exports = tuple(pipeline_package.__all__)
    assert len(exports) == 20
    assert len(set(exports)) == 20
    assert set(exports) == set(FROZEN_PUBLIC_SYMBOLS)
    assert exports == FROZEN_PUBLIC_SYMBOLS
    assert [name for name in exports if name.startswith("PIPELINE_")] == [
        "PIPELINE_DIGEST_ALGORITHM",
        "PIPELINE_SCHEMA_VERSION",
        "PIPELINE_STAGE_SEQUENCE",
        "PIPELINE_STATE",
    ]

    observed = {
        "mechanism": mechanism_package,
        "planning": planning_package,
        "datasets": datasets_package,
        "execution": execution_package,
        "registry": registry_package,
    }
    for name, module in observed.items():
        assert tuple(sorted(module.__all__)) == FROZEN_PACKAGE_EXPORTS[name], name


def test_ac03_canonical_bytes_and_deterministic_repeat_runs(monkeypatch):
    """AC-03a-c: byte equality within one interpreter, order/cwd invariance; AC-03d premise.

    Sandbox note: a *dedicated* new directory under the platform temp root cannot be entered in
    this DSH sandbox (``chdir`` is denied on newly created subdirectories, and file creation there
    is denied as well -- recorded in the acceptance evidence).  The platform temp root itself is
    outside the repository and is enterable, so it is used as the external working directory; the
    host rerun may substitute a dedicated ``tmp_path``.
    """

    chain = _base_chain()
    first = _result_bytes()
    second = serialize_pipeline_result(run_synthetic_pipeline(request=chain.request))
    assert first == second

    # AC-03b (observation order): the adapter's ordering rule makes tuple order irrelevant.
    reversed_observations = replace(
        chain.bound_inputs, observations=tuple(reversed(chain.bound_inputs.observations))
    )
    permuted = run_synthetic_pipeline(request=_request(bound_inputs=reversed_observations))
    assert serialize_pipeline_result(permuted) == first

    # AC-03c (working directory): the platform temp root is outside the repository.
    external = Path(tempfile.gettempdir())
    assert not external.is_relative_to(ROOT)
    monkeypatch.chdir(external)
    elsewhere = run_synthetic_pipeline(request=chain.request)
    assert serialize_pipeline_result(elsewhere) == first

    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert b"\r" not in first
    parsed = json.loads(first.decode("utf-8"))
    assert (
        json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8") == first

    # AC-03 item 2 (cross process): a fresh interpreter rebuilds the same synthetic fixture and
    # produces the same envelope bytes, so the identity is not an in-process artifact.
    child_digest = _run_child(
        "from test_m4_synthetic_pipeline_orchestrator import _cross_process_result_sha256 as f;"
        "print(f())"
    )
    assert child_digest == hashlib.sha256(first).hexdigest()

    # AC-03d: byte equality is promised only inside one interpreter and one numpy build.  The
    # envelope pins the numpy version string verbatim, so a cross-version difference is a recorded
    # environment difference rather than a pipeline defect; no equality against another interpreter
    # is asserted here.
    import numpy

    assert _result().execution.method_configuration.numeric_runtime == numpy.__version__


def test_ac04_canonical_projection_reuses_every_existing_projection():
    """AC-04: six-layer canonical dictionary, existing projections, fresh containers."""

    result = _result()
    payload = pipeline_result_to_canonical_dict(result)
    assert set(payload) == {"metadata", "contract", "plan", "preparation", "matrix", "execution"}
    assert payload["contract"] == contract_to_canonical_dict(result.contract)
    assert payload["plan"] == plan_to_canonical_dict(result.plan)
    assert payload["preparation"] == dataset_to_canonical_dict(result.preparation)
    assert payload["matrix"] == matrix_to_canonical_dict(result.matrix)
    assert payload["execution"] == execution_artifact_to_canonical_dict(result.execution)
    assert "pipeline_digest" not in payload["metadata"]
    assert set(payload["metadata"]) == {
        "interpretation_boundary",
        "orchestrator_version",
        "pipeline_schema_version",
        "pipeline_state",
        "registry_binding",
        "registry_binding_digest",
        "stages_completed",
    }

    before = serialize_pipeline_result(result)
    payload["metadata"]["pipeline_state"] = "TAMPERED"
    payload["execution"]["estimator"] = None
    payload["contract"]["hypothesis_id"] = "TAMPERED"
    payload["plan"]["plan_digest"] = "0" * 64
    payload["preparation"]["status"] = "TAMPERED"
    payload["matrix"]["rows"].clear()
    assert serialize_pipeline_result(result) == before
    assert (
        pipeline_result_to_canonical_dict(result)["metadata"]["pipeline_state"]
        == "SYNTHETIC_PIPELINE_COMPLETED"
    )


# ==============================================================================================
# 3. Boundary cases
# ==============================================================================================


def test_ac05_minimum_materializable_domain_and_empty_domain_boundary():
    """AC-05 (COMPOSED_ENTRY): empty domain fails closed; minimal domain yields a stable error."""

    domain = _base_chain().bound_inputs.domain
    with pytest.raises(AdapterError) as empty:
        ExpectedDomainV1(
            "SYNTH_DOMAIN_A",
            "SYNTH_UNIVERSE_A",
            "SYNTHETIC_FIXED_UNIVERSE",
            "EXPLICIT_PIT",
            "SYNTH_TARGET_A",
            "SYNTHETIC_FIXED_IDENTITY",
            "2020-01-01",
            "2022-12-31",
            (),
            domain.calendar_evidence,
            domain.membership_evidence,
        )
    assert _code(empty.value) == "EMPTY_EXPECTED_DOMAIN"

    minimal = _chain(rows=3)
    with pytest.raises(ExecutionError) as caught:
        run_synthetic_pipeline(request=minimal.request)
    # Corrected AC-05: this three-row domain reaches the frozen S6 full-rank gate after adapter
    # and matrix construction, then propagates the existing ``ExecutionError("SINGULAR_DESIGN")``.
    # The composed entry returns no partial envelope and does not bypass the rank check.
    assert caught.value.code == "SINGULAR_DESIGN"
    assert type(caught.value) is not PipelineError
    assert isinstance(caught.value, ValueError)
    # The minimal domain still flows through the frozen chain: the contract is identical (the plan
    # does not depend on the synthetic calendar) and only the preparation/matrix shrink.
    assert minimal.contract.contract_digest == _base_chain().contract.contract_digest
    assert minimal.plan.plan_digest == _base_chain().plan.plan_digest
    assert minimal.bound_inputs.input_digest != _base_chain().bound_inputs.input_digest
    preparation = materialize_analysis_dataset(
        minimal.contract, minimal.plan, minimal.bound_inputs
    )
    assert preparation.quality.coverage_denominator == 3


def test_ac06_quality_rejection_stops_after_s4_with_disposition_word():
    """AC-06 (COMPOSED_ENTRY): REJECTED_QUALITY stops at S4 without repair or downgrade."""

    document = _config_document(quality={"coverage_gate": "1.0000"})
    chain = _chain(document=document, missing=("FACTOR", _dates(POSITIVE_ROWS)[0]))
    preparation = materialize_analysis_dataset(chain.contract, chain.plan, chain.bound_inputs)
    assert preparation.status == "REJECTED_QUALITY"
    assert preparation.complete_rows == ()
    assert preparation.quality.failure_disposition == "INCONCLUSIVE"

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=chain.request)
    assert caught.value.code == "PIPELINE_QUALITY_NOT_READY"
    assert str(caught.value) == (
        "preparation status is not READY_SYNTHETIC; "
        "data_quality_failure_disposition=INCONCLUSIVE"
    )
    assert _code(caught.value) != "DATASET_NOT_READY"
    assert _code(caught.value) != "DATA_QUALITY_REJECTED"

    # The orchestrator neither repairs nor relaxes the gate: the same input keeps failing, the
    # contract still declares the original gate, and no result object is ever returned.
    with pytest.raises(PipelineError):
        run_synthetic_pipeline(request=chain.request)
    assert chain.contract.data_quality_gates.coverage_gate == "1"
    assert chain.contract.data_quality_gates.missingness_policy == "FAIL_CLOSED"


def test_ac07_version_gates_short_circuit_before_any_contract_object():
    """AC-07 (COMPOSED_ENTRY): version constants are gates evaluated at S0."""

    broken_config = replace(_base_chain().config, hypothesis_id="SYNTHETIC WITH SPACES")
    for changes in (
        {"schema_version": "M4_SYNTHETIC_PIPELINE_RESULT_V2"},
        {"orchestrator_version": "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V2"},
        {"schema_version": 1},
        {"orchestrator_version": None},
    ):
        candidate = _request(**changes, config=broken_config)
        with pytest.raises(PipelineError) as caught:
            run_synthetic_pipeline(request=candidate)
        assert caught.value.code == "PIPELINE_VERSION_UNSUPPORTED"


def test_ac08_absent_registry_binding_is_a_first_class_explicit_form():
    """AC-08: explicit None is a first-class state; omitting the key is not expressible."""

    result = _result()
    assert result.metadata.registry_binding is None
    assert result.metadata.registry_binding_digest == canonical_digest(
        {"binding_state": REGISTRY_BINDING_ABSENT}
    )
    assert json.loads(_result_bytes().decode("utf-8"))["metadata"]["registry_binding"] is None
    validate_pipeline_result(result, _base_chain().request)

    with pytest.raises(TypeError):
        SyntheticPipelineRequestV1(  # type: ignore[call-arg]
            PIPELINE_SCHEMA_VERSION,
            ORCHESTRATOR_VERSION,
            _base_chain().config,
            _base_chain().bound_inputs,
        )


def test_ac09_bootstrap_two_states_come_only_from_the_plan():
    """AC-09 (COMPOSED_ENTRY): enabled and disabled bootstrap, seed never an envelope field."""

    enabled = _result()
    plan_payload = plan_to_canonical_dict(enabled.plan)
    assert enabled.execution.bootstrap.enabled is True
    assert enabled.execution.bootstrap.seed == plan_payload["bootstrap_plan"]["seed"]
    assert (
        enabled.execution.bootstrap.replications
        == plan_payload["bootstrap_plan"]["replications"]
    )

    disabled = run_synthetic_pipeline(
        request=_chain(
            document=_config_document(bootstrap={"enabled": False, "method_id": "DISABLED"})
        ).request
    )
    assert disabled.execution.bootstrap.enabled is False
    assert disabled.execution.bootstrap.primary_effect_lower is None
    assert disabled.execution.bootstrap.primary_effect_upper is None
    assert disabled.execution.bootstrap.seed is None

    # Design section 11.2: the orchestrator neither accepts, derives, overrides nor records a seed.
    # The envelope's own metadata layer carries no seed, the request type has no seed field, and the
    # only ``seed`` occurrences are the ones the existing plan/execution artifacts already contain
    # and that the orchestrator forwards verbatim (design 11.2's explicit exception).
    metadata_keys = {key.lower() for key in pipeline_result_to_canonical_dict(disabled)["metadata"]}
    assert "seed" not in metadata_keys
    assert "seed" not in {field.name for field in fields(SyntheticPipelineRequestV1)}
    canonical = pipeline_result_to_canonical_dict(disabled)
    assert "seed" in canonical["plan"]["bootstrap_plan"]
    assert canonical["execution"]["method_configuration"]["bootstrap_seed"] == (
        plan_to_canonical_dict(disabled.plan)["bootstrap_plan"]["seed"]
    )


# ==============================================================================================
# 4. Tamper cases
# ==============================================================================================


def test_ac10_stage_level_probe_contract_field_tampered_without_digest():
    """AC-10 (STAGE_LEVEL_PROBE): S1's own post-validator rejects a stale contract digest."""

    chain = _base_chain()
    tampered = replace(
        chain.contract,
        evidence_rule=replace(chain.contract.evidence_rule, rule_id="SYNTHETIC_RULE_B"),
    )
    with pytest.raises(ContractCompilationError) as caught:
        validate_contract(tampered)
    assert caught.value.code == "CONTRACT_DIGEST_MISMATCH"

    # Structural proof that the composed S1 cannot be bypassed: the request type exposes no
    # contract, plan, preparation, matrix or execution field.
    assert {field.name for field in fields(SyntheticPipelineRequestV1)} == {
        "schema_version",
        "orchestrator_version",
        "config",
        "bound_inputs",
        "registry_record",
    }


def test_ac11_stage_level_probe_self_consistent_forged_contract_fails_at_plan_layer():
    """AC-11 (STAGE_LEVEL_PROBE): a re-signed contract is rejected by the recompile comparison."""

    chain = _base_chain()
    forged = replace(
        chain.contract,
        evidence_rule=replace(chain.contract.evidence_rule, rule_id="SYNTHETIC_RULE_B"),
    )
    forged = replace(forged, contract_digest=compute_contract_digest(forged))
    validate_contract(forged)  # self-consistent: the first detection level passes

    with pytest.raises(ValueError) as caught:
        build_analysis_plan(forged)
    assert type(caught.value) is ValueError
    assert str(caught.value) in {"NON_CANONICAL_CONTRACT", "CONTRACT_DIGEST_MISMATCH"}
    assert hasattr(caught.value, "code") is False


def test_ac12a_stage_level_probe_plan_semantic_field_tampered_without_digest():
    """AC-12a (STAGE_LEVEL_PROBE): a semantic plan field changed while ``plan_digest`` is kept.

    Probe entry: the existing plan validator, directly.  The composed entry cannot receive a plan
    at all (AC-30), so this is stage-level regression evidence, not composed behaviour.
    """

    chain = _base_chain()
    design_items = tuple(
        (key, "OLS_ALTERNATE" if key == "model_family" else value)
        for key, value in chain.plan.design_plan.items
    )
    semantic_tamper = replace(chain.plan, design_plan=FrozenJSONObject(design_items))
    with pytest.raises(ValueError) as caught:
        validate_analysis_plan(semantic_tamper)
    assert type(caught.value) is ValueError
    assert str(caught.value) == "PLAN_DIGEST_MISMATCH"
    assert hasattr(caught.value, "code") is False

    # A structural plan field is rejected by its own earlier check (also a plan-layer stage code).
    with pytest.raises(ValueError) as caught:
        validate_analysis_plan(replace(chain.plan, plan_state="OTHER_STATE"))
    assert str(caught.value) == "INVALID_PLAN_STATE"


def test_ac12b_composed_entry_changed_config_cannot_follow_stale_bindings():
    """AC-12b (COMPOSED_ENTRY): the caller changes ``config``, so the compiled contract/plan move.

    ``bound_inputs`` still carries the old digests, and the input digest can never "follow" a
    changed plan.  Changing ``config`` changes ``contract_digest`` too, so G9 normally wins over
    the same-coded G10 -- both are ``PIPELINE_INPUT_BINDING_MISMATCH`` and the observable error is
    identical.  The caller *cannot* submit a tampered plan: "changed config plus rebound inputs" is
    simply a new, legal request.
    """

    chain = _base_chain()
    changed_config = replace(chain.config, hypothesis_id="SYNTH_DALLY_CONTROLLED_002")
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(config=changed_config))
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"


def test_ac12c_stage_level_probe_plan_source_contract_digest_tampered():
    """AC-12c (STAGE_LEVEL_PROBE): only ``plan.source_contract_digest`` is changed."""

    chain = _base_chain()
    with pytest.raises(ValueError) as caught:
        validate_analysis_plan(replace(chain.plan, source_contract_digest="0" * 64))
    assert str(caught.value) == "PLAN_DIGEST_MISMATCH"
    assert type(caught.value) is ValueError
    assert hasattr(caught.value, "code") is False


def test_ac13_bound_inputs_digest_and_observation_tampering():
    """AC-13a-g (COMPOSED_ENTRY): input identity is enforced at S3 and again at S4."""

    chain = _base_chain()
    bound = chain.bound_inputs

    for changes in (
        {"source_contract_digest": "f" * 64},
        {"plan_digest": "f" * 64},
    ):
        with pytest.raises(PipelineError) as caught:
            run_synthetic_pipeline(request=_request(bound_inputs=replace(bound, **changes)))
        assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"

    for mode in ("REAL", "UNKNOWN"):
        with pytest.raises(PipelineError) as caught:
            run_synthetic_pipeline(request=_request(bound_inputs=replace(bound, mode=mode)))
        assert caught.value.code == "PIPELINE_UNSUPPORTED_MODE"
        assert _code(caught.value) != "UNSUPPORTED_MODE"
        assert _code(caught.value) != "UNSUPPORTED_DATASET_MODE"

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(
                bound_inputs=replace(bound, schema_version="M4_BOUND_SYNTHETIC_DATASET_V2")
            )
        )
    assert caught.value.code == "PIPELINE_INPUT_SCHEMA_UNSUPPORTED"

    observations = list(bound.observations)
    index = next(position for position, item in enumerate(observations) if item.role == "FACTOR")
    observations[index] = replace(observations[index], value="-0.99")
    stale = replace(bound, observations=tuple(observations))
    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(request=_request(bound_inputs=stale))
    assert caught.value.code == "EVIDENCE_DIGEST_MISMATCH"

    refreshed = replace(
        stale,
        input_digest=canonical_digest(
            bound_inputs_identity_payload(
                chain.contract, chain.plan, stale.domain, stale.bindings, stale.observations
            )
        ),
    )
    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(request=_request(bound_inputs=refreshed))
    assert caught.value.code == "EVIDENCE_DIGEST_MISMATCH"

    forged_calendar = replace(bound.domain.calendar_evidence, evidence_digest="0" * 64)
    forged_domain = replace(bound.domain)
    object.__setattr__(forged_domain, "calendar_evidence", forged_calendar)
    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(request=_request(bound_inputs=replace(bound, domain=forged_domain)))
    assert caught.value.code == "EVIDENCE_DIGEST_MISMATCH"


def test_ac14_stage_level_probe_dataset_and_matrix_rehash_forgeries():
    """AC-14a-d (STAGE_LEVEL_PROBE): re-hashed dataset and matrix forgeries fail at S5."""

    result = _result()
    preparation = result.preparation
    matrix = result.matrix
    chain = _base_chain()

    # AC-14a: a *semantically different* preparation that is nevertheless fully self-consistent
    # (the frozen adapter produced it for a different legal synthetic input, and its own
    # ``dataset_digest`` verifies).  S5 still fails it, because the validator recomputes the
    # preparation from ``bound_inputs`` and compares bytes.
    other_inputs = _chain(rows=POSITIVE_ROWS - 1)
    other_preparation = materialize_analysis_dataset(
        other_inputs.contract, other_inputs.plan, other_inputs.bound_inputs
    )
    assert other_preparation.status == "READY_SYNTHETIC"
    assert len(other_preparation.complete_rows) != len(preparation.complete_rows)
    validate_dataset(
        other_preparation, other_inputs.contract, other_inputs.plan, other_inputs.bound_inputs
    )
    with pytest.raises(AdapterError) as caught:
        validate_design_matrix(
            matrix, other_preparation, result.contract, result.plan, chain.bound_inputs
        )
    assert caught.value.code == "IDENTITY_CONFLICT"

    # AC-14a (identity-link variant): every semantic field is kept, but a re-signed
    # ``dataset_digest`` covers a wrong ``input_digest``.
    rehashed = _rehash_dataset(replace(preparation, input_digest="f" * 64))
    with pytest.raises(AdapterError) as caught:
        validate_design_matrix(matrix, rehashed, result.contract, result.plan, chain.bound_inputs)
    assert caught.value.code == "IDENTITY_CONFLICT"

    stale = replace(preparation, input_digest="f" * 64)
    with pytest.raises(AdapterError) as caught:
        validate_design_matrix(matrix, stale, result.contract, result.plan, chain.bound_inputs)
    assert caught.value.code == "INPUT_DIGEST_MISMATCH"

    rows = list(matrix.rows)
    original = rows[0].cells[1]
    replacement = "0.5" if original != "0.5" else "0.25"
    rows[0] = replace(rows[0], cells=(rows[0].cells[0], replacement) + rows[0].cells[2:])
    forged_rows = tuple(rows)

    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(
            _rehash_matrix(replace(matrix, rows=forged_rows)),
            preparation,
            result.contract,
            result.plan,
            chain.bound_inputs,
        )
    assert caught.value.code == "IDENTITY_CONFLICT"

    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(
            replace(matrix, rows=forged_rows),
            preparation,
            result.contract,
            result.plan,
            chain.bound_inputs,
        )
    assert caught.value.code == "MATRIX_DIGEST_MISMATCH"


def _forged_coefficient_artifact():
    """The AC-15a/b forgery: one estimator coefficient replaced, digest untouched."""

    result = _result()
    forged_pair = Float64ValueV1(float.hex(0.123456789), canonical_decimal(repr(0.123456789)))
    coefficients = list(result.execution.estimator.coefficients)
    coefficients[0] = replace(coefficients[0], value=forged_pair)
    forged_estimator = replace(
        result.execution.estimator, coefficients=tuple(coefficients)
    )
    return replace(result.execution, estimator=forged_estimator)


def test_ac15a_stage_level_probe_artifact_coefficient_tampered_without_digest():
    """AC-15a (STAGE_LEVEL_PROBE): a changed coefficient with the kept digest fails V1."""

    result = _result()
    with pytest.raises(ExecutionError) as caught:
        validate_execution_artifact(
            _forged_coefficient_artifact(),
            result.matrix,
            result.preparation,
            result.contract,
            result.plan,
            _base_chain().bound_inputs,
        )
    assert caught.value.code == "ARTIFACT_DIGEST_MISMATCH"


def test_ac15b_stage_level_probe_resigned_artifact_fails_reexecution_comparison():
    """AC-15b (STAGE_LEVEL_PROBE): a self-consistent re-signed artifact still fails V3/V4."""

    result = _result()
    resigned = _rehash_artifact(_forged_coefficient_artifact())
    with pytest.raises(ExecutionError) as caught:
        validate_execution_artifact(
            resigned,
            result.matrix,
            result.preparation,
            result.contract,
            result.plan,
            _base_chain().bound_inputs,
        )
    assert caught.value.code == "IDENTITY_CONFLICT"


def test_ac15c_stage_level_probe_source_chain_tampered():
    """AC-15c (STAGE_LEVEL_PROBE): malformed and well-formed forged source-chain fields."""

    result = _result()
    bound = _base_chain().bound_inputs
    malformed = replace(
        result.execution, source_chain=replace(result.execution.source_chain, input_digest="nope")
    )
    with pytest.raises(ExecutionError) as caught:
        validate_execution_artifact(
            malformed, result.matrix, result.preparation, result.contract, result.plan, bound
        )
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"

    forged_chain = _rehash_artifact(
        replace(
            result.execution,
            source_chain=replace(result.execution.source_chain, matrix_digest="0" * 64),
        )
    )
    with pytest.raises(ExecutionError) as caught:
        validate_execution_artifact(
            forged_chain, result.matrix, result.preparation, result.contract, result.plan, bound
        )
    assert caught.value.code == "IDENTITY_CONFLICT"


def test_ac15d_stage_level_probe_provenance_real_data_flag_tampered():
    """AC-15d (STAGE_LEVEL_PROBE): ``real_data_used=True`` is structurally rejected."""

    result = _result()
    forged_provenance = _rehash_artifact(
        replace(
            result.execution,
            provenance=replace(result.execution.provenance, real_data_used=True),
        )
    )
    with pytest.raises(ExecutionError) as caught:
        validate_execution_artifact(
            forged_provenance,
            result.matrix,
            result.preparation,
            result.contract,
            result.plan,
            _base_chain().bound_inputs,
        )
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"


def test_ac15e_envelope_layer_pipeline_digest_tampered():
    """AC-15e (ENVELOPE_LAYER): the public validator recomputes L14 and rejects the forgery."""

    result = _result()
    tampered_digest = replace(result, metadata=replace(result.metadata, pipeline_digest="0" * 64))
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(tampered_digest, _base_chain().request)
    assert caught.value.code == "PIPELINE_DIGEST_MISMATCH"


def test_ac15f_envelope_layer_resigned_envelope_cannot_hide_upstream_tamper():
    """AC-15f (ENVELOPE_LAYER): a re-signed envelope digest cannot mask a forged preparation."""

    result = _result()
    forged_preparation = _rehash_dataset(replace(result.preparation, input_digest="f" * 64))
    resigned_envelope = _resign(replace(result, preparation=forged_preparation))
    assert resigned_envelope.metadata.pipeline_digest == canonical_digest(
        pipeline_result_to_canonical_dict(resigned_envelope)
    )
    with pytest.raises(AdapterError) as caught:
        validate_pipeline_result(resigned_envelope, _base_chain().request)
    assert caught.value.code == "IDENTITY_CONFLICT"


# ==============================================================================================
# 5. First-error order cases
# ==============================================================================================


def test_ac16_first_error_is_unique_and_follows_the_frozen_gate_order():
    """AC-16a-e (COMPOSED_ENTRY): one error per call, at the frozen gate position."""

    chain = _base_chain()
    bound = chain.bound_inputs

    # AC-16a: bad version, illegal config, unsupported mode -> the version gate wins at S0.
    illegal_config = replace(chain.config, hypothesis_id="SYNTHETIC WITH SPACES")
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(
                schema_version="WRONG",
                config=illegal_config,
                bound_inputs=replace(bound, mode="REAL"),
            )
        )
    assert caught.value.code == "PIPELINE_VERSION_UNSUPPORTED"

    # AC-16b: illegal config and unsupported mode -> the contract gate wins at S1.
    with pytest.raises(ContractCompilationError) as caught:
        run_synthetic_pipeline(
            request=_request(config=illegal_config, bound_inputs=replace(bound, mode="REAL"))
        )
    assert caught.value.code in {"INVALID_HYPOTHESIS_ID", "NON_CANONICALIZABLE_VALUE"}

    # AC-16c: unsupported mode and wrong plan digest -> G7 precedes G10.
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(bound_inputs=replace(bound, mode="REAL", plan_digest="f" * 64))
        )
    assert caught.value.code == "PIPELINE_UNSUPPORTED_MODE"

    # AC-16d: wrong plan digest and a later S4 input fault -> G10 precedes S4.  A non-canonical
    # decimal value cannot even be constructed (the frozen ``ObservationV1`` rejects it), so the S4
    # fault used here is a duplicate observation, which the adapter detects at the same stage and
    # after the same G10 gate.
    with pytest.raises(AdapterError) as cannot_construct:
        replace(bound.observations[0], value="-0.000")
    assert cannot_construct.value.code == "INVALID_VALUE"

    duplicated = tuple(bound.observations) + (bound.observations[0],)
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(
                bound_inputs=replace(bound, plan_digest="f" * 64, observations=duplicated)
            )
        )
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"

    # AC-16e: duplicate observation and insufficient coverage -> uniqueness precedes coverage.
    document = _config_document(quality={"coverage_gate": "1.0000"})
    duplicate_chain = _chain(document=document, observations=duplicated)
    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(request=duplicate_chain.request)
    assert caught.value.code == "DUPLICATE_OBSERVATION"


def test_ac17a_composed_entry_development_holdout_overlap_passes_through():
    """AC-17a (COMPOSED_ENTRY): the caller's own ``config`` can express the overlap fault.

    Corrected acceptance classification: this case is composed-entry reachable, not a stage-level
    probe, because the fault lives in the caller-supplied ``config``.
    """

    overlapping = replace(
        _base_chain().config,
        holdout_policy=HoldoutPolicy(
            start=datetime.date(2020, 1, 1),
            end=datetime.date(2023, 12, 31),
            policy_id="SYNTH_HOLDOUT_1",
            max_accepted_primary_executions=1,
        ),
    )
    with pytest.raises(ContractCompilationError) as caught:
        run_synthetic_pipeline(request=_request(config=overlapping))
    assert caught.value.code == "DEVELOPMENT_HOLDOUT_OVERLAP"
    assert type(caught.value) is ContractCompilationError


def test_ac17b_stage_level_probe_plan_layer_code_is_bare_value_error():
    """AC-17b (STAGE_LEVEL_PROBE): plan-layer codes are bare ``ValueError`` with no ``.code``."""

    with pytest.raises(ValueError) as caught:
        validate_analysis_plan(replace(_base_chain().plan, analysis_method_id="OTHER_METHOD"))
    assert type(caught.value) is ValueError
    assert str(caught.value) == "UNSUPPORTED_ANALYSIS_METHOD"
    assert hasattr(caught.value, "code") is False
    assert _code(caught.value) == "UNSUPPORTED_ANALYSIS_METHOD"


def test_ac17cd_composed_entry_adapter_codes_pass_through_unrewritten():
    """AC-17c/d (COMPOSED_ENTRY): adapter role-binding and input-digest codes are not rewritten."""

    chain = _base_chain()
    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(
            request=_request(
                bound_inputs=replace(
                    chain.bound_inputs, bindings=tuple(reversed(chain.bound_inputs.bindings))
                )
            )
        )
    assert caught.value.code == "ROLE_BINDING_MISMATCH"
    assert type(caught.value) is AdapterError

    with pytest.raises(AdapterError) as caught:
        run_synthetic_pipeline(
            request=_request(bound_inputs=replace(chain.bound_inputs, input_digest="0" * 64))
        )
    assert caught.value.code == "INPUT_DIGEST_MISMATCH"
    assert type(caught.value) is AdapterError


def test_ac17e_internal_projection_probe_plan_term_role_mismatch_is_downstream_only():
    """AC-17e (INTERNAL_PROJECTION_PROBE): the term-role defence exists but is pre-empted.

    Probe entry: the existing *private* projection helper ``_project_validated_matrix``.  Design
    section 6.3 forbids the orchestrator from calling private helpers; the acceptance suite may do
    so once annotated.  ``PLAN_TERM_ROLE_MISMATCH`` is composed-entry unreachable, so this case is
    never written as ``run_synthetic_pipeline`` behaviour.  Both facts are pinned:

    1. the internal projection probe does produce ``MatrixError("PLAN_TERM_ROLE_MISMATCH")``;
    2. the *public* stage validator is pre-empted earlier by
       ``AdapterError("CONTRACT_PLAN_MISMATCH")`` (design section 8.5.2).
    """

    chain = _base_chain()
    terms = []
    for key, value in chain.plan.design_plan.items:
        if key == "ordered_terms":
            terms.extend(dict(entry.items) for entry in value.items)
    terms[2]["term_role"], terms[3]["term_role"] = terms[3]["term_role"], terms[2]["term_role"]
    swapped_terms = FrozenJSONList(
        tuple(FrozenJSONObject(tuple(sorted(term.items()))) for term in terms)
    )
    forged_design = FrozenJSONObject(
        tuple(
            (key, swapped_terms if key == "ordered_terms" else value)
            for key, value in chain.plan.design_plan.items
        )
    )
    forged_plan = replace(chain.plan, design_plan=forged_design)

    with pytest.raises(MatrixError) as caught:
        matrix_module._project_validated_matrix(_result().preparation, forged_plan)
    assert caught.value.code == "PLAN_TERM_ROLE_MISMATCH"

    with pytest.raises(AdapterError) as caught:
        validate_design_matrix(
            _result().matrix,
            _result().preparation,
            chain.contract,
            forged_plan,
            chain.bound_inputs,
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"


def test_ac17f_stage_level_probe_robustness_dispatch_rejects_forbidden_content():
    """AC-17f (STAGE_LEVEL_PROBE): the off-chain robustness dispatch has its own content scan."""

    forbidden_registry = [
        {
            "robustness_id": "SYNTH_ROBUSTNESS_1",
            "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
            "parameters": {"trim": "A/B"},
        }
    ]
    stage_chain = _chain(document=_config_document(registry=forbidden_registry))
    preparation = materialize_analysis_dataset(
        stage_chain.contract, stage_chain.plan, stage_chain.bound_inputs
    )
    matrix = materialize_design_matrix(
        preparation, stage_chain.contract, stage_chain.plan, stage_chain.bound_inputs
    )
    with pytest.raises(ExecutionError) as caught:
        prepare_registered_robustness_dispatch(
            matrix,
            preparation,
            stage_chain.contract,
            stage_chain.plan,
            stage_chain.bound_inputs,
            ("SYNTH_ROBUSTNESS_1",),
        )
    assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"


def test_ac18_type_error_comes_only_from_the_signature_and_s0_gates():
    """AC-18a-h: the signature is the first rejection surface; S0 gates use stable codes."""

    request = _base_chain().request
    with pytest.raises(TypeError):
        run_synthetic_pipeline(config=_base_chain().config)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        run_synthetic_pipeline(request, _base_chain().bound_inputs)  # type: ignore[call-arg]
    for extra in ({"holdout": True}, {"seed": 7}, {"real_data": True}, {"path": "C:/x"}):
        with pytest.raises(TypeError):
            run_synthetic_pipeline(request=request, **extra)  # type: ignore[call-arg]

    signature = inspect.signature(run_synthetic_pipeline)
    parameters = list(signature.parameters.values())
    assert len(parameters) == 1
    assert parameters[0].name == "request"
    assert parameters[0].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[0].default is inspect.Parameter.empty
    assert not any(
        item.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        for item in parameters
    )

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=object())  # type: ignore[arg-type]
    assert type(caught.value) is PipelineError
    assert caught.value.code == "PIPELINE_REQUEST_TYPE_INVALID"


def test_ac19_no_partial_results_no_error_envelope_and_no_blanket_catch():
    """AC-19: failures are exceptions only; the mapping surface is closed and enumerable."""

    chain = _base_chain()
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(bound_inputs=replace(chain.bound_inputs, plan_digest="f" * 64))
        )
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"

    envelope_names = set(SyntheticPipelineResultV1.__dataclass_fields__)
    assert envelope_names == {
        "metadata",
        "contract",
        "plan",
        "preparation",
        "matrix",
        "execution",
    }
    assert not envelope_names & {"errors", "ok", "partial", "warnings", "status_code"}

    for path, source in NEW_SOURCES:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ExceptHandler):
                assert node.type is not None, path
                names = (
                    [node.type.id]
                    if isinstance(node.type, ast.Name)
                    else [item.id for item in node.type.elts]
                )
                assert "Exception" not in names, path
                assert "BaseException" not in names, path
        assert "contextlib" not in source
        assert "retry" not in source.lower()

    codes = _raised_literals(ORCHESTRATOR_SOURCE, "PipelineError")
    assert codes == CLOSED_PIPELINE_CODES
    assert _raised_literals(ORCHESTRATOR_SOURCE, "ExecutionError") == {"FORBIDDEN_ARTIFACT_CONTENT"}

    # M3 is pinned structurally: exactly one try block whose single handler is exactly the five
    # named bare-exception types, and whose raise preserves the original as ``__cause__``.
    try_blocks = [
        node for node in ast.walk(ast.parse(ORCHESTRATOR_SOURCE)) if isinstance(node, ast.Try)
    ]
    bare_exception_handlers = [
        node
        for node in try_blocks
        if len(node.handlers) == 1 and isinstance(node.handlers[0].type, ast.Tuple)
    ]
    assert len(bare_exception_handlers) == 1
    handler = bare_exception_handlers[0].handlers[0]
    assert [item.id for item in handler.type.elts] == [
        "KeyError",
        "AttributeError",
        "IndexError",
        "AssertionError",
        "ZeroDivisionError",
    ]
    raises = [node for node in ast.walk(handler) if isinstance(node, ast.Raise)]
    assert len(raises) == 1
    assert raises[0].cause is not None and raises[0].cause.id == "exc"
    assert raises[0].exc.args[0].value == "PIPELINE_INTERNAL_SOURCE_UNMAPPED"
    # The other two try blocks only translate the registry validator's own error type.
    registry_handlers = [
        node
        for block in try_blocks
        if block not in bare_exception_handlers
        for node in block.handlers
    ]
    assert len(registry_handlers) == 2
    assert {node.type.id for node in registry_handlers} == {"RegistryError"}


# ==============================================================================================
# 6. Structural prohibition cases
# ==============================================================================================


def test_ac20_holdout_real_data_provider_database_and_path_are_inexpressible():
    """AC-20: no field, import or loader can express holdout, real data, providers or paths."""

    request_fields = {field.name for field in fields(SyntheticPipelineRequestV1)}
    assert request_fields == {
        "schema_version",
        "orchestrator_version",
        "config",
        "bound_inputs",
        "registry_record",
    }
    forbidden_names = {
        "holdout",
        "holdout_window",
        "real_data",
        "provider",
        "database",
        "db",
        "path",
        "seed",
        "token",
        "kwargs",
    }
    assert not request_fields & forbidden_names
    result_fields = {field.name for field in fields(SyntheticPipelineResultV1)}
    assert result_fields == {"metadata", "contract", "plan", "preparation", "matrix", "execution"}

    for path, source in NEW_SOURCES:
        imported = _imported_modules(source)
        assert not imported & BANNED_IMPORTS, (path, imported & BANNED_IMPORTS)
        assert imported <= ALLOWED_TOP_LEVEL_IMPORTS | {"ashare_research"}
        for module in _imported_from_modules(source):
            assert module.rsplit(".", 1)[-1] not in BANNED_INTERNAL_MODULES, (path, module)
        assert "load_hypothesis_config" not in source
        assert "**kwargs" not in source


def test_ac21_no_external_io_no_ambient_mutation_and_no_output(monkeypatch, capsys, tmp_path):
    """AC-21: an isolated external cwd stays unchanged; IO probes and output remain silent."""

    chain = _base_chain()
    external = tmp_path.resolve()
    assert not external.is_relative_to(ROOT)

    # A fresh interpreter that imports only the pipeline package must not pull in a provider,
    # database or network client.  This is satisfiable and is the strongest available form of the
    # acceptance requirement; an in-process ``sys.modules`` absence assertion is not, because the
    # host test session itself preloads unrelated modules (for example ``duckdb`` arrives through
    # this repository's own conftest/legacy baseline guards, not through the pipeline).
    child_modules = _run_child(
        "import json, sys;"
        "import ashare_research.mechanism.pipeline;"
        "print(json.dumps(sorted(m for m in ('duckdb','requests','urllib.request') "
        "if m in sys.modules)))"
    )
    assert child_modules == "[]", child_modules

    monkeypatch.chdir(external)
    before_repo = sorted(item.name for item in ROOT.iterdir())
    before_mechanism = sorted(
        str(item.relative_to(ROOT)) for item in (ROOT / "src" / "ashare_research").rglob("*")
    )
    before_external = sorted(item.name for item in external.iterdir())
    before_modules = set(sys.modules)

    def forbidden(*args, **kwargs):
        raise AssertionError("external I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    produced = run_synthetic_pipeline(request=chain.request)
    assert serialize_pipeline_result(produced).endswith(b"\n")

    assert Path.cwd() == external
    assert sorted(item.name for item in ROOT.iterdir()) == before_repo
    package_files = (ROOT / "src" / "ashare_research").rglob("*")
    assert sorted(str(item.relative_to(ROOT)) for item in package_files) == before_mechanism
    assert sorted(item.name for item in external.iterdir()) == before_external

    # The call introduces none of the three, whatever the host had already loaded.
    assert not {"duckdb", "requests", "urllib.request"} & (set(sys.modules) - before_modules)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    for path, source in NEW_SOURCES:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                assert not (
                    isinstance(node.func, ast.Name) and node.func.id in {"open", "print"}
                ), (path, node.lineno)
                assert not (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in {"os", "pathlib", "socket", "sys"}
                ), (path, node.lineno)


def test_ac22_forbidden_keys_and_path_values_are_a_closed_set(monkeypatch):
    """AC-22a-g: 24-key closed vocabulary, exact lower-case matching, slash ban in values."""

    payload = pipeline_result_to_canonical_dict(_result())
    for key in _walk_keys(payload):
        assert key.lower() not in FORBIDDEN_KEYS
    assert len(FORBIDDEN_KEYS) == 24

    # Rule-level probe (not a composed call).  The frozen envelope dataclasses have fixed fields,
    # so an arbitrary forbidden key cannot be injected into ``metadata`` through the public API:
    # a *valid* envelope structurally cannot carry one.  The restated rule is therefore exercised
    # directly and drift-guarded against the frozen executor regex and key set below, while the
    # public surfaces are covered by AC-22d (composed entry, V5) and by AC-15e/f and AC-25
    # (``validate_pipeline_result``).
    checker = ORCHESTRATOR_MODULE._check_forbidden_content
    for key in ("path", "Path", "PATH", "cwd", "session", "best_result", "ranking"):
        with pytest.raises(ExecutionError) as caught:
            checker({"metadata": {key: "value"}})
        assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"
    checker({"metadata": {"my_path": "value", "pathological": "value"}})

    for value in ("AND/OR", "A/B", "x y/z", "M4-A/M4-B", "C:/x", "\\\\host\\share"):
        with pytest.raises(ExecutionError) as caught:
            checker({"metadata": {"note": value}})
        assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"
    for value in ("2015-03-16", "SYNTH_ROBUSTNESS_1", "A-B", "SYNTHETIC_TEST_ONLY: ok"):
        checker({"metadata": {"note": value}})

    # Drift guard: the restated rule must stay equivalent to the frozen executor rule it mirrors.
    execution_bounded = sys.modules["ashare_research.mechanism.execution.bounded"]
    assert (
        ORCHESTRATOR_MODULE._FORBIDDEN_PATH_RE.pattern
        == execution_bounded._ABSOLUTE_PATH_RE.pattern
    )
    assert ORCHESTRATOR_MODULE.FORBIDDEN_KEYS is execution_package.FORBIDDEN_KEYS
    assert ORCHESTRATOR_MODULE.FORBIDDEN_KEYS == execution_bounded.FORBIDDEN_KEYS

    # AC-22d (COMPOSED_ENTRY): a contract-declared robustness parameter with a forbidden key or a
    # slash-bearing value is rejected with the frozen existing code.  Corrected measurement note:
    # the frozen execution payload does NOT contain the robustness block, so the executor itself
    # succeeds; the composed rejection is the envelope content rule V5 *after* the whole S1-S6 chain
    # has run -- not an executor-internal scan.  The counters below pin exactly that timing, and the
    # off-chain dispatch entry is covered separately by AC-17f.
    dataset_module = sys.modules["ashare_research.mechanism.datasets.synthetic"]
    execution_module = sys.modules["ashare_research.mechanism.execution.bounded"]

    def counted(store, name, real):
        def wrapper(*args, **kwargs):
            store[name] += 1
            return real(*args, **kwargs)

        return wrapper

    for parameters in ({"trim": "A/B"}, {"path": "0.0100"}):
        registry = [
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": parameters,
            }
        ]
        request = _chain(document=_config_document(registry=registry)).request
        work = {"datasets": 0, "execute": 0, "entry": 0}
        with monkeypatch.context() as patcher:
            patcher.setattr(
                dataset_module,
                "materialize_analysis_dataset",
                counted(work, "datasets", dataset_module.materialize_analysis_dataset),
            )
            patcher.setattr(
                execution_module, "_execute", counted(work, "execute", execution_module._execute)
            )
            patcher.setattr(
                ORCHESTRATOR_MODULE,
                "execute_bounded_analysis",
                counted(work, "entry", ORCHESTRATOR_MODULE.execute_bounded_analysis),
            )
            with pytest.raises(ExecutionError) as caught:
                run_synthetic_pipeline(request=request)
        assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"
        # S1-S6 completed (the executor ran and its V3 re-execution ran) before V5 rejected.
        assert work["datasets"] >= 1, work
        assert work["entry"] == 1, work
        assert work["execute"] == 3, work

    # The non-matching sample passes untouched.
    clean_registry = [
        {
            "robustness_id": "SYNTH_ROBUSTNESS_1",
            "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
            "parameters": {"trim": "0.0100"},
        }
    ]
    produced = run_synthetic_pipeline(
        request=_chain(document=_config_document(registry=clean_registry)).request
    )
    assert produced.metadata.pipeline_state == PIPELINE_STATE
    assert produced.metadata.stages_completed == REQUIRED_STAGES_COMPLETED


def test_ac22g_no_seed_or_selection_field_exists_in_the_envelope():
    """AC-22g: no seed at the envelope-own layer; no selection/ranking field anywhere.

    Design section 11.2 records the explicit exception: ``plan.bootstrap_plan.seed`` is existing
    upstream artifact content that the orchestrator only forwards.  What must not exist is any seed
    the orchestrator itself accepts, derives or records, and any selection/ranking/tuning field.
    """

    canonical = pipeline_result_to_canonical_dict(_result())
    metadata_keys = {key.lower() for key in canonical["metadata"]}
    assert "seed" not in metadata_keys
    assert "seed" not in {field.name for field in fields(SyntheticPipelineRequestV1)}
    assert "seed" not in {field.name for field in fields(PipelineMetadataV1)}

    keys = {key.lower() for key in _walk_keys(canonical)}
    assert not keys & {
        "best",
        "best_result",
        "best_id",
        "selected",
        "selected_id",
        "winner",
        "aggregate",
        "ranking",
        "optimize",
        "tuned",
        "search",
    }


def test_ac23_no_robustness_dispatch_no_duplicate_statistics():
    """AC-23: the single statistics entry is the frozen executor; no second implementation."""

    statistical_names = {
        "mean",
        "median",
        "quantile",
        "percentile",
        "std",
        "var",
        "lstsq",
        "ols",
        "bootstrap",
    }
    for path, source in NEW_SOURCES:
        tree = ast.parse(source)
        assert "prepare_registered_robustness_dispatch" not in source, path
        imported = _imported_modules(source)
        assert not imported & {"numpy", "scipy", "statsmodels", "pandas"}, path
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not {name.lower() for name in defined} & statistical_names, (path, defined)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = node.func
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                assert name.lower() not in statistical_names, (path, node.lineno, name)

    called = {
        node.func.id
        for node in ast.walk(ast.parse(ORCHESTRATOR_SOURCE))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "execute_bounded_analysis" in called
    assert "prepare_registered_robustness_dispatch" not in called

    # No arithmetic that a duplicated statistical implementation would require: no true division,
    # floor division or matrix multiplication anywhere in the orchestrator.
    operators = {
        type(node.op).__name__
        for node in ast.walk(ast.parse(ORCHESTRATOR_SOURCE))
        if isinstance(node, ast.BinOp)
    }
    assert not operators & {"Div", "FloorDiv", "MatMult"}, operators

    # Design section 6.3: the orchestrator must not rewrite any artifact with dataclasses.replace.
    replace_calls = [
        node
        for node in ast.walk(ast.parse(ORCHESTRATOR_SOURCE))
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "replace")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "replace")
        )
    ]
    assert replace_calls == []
    dataclasses_imports = {
        alias.name
        for node in ast.walk(ast.parse(ORCHESTRATOR_SOURCE))
        if isinstance(node, ast.ImportFrom) and node.module == "dataclasses"
        for alias in node.names
    }
    assert dataclasses_imports == {"dataclass", "fields"}


# ==============================================================================================
# 7. Authorization cases
# ==============================================================================================


def test_ac24_synthetic_provenance_and_interpretation_boundary_are_verbatim():
    """AC-24: synthetic provenance, verbatim boundary literals, no upgrade vocabulary."""

    result = _result()
    assert result.execution.provenance.provenance_class == "SYNTHETIC_TEST_ONLY"
    assert result.execution.provenance.synthetic_test_only is True
    assert result.execution.provenance.real_data_used is False
    assert result.execution.provenance.holdout_accessed is False
    assert result.execution.evidence.interpretation_boundary == INTERPRETATION_BOUNDARY
    assert result.metadata.interpretation_boundary == INTERPRETATION_BOUNDARY
    assert result.metadata.interpretation_boundary == (
        "SYNTHETIC_TEST_ONLY: output of the frozen bounded executor on validated synthetic "
        "inputs. Not a research finding; not evidence of estimability, significance, economic "
        "validity or tradability; not an A-share mechanism result; not an authorization to "
        "execute on real data, on holdout data, or to enter M4-B."
    )
    # I6: only the execution-layer literal may be imported; the registry snapshot literal has a
    # different value and would itself trip the slash ban.
    assert "REGISTRY_METADATA_ONLY" not in ORCHESTRATOR_SOURCE
    registry_imports = [
        module for module in _imported_from_modules(ORCHESTRATOR_SOURCE) if "registry" in module
    ]
    assert registry_imports == ["ashare_research.mechanism.registry"]

    keys = {key.lower() for key in _walk_keys(pipeline_result_to_canonical_dict(result))}
    assert not keys & {
        "p_value",
        "pvalue",
        "significant",
        "significance",
        "established",
        "recommendation",
        "expected_return",
        "tradable",
        "tradability",
    }


def test_ac25_registry_metadata_binding_is_read_only_non_evidence_and_claim_bounded():
    """AC-25a-e: binding is metadata only; execution-state records are not bindable."""

    record = _discovered_record()
    before = (record.status, record.state_history, hypothesis_record_digest(record))

    bound = _bound_result()
    binding = bound.metadata.registry_binding
    assert binding.binding_state == REGISTRY_BINDING_PRESENT
    assert binding.record_status == "DISCOVERED"
    assert binding.record_bytes_hex == serialize_hypothesis_record(record).hex()
    assert bytes.fromhex(binding.record_bytes_hex) == serialize_hypothesis_record(record)
    # AC-25 item 7 (corrected design J4/R11): the encoded length is exactly twice the *concrete*
    # record's bytes, no pipeline-layer size gate exists, and the M4-B schema has no uniform total
    # ceiling (uncapped tuples, ``state_history``, ``authorization_ref``, ``schema_version``).
    assert len(binding.record_bytes_hex) == 2 * len(serialize_hypothesis_record(record))
    assert "MAX_RECORD_BYTES" not in ORCHESTRATOR_SOURCE
    assert bound.metadata.registry_binding_digest == canonical_digest(
        {
            "binding_state": REGISTRY_BINDING_PRESENT,
            "record_digest": hypothesis_record_digest(record),
            "record_identity_digest": hypothesis_record_identity_digest(record),
            "record_status": record.status,
            "record_hypothesis_id": record.hypothesis_id,
            "record_hypothesis_version": record.hypothesis_version,
            "record_bytes_sha256": hashlib.sha256(serialize_hypothesis_record(record)).hexdigest(),
        }
    )
    validate_pipeline_result(bound, _request(registry_record=record))

    assert (record.status, record.state_history, hypothesis_record_digest(record)) == before
    assert serialize_execution_artifact(bound.execution) == serialize_execution_artifact(
        _result().execution
    )
    assert bound.metadata.pipeline_state == _result().metadata.pipeline_state
    assert bound.metadata.stages_completed == _result().metadata.stages_completed
    assert bound.execution.execution_authorized is False

    for forbidden_call in (
        "transition_hypothesis_record",
        "validate_state_transition",
        "build_hypothesis_registry_snapshot",
    ):
        assert forbidden_call not in ORCHESTRATOR_SOURCE

    # AC-25b
    mismatched = _record(identifier="synthetic.other")
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(registry_record=mismatched))
    assert caught.value.code == "PIPELINE_REGISTRY_IDENTITY_MISMATCH"

    # AC-25c
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(registry_record=object()))
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"
    stale_record = replace(_discovered_record(), record_digest="0" * 64)
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(registry_record=stale_record))
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"

    # AC-25d: legal records in the six execution-carrying states are not bindable.
    for state in (
        "DEVELOPMENT_EXECUTED",
        "ROBUSTNESS_EXECUTED",
        "OOS_EXECUTED",
        "NOT_ESTABLISHED",
        "ESTABLISHED",
        "INCONCLUSIVE",
    ):
        executed = _executed_record(state)
        validate_hypothesis_record(executed)
        assert executed.status == state
        with pytest.raises(PipelineError) as caught:
            run_synthetic_pipeline(request=_request(registry_record=executed))
        assert caught.value.code == "PIPELINE_REGISTRY_STATUS_NOT_BINDABLE"

    # Design R15: G12/G13 are evaluated at S7, not at S0.  Combining a bindable-but-wrong-identity
    # record or a non-bindable record with an earlier S3 binding fault must report the S3 fault,
    # which an S0-time registry identity/status check could not.
    bad_plan_binding = replace(_base_chain().bound_inputs, plan_digest="f" * 64)
    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(
                registry_record=_executed_record("ESTABLISHED"),
                bound_inputs=bad_plan_binding,
            )
        )
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(
            request=_request(
                registry_record=_record(identifier="synthetic.other"),
                bound_inputs=bad_plan_binding,
            )
        )
    assert caught.value.code == "PIPELINE_INPUT_BINDING_MISMATCH"

    # RB1: the binding state is a closed two-word vocabulary.
    bogus_state = replace(
        binding,
        binding_state="M4B_REGISTRY_METADATA_BOUND_READ_WRITE",
    )
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(
            _resign(replace(bound, metadata=replace(bound.metadata, registry_binding=bogus_state))),
            _request(registry_record=record),
        )
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"

    # AC-25e: a pre-execution status binds and is copied read-only.
    not_tested = _executed_record("NOT_TESTED")
    assert not_tested.status == "NOT_TESTED"
    succeeded = run_synthetic_pipeline(request=_request(registry_record=not_tested))
    assert succeeded.metadata.registry_binding.record_status == "NOT_TESTED"
    assert succeeded.metadata.pipeline_state == PIPELINE_STATE
    assert serialize_execution_artifact(succeeded.execution) == serialize_execution_artifact(
        _result().execution
    )


def test_ac26_readiness_is_not_authorization():
    """AC-26: readiness never becomes an authorization anywhere in the envelope."""

    result = _result()
    assert result.preparation.execution_authorized is False
    assert result.matrix.execution_authorized is False
    assert result.execution.execution_authorized is False
    assert result.metadata.pipeline_state == "SYNTHETIC_PIPELINE_COMPLETED"
    assert result.metadata.pipeline_state not in {
        "ESTABLISHED",
        "AUTHORIZED",
        "READY_FOR_REAL_DATA",
    }
    keys = {key.lower() for key in _walk_keys(pipeline_result_to_canonical_dict(result))}
    assert not keys & {"authorized", "authorization", "authorized_real_data"}


# ==============================================================================================
# 8. Regression cases
# ==============================================================================================


def test_ac27_frozen_blobs_are_byte_identical_and_new_sources_are_present():
    """AC-27: the seven protected blobs keep their recorded identity; only two files are new."""

    for relative, expected in FROZEN_BLOBS.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert _git_blob_hash(path) == expected, relative

    assert ORCHESTRATOR_PATH.is_file()
    assert INIT_PATH.is_file()
    assert tuple(
        sorted(path.name for path in PIPELINE_DIR.iterdir() if path.is_file())
    ) == ("__init__.py", "orchestrator.py")
    for path, source in NEW_SOURCES:
        assert path.read_bytes().endswith(b"\n"), path
        assert "\r" not in source, path
        assert "<<<<<<<" not in source and ">>>>>>>" not in source, path
        assert all(line == line.rstrip() for line in source.splitlines()), path


def test_ac27b_stage_bindings_and_domain_digest_remain_the_frozen_ones():
    """AC-27: the five-stage binding chain is unchanged and independently reproducible."""

    result = _result()
    chain = _base_chain()
    assert result.plan.source_contract_digest == result.contract.contract_digest
    assert result.matrix.plan_digest == result.plan.plan_digest
    assert result.matrix.input_digest == chain.bound_inputs.input_digest
    assert result.execution.source_chain.matrix_digest == result.matrix.matrix_digest
    domain = chain.bound_inputs.domain
    assert result.preparation.domain_digest == canonical_digest(
        {
            "domain_id": domain.domain_id,
            "universe_id": domain.universe_id,
            "membership_policy": domain.membership_policy,
            "pit_policy": domain.pit_policy,
            "target_series_id": domain.target_series_id,
            "identity_policy": domain.identity_policy,
            "development_start": domain.development_start,
            "development_end": domain.development_end,
            "expected_dates": list(domain.expected_dates),
            "calendar_evidence": domain.calendar_evidence.as_dict(),
            "membership_evidence": domain.membership_evidence.as_dict(),
        }
    )


# ==============================================================================================
# 9. Resource and determinism cases
# ==============================================================================================


def test_ac28_replication_resource_gate(monkeypatch):
    """AC-28a-d: the replication bound is a pipeline-layer policy evaluated inside S3."""

    # AC-28a: one replication passes the pipeline gate and fails in the frozen executor.
    with pytest.raises(ExecutionError) as caught:
        run_synthetic_pipeline(
            request=_chain(
                document=_config_document(bootstrap={"replications": 1})
            ).request
        )
    assert caught.value.code == "INSUFFICIENT_REPLICATIONS"

    # AC-28b: a legal replication count succeeds and the declared value is forwarded.
    legal = run_synthetic_pipeline(
        request=_chain(document=_config_document(bootstrap={"replications": 2})).request
    )
    assert legal.execution.bootstrap.replications == 2

    # AC-28c: above the absolute ceiling the call stops inside S3 with no downstream work at all -
    # no dataset materialization, no execution, hence no resampling ("先拒绝，再计算").
    dataset_module = sys.modules["ashare_research.mechanism.datasets.synthetic"]
    execution_module = sys.modules["ashare_research.mechanism.execution.bounded"]
    work = {"datasets": 0, "execute": 0, "entry": 0}

    def counted(name, real):
        def wrapper(*args, **kwargs):
            work[name] += 1
            return real(*args, **kwargs)

        return wrapper

    with monkeypatch.context() as patcher:
        patcher.setattr(
            dataset_module,
            "materialize_analysis_dataset",
            counted("datasets", dataset_module.materialize_analysis_dataset),
        )
        patcher.setattr(
            ORCHESTRATOR_MODULE,
            "materialize_analysis_dataset",
            counted("datasets", ORCHESTRATOR_MODULE.materialize_analysis_dataset),
        )
        patcher.setattr(
            execution_module, "_execute", counted("execute", execution_module._execute)
        )
        patcher.setattr(
            ORCHESTRATOR_MODULE,
            "execute_bounded_analysis",
            counted("entry", ORCHESTRATOR_MODULE.execute_bounded_analysis),
        )
        over_limit = _chain(
            document=_config_document(bootstrap={"replications": 10**9})
        )
        with pytest.raises(PipelineError) as caught:
            run_synthetic_pipeline(request=over_limit.request)
        assert caught.value.code == "PIPELINE_REPLICATIONS_EXCEED_LIMIT"
    assert work == {"datasets": 0, "execute": 0, "entry": 0}, work

    # AC-28d: with bootstrap disabled the gate does not apply, so even a huge declared count runs
    # (the executor establishes no generator).  This follows the explicit AC-28d wording
    # "上界门不适用", which overrides a literal reading of G11: the bound is a *resampling* bound.
    disabled = run_synthetic_pipeline(
        request=_chain(
            document=_config_document(
                bootstrap={"enabled": False, "method_id": "DISABLED", "replications": 10**9}
            )
        ).request
    )
    assert disabled.execution.bootstrap.enabled is False
    assert disabled.execution.bootstrap.replications is None

    # The bound is a pipeline-layer policy: it is not part of the frozen export surface.
    assert "MAX_BOOTSTRAP_REPLICATIONS" not in pipeline_package.__all__
    assert "MAX_BOOTSTRAP_REPLICATIONS = 100000" in ORCHESTRATOR_SOURCE


def test_ac29_decimal_context_is_fixed_locally_and_never_written_globally():
    """AC-29a-d: ambient precision cannot change bytes; the host context is left untouched."""

    baseline = _result_bytes()
    context = decimal.getcontext()
    saved_prec = context.prec
    try:
        for precision in (28, 8, 4):
            context.prec = precision
            assert (
                serialize_pipeline_result(run_synthetic_pipeline(request=_base_chain().request))
                == baseline
            )
    finally:
        context.prec = saved_prec
    assert context.prec == 28

    def snapshot():
        current = decimal.getcontext()
        return (current.prec, dict(current.traps), dict(current.flags))

    context.prec = 8
    try:
        before = snapshot()
        run_synthetic_pipeline(request=_base_chain().request)
        assert snapshot() == before

        before = snapshot()
        with pytest.raises(PipelineError):
            run_synthetic_pipeline(
                request=_request(
                    bound_inputs=replace(
                        _base_chain().bound_inputs, source_contract_digest="0" * 64
                    )
                )
            )
        assert snapshot() == before
        assert decimal.getcontext().prec == 8
    finally:
        context.prec = saved_prec

    # C5 fixes only ``prec``; the byte-equality promise assumes the host keeps the default traps.
    assert "DECIMAL_CONTEXT_PRECISION = 28" in ORCHESTRATOR_SOURCE
    assert "localcontext" in ORCHESTRATOR_SOURCE
    assert "getcontext" not in ORCHESTRATOR_SOURCE
    assert "setcontext" not in ORCHESTRATOR_SOURCE


def test_bounded_resource_profile_is_constant_and_within_frozen_ceilings(monkeypatch):
    """Design section 11.3 / acceptance section 10.7: measured counts against frozen ceilings.

    The corrected design freezes the **measured** successful-call ceilings
    ``build_analysis_plan <= 12``, ``materialize_analysis_dataset <= 11`` and ``_execute <= 3``
    (they include the chained recomputation of the existing validators plus the extra S7
    ``validate_pipeline_result`` V2 pass).  Acceptance section 10.7 requires the implementation to
    assert each ``<=`` bound and record the measured counts; the bounds may not be relaxed, so the
    exact measured profile is also pinned here.
    """

    dataset_module = sys.modules["ashare_research.mechanism.datasets.synthetic"]
    execution_module = sys.modules["ashare_research.mechanism.execution.bounded"]
    counters = {
        "datasets_adapter": 0,
        "datasets_direct": 0,
        "plans_adapter": 0,
        "plans_direct": 0,
        "execute": 0,
        "entry": 0,
    }

    def counted(name, real):
        def wrapper(*args, **kwargs):
            counters[name] += 1
            return real(*args, **kwargs)

        return wrapper

    # Count both call sites: the adapter's internal reference (used by the chained recomputation)
    # and the orchestrator's own direct reference (S2/S4), so the measured profile excludes nothing.
    monkeypatch.setattr(
        dataset_module,
        "materialize_analysis_dataset",
        counted("datasets_adapter", dataset_module.materialize_analysis_dataset),
    )
    monkeypatch.setattr(
        ORCHESTRATOR_MODULE,
        "materialize_analysis_dataset",
        counted("datasets_direct", ORCHESTRATOR_MODULE.materialize_analysis_dataset),
    )
    monkeypatch.setattr(
        dataset_module,
        "build_analysis_plan",
        counted("plans_adapter", dataset_module.build_analysis_plan),
    )
    monkeypatch.setattr(
        ORCHESTRATOR_MODULE,
        "build_analysis_plan",
        counted("plans_direct", ORCHESTRATOR_MODULE.build_analysis_plan),
    )
    monkeypatch.setattr(execution_module, "_execute", counted("execute", execution_module._execute))
    monkeypatch.setattr(
        ORCHESTRATOR_MODULE,
        "execute_bounded_analysis",
        counted("entry", ORCHESTRATOR_MODULE.execute_bounded_analysis),
    )

    run_synthetic_pipeline(request=_base_chain().request)
    measured = dict(counters)

    for key in counters:
        counters[key] = 0
    run_synthetic_pipeline(request=_base_chain().request)
    assert dict(counters) == measured

    # MEASURED_CALL_PROFILE, recorded from this implementation and checked against the corrected
    # design ceilings (design section 11.3):
    #   execute_bounded_analysis (entry)            = 1
    #   _execute                                    = 3  (S6 + validate V3 + validate_pipeline V3)
    #   materialize_analysis_dataset (adapter+own)  = 11 (ceiling <= 11)
    #   build_analysis_plan (adapter + own S2 call) = 12 (ceiling <= 12)
    assert measured == {
        "datasets_adapter": 10,
        "datasets_direct": 1,
        "plans_adapter": 11,
        "plans_direct": 1,
        "execute": 3,
        "entry": 1,
    }
    total_datasets = measured["datasets_adapter"] + measured["datasets_direct"]
    total_plans = measured["plans_adapter"] + measured["plans_direct"]
    assert total_plans <= 12, (total_plans, "design section 11.3 ceiling")
    assert total_datasets <= 11, (total_datasets, "design section 11.3 ceiling")
    assert measured["execute"] <= 3, (measured["execute"], "design section 11.3 ceiling")
    assert total_datasets == 11 and total_plans == 12


# ==============================================================================================
# 10. Structural prohibition: upstream objects cannot be submitted
# ==============================================================================================


def test_ac30_upstream_objects_are_not_submittable():
    """AC-30: forged upstream objects are inexpressible at the request type level."""

    request_fields = {field.name for field in fields(SyntheticPipelineRequestV1)}
    assert request_fields == {
        "schema_version",
        "orchestrator_version",
        "config",
        "bound_inputs",
        "registry_record",
    }
    for forbidden in ("contract", "plan", "preparation", "matrix", "execution", "result"):
        assert forbidden not in request_fields

    signature = inspect.signature(run_synthetic_pipeline)
    assert not any(
        item.kind is inspect.Parameter.VAR_KEYWORD for item in signature.parameters.values()
    )
    request_signature = inspect.signature(SyntheticPipelineRequestV1)
    assert not any(
        item.kind is inspect.Parameter.VAR_KEYWORD
        for item in request_signature.parameters.values()
    )
    assert all(
        item.default is inspect.Parameter.empty for item in request_signature.parameters.values()
    )

    result = _result()
    upstream = {
        "contract": result.contract,
        "plan": result.plan,
        "preparation": result.preparation,
        "matrix": result.matrix,
        "execution": result.execution,
    }
    for name, value in upstream.items():
        with pytest.raises(TypeError):
            SyntheticPipelineRequestV1(  # type: ignore[call-arg]
                PIPELINE_SCHEMA_VERSION,
                ORCHESTRATOR_VERSION,
                _base_chain().config,
                _base_chain().bound_inputs,
                None,
                **{name: value},
            )


# ==============================================================================================
# Implementation-review conformance cases required by the design
# ==============================================================================================


def test_a2_bound_inputs_identity_payload_mirrors_the_private_adapter_payload():
    """Design section 4.5.1 A1-A5 / R18: deep equality with the frozen private payload."""

    chain = _base_chain()
    bound = chain.bound_inputs
    public = bound_inputs_identity_payload(
        chain.contract, chain.plan, bound.domain, bound.bindings, bound.observations
    )
    private = _input_payload(replace(bound, input_digest="placeholder-not-used"))
    assert public == private
    assert set(public) == {
        "schema_version",
        "mode",
        "source_contract_digest",
        "plan_digest",
        "domain",
        "bindings",
        "observations",
    }
    assert public["schema_version"] == "M4_BOUND_SYNTHETIC_DATASET_V1"
    assert public["mode"] == SYNTHETIC_PIPELINE_MODE
    assert public["source_contract_digest"] == chain.contract.contract_digest
    assert public["plan_digest"] == chain.plan.plan_digest
    assert public["domain"]["expected_dates"] == list(bound.domain.expected_dates)
    assert len(public["bindings"]) == len(bound.bindings)
    assert len(public["observations"]) == len(bound.observations)

    # Ordering rule: (trade_date, bindings order) -- observation tuple order is irrelevant.
    shuffled = bound_inputs_identity_payload(
        chain.contract,
        chain.plan,
        bound.domain,
        bound.bindings,
        tuple(reversed(bound.observations)),
    )
    assert shuffled == public
    assert canonical_digest(public) == bound.input_digest

    # A1: pure function -- it takes no BoundDatasetInputsV1 and validates no digest.
    assert list(inspect.signature(bound_inputs_identity_payload).parameters) == [
        "contract",
        "plan",
        "domain",
        "bindings",
        "observations",
    ]


def test_j1_j4_record_bytes_hex_encoding_and_skeleton_measurement():
    """Design J1-J4 / R11: hex encoding, round-trip, charset, bounded-skeleton measurement."""

    record = _discovered_record()
    binding = _bound_result().metadata.registry_binding
    raw = serialize_hypothesis_record(record)
    assert binding.record_bytes_hex == raw.hex()
    assert len(binding.record_bytes_hex) == 2 * len(raw)
    assert all(character in "0123456789abcdef" for character in binding.record_bytes_hex)
    assert bytes.fromhex(binding.record_bytes_hex) == raw
    assert "/" not in binding.record_bytes_hex and "\\" not in binding.record_bytes_hex

    from ashare_research.mechanism.registry import (
        CITATION_MAX_LEN,
        HYPOTHESIS_ID_MAX_LEN,
        LONG_TEXT_MAX_LEN,
        NOTES_MAX_LEN,
        SHORT_TEXT_MAX_LEN,
        SOURCE_VERSION_MAX_LEN,
        TARGET_HORIZON_MAX_LEN,
    )

    filler = "A"
    maximal = _record(
        hypothesis_id=filler * HYPOTHESIS_ID_MAX_LEN,
        source_title=filler * SHORT_TEXT_MAX_LEN,
        authors_or_issuer=filler * SHORT_TEXT_MAX_LEN,
        citation_or_source_identity=filler * CITATION_MAX_LEN,
        source_version=filler * SOURCE_VERSION_MAX_LEN,
        source_notes=filler * NOTES_MAX_LEN,
        theory=filler * LONG_TEXT_MAX_LEN,
        original_market=filler * SHORT_TEXT_MAX_LEN,
        original_sample=filler * LONG_TEXT_MAX_LEN,
        candidate_signal=filler * SHORT_TEXT_MAX_LEN,
        target_horizon=filler * TARGET_HORIZON_MAX_LEN,
    )
    maximal_bytes = serialize_hypothesis_record(maximal)
    assert bytes.fromhex(maximal_bytes.hex()) == maximal_bytes
    assert len(maximal_bytes.hex()) == 2 * len(maximal_bytes)

    # Measured evidence for one bounded *text skeleton* only.  The ceiling is derived from the
    # frozen per-field limits this fixture actually fills, allowing six output bytes per character
    # (worst-case ``\uXXXX`` JSON escaping), doubled for hex, plus a fixed allowance for keys and
    # the remaining short/enum/digest fields.  It is deliberately NOT a schema guarantee.
    text_limit_sum = (
        HYPOTHESIS_ID_MAX_LEN
        + 4 * SHORT_TEXT_MAX_LEN
        + CITATION_MAX_LEN
        + SOURCE_VERSION_MAX_LEN
        + NOTES_MAX_LEN
        + 2 * LONG_TEXT_MAX_LEN
        + TARGET_HORIZON_MAX_LEN
    )
    skeleton_ceiling = 2 * 6 * text_limit_sum + 8192
    assert len(maximal_bytes.hex()) <= skeleton_ceiling

    # Honest limitation (corrected design J4/R11, acceptance AC-25 item 7): the true total is NOT
    # finitely bounded upstream, because tuple cardinality, ``state_history`` length,
    # ``authorization_ref`` length and ``schema_version`` are uncapped.  No pipeline-layer size
    # gate exists, and no test may promote the skeleton measurement above to a schema bound.
    assert "MAX_RECORD_BYTES" not in ORCHESTRATOR_SOURCE
    assert "record_bytes_hex" in ORCHESTRATOR_SOURCE


def test_structural_constants_and_stage_sequence_are_consistent():
    """Design section 3: frozen constants, exact tuple shapes and their mutual relations."""

    assert ORCHESTRATOR_VERSION == "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1"
    assert PIPELINE_SCHEMA_VERSION == "M4_SYNTHETIC_PIPELINE_RESULT_V1"
    assert PIPELINE_STATE == "SYNTHETIC_PIPELINE_COMPLETED"
    assert PIPELINE_DIGEST_ALGORITHM == "M4_CANONICAL_PIPELINE_RESULT_DIGEST_V1"
    assert REGISTRY_BINDING_ABSENT == "NO_M4B_REGISTRY_METADATA_BOUND"
    assert REGISTRY_BINDING_PRESENT == "M4B_REGISTRY_METADATA_BOUND_READ_ONLY"
    assert REGISTRY_BINDING_DIGEST_ALGORITHM == "M4_CANONICAL_REGISTRY_BINDING_DIGEST_V1"
    assert SYNTHETIC_PIPELINE_MODE == "SYNTHETIC"
    assert PIPELINE_STAGE_SEQUENCE == (
        "INTAKE",
        "CONTRACT",
        "PLAN",
        "SYNTHETIC_INPUT",
        "DATASET",
        "MATRIX",
        "EXECUTION",
        "ENVELOPE",
    )
    assert type(PIPELINE_STAGE_SEQUENCE) is tuple
    assert type(REQUIRED_STAGES_COMPLETED) is tuple
    assert len(PIPELINE_STAGE_SEQUENCE) == 8
    assert PIPELINE_STAGE_SEQUENCE[1:7] == REQUIRED_STAGES_COMPLETED

    assert ORCHESTRATOR_MODULE.BINDABLE_REGISTRY_STATUSES == (
        "DISCOVERED",
        "LITERATURE_REVIEWED",
        "A_SHARE_FEASIBILITY_REVIEWED",
        "NOT_TESTED",
        "PRE_REGISTERED",
        "DEFERRED",
    )
    for name in (
        "DECIMAL_CONTEXT_PRECISION",
        "MAX_BOOTSTRAP_REPLICATIONS",
        "BINDABLE_REGISTRY_STATUSES",
    ):
        assert name not in pipeline_package.__all__

    assert canonical_digest({"binding_state": REGISTRY_BINDING_ABSENT}) == (
        _result().metadata.registry_binding_digest
    )
    assert len(_result().metadata.pipeline_digest) == 64
    assert _result().metadata.pipeline_digest == canonical_digest(
        pipeline_result_to_canonical_dict(_result())
    )


def test_pipeline_error_is_a_value_error_with_a_stable_code():
    """Design section 8.2/8.3: PipelineError shape and the closed code table."""

    error = PipelineError("PIPELINE_VERSION_UNSUPPORTED")
    assert isinstance(error, ValueError)
    assert error.code == "PIPELINE_VERSION_UNSUPPORTED"
    assert str(error) == "PIPELINE_VERSION_UNSUPPORTED"
    with_message = PipelineError("PIPELINE_VERSION_UNSUPPORTED", "detail")
    assert with_message.code == "PIPELINE_VERSION_UNSUPPORTED"
    assert str(with_message) == "detail"
    assert _code(with_message) == "PIPELINE_VERSION_UNSUPPORTED"
    raised = frozenset(_raised_literals(ORCHESTRATOR_SOURCE, "PipelineError"))
    assert raised == CLOSED_PIPELINE_CODES


def test_registry_binding_hex_tamper_and_absent_digest_tamper_are_detected():
    """Design RB2/RB3/RB5: binding bytes, binding digest and presence coherence fail closed."""

    chain = _base_chain()
    record = _discovered_record()
    bound = _bound_result()
    binding = bound.metadata.registry_binding

    replacement = "a" if binding.record_bytes_hex[0] != "a" else "b"
    tampered = replace(
        bound,
        metadata=replace(
            bound.metadata,
            registry_binding=replace(
                binding, record_bytes_hex=replacement + binding.record_bytes_hex[1:]
            ),
        ),
    )
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(_resign(tampered), _request(registry_record=record))
    # AC-25 key assertion 5 fixes this single code; the byte re-parse (RB5) is what fails.
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"

    absent_tamper = replace(
        _result(), metadata=replace(_result().metadata, registry_binding_digest="0" * 64)
    )
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(absent_tamper, chain.request)
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"

    unbound_metadata = replace(bound.metadata, registry_binding=None)
    present_but_unrequested = replace(bound, metadata=unbound_metadata)
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(_resign(present_but_unrequested), chain.request)
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"

    # RB4: the bound identity must be the request's identity.
    other_record = _record(identifier="synthetic.other")
    with pytest.raises(PipelineError) as caught:
        validate_pipeline_result(bound, _request(registry_record=other_record))
    assert caught.value.code == "PIPELINE_REGISTRY_IDENTITY_MISMATCH"


def test_invalid_binding_hex_is_rejected_by_the_encoder():
    """Design RB5: non-hex and odd-length encodings are structural registry failures."""

    binding = RegistryMetadataBindingV1(
        binding_state=REGISTRY_BINDING_PRESENT,
        hypothesis_id=HYPOTHESIS_ID,
        hypothesis_version=1,
        record_identity_digest="0" * 64,
        record_digest="0" * 64,
        record_status="DISCOVERED",
        record_bytes_hex="zz",
    )
    with pytest.raises(PipelineError) as caught:
        ORCHESTRATOR_MODULE._record_bytes(binding)
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"
    with pytest.raises(PipelineError) as caught:
        ORCHESTRATOR_MODULE._record_bytes(replace(binding, record_bytes_hex="abc"))
    assert caught.value.code == "PIPELINE_REGISTRY_RECORD_INVALID"


def test_request_carries_the_frozen_input_types_exactly():
    """Design section 5.3 / G3 / G4: config and bound_inputs use the frozen types, never dicts."""

    chain = _base_chain()
    assert type(chain.bound_inputs).__name__ == "BoundDatasetInputsV1"
    assert type(chain.bound_inputs.domain) is ExpectedDomainV1
    assert all(type(item) is ObservationV1 for item in chain.bound_inputs.observations)
    assert dataclasses.is_dataclass(chain.config)

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(config={"hypothesis_id": HYPOTHESIS_ID}))
    assert caught.value.code == "PIPELINE_CONFIG_TYPE_INVALID"

    with pytest.raises(PipelineError) as caught:
        run_synthetic_pipeline(request=_request(bound_inputs={"mode": "SYNTHETIC"}))
    assert caught.value.code == "PIPELINE_INPUT_TYPE_INVALID"
