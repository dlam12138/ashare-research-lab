"""Fail-closed, synthetic-only Stage 3D-B pre-unseal contract validator."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ashare_research.tools.m3_stage3cb_development import verify_adapter_lock, verify_frozen_lock
from ashare_research.tools.m3_stage3db_oos_identity import build_oos_execution_adapter_digest

BASELINE = "25424aa767e90a098ba11223191fb9e731e1ff25"
UPSTREAM = "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
PIPELINE = "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
MODEL = "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"
ADAPTER = "9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78"
DATA_MANIFEST = "7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2"
ROBUSTNESS = "8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527"
AUTH = "reports/m3_stage3db_execution_authorization_v1.json"
SCHEMA = "reports/m3_stage3db_holdout_primary_result_schema_v1.json"
DA_DECISION = "reports/m3_stage3da_holdout_unseal_decision_v1.json"
DA_EXECUTION = "reports/m3_stage3da_frozen_oos_execution_contract_v1.json"
DA_POLICY = "reports/m3_stage3da_holdout_interpretation_policy_v1.json"


class PreUnsealError(ValueError):
    pass


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load(root: Path, path: str) -> dict[str, Any]:
    value = json.loads((root / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreUnsealError(f"M3_STAGE3DB_CONTRACT_OBJECT_REQUIRED:{path}")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PreUnsealError(code)


def validate_preunseal(root: Path | None = None) -> dict[str, Any]:
    repo = (root or _root()).resolve()
    auth = _load(repo, AUTH)
    schema = _load(repo, SCHEMA)
    _require(auth["canonical_base"] == BASELINE, "M3_STAGE3DB_BASE_GATE_FAILED")
    _require(
        auth["analysis_start"] == "2023-01-01" and auth["analysis_end"] == "2026-08-13",
        "M3_STAGE3DB_HOLDOUT_WINDOW",
    )
    _require(auth["warmup_start"] == "2022-12-01", "M3_STAGE3DB_WARMUP_WINDOW")
    _require(auth["execution_mode"] == "HOLDOUT_PRIMARY_ONLY", "M3_STAGE3DB_EXECUTION_MODE")
    _require(auth["accepted_execution_max_count"] == 1, "M3_STAGE3DB_EXECUTION_COUNT")
    _require(auth["holdout_currently_sealed"] is True, "M3_STAGE3DB_HOLDOUT_NOT_SEALED")
    _require(auth["unseal_requires_preexecution_ci"] is True, "M3_STAGE3DB_PREUNSEAL_CI_REQUIRED")
    _require(
        auth["holdout_read"] is False and auth["holdout_download"] is False,
        "M3_STAGE3DB_PREUNSEAL_HOLDOUT_ACCESS",
    )
    _require(schema["stage"] == "M3_STAGE3DB", "M3_STAGE3DB_SCHEMA_STAGE")
    _require(
        set(schema["required_fields"]).issubset(set(schema["allowed_fields"])),
        "M3_STAGE3DB_SCHEMA_REQUIRED_FIELDS",
    )
    _require(
        set(schema["forbidden_fields"]).isdisjoint(set(schema["allowed_fields"])),
        "M3_STAGE3DB_SCHEMA_FORBIDDEN_FIELDS",
    )
    for path, key in (
        (DA_DECISION, "stage3da_decision_contract"),
        (DA_EXECUTION, "stage3da_frozen_oos_contract"),
        (DA_POLICY, "interpretation_policy"),
    ):
        actual = sha256((repo / path).read_bytes()).hexdigest()
        _require(actual == auth[key]["sha256"], f"M3_STAGE3DB_STAGE3DA_BINDING:{path}")
    frozen = verify_frozen_lock()
    _require(frozen["upstream_inventory_sha256"] == UPSTREAM, "M3_STAGE3DB_IDENTITY_UPSTREAM")
    _require(frozen["pipeline_digest"] == PIPELINE, "M3_STAGE3DB_IDENTITY_PIPELINE")
    _require(frozen["model_digest"] == MODEL, "M3_STAGE3DB_IDENTITY_MODEL")
    _require(verify_adapter_lock() == ADAPTER, "M3_STAGE3DB_IDENTITY_ADAPTER")
    adapter_digest, payload = build_oos_execution_adapter_digest(repo)
    _require(
        adapter_digest == auth["oos_execution_adapter_digest"], "M3_STAGE3DB_OOS_ADAPTER_IDENTITY"
    )
    _require(
        auth["upstream_inventory_sha"] == UPSTREAM and auth["pipeline_digest"] == PIPELINE,
        "M3_STAGE3DB_AUTH_IDENTITY",
    )
    return {
        "schema": "m3_stage3db_preunseal_readiness_v1",
        "status": "PASS",
        "stage": "M3_STAGE3DB",
        "canonical_base": BASELINE,
        "holdout_start": "2023-01-01",
        "holdout_end": "2026-08-13",
        "warmup_start": "2022-12-01",
        "holdout_read": False,
        "holdout_download": False,
        "oos_execution_adapter_digest": adapter_digest,
        "oos_execution_adapter_digest_payload": payload,
        "development_data_manifest_digest": DATA_MANIFEST,
        "development_robustness_execution_digest": ROBUSTNESS,
        "stage3db_status": "PRE_UNSEAL_READY",
        "next_boundary": "HOLDOUT_UNSEAL_BOUNDARY_REACHED_AFTER_EXACT_CI_HEAD_CHECK",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-contracts",))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_preunseal()
    except Exception as exc:  # fail closed at the CLI boundary
        print(str(exc))
        return 1
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    print("M3_STAGE3DB_PREUNSEAL_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
