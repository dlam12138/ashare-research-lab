"""M2 Stage 2K.1R4C.1 identity diagnostic tool (read-only).

Produces a minimal, deterministic fingerprint of the score-input identity chain
(schema ``scoring_identity_fingerprint_v1``) and compares two fingerprints to
report the FIRST mismatch path. Used by the CI ubuntu/windows compare jobs to
prove cross-platform identity.

The fingerprint contains NO absolute paths and NO run time: every value is
derived from committed inputs and the deterministic engine, so identical
inputs on any platform produce byte-identical fingerprints. Components are
sorted by component_id; the output is canonical JSON (sorted keys, compact
separators).

CLI:
    python -m ashare_research.tools.m2_stage2k1r4c1_identity_diagnose \\
        --fingerprint --output <path>
    python -m ashare_research.tools.m2_stage2k1r4c1_identity_diagnose \\
        --compare <fingerprint-a.json> <fingerprint-b.json>

Exit codes: 0 = ok / identical; 1 = difference found (compare) or error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import validator as validator_mod

FINGERPRINT_SCHEMA = "scoring_identity_fingerprint_v1"
FINGERPRINT_VERSION = "1.0"

_CANONICAL_SEP = (",", ":")


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def _registry_digest() -> str:
    registry = cap._load(cap.REGISTRY_PATH)
    return cap._sha256_bytes(cap._canonical(registry))


def build_fingerprint() -> dict[str, Any]:
    """Build the identity fingerprint for the current committed inputs.

    Read-only: never writes reports, never touches the market cache, never
    mutates any config. The fingerprint embeds the identity chain from
    artifact digests up to the sensitivity ledger digest.
    """
    capsule = cap.build_capsule()
    lineage_report = validator_mod.validate_capsule(capsule)
    lineage_report["report_digest"] = cap._sha256_bytes(
        cap._canonical(lineage_report)
    )
    confidence = confidence_mod.build_confidence(capsule, lineage_report)
    sensitivity = sensitivity_mod.build_sensitivity_v7(capsule, confidence)

    components: dict[str, Any] = {}
    for cid in sorted(capsule["components"]):
        comp = capsule["components"][cid]
        records = []
        for r in comp.get("resolved_records", []):
            records.append(
                {
                    "artifact_logical_path": r["artifact_logical_path"],
                    "algorithm": r["artifact_digest_algorithm"],
                    "sha256": r["artifact_sha256"],
                    "byte_size": r["artifact_byte_size"],
                    "record_id": r["record_id"],
                    "record_digest": r["record_digest"],
                }
            )
        components[cid] = {
            "score_input_id": comp["score_input_id"],
            "records": records,
        }

    return {
        "schema": FINGERPRINT_SCHEMA,
        "version": FINGERPRINT_VERSION,
        "symbol": capsule["symbol"],
        "capsule_schema": capsule["schema"],
        "capsule_digest": capsule["capsule_digest"],
        "time_contract_digest": cap.time_contract_digest(),
        "registry_digest": _registry_digest(),
        "sensitivity_schema": sensitivity["schema"],
        "sensitivity_ledger_digest": sensitivity["ledger_digest"],
        "components": components,
        "scenario_ids": [s["scenario_id"] for s in sensitivity["scenarios"]],
    }


def fingerprint_digest(fingerprint: dict[str, Any]) -> str:
    """Canonical digest of the fingerprint itself (excluding ``fingerprint_digest``)."""
    payload = {k: v for k, v in fingerprint.items() if k != "fingerprint_digest"}
    return cap._sha256_bytes(_canonical_bytes(payload))


def compare_fingerprints(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare two fingerprints; report the FIRST mismatch as a nested path.

    Returns ``{"identical": True/False, "first_mismatch_path": ..., ...}``.
    The walk is deterministic (sorted keys for dicts; list order preserved).
    """
    mismatches: list[dict[str, Any]] = []

    def walk(pa: Any, pb: Any, path: str) -> None:
        if mismatches:
            return  # only the first mismatch is reported
        if isinstance(pa, dict) and isinstance(pb, dict):
            keys = sorted(set(pa) | set(pb))
            for k in keys:
                if k not in pa:
                    mismatches.append(
                        {"path": f"{path}.{k}", "reason": "missing_in_a",
                         "a": None, "b": pb[k]}
                    )
                    return
                if k not in pb:
                    mismatches.append(
                        {"path": f"{path}.{k}", "reason": "missing_in_b",
                         "a": pa[k], "b": None}
                    )
                    return
                walk(pa[k], pb[k], f"{path}.{k}")
            return
        if isinstance(pa, list) and isinstance(pb, list):
            if len(pa) != len(pb):
                mismatches.append(
                    {"path": f"{path}", "reason": "length_mismatch",
                     "a": len(pa), "b": len(pb)}
                )
                return
            for i, (x, y) in enumerate(zip(pa, pb, strict=False)):
                walk(x, y, f"{path}[{i}]")
            return
        if pa != pb:
            mismatches.append(
                {"path": path, "reason": "value_mismatch", "a": pa, "b": pb}
            )

    walk(a, b, "fingerprint")
    if mismatches:
        m = mismatches[0]
        return {
            "identical": False,
            "first_mismatch_path": m["path"],
            "reason": m["reason"],
            "a": m["a"],
            "b": m["b"],
            "fingerprint_digest_a": fingerprint_digest(a),
            "fingerprint_digest_b": fingerprint_digest(b),
        }
    return {
        "identical": True,
        "fingerprint_digest": fingerprint_digest(a),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M2 Stage 2K.1R4C.1 identity diagnostic")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fingerprint")
    p.add_argument("--output", required=True)

    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")

    args = parser.parse_args(argv)

    if args.command == "fingerprint":
        fp = build_fingerprint()
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(fp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "output": str(out)}, ensure_ascii=False))
        return 0

    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))
    result = compare_fingerprints(a, b)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
