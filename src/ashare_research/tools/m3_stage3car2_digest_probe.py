"""Probe the canonical M3 digest identity without loading research data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ashare_research.mechanism.analysis_contracts import (
    UPSTREAM_INVENTORY_NAME,
    contract_path,
)
from ashare_research.mechanism.model_digest import (
    DIGEST_ALGORITHM,
    build_model_digest,
    build_pipeline_digest,
    sha256_file,
)
from ashare_research.tools.m3_stage3ca_pipeline import _source_paths


def build_identity() -> dict:
    """Build the portable identity envelope from repository-local bytes only."""

    source_paths = _source_paths()
    contract_names = (
        "m3_stage3ca_analysis_pipeline_contract_v2.json",
        "m3_stage3ca_model_specification_v2.json",
        "m3_stage3ca_robustness_registry_v2.json",
        "m3_stage3ca_output_schema_v2.json",
        UPSTREAM_INVENTORY_NAME,
    )
    contract_paths = [contract_path(name) for name in contract_names]
    inventory_path = contract_path(UPSTREAM_INVENTORY_NAME)
    pipeline_digest, pipeline_payload = build_pipeline_digest(source_paths)
    model_digest, model_payload = build_model_digest(
        pipeline_digest=pipeline_digest,
        contract_paths=contract_paths,
        source_paths=source_paths,
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "numpy_rng": "PCG64"},
        upstream_inventory_path=inventory_path,
    )
    envelope = {
        "upstream_inventory_sha256": sha256_file(inventory_path),
        "pipeline_digest": pipeline_digest,
        "model_digest": model_digest,
        "digest_algorithm": DIGEST_ALGORITHM,
        "pipeline_payload": pipeline_payload,
        "model_payload": model_payload,
    }
    encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True)
    envelope["repository_absolute_path_in_payload"] = bool(
        re.search(r"(?:^[A-Za-z]:[\\/]|^/|^\\\\)", encoded, re.MULTILINE)
    )
    return envelope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("LEFT", "RIGHT"))
    return parser


def compare_identities(left_path: Path, right_path: Path) -> None:
    left = json.loads(left_path.read_text(encoding="utf-8"))
    right = json.loads(right_path.read_text(encoding="utf-8"))
    fields = (
        "upstream_inventory_sha256",
        "pipeline_digest",
        "model_digest",
        "digest_algorithm",
    )
    for field in fields:
        if left.get(field) != right.get(field):
            raise ValueError(f"DIGEST_IDENTITY_MISMATCH:{field}")
    if left.get("repository_absolute_path_in_payload") is not False:
        raise ValueError("DIGEST_ABSOLUTE_PATH_LEAK_LEFT")
    if right.get("repository_absolute_path_in_payload") is not False:
        raise ValueError("DIGEST_ABSOLUTE_PATH_LEAK_RIGHT")
    if left.get("pipeline_payload") != right.get("pipeline_payload"):
        raise ValueError("DIGEST_PIPELINE_PAYLOAD_MISMATCH")
    if left.get("model_payload") != right.get("model_payload"):
        raise ValueError("DIGEST_MODEL_PAYLOAD_MISMATCH")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.compare is not None:
        compare_identities(*args.compare)
        print("M3_STAGE3CAR2_DIGEST_IDENTITY_MATCH")
        return 0
    payload = build_identity()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
