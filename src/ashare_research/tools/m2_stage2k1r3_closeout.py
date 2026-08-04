"""M2 Stage 2K.1R4A closeout CLI orchestrator (thin).

Thin CLI only: parses arguments, dispatches to the scoring modules, writes the
output, and enforces fail-closed exit codes. Business logic lives in
``ashare_research.scoring.{capsule,validator,confidence,shadow,sensitivity,
artifact_manifest}``.

Exit codes (fail-closed):
  0 = success (build / resolve / validate pass / verify pass)
  1 = validate or verify-artifacts FAILED (validation errors present;
      any artifact-manifest check failure)
  2 = contract / parameter / internal error (bad args, missing config, exception,
      unsupported manifest schema, missing manifest)
  3 = external cache required for real mode but missing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.scoring import artifact_manifest as am
from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import market_observation_set as mos
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import shadow as shadow_mod
from ashare_research.scoring import validator as validator_mod

EXIT_OK = 0
EXIT_CHECK_FAIL = 1
EXIT_CONTRACT_ERROR = 2
EXIT_EXTERNAL_CACHE_MISSING = 3

# Default manifest verified by `verify-artifacts` when --manifest is not given.
# This is the current stage's committed artifact manifest.
DEFAULT_MANIFEST = cap.ROOT / "reports" / "m2_stage2k1r4c_artifact_manifest.json"

# subcommands that run a validation/verification gate and must exit 1 on failure
CHECK_COMMANDS = {"validate", "verify-artifacts"}


def _write_output(output: str, result: dict[str, Any]) -> None:
    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "output": str(out)}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _build_args() -> tuple[Path | None, Path | None, Path | None, str, str, argparse.Namespace]:
    """Return (cache_root, fixture_root, market_registry, mode,
    market_validation_mode, args). Real cache mode demands an external cache
    root; without it, exit 3."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    def add_output(p):
        p.add_argument("--output", default="")
        p.add_argument("--market-cache-root", default=None)
        p.add_argument("--market-fixture-root", default=None)
        p.add_argument("--market-registry", default=None)

    for cmd in (
        "resolve",
        "build-capsule",
        "validate",
        "build-market-observation-set",
        "build-confidence",
        "build-shadow",
        "build-sensitivity",
    ):
        p = sub.add_parser(cmd)
        add_output(p)
    # verify-artifacts takes an explicit --manifest path (defaults to the
    # current stage's committed artifact manifest when omitted).
    p = sub.add_parser("verify-artifacts")
    add_output(p)
    p.add_argument("--manifest", default=None)

    args = parser.parse_args()
    cache_root = Path(args.market_cache_root) if args.market_cache_root else None
    fixture_root = Path(args.market_fixture_root) if args.market_fixture_root else None
    market_registry = Path(args.market_registry) if args.market_registry else None

    if args.command == "build-market-observation-set" and cache_root is None:
        # real observation set requires an external cache
        print(
            json.dumps(
                {"status": "error", "error_code": "external_cache_required",
                 "message": "--market-cache-root required for real observation set"},
                ensure_ascii=False,
            )
        )
        sys.exit(EXIT_EXTERNAL_CACHE_MISSING)

    mode = "real_research" if cache_root else "test_capsule"
    market_validation_mode = "external_verified_cache" if cache_root else "synthetic_test_capsule"
    return cache_root, fixture_root, market_registry, mode, market_validation_mode, args


def _build_capsule(cache_root, fixture_root, market_registry, market_validation_mode):
    return cap.build_capsule(
        market_cache_root=cache_root,
        market_fixture_root=fixture_root,
        market_validation_mode=market_validation_mode,
        market_registry=market_registry,
    )


def _validate(cache_root, fixture_root, market_registry, market_validation_mode):
    capsule = _build_capsule(cache_root, fixture_root, market_registry, market_validation_mode)
    return validator_mod.validate_capsule(
        capsule, market_cache_root=cache_root, market_fixture_root=fixture_root,
        market_registry=market_registry,
    )


def _lineage_report(cache_root, fixture_root, market_registry, market_validation_mode):
    rep = _validate(cache_root, fixture_root, market_registry, market_validation_mode)
    rep["report_digest"] = cap._sha256_bytes(cap._canonical(rep))
    return rep


def main() -> int:
    try:
        cache_root, fixture_root, market_registry, mode, mvm, args = _build_args()
    except SystemExit as exc:
        return int(exc.code or 0)

    try:
        if args.command == "resolve":
            result = _build_capsule(cache_root, fixture_root, market_registry, mvm)
            result = {"status": "resolve", "component_count": result["component_count"]}
        elif args.command == "build-capsule":
            result = _build_capsule(cache_root, fixture_root, market_registry, mvm)
        elif args.command == "validate":
            result = _validate(cache_root, fixture_root, market_registry, mvm)
        elif args.command == "build-market-observation-set":
            result = mos.build_observation_set(
                registry_path=market_registry or cap.MARKET_REGISTRY,
                mode=mode,
                cache_root=cache_root,
                fixture_root=fixture_root,
                symbol=cap.SYMBOL,
                market_data_as_of_date="2026-07-31",
                scorecard_formed_at="2026-08-02",
            )
        elif args.command == "build-confidence":
            rep = _lineage_report(cache_root, fixture_root, market_registry, mvm)
            capsule = _build_capsule(cache_root, fixture_root, market_registry, mvm)
            result = confidence_mod.build_confidence(capsule, rep)
        elif args.command == "build-shadow":
            rep = _lineage_report(cache_root, fixture_root, market_registry, mvm)
            capsule = _build_capsule(cache_root, fixture_root, market_registry, mvm)
            confidence = confidence_mod.build_confidence(capsule, rep)
            result = shadow_mod.build_shadow(capsule, confidence)
        elif args.command == "build-sensitivity":
            capsule = _build_capsule(cache_root, fixture_root, market_registry, mvm)
            rep = _lineage_report(cache_root, fixture_root, market_registry, mvm)
            confidence = confidence_mod.build_confidence(capsule, rep)
            result = sensitivity_mod.build_sensitivity_v6(capsule, confidence)
        elif args.command == "verify-artifacts":
            manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST
            if not manifest_path.is_file():
                print(
                    json.dumps(
                        {"status": "error", "error_code": "manifest_not_found",
                         "message": f"artifact manifest not found: {manifest_path}"},
                        ensure_ascii=False,
                    )
                )
                return EXIT_CONTRACT_ERROR
            result = am.verify_artifact_manifest(
                manifest_path, repository_root=cap.ROOT
            ).to_dict()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error_code": "internal_error", "message": str(exc)}))
        return EXIT_CONTRACT_ERROR

    _write_output(args.output, result)

    if args.command in CHECK_COMMANDS and result.get("status") != "pass":
        return EXIT_CHECK_FAIL
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
