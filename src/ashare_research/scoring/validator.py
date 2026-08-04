"""M2 Stage 2K.1R4A validator.

Recomputes every score input from the upstream records (never trusts the
capsule's claims — value, source tier, score_input_id) and additionally
requires that the capsule's ``resolved_records`` audit snapshot matches the
authoritative recomputation. Fail-closed: any mismatch -> status fail.

This extends the Stage 2K.1R3 validator with the Capsule Audit Snapshot
Consistency check (problem #3): the R3 validator recomputed from upstream but
did not require the capsule's resolved_records snapshot to agree with that
recomputation. Here the snapshot is compared against the authoritative record
set and a mismatch is reported as ``capsule_snapshot_mismatch``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import lineage
from ashare_research.scoring import market_observation_set as mos


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_capsule(
    capsule: dict[str, Any],
    *,
    market_cache_root: Path | None = None,
    market_fixture_root: Path | None = None,
    market_registry: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed validation. Two independent checks:

    - authoritative recomputation: value / source_tier / score_input_id are
      recomputed from the upstream records and compared to the capsule.
    - audit snapshot consistency: the capsule's resolved_records snapshot is
      compared to the authoritative recomputed record set
      (``capsule_snapshot_mismatch`` on any difference).
    """
    errors: list[str] = []
    warnings: list[str] = []
    snapshot_errors: list[str] = []
    registry = _load(cap.UPSTREAM_REGISTRY)
    by_id = {c["component_id"]: c for c in registry["components"]}

    if capsule.get("schema") not in {
        "petrochina_score_input_capsule_v4",
    }:
        errors.append(f"schema mismatch: {capsule.get('schema')!r}")
    if capsule.get("symbol") != cap.SYMBOL:
        errors.append(f"symbol mismatch: {capsule.get('symbol')!r}")

    formed_at = capsule["time_contract"]["scorecard_formed_at"]
    market_as_of = capsule["time_contract"]["market_data_as_of_date"]

    # real mode: rebuild the verified observation set to recompute the real
    # percentiles for the valuation components.
    real_observation_set = None
    if capsule.get("market_validation_mode") == "external_verified_cache":
        real_observation_set = mos.build_observation_set(
            registry_path=market_registry or cap.MARKET_REGISTRY,
            mode="real_research",
            cache_root=market_cache_root,
            fixture_root=None,
            symbol=cap.SYMBOL,
            market_data_as_of_date=market_as_of,
            scorecard_formed_at=formed_at,
        )

    # every registry component must be present in the capsule
    for cid in by_id:
        if cid not in capsule["components"]:
            errors.append(f"{cid}: missing from capsule (must be present)")

    for cid, comp in capsule["components"].items():
        spec = by_id.get(cid)
        if spec is None:
            errors.append(f"{cid}: component not in upstream registry")
            continue
        # recompute records from the upstream registry (independent of capsule)
        try:
            recs = cap._resolve_records(
                spec, market_cache_root=market_cache_root, market_fixture_root=market_fixture_root
            )
        except lineage.LineageError as exc:
            errors.append(f"{cid}: re-resolve failed: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cid}: re-resolve failed: {exc}")
            continue

        # AUDIT SNAPSHOT CONSISTENCY: the capsule's resolved_records snapshot
        # must equal the authoritative recomputed record set.
        authoritative = [cap._record_dict(r) for r in recs]
        snapshot = comp.get("resolved_records", [])
        if authoritative != snapshot:
            snapshot_errors.append(f"{cid}: capsule_snapshot_mismatch")

        # recompute score_input_id from the recomputed upstream records
        try:
            recomputed = cap._make_score_input(
                spec,
                recs,
                market_validation_mode=capsule.get(
                    "market_validation_mode", "synthetic_test_capsule"
                ),
                real_observation_set=real_observation_set,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cid}: recompute score_input failed: {exc}")
            continue

        if recomputed["score_input_id"] != comp.get("score_input_id"):
            errors.append(f"{cid}: score_input_id_mismatch")

        # recompute value
        if recomputed["selected_value_decimal"] != comp.get("selected_value_decimal"):
            errors.append(
                f"{cid}: upstream_recomputed_value_mismatch expected="
                f"{recomputed['selected_value_decimal']!r} "
                f"got={comp.get('selected_value_decimal')!r}"
            )

        # source tier derived by resolver must match capsule claim
        expected_tier = recomputed["resolved_source_tier"]
        claimed_tier = comp.get("resolved_source_tier")
        if expected_tier != claimed_tier:
            errors.append(
                f"{cid}: source_tier_mismatch expected={expected_tier!r} got={claimed_tier!r}"
            )
        # allowed tiers
        allowed = spec.get("allowed_source_tiers", [])
        if expected_tier not in allowed:
            errors.append(
                f"{cid}: source_tier {expected_tier} not allowed for {spec['resolver_id']}"
            )

        # PIT (date-only comparison so timestamps like 2026-08-02T06:30:00+08:00
        # are not misread as after the date-only scorecard_formed_at)
        aa = comp.get("available_at")
        aa_date = (aa or "").split("T")[0]
        if aa_date and aa_date > formed_at:
            errors.append(f"{cid}: available_at {aa} > scorecard_formed_at {formed_at}")

    # capsule digest
    recomputed_digest = cap.capsule_digest(capsule)
    if recomputed_digest != capsule.get("capsule_digest"):
        errors.append("capsule_digest_mismatch")

    authoritative_status = "pass" if not errors else "fail"
    audit_status = "pass" if not snapshot_errors else "fail"
    return {
        "status": "fail" if (errors or snapshot_errors) else "pass",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "authoritative_recomputation_status": authoritative_status,
        "audit_snapshot_status": audit_status,
        "snapshot_errors": snapshot_errors,
        "snapshot_warning_count": len(snapshot_errors),
    }
