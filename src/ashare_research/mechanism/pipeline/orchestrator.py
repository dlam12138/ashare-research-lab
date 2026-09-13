"""Synthetic-only end-to-end orchestration for the frozen M4 design.

This module is the single public composition entry for the five already-frozen synthetic
stages ``Typed Contract -> Plan -> Synthetic Dataset -> Immutable Matrix -> Bounded Execution``
plus an optional, read-only, non-evidence M4-B registry metadata binding.  It defines no
statistics of its own, performs no external IO, and produces one immutable result envelope.

Design: ``docs/m4_synthetic_end_to_end_pipeline_design_v1.md``.

Boundary: this module authorizes computation only on caller-supplied synthetic strategy inputs.
It is not a generic research executor; it has no provider, network, filesystem, environment,
database, market, literature or holdout surface, and it creates no research, significance,
tradability or A-share mechanism conclusion.
"""

from __future__ import annotations

import decimal
import hashlib
import json
import re
from dataclasses import dataclass, fields
from typing import Any

from ashare_research.mechanism.contract_compiler import (
    FrozenMechanismContract,
    compile_hypothesis_config,
    contract_to_canonical_dict,
    validate_contract,
)
from ashare_research.mechanism.datasets import (
    BoundDatasetInputsV1,
    DatasetPreparationV1,
    ExpectedDomainV1,
    ObservationV1,
    RoleBindingV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    validate_dataset,
)
from ashare_research.mechanism.datasets.synthetic import SCHEMA as BOUND_DATASET_SCHEMA
from ashare_research.mechanism.execution import (
    FORBIDDEN_KEYS,
    INTERPRETATION_BOUNDARY,
    ExecutionArtifactV1,
    ExecutionError,
    execute_bounded_analysis,
    execution_artifact_to_canonical_dict,
    validate_execution_artifact,
)
from ashare_research.mechanism.hypothesis_config import HypothesisConfig
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import (
    DeterministicAnalysisPlan,
    build_analysis_plan,
    compute_plan_digest,
    plan_to_canonical_dict,
    validate_analysis_plan,
)
from ashare_research.mechanism.planning.matrix import (
    MatrixPreparationV1,
    materialize_design_matrix,
    matrix_to_canonical_dict,
    validate_design_matrix,
)
from ashare_research.mechanism.registry import (
    HypothesisRecordV1,
    RegistryError,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    hypothesis_record_to_canonical_dict,
    parse_hypothesis_record,
    serialize_hypothesis_record,
    validate_hypothesis_record,
)

# --- Frozen public constants (design section 3) -------------------------------------------------

ORCHESTRATOR_VERSION = "M4_SYNTHETIC_END_TO_END_ORCHESTRATOR_V1"
PIPELINE_SCHEMA_VERSION = "M4_SYNTHETIC_PIPELINE_RESULT_V1"
PIPELINE_STATE = "SYNTHETIC_PIPELINE_COMPLETED"
PIPELINE_DIGEST_ALGORITHM = "M4_CANONICAL_PIPELINE_RESULT_DIGEST_V1"
PIPELINE_STAGE_SEQUENCE = (
    "INTAKE",
    "CONTRACT",
    "PLAN",
    "SYNTHETIC_INPUT",
    "DATASET",
    "MATRIX",
    "EXECUTION",
    "ENVELOPE",
)
REQUIRED_STAGES_COMPLETED = (
    "CONTRACT",
    "PLAN",
    "SYNTHETIC_INPUT",
    "DATASET",
    "MATRIX",
    "EXECUTION",
)
REGISTRY_BINDING_ABSENT = "NO_M4B_REGISTRY_METADATA_BOUND"
REGISTRY_BINDING_PRESENT = "M4B_REGISTRY_METADATA_BOUND_READ_ONLY"
REGISTRY_BINDING_DIGEST_ALGORITHM = "M4_CANONICAL_REGISTRY_BINDING_DIGEST_V1"
SYNTHETIC_PIPELINE_MODE = "SYNTHETIC"

# --- Implementation-detail constants (NOT part of the public export surface, C6/BS6/R17.5) ------

DECIMAL_CONTEXT_PRECISION = 28
MAX_BOOTSTRAP_REPLICATIONS = 100000
BINDABLE_REGISTRY_STATUSES = (
    "DISCOVERED",
    "LITERATURE_REVIEWED",
    "A_SHARE_FEASIBILITY_REVIEWED",
    "NOT_TESTED",
    "PRE_REGISTERED",
    "DEFERRED",
)

# Private literal aliases.  Design section 3 forbids adding, renaming or revaluing *contract*
# constants, so these two are deliberately underscore-private local aliases: they carry no policy
# and are not part of the section 3 constant surface.
_READY_DATASET_STATUS = "READY_SYNTHETIC"
_MISSING_BINDING_ORDER = 10**9

# Equivalent of the frozen executor content rule (design sections 5.5, 9.5 V5).  The upstream
# helper and the upstream regex are private, and design section 6.3 forbids calling private
# helpers, so the rule is restated here verbatim rather than delegated.
_FORBIDDEN_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/])|(?:\\\\)|(?:/[^/\s]+)")
_LOWER_HEX_RE = re.compile(r"[0-9a-f]*")


class PipelineError(ValueError):
    """Composed-pipeline failure carrying one of the frozen closed pipeline error codes."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class SyntheticPipelineRequestV1:
    """The frozen synthetic strategy inputs plus an explicit, nullable registry record.

    ``config`` and ``bound_inputs`` are caller-supplied *synthetic declarations*.  Contract, plan,
    preparation, matrix and execution objects are never accepted from the caller; the pipeline
    compiles them itself, so a forged upstream object is structurally inexpressible.
    """

    schema_version: str
    orchestrator_version: str
    config: HypothesisConfig
    bound_inputs: BoundDatasetInputsV1
    registry_record: HypothesisRecordV1 | None


@dataclass(frozen=True)
class RegistryMetadataBindingV1:
    """Read-only snapshot of an M4-B record bound as metadata.  Never execution evidence."""

    binding_state: str
    hypothesis_id: str
    hypothesis_version: int
    record_identity_digest: str
    record_digest: str
    record_status: str
    record_bytes_hex: str


@dataclass(frozen=True)
class PipelineMetadataV1:
    """Envelope metadata; ``pipeline_digest`` is excluded from its own digest (L14)."""

    orchestrator_version: str
    pipeline_schema_version: str
    pipeline_state: str
    stages_completed: tuple[str, ...]
    registry_binding: RegistryMetadataBindingV1 | None
    registry_binding_digest: str
    interpretation_boundary: str
    pipeline_digest: str


@dataclass(frozen=True)
class SyntheticPipelineResultV1:
    """The single immutable composed result envelope."""

    metadata: PipelineMetadataV1
    contract: FrozenMechanismContract
    plan: DeterministicAnalysisPlan
    preparation: DatasetPreparationV1
    matrix: MatrixPreparationV1
    execution: ExecutionArtifactV1


def bound_inputs_identity_payload(
    contract: FrozenMechanismContract,
    plan: DeterministicAnalysisPlan,
    domain: ExpectedDomainV1,
    bindings: tuple[RoleBindingV1, ...],
    observations: tuple[ObservationV1, ...],
) -> dict:
    """Return the canonical ``input_digest`` payload for synthetic bound inputs (L6).

    The returned dictionary is deeply equal to the frozen adapter's private ``_input_payload``
    for the corresponding ``BoundDatasetInputsV1``.  It is a pure function: it performs no IO and
    validates no digest.  Callers compute
    ``input_digest = canonical_digest(bound_inputs_identity_payload(...))`` themselves, which is
    what makes "was the input altered?" decidable rather than orchestrator-decided.
    """

    role_order = {binding.role: index for index, binding in enumerate(bindings)}
    return {
        "schema_version": BOUND_DATASET_SCHEMA,
        "mode": SYNTHETIC_PIPELINE_MODE,
        "source_contract_digest": contract.contract_digest,
        "plan_digest": plan.plan_digest,
        "domain": _domain_projection(domain),
        "bindings": [
            {field.name: getattr(binding, field.name) for field in fields(binding)}
            for binding in bindings
        ],
        "observations": [
            {field.name: getattr(observation, field.name) for field in fields(observation)}
            for observation in sorted(
                observations,
                key=lambda item: (
                    item.trade_date,
                    role_order.get(item.role, _MISSING_BINDING_ORDER),
                ),
            )
        ],
    }


def pipeline_result_to_canonical_dict(result: SyntheticPipelineResultV1) -> dict:
    """Return an independent canonical dictionary without ``metadata.pipeline_digest``.

    Every container is freshly built, so mutating the result cannot change the envelope or any
    later serialization.  The five stage projections come from the existing authoritative
    functions and are neither rewritten nor reordered.
    """

    if type(result) is not SyntheticPipelineResultV1:
        raise TypeError("result must be SyntheticPipelineResultV1")
    metadata = result.metadata
    if type(metadata) is not PipelineMetadataV1:
        raise TypeError("result.metadata must be PipelineMetadataV1")
    return {
        "metadata": {
            "orchestrator_version": metadata.orchestrator_version,
            "pipeline_schema_version": metadata.pipeline_schema_version,
            "pipeline_state": metadata.pipeline_state,
            "stages_completed": list(metadata.stages_completed),
            "registry_binding": (
                None
                if metadata.registry_binding is None
                else {
                    "binding_state": metadata.registry_binding.binding_state,
                    "hypothesis_id": metadata.registry_binding.hypothesis_id,
                    "hypothesis_version": metadata.registry_binding.hypothesis_version,
                    "record_identity_digest": metadata.registry_binding.record_identity_digest,
                    "record_digest": metadata.registry_binding.record_digest,
                    "record_status": metadata.registry_binding.record_status,
                    "record_bytes_hex": metadata.registry_binding.record_bytes_hex,
                }
            ),
            "registry_binding_digest": metadata.registry_binding_digest,
            "interpretation_boundary": metadata.interpretation_boundary,
        },
        "contract": contract_to_canonical_dict(result.contract),
        "plan": plan_to_canonical_dict(result.plan),
        "preparation": dataset_to_canonical_dict(result.preparation),
        "matrix": matrix_to_canonical_dict(result.matrix),
        "execution": execution_artifact_to_canonical_dict(result.execution),
    }


def serialize_pipeline_result(result: SyntheticPipelineResultV1) -> bytes:
    """Validate then emit canonical UTF-8 JSON with exactly one final newline."""

    _check_envelope(result)
    payload = pipeline_result_to_canonical_dict(result)
    payload["metadata"]["pipeline_digest"] = result.metadata.pipeline_digest
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def validate_pipeline_result(
    result: SyntheticPipelineResultV1,
    request: SyntheticPipelineRequestV1,
) -> None:
    """V1-V6: envelope shape, upstream revalidation, digest chain, binding, content, self digest."""

    # V1 -- exact types of the envelope and of its six fields.
    if type(result) is not SyntheticPipelineResultV1:
        raise TypeError("result must be SyntheticPipelineResultV1")
    if type(request) is not SyntheticPipelineRequestV1:
        raise TypeError("request must be SyntheticPipelineRequestV1")
    _expect_type(result.metadata, PipelineMetadataV1, "result.metadata")
    _expect_type(result.contract, FrozenMechanismContract, "result.contract")
    _expect_type(result.plan, DeterministicAnalysisPlan, "result.plan")
    _expect_type(result.preparation, DatasetPreparationV1, "result.preparation")
    _expect_type(result.matrix, MatrixPreparationV1, "result.matrix")
    _expect_type(result.execution, ExecutionArtifactV1, "result.execution")

    bound_inputs = request.bound_inputs
    contract = result.contract
    plan = result.plan
    preparation = result.preparation
    matrix = result.matrix
    execution = result.execution

    # V2 -- the five frozen stage validators, in the S1-S6 order and with the S1-S6 arguments.
    validate_contract(contract)
    validate_analysis_plan(plan)
    validate_dataset(preparation, contract, plan, bound_inputs)
    validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)
    validate_execution_artifact(execution, matrix, preparation, contract, plan, bound_inputs)

    # V3 -- the cross-artifact digest chain, compared field by field.
    chain = execution.source_chain
    actual_chain = (
        chain.contract_digest,
        chain.plan_digest,
        chain.input_digest,
        chain.domain_digest,
        chain.dataset_digest,
        chain.matrix_digest,
    )
    expected_chain = (
        contract.contract_digest,
        plan.plan_digest,
        bound_inputs.input_digest,
        preparation.domain_digest,
        preparation.dataset_digest,
        matrix.matrix_digest,
    )
    if actual_chain != expected_chain:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "execution source chain is not bound")

    # V4 -- metadata invariants and the registry metadata binding rules RB1-RB6.
    _check_metadata(result.metadata, request.registry_record)

    # V5 -- forbidden host/path/session/selection content over the whole canonical envelope.
    payload = pipeline_result_to_canonical_dict(result)
    payload["metadata"]["pipeline_digest"] = result.metadata.pipeline_digest
    _check_forbidden_content(payload)

    # V6 -- envelope self digest.
    recomputed = canonical_digest(pipeline_result_to_canonical_dict(result))
    if recomputed != result.metadata.pipeline_digest:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH")


def run_synthetic_pipeline(*, request: SyntheticPipelineRequestV1) -> SyntheticPipelineResultV1:
    """Run the frozen S0-S8 synthetic composition and return the immutable result envelope.

    The single keyword-only ``request`` parameter is the first rejection surface: holdout windows,
    real-data switches, providers, databases, paths and seeds are not expressible at all.  The
    whole call is evaluated inside a fixed local ``decimal`` context so that ambient precision
    cannot change result bytes; the host's global context is never written.
    """

    with decimal.localcontext() as context:
        context.prec = DECIMAL_CONTEXT_PRECISION
        return _run_pipeline(request)


def _run_pipeline(request: SyntheticPipelineRequestV1) -> SyntheticPipelineResultV1:
    # Unmapped bare exceptions from the existing modules are reported once, per design M3; the
    # original exception is preserved as ``__cause__``.  ``ValueError`` subclasses and ``TypeError``
    # are deliberately NOT caught here (M1/M2).
    try:
        return _compose(request)
    except (KeyError, AttributeError, IndexError, AssertionError, ZeroDivisionError) as exc:
        raise PipelineError("PIPELINE_INTERNAL_SOURCE_UNMAPPED") from exc


def _compose(request: SyntheticPipelineRequestV1) -> SyntheticPipelineResultV1:
    # S0 -- INTAKE: shape, version, registry record type and self-consistency, G14 (record part).
    if type(request) is not SyntheticPipelineRequestV1:
        raise PipelineError("PIPELINE_REQUEST_TYPE_INVALID")
    if (
        request.schema_version != PIPELINE_SCHEMA_VERSION
        or request.orchestrator_version != ORCHESTRATOR_VERSION
    ):
        raise PipelineError("PIPELINE_VERSION_UNSUPPORTED")
    if type(request.config) is not HypothesisConfig:
        raise PipelineError("PIPELINE_CONFIG_TYPE_INVALID")
    if type(request.bound_inputs) is not BoundDatasetInputsV1:
        raise PipelineError("PIPELINE_INPUT_TYPE_INVALID")
    record = request.registry_record
    if record is not None and type(record) is not HypothesisRecordV1:
        raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")
    if record is not None:
        try:
            validate_hypothesis_record(record)
        except RegistryError as exc:
            raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID") from exc
        _check_forbidden_content(hypothesis_record_to_canonical_dict(record))

    # S1 -- CONTRACT.
    contract = compile_hypothesis_config(request.config)
    validate_contract(contract)

    # S2 -- PLAN.
    plan = build_analysis_plan(contract)
    validate_analysis_plan(plan)
    if compute_plan_digest(plan) != plan.plan_digest:
        raise PipelineError("PIPELINE_INPUT_BINDING_MISMATCH", "plan digest is not self-consistent")
    if plan.source_contract_digest != contract.contract_digest:
        raise PipelineError("PIPELINE_INPUT_BINDING_MISMATCH", "plan is not bound to the contract")

    # S3 -- SYNTHETIC_INPUT: G7, G8, G9, G10, G11 in frozen row order.
    bound_inputs = request.bound_inputs
    if bound_inputs.mode != SYNTHETIC_PIPELINE_MODE:
        raise PipelineError("PIPELINE_UNSUPPORTED_MODE")
    if bound_inputs.schema_version != BOUND_DATASET_SCHEMA:
        raise PipelineError("PIPELINE_INPUT_SCHEMA_UNSUPPORTED")
    if bound_inputs.source_contract_digest != contract.contract_digest:
        raise PipelineError("PIPELINE_INPUT_BINDING_MISMATCH", "contract digest does not match")
    if bound_inputs.plan_digest != plan.plan_digest:
        raise PipelineError("PIPELINE_INPUT_BINDING_MISMATCH", "plan digest does not match")
    bootstrap = plan_to_canonical_dict(plan)["bootstrap_plan"]
    if bootstrap["enabled"] is True and bootstrap["replications"] > MAX_BOOTSTRAP_REPLICATIONS:
        raise PipelineError(
            "PIPELINE_REPLICATIONS_EXCEED_LIMIT",
            f"declared replications exceed {MAX_BOOTSTRAP_REPLICATIONS}",
        )

    # S4 -- DATASET.
    preparation = materialize_analysis_dataset(contract, plan, bound_inputs)
    validate_dataset(preparation, contract, plan, bound_inputs)
    if preparation.status != _READY_DATASET_STATUS:
        raise PipelineError(
            "PIPELINE_QUALITY_NOT_READY",
            "preparation status is not READY_SYNTHETIC; data_quality_failure_disposition="
            f"{contract.evidence_rule.data_quality_failure_disposition}",
        )

    # S5 -- MATRIX.
    matrix = materialize_design_matrix(preparation, contract, plan, bound_inputs)
    validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)

    # S6 -- EXECUTION.
    execution = execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)
    validate_execution_artifact(execution, matrix, preparation, contract, plan, bound_inputs)

    # S7 -- ENVELOPE: G12, G13, then L13 and L14.
    if record is not None:
        if record.hypothesis_id != plan.hypothesis_id:
            raise PipelineError("PIPELINE_REGISTRY_IDENTITY_MISMATCH")
        if record.status not in BINDABLE_REGISTRY_STATUSES:
            raise PipelineError("PIPELINE_REGISTRY_STATUS_NOT_BINDABLE")
    metadata = PipelineMetadataV1(
        orchestrator_version=ORCHESTRATOR_VERSION,
        pipeline_schema_version=PIPELINE_SCHEMA_VERSION,
        pipeline_state=PIPELINE_STATE,
        stages_completed=REQUIRED_STAGES_COMPLETED,
        registry_binding=_registry_binding(record),
        registry_binding_digest=canonical_digest(_registry_binding_payload(record)),
        interpretation_boundary=INTERPRETATION_BOUNDARY,
        pipeline_digest="",
    )
    provisional = SyntheticPipelineResultV1(
        metadata=metadata,
        contract=contract,
        plan=plan,
        preparation=preparation,
        matrix=matrix,
        execution=execution,
    )
    # The frozen design forbids rewriting artifacts with the dataclass replace helper (section 6.3),
    # so this module never imports or calls it: the envelope is simply rebuilt once with the self
    # digest filled in.  ``pipeline_digest`` is excluded from its own digest, so the provisional
    # placeholder value cannot influence the computed digest.
    pipeline_digest = canonical_digest(pipeline_result_to_canonical_dict(provisional))
    result = SyntheticPipelineResultV1(
        metadata=PipelineMetadataV1(
            orchestrator_version=ORCHESTRATOR_VERSION,
            pipeline_schema_version=PIPELINE_SCHEMA_VERSION,
            pipeline_state=PIPELINE_STATE,
            stages_completed=REQUIRED_STAGES_COMPLETED,
            registry_binding=metadata.registry_binding,
            registry_binding_digest=metadata.registry_binding_digest,
            interpretation_boundary=INTERPRETATION_BOUNDARY,
            pipeline_digest=pipeline_digest,
        ),
        contract=contract,
        plan=plan,
        preparation=preparation,
        matrix=matrix,
        execution=execution,
    )
    validate_pipeline_result(result, request)

    # S8 -- RETURN.
    return result


def _expect_type(value: Any, expected: type, name: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{name} must be {expected.__name__}")


def _domain_projection(domain: ExpectedDomainV1) -> dict:
    """Mirror of the frozen adapter domain projection used by the L6/L7 payloads."""

    return {
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


def _registry_binding(record: HypothesisRecordV1 | None) -> RegistryMetadataBindingV1 | None:
    if record is None:
        return None
    return RegistryMetadataBindingV1(
        binding_state=REGISTRY_BINDING_PRESENT,
        hypothesis_id=record.hypothesis_id,
        hypothesis_version=record.hypothesis_version,
        record_identity_digest=hypothesis_record_identity_digest(record),
        record_digest=hypothesis_record_digest(record),
        record_status=record.status,
        record_bytes_hex=serialize_hypothesis_record(record).hex(),
    )


def _registry_binding_payload(record: HypothesisRecordV1 | None) -> dict:
    """L13 payload (design section 10.2); ``record_bytes_sha256`` digests the record bytes."""

    if record is None:
        return {"binding_state": REGISTRY_BINDING_ABSENT}
    return {
        "binding_state": REGISTRY_BINDING_PRESENT,
        "record_digest": hypothesis_record_digest(record),
        "record_identity_digest": hypothesis_record_identity_digest(record),
        "record_status": record.status,
        "record_hypothesis_id": record.hypothesis_id,
        "record_hypothesis_version": record.hypothesis_version,
        "record_bytes_sha256": hashlib.sha256(serialize_hypothesis_record(record)).hexdigest(),
    }


def _record_bytes(binding: RegistryMetadataBindingV1) -> bytes:
    hex_text = binding.record_bytes_hex
    if type(hex_text) is not str or len(hex_text) % 2 or _LOWER_HEX_RE.fullmatch(hex_text) is None:
        raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")
    return bytes.fromhex(hex_text)


def _check_registry_binding(
    metadata: PipelineMetadataV1,
    record: HypothesisRecordV1 | None,
    *,
    request_present: bool = True,
) -> None:
    """RB1-RB6, evaluated in the frozen order.

    ``request_present=False`` is used by the self-contained serializer pre-check, where no
    ``SyntheticPipelineRequestV1`` is available: the request-agreement clauses RB3/RB4 are then
    not evaluable and are skipped, while RB1/RB2/RB5 still run.
    """

    binding = metadata.registry_binding

    # RB1 -- the binding state is a closed two-word vocabulary and must match the binding object.
    if binding is None:
        state = REGISTRY_BINDING_ABSENT
        raw = None
    else:
        _expect_type(binding, RegistryMetadataBindingV1, "metadata.registry_binding")
        state = binding.binding_state
        if state != REGISTRY_BINDING_PRESENT:
            raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")
        raw = _record_bytes(binding)

    # RB2 -- the binding digest is recomputed from the binding alone.
    if state == REGISTRY_BINDING_ABSENT:
        expected_digest = canonical_digest({"binding_state": REGISTRY_BINDING_ABSENT})
    else:
        expected_digest = canonical_digest(
            {
                "binding_state": binding.binding_state,
                "record_digest": binding.record_digest,
                "record_identity_digest": binding.record_identity_digest,
                "record_status": binding.record_status,
                "record_hypothesis_id": binding.hypothesis_id,
                "record_hypothesis_version": binding.hypothesis_version,
                "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if metadata.registry_binding_digest != expected_digest:
        raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")

    # RB3 -- binding presence must agree with the request.
    if request_present:
        if state == REGISTRY_BINDING_ABSENT:
            if record is not None or binding is not None:
                raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")
        elif record is None:
            raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")
    if state == REGISTRY_BINDING_ABSENT:
        return

    # RB4 -- the seven binding fields map onto the frozen section 10.2 payload fields.
    if request_present:
        if binding.hypothesis_id != record.hypothesis_id:
            raise PipelineError("PIPELINE_REGISTRY_IDENTITY_MISMATCH")
        if (
            binding.hypothesis_version != record.hypothesis_version
            or binding.record_status != record.status
            or binding.record_digest != hypothesis_record_digest(record)
            or binding.record_identity_digest != hypothesis_record_identity_digest(record)
            or raw != serialize_hypothesis_record(record)
        ):
            raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")

    # RB5 -- the encoded bytes reparse and their derived identity is recomputed.
    try:
        reparsed = parse_hypothesis_record(raw)
    except RegistryError as exc:
        raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID") from exc
    if (
        hypothesis_record_identity_digest(reparsed) != binding.record_identity_digest
        or hypothesis_record_digest(reparsed) != binding.record_digest
        or reparsed.status != binding.record_status
    ):
        raise PipelineError("PIPELINE_REGISTRY_RECORD_INVALID")

    # RB6 -- registry content never participates in pipeline state, stage completion or execution.
    # ``pipeline_state`` and ``stages_completed`` are registry-independent constants, checked in
    # ``_check_metadata`` before this function; the behavioral proof (byte-identical execution
    # artifact with and without a bound record) is an acceptance item, not a runtime branch.


def _check_metadata(metadata: PipelineMetadataV1, record: HypothesisRecordV1 | None) -> None:
    """V4 -- metadata invariants plus RB1-RB6."""

    if metadata.pipeline_state != PIPELINE_STATE:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "unexpected pipeline state")
    if metadata.stages_completed != REQUIRED_STAGES_COMPLETED:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "incomplete stage sequence")
    _check_registry_binding(metadata, record)


def _check_envelope(result: SyntheticPipelineResultV1) -> None:
    """Self-contained envelope validation used before serialization.

    Mirrors the existing ``serialize_*`` pattern: shape plus the envelope's own invariants.  The
    full request-dependent V1-V6 chain lives in ``validate_pipeline_result``.
    """

    if type(result) is not SyntheticPipelineResultV1:
        raise TypeError("result must be SyntheticPipelineResultV1")
    _expect_type(result.metadata, PipelineMetadataV1, "result.metadata")
    _expect_type(result.contract, FrozenMechanismContract, "result.contract")
    _expect_type(result.plan, DeterministicAnalysisPlan, "result.plan")
    _expect_type(result.preparation, DatasetPreparationV1, "result.preparation")
    _expect_type(result.matrix, MatrixPreparationV1, "result.matrix")
    _expect_type(result.execution, ExecutionArtifactV1, "result.execution")
    metadata = result.metadata
    if metadata.pipeline_state != PIPELINE_STATE:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "unexpected pipeline state")
    if metadata.stages_completed != REQUIRED_STAGES_COMPLETED:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "incomplete stage sequence")
    _check_registry_binding(metadata, None, request_present=False)
    payload = pipeline_result_to_canonical_dict(result)
    payload["metadata"]["pipeline_digest"] = metadata.pipeline_digest
    _check_forbidden_content(payload)
    if canonical_digest(pipeline_result_to_canonical_dict(result)) != metadata.pipeline_digest:
        raise PipelineError("PIPELINE_DIGEST_MISMATCH")


def _check_forbidden_content(payload: Any) -> None:
    """Fail-closed equivalent of the frozen executor content rule (design sections 5.5, V5)."""

    if type(payload) is dict:
        for key, value in payload.items():
            if type(key) is not str or key.lower() in FORBIDDEN_KEYS:
                raise ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")
            _check_forbidden_content(value)
        return
    if type(payload) is list:
        for item in payload:
            _check_forbidden_content(item)
        return
    if type(payload) is str and _FORBIDDEN_PATH_RE.search(payload) is not None:
        raise ExecutionError("FORBIDDEN_ARTIFACT_CONTENT")


__all__ = [
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
]
