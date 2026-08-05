"""M2 Stage 2K.1R4C.1 identity diagnostic tool (read-only), envelope v2.

Produces a deterministic identity fingerprint **envelope** (schema
``scoring_identity_fingerprint_envelope_v2``) with two strictly separated parts:

- ``provenance`` — where/when the fingerprint was built: ``runner_os`` (from
  ``platform.system()``), ``matrix_platform`` (explicit CI matrix value), and
  ``github_sha`` (from ``GITHUB_SHA`` env or an explicit ``--github-sha``). This
  part is platform-specific and MUST differ between the ubuntu and windows CI
  jobs.
- ``identity`` — the cross-platform score-input identity chain (artifact digests,
  record ids, score-input ids, capsule digest, time contract, registry digest,
  scenario ids, sensitivity ledger digest). This part MUST be byte-identical
  between ubuntu and windows. ``identity_digest`` is the canonical SHA-256 of
  ``identity`` alone.

The envelope contains NO absolute paths and NO run time: every identity value is
derived from committed inputs and the deterministic engine.

``compare`` first gates on provenance (left = ubuntu/Linux, right = windows/Windows,
same github_sha), then compares only ``identity`` + ``identity_digest`` and reports
the FIRST mismatch path. Any provenance-gate failure exits non-zero.

CLI:
    python -m ashare_research.tools.m2_stage2k1r4c1_identity_diagnose \\
        fingerprint --output <path> [--matrix-platform ubuntu|windows] \\
                    [--github-sha <sha>]
    python -m ashare_research.tools.m2_stage2k1r4c1_identity_diagnose \\
        compare <envelope-a.json> <envelope-b.json>

Exit codes: 0 = ok / identical; 1 = provenance gate or identity difference (or error).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import validator as validator_mod

ENVELOPE_SCHEMA = "scoring_identity_fingerprint_envelope_v2"
ENVELOPE_VERSION = "2.0"

#: Canonical matrix platform names (match the CI workflow matrix `platform`).
PLATFORM_UBUNTU = "ubuntu"
PLATFORM_WINDOWS = "windows"

#: runner_os (platform.system()) -> canonical matrix platform name (fallback).
_PLATFORM_BY_RUNNER_OS = {
    "Linux": PLATFORM_UBUNTU,
    "Windows": PLATFORM_WINDOWS,
    "Darwin": "macos",
}

#: Expected provenance of the left / right envelope in a compare.
_LEFT_RUNNER_OS = "Linux"
_LEFT_PLATFORM = PLATFORM_UBUNTU
_RIGHT_RUNNER_OS = "Windows"
_RIGHT_PLATFORM = PLATFORM_WINDOWS

_CANONICAL_SEP = (",", ":")


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def _registry_digest() -> str:
    registry = cap._load(cap.REGISTRY_PATH)
    return cap._sha256_bytes(cap._canonical(registry))


# ---------------------------------------------------------------------------
# Identity payload (cross-platform identical)
# ---------------------------------------------------------------------------


def build_identity() -> dict[str, Any]:
    """Build the cross-platform identity payload.

    Read-only: never writes reports, never touches the market cache, never mutates
    any config. Every value is derived from committed inputs and the deterministic
    engine, so identical inputs on any platform produce byte-identical payloads.
    Components are sorted by component_id; the payload contains no provenance, no
    absolute paths, and no run time.
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


# ---------------------------------------------------------------------------
# Envelope (provenance + identity + identity_digest)
# ---------------------------------------------------------------------------


def build_envelope(
    *,
    matrix_platform: str | None = None,
    github_sha: str | None = None,
) -> dict[str, Any]:
    """Build a fingerprint envelope for the current platform / commit.

    ``matrix_platform`` defaults to a canonical name derived from
    ``platform.system()`` (Linux -> ubuntu, Windows -> windows). ``github_sha``
    defaults to the ``GITHUB_SHA`` environment variable (set by GitHub Actions)
    or ``None`` when run outside CI.
    """
    runner_os = platform.system()
    if matrix_platform is None:
        matrix_platform = _PLATFORM_BY_RUNNER_OS.get(runner_os)
    if github_sha is None:
        github_sha = os.environ.get("GITHUB_SHA")

    identity = build_identity()
    envelope: dict[str, Any] = {
        "schema": ENVELOPE_SCHEMA,
        "version": ENVELOPE_VERSION,
        "provenance": {
            "runner_os": runner_os,
            "matrix_platform": matrix_platform,
            "github_sha": github_sha,
        },
        "identity": identity,
    }
    envelope["identity_digest"] = identity_digest(envelope)
    return envelope


def identity_digest(envelope: dict[str, Any]) -> str:
    """Canonical SHA-256 of the envelope's ``identity`` payload only."""
    return cap._sha256_bytes(_canonical_bytes(envelope["identity"]))


# ---------------------------------------------------------------------------
# Gated compare
# ---------------------------------------------------------------------------


def _provenance_of(envelope: dict[str, Any]) -> dict[str, Any]:
    return envelope.get("provenance") or {}


def _gate_fail(
    gate: str, reason: str, a: Any = None, b: Any = None, path: str | None = None
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "identical": False,
        "gate": gate,
        "reason": reason,
    }
    if path is not None:
        out["first_mismatch_path"] = path
    if a is not None:
        out["a"] = a
    if b is not None:
        out["b"] = b
    return out


def compare_envelopes(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare two envelopes under the cross-platform provenance contract.

    Hard gates, in order:
      1. both envelopes use the v2 schema;
      2. left provenance is ubuntu (``runner_os == Linux``, ``matrix_platform ==
         ubuntu``);
      3. right provenance is windows (``runner_os == Windows``, ``matrix_platform
         == windows``);
      4. ``github_sha`` is present and identical on both sides;
      5. ``identity_digest`` is identical;
      6. ``identity`` payloads are deeply identical (first mismatch reported).

    Any failed gate returns ``identical: false`` with the failing gate name.
    """
    if a.get("schema") != ENVELOPE_SCHEMA or b.get("schema") != ENVELOPE_SCHEMA:
        return _gate_fail(
            "schema",
            f"expected schema {ENVELOPE_SCHEMA!r}",
            a.get("schema"),
            b.get("schema"),
        )

    pa, pb = _provenance_of(a), _provenance_of(b)
    if not (
        pa.get("runner_os") == _LEFT_RUNNER_OS
        and pa.get("matrix_platform") == _LEFT_PLATFORM
    ):
        return _gate_fail(
            "provenance_left",
            f"left must be {_LEFT_PLATFORM}/{_LEFT_RUNNER_OS}",
            pa,
        )
    if not (
        pb.get("runner_os") == _RIGHT_RUNNER_OS
        and pb.get("matrix_platform") == _RIGHT_PLATFORM
    ):
        return _gate_fail(
            "provenance_right",
            f"right must be {_RIGHT_PLATFORM}/{_RIGHT_RUNNER_OS}",
            pb,
        )
    if pa.get("github_sha") != pb.get("github_sha") or not pa.get("github_sha"):
        return _gate_fail(
            "github_sha",
            "github_sha must be present and identical",
            pa.get("github_sha"),
            pb.get("github_sha"),
        )

    mismatches: list[dict[str, Any]] = []

    def walk(x: Any, y: Any, path: str) -> None:
        if mismatches:
            return  # only the first mismatch is reported
        if isinstance(x, dict) and isinstance(y, dict):
            keys = sorted(set(x) | set(y))
            for k in keys:
                if k not in x:
                    mismatches.append(
                        {"path": f"{path}.{k}", "reason": "missing_in_a",
                         "a": None, "b": y[k]}
                    )
                    return
                if k not in y:
                    mismatches.append(
                        {"path": f"{path}.{k}", "reason": "missing_in_b",
                         "a": x[k], "b": None}
                    )
                    return
                walk(x[k], y[k], f"{path}.{k}")
            return
        if isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                mismatches.append(
                    {"path": path, "reason": "length_mismatch",
                     "a": len(x), "b": len(y)}
                )
                return
            for i, (m, n) in enumerate(zip(x, y, strict=False)):
                walk(m, n, f"{path}[{i}]")
            return
        if x != y:
            mismatches.append(
                {"path": path, "reason": "value_mismatch", "a": x, "b": y}
            )

    # the detailed identity walk runs first so an identity difference reports
    # the FIRST mismatch path (not just a digest mismatch)
    walk(a["identity"], b["identity"], "identity")
    if mismatches:
        m = mismatches[0]
        out: dict[str, Any] = _gate_fail(
            "identity", m["reason"], m.get("a"), m.get("b"), path=m["path"],
        )
        out["identity_digest_a"] = identity_digest(a)
        out["identity_digest_b"] = identity_digest(b)
        return out

    # identity payloads are equal; now verify the digest bindings are intact
    digest_a = identity_digest(a)
    digest_b = identity_digest(b)
    stored_a = a.get("identity_digest")
    stored_b = b.get("identity_digest")
    if stored_a != digest_a or stored_b != digest_b or stored_a != stored_b:
        return _gate_fail(
            "identity_digest",
            "identity_digest must match its own identity payload and be identical",
            stored_a,
            stored_b,
        )

    return {
        "identical": True,
        "gate": "ok",
        "identity_digest": digest_a,
        "provenance_left": pa,
        "provenance_right": pb,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M2 Stage 2K.1R4C.1 identity diagnostic (envelope v2)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fingerprint")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--matrix-platform",
        choices=[PLATFORM_UBUNTU, PLATFORM_WINDOWS],
        default=None,
        help="canonical CI matrix platform (default: derived from runner_os)",
    )
    p.add_argument(
        "--github-sha",
        default=None,
        help="commit sha (default: $GITHUB_SHA env)",
    )

    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")

    args = parser.parse_args(argv)

    if args.command == "fingerprint":
        env = build_envelope(
            matrix_platform=args.matrix_platform,
            github_sha=args.github_sha,
        )
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "output": str(out)}, ensure_ascii=False))
        return 0

    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))
    result = compare_envelopes(a, b)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
