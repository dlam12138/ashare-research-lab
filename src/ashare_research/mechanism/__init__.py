"""M3 data-preparation layers plus bounded synthetic M4-A.1 contract primitives.

Stage 3B contracts, normalization, lineage, acquisition, and market-proxy
construction remain the canonical data layer. Stage 3C-A modules are imported
directly and remain synthetic-only; M4-A.1 adds compile-only typed contract
objects and exposes no real mechanism result.
"""

from ashare_research.mechanism.contract_compiler import (
    ContractCompilationError,
    FrozenMechanismContract,
    compile_hypothesis_config,
    compute_contract_digest,
    contract_to_canonical_dict,
    serialize_frozen_contract,
    validate_contract,
)
from ashare_research.mechanism.contracts import Stage3BContractError
from ashare_research.mechanism.hypothesis_config import (
    HypothesisConfig,
    HypothesisConfigError,
    load_hypothesis_config,
    parse_hypothesis_config,
)

__all__ = [
    "ContractCompilationError",
    "FrozenMechanismContract",
    "HypothesisConfig",
    "HypothesisConfigError",
    "Stage3BContractError",
    "compile_hypothesis_config",
    "compute_contract_digest",
    "contract_to_canonical_dict",
    "load_hypothesis_config",
    "parse_hypothesis_config",
    "serialize_frozen_contract",
    "validate_contract",
]
