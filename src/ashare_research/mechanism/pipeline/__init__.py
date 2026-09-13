"""Synthetic-only end-to-end M4 pipeline package.

The package exports exactly the twenty frozen public symbols of design section 4.4: ten constants,
five classes (four immutable envelope types plus ``PipelineError``) and five public functions.
Private implementation helpers are not re-exported and are not acceptance entries.

``run_synthetic_pipeline`` composes the five already-frozen synthetic stages on caller-supplied
synthetic strategy inputs.  It is not a generic research executor and it creates no real-data,
provider, database, literature, holdout, ranking or trading capability.
"""

from .orchestrator import (
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
