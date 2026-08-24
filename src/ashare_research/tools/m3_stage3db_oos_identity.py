"""Repository-relative Stage 3D-B OOS adapter identity, without data access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ashare_research.mechanism.model_digest import canonical_digest

ADAPTER_DIGEST_ALGORITHM = "M3_REPOSITORY_RELATIVE_OOS_EXECUTION_ADAPTER_DIGEST_V1"
AUTH_PATH = "reports/m3_stage3db_execution_authorization_v1.json"
SCHEMA_PATH = "reports/m3_stage3db_holdout_primary_result_schema_v1.json"
ACQUISITION_PATH = "src/ashare_research/tools/m3_stage3db_oos_acquisition.py"
INPUTS_PATH = "src/ashare_research/tools/m3_stage3db_oos_inputs.py"
EXECUTION_PATH = "src/ashare_research/tools/m3_stage3db_oos_execution.py"
DECISION_PATH = "reports/m3_stage3da_holdout_unseal_decision_v1.json"
OOS_CONTRACT_PATH = "reports/m3_stage3da_frozen_oos_execution_contract_v1.json"
POLICY_PATH = "reports/m3_stage3da_holdout_interpretation_policy_v1.json"
MODEL_DIGEST = "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_oos_execution_adapter_digest(root: Path | None = None) -> tuple[str, dict[str, Any]]:
    repo = (root or Path(__file__).resolve().parents[3]).resolve()
    paths = {
        "authorization": repo / AUTH_PATH,
        "result_schema": repo / SCHEMA_PATH,
        "acquisition": repo / ACQUISITION_PATH,
        "inputs": repo / INPUTS_PATH,
        "execution": repo / EXECUTION_PATH,
        "stage3da_decision": repo / DECISION_PATH,
        "stage3da_oos_contract": repo / OOS_CONTRACT_PATH,
        "stage3da_policy": repo / POLICY_PATH,
    }
    if any(not path.is_file() for path in paths.values()):
        missing = [key for key, path in paths.items() if not path.is_file()]
        raise ValueError(f"M3_STAGE3DB_ADAPTER_SOURCE_MISSING:{','.join(missing)}")
    authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
    authorization.pop("oos_execution_adapter_digest", None)
    contract_hashes = {
        relative(repo, paths[key]): sha256_file(paths[key])
        for key in (
            "result_schema",
            "stage3da_decision",
            "stage3da_oos_contract",
            "stage3da_policy",
        )
    }
    contract_hashes[
        "reports/m3_stage3db_execution_authorization_v1.json#without_adapter_digest"
    ] = canonical_digest(authorization)
    payload = {
        "digest_algorithm": ADAPTER_DIGEST_ALGORITHM,
        "stage": "M3_STAGE3DB",
        "contract_hashes": contract_hashes,
        "source_hashes": {
            relative(repo, paths[key]): sha256_file(paths[key])
            for key in ("acquisition", "inputs", "execution")
        },
        "frozen_model_digest": MODEL_DIGEST,
        "scope": (
            "stage3db_authorization,result_schema,holdout_acquisition,"
            "oos_inputs,oos_primary_execution"
        ),
    }
    return canonical_digest(payload), payload
