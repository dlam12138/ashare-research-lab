"""Explicit recovery-capsule helpers for Stage 3D-B-R1.

No network transport is imported here.  Acquisition callers may use the frozen
Stage 3D-B transport only after Gate A has frozen the inventory and only write
responses to the overlay via :func:`write_once_overlay`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.tools.m3_stage3dbr1_market_recovery import (
    resolve_capsule_file,
    sha256_file,
    write_once_overlay,
)


def initialize_recovery_capsule(
    recovery_root: str | Path,
    *,
    base_root: str | Path,
    base_event_sha256: str,
    recovery_adapter_digest: str,
) -> dict[str, Any]:
    """Create only recovery metadata directories and immutable references."""

    root = Path(recovery_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "raw_overlay" / "akshare").mkdir(parents=True, exist_ok=True)
    (root / "manifests").mkdir(parents=True, exist_ok=True)
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    event = {
        "stage": "M3_STAGE3DBR1",
        "recovery_class": "POST_UNSEAL_TECHNICAL_ADAPTER_RECOVERY",
        "base_capsule": "D:/m3_stage3db_holdout_retry",
        "base_capsule_event_sha256": base_event_sha256,
        "recovery_adapter_digest": recovery_adapter_digest,
        "raw_price_parse_before_gate_a": False,
        "primary_statistic_observed_before_repair": False,
        "accepted_primary_execution_count": 0,
    }
    event_path = root / "recovery_event.json"
    if event_path.exists() and json.loads(event_path.read_text(encoding="utf-8")) != event:
        raise ValueError("M3_STAGE3DBR1_RECOVERY_EVENT_IMMUTABLE_CONFLICT")
    if not event_path.exists():
        event_path.write_text(
            json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    base_ref = {
        "identity": "BASE_IMMUTABLE_CAPSULE",
        "base_root": "D:/m3_stage3db_holdout_retry",
        "base_event_sha256": base_event_sha256,
        "write_policy": "BASE_PREFERRED_OVERLAY_CONFLICT_ON_SHA_MISMATCH",
    }
    ref_path = root / "base_capsule_ref.json"
    if ref_path.exists() and json.loads(ref_path.read_text(encoding="utf-8")) != base_ref:
        raise ValueError("M3_STAGE3DBR1_BASE_REF_IMMUTABLE_CONFLICT")
    if not ref_path.exists():
        ref_path.write_text(
            json.dumps(base_ref, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return event


def build_logical_raw_capsule_manifest(
    base_root: str | Path,
    overlay_root: str | Path,
    relative_paths: list[str],
    *,
    required_symbols: list[str],
    never_eligible_files: int,
    metadata_insufficient_count: int,
) -> dict[str, Any]:
    """Build a hash-first BASE+OVERLAY manifest without parsing any price rows."""

    resolved = [
        resolve_capsule_file(base_root, overlay_root, path) for path in sorted(relative_paths)
    ]
    by_symbol = {
        Path(item["path"]).stem.removeprefix("daily_"): item
        for item in resolved
        if Path(item["path"]).name.startswith("daily_")
    }
    required_items = [
        by_symbol.get(symbol, {"source": "MISSING", "path": f"daily_{symbol}.csv", "sha256": None})
        for symbol in sorted(required_symbols)
    ]
    base_digest = sha256_file(Path(base_root) / "holdout_unseal_event.json")
    payload: dict[str, Any] = {
        "stage": "M3_STAGE3DBR1",
        "base_capsule_manifest_digest": base_digest,
        "base_file_count": sum(item["source"] == "BASE" for item in resolved),
        "overlay_file_count": sum(item["source"] == "OVERLAY" for item in resolved),
        "required_universe_count": len(required_symbols),
        "required_already_available_count": sum(
            item["source"] == "BASE" for item in required_items
        ),
        "required_recovered_count": sum(item["source"] == "OVERLAY" for item in required_items),
        "required_still_missing_count": sum(item["source"] == "MISSING" for item in required_items),
        "never_eligible_original_files_count": never_eligible_files,
        "metadata_insufficient_count": metadata_insufficient_count,
        "required_series": required_items,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    import hashlib

    payload["recovered_raw_capsule_digest"] = hashlib.sha256(encoded).hexdigest()
    return payload


__all__ = [
    "build_logical_raw_capsule_manifest",
    "initialize_recovery_capsule",
    "resolve_capsule_file",
    "sha256_file",
    "write_once_overlay",
]
