"""Stage 2G.2 offline reproducibility entry point.

The CLI has deliberately explicit modes.  Test-capsule mode consumes only
committed snapshot contracts and generated synthetic market rows.  Real mode
requires an explicit canonical Fact DB and an explicit external market-cache
root; it never falls back to either test or default local data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ashare_research.reproducibility.artifacts import verify_artifacts
from ashare_research.reproducibility.capsule import (
    MARKET_FIXTURE_DIR,
    build_temp_fact_db,
    build_test_capsule,
    export_facts,
    validate_snapshot,
    verify_capsule_manifest,
)
from ashare_research.reproducibility.market import MarketSnapshotResolver
from ashare_research.reproducibility.rule007 import RULE007_PAIR_REGISTRY
from ashare_research.tools.petrochina_valuation_and_value_profile import (
    EVENT_PATH,
    EVIDENCE_PATH,
    ROOT,
    _load_canonical_facts,
    _load_market,
    run_formal,
    validate_dividend_evidence,
)

COMMITTED_SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
COMMITTED_REGISTRY = ROOT / "events" / "market_data_snapshot_registry.json"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def verify_contracts() -> dict[str, Any]:
    snapshot = validate_snapshot(COMMITTED_SNAPSHOT)
    registry = json.loads(COMMITTED_REGISTRY.read_text(encoding="utf-8"))
    MarketSnapshotResolver.validate_registry_contract(registry)
    evidence = validate_dividend_evidence()
    if any(
        item["event"]["event_id"] in evidence["rule007_eligible_events"]
        and any(
            source.get("source_type") == "designated_disclosure_platform"
            for source in item["sources"]
        )
        for item in evidence["eligible"]
    ):
        raise ValueError("designated_disclosure_platform cannot satisfy Rule007")
    serialized_registry = COMMITTED_REGISTRY.read_text(encoding="utf-8")
    if "D:\\" in serialized_registry or "D:/" in serialized_registry:
        raise ValueError("committed market registry contains an absolute path")
    source_text = (
        ROOT / "src" / "ashare_research" / "tools" / "petrochina_valuation_and_value_profile.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "D:\\量化分析-cache",
        "data/parquet/stock_daily/601857_SH.parquet",
    ):
        if forbidden in source_text:
            raise ValueError(f"formal runner contains forbidden portability reference: {forbidden}")
    return {
        "status": "pass_with_explicit_gaps" if evidence["gaps"] else "pass",
        "snapshot": {
            "row_count": snapshot["row_count"],
            "facts_sha256": snapshot["facts_sha256"],
            "identity": snapshot["manifest"]["identity_validation"],
            "version_chain": snapshot["manifest"]["version_chain_validation"],
        },
        "market_registry": {
            "contract": registry["contract"],
            "providers": len(registry["providers"]),
            "path_portable": True,
        },
        "dividend_evidence": {
            "status": evidence["status"],
            "rule007_eligible_event_count": evidence["rule007_eligible_event_count"],
            "gaps": len(evidence["gaps"]),
        },
        "rule007_contract": RULE007_PAIR_REGISTRY,
        "network_used": False,
    }


def run_test_capsule(
    capsule_dir: Path | str, output_root: Path | str | None = None
) -> dict[str, Any]:
    root = Path(capsule_dir)
    manifest = verify_capsule_manifest(root)
    snapshot_dir = root / "canonical_fact_snapshot_v1"
    temp_db = root / "temporary_fact.duckdb"
    if not temp_db.is_file():
        build_temp_fact_db(snapshot_dir, temp_db)
    run_root = Path(output_root) if output_root is not None else root / "runs"
    result = run_formal(
        output_root=run_root,
        run_id="stage2g2_test_capsule",
        fact_db=temp_db,
        registry_path=root / "market_data_snapshot_registry_v2.json",
        market_mode="test_capsule",
        market_fixture_root=root / MARKET_FIXTURE_DIR,
        publish_reports=False,
        fact_input_contract={
            "logical_name": "canonical_fact_snapshot_v1/facts.json",
            "schema_version": manifest["inputs"]["canonical_fact_snapshot"].get(
                "contract_version", "stage2g_canonical_fact_snapshot_v1"
            ),
            "sha256": manifest["inputs"]["canonical_fact_snapshot"]["sha256"],
            "row_count": manifest["inputs"]["canonical_fact_snapshot"]["row_count"],
        },
    )
    artifact = verify_artifacts(Path(result["run_dir"]))
    return {
        "status": "pass",
        "mode": "test_capsule",
        "capsule_contract": manifest["contract"],
        "run_dir": str(Path(result["run_dir"]).name),
        "market_days": result["manifest"]["market_row_count"],
        "observation_count": result["manifest"]["observation_count"],
        "artifact_verification": artifact,
        "network_used": False,
        "default_db_mutated": False,
    }


def verify_real_inputs(
    *,
    fact_db: Path | str,
    market_cache_root: Path | str,
    registry_path: Path | str | None = None,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read-only preflight for explicit real research inputs."""

    facts, fact_meta = _load_canonical_facts(Path(fact_db))
    market, registry = _load_market(
        Path(registry_path) if registry_path is not None else COMMITTED_REGISTRY,
        market_mode="real_research",
        market_cache_root=market_cache_root,
    )
    result = {
        "contract": "stage2g_real_input_preflight_v2",
        "status": "pass",
        "mode": "real_research",
        "fact_db": {
            "logical_name": fact_meta["logical_name"],
            "sha256": fact_meta["sha256"],
            "row_count": fact_meta["fact_count"],
            "identity_status": fact_meta["identity_status"],
            "version_chain_status": fact_meta["version_chain_status"],
        },
        "market": {
            "registry_contract": registry["contract"],
            "row_count": len(market),
            "date_range": {
                "start": str(market["trade_date"].min()),
                "end": str(market["trade_date"].max()),
            },
            "provider_hashes": [record["sha256"] for record in registry["providers"]],
            "reconciliation_status": registry.get("reconciliation_status"),
        },
        "event_evidence_sha256": {
            "events": __import__("hashlib").sha256(EVENT_PATH.read_bytes()).hexdigest(),
            "sources": __import__("hashlib").sha256(EVIDENCE_PATH.read_bytes()).hexdigest(),
        },
        "network_used": False,
        "default_db_mutated": False,
        "fact_rows_used": len(facts),
    }
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_json(result) + "\n", encoding="utf-8")
    return result


def run_real(
    *,
    fact_db: Path | str,
    market_cache_root: Path | str,
    output_root: Path | str,
    run_id: str,
    registry_path: Path | str | None = None,
    publish_reports: bool = False,
) -> dict[str, Any]:
    preflight = verify_real_inputs(
        fact_db=fact_db,
        market_cache_root=market_cache_root,
        registry_path=registry_path,
    )
    result = run_formal(
        output_root=output_root,
        run_id=run_id,
        fact_db=fact_db,
        registry_path=Path(registry_path) if registry_path is not None else COMMITTED_REGISTRY,
        market_mode="real_research",
        market_cache_root=market_cache_root,
        publish_reports=publish_reports,
    )
    return {
        "status": "pass_with_explicit_gaps",
        "preflight": preflight,
        "run_dir": str(Path(result["run_dir"]).name),
        "artifact_verification": verify_artifacts(Path(result["run_dir"])),
        "rule007_eligible_event_count": result["manifest"]["rule007_eligible_event_count"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify-contracts")
    export = sub.add_parser("export-facts")
    export.add_argument("--fact-db", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    build = sub.add_parser("build-test-capsule")
    build.add_argument("--output", type=Path, required=True)
    run_test = sub.add_parser("run-test-capsule")
    run_test.add_argument("--capsule-dir", type=Path, required=True)
    run_test.add_argument("--output", type=Path)
    real_preflight = sub.add_parser("verify-real-inputs")
    real_preflight.add_argument("--fact-db", type=Path, required=True)
    real_preflight.add_argument("--market-cache-root", type=Path, required=True)
    real_preflight.add_argument("--market-registry", type=Path)
    real_preflight.add_argument("--output", type=Path, required=True)
    real = sub.add_parser("run-real")
    real.add_argument("--fact-db", type=Path, required=True)
    real.add_argument("--market-cache-root", type=Path, required=True)
    real.add_argument("--market-registry", type=Path)
    real.add_argument("--output", type=Path, required=True)
    real.add_argument("--run-id", required=True)
    real.add_argument("--publish-reports", action="store_true")
    artifacts = sub.add_parser("verify-artifacts")
    artifacts.add_argument("--run-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify-contracts":
        result = verify_contracts()
    elif args.command == "export-facts":
        result = export_facts(args.fact_db, args.output)
    elif args.command == "build-test-capsule":
        result = build_test_capsule(args.output, committed_snapshot_dir=COMMITTED_SNAPSHOT)
    elif args.command == "run-test-capsule":
        result = run_test_capsule(args.capsule_dir, args.output)
    elif args.command == "verify-real-inputs":
        result = verify_real_inputs(
            fact_db=args.fact_db,
            market_cache_root=args.market_cache_root,
            registry_path=args.market_registry,
            output_path=args.output,
        )
    elif args.command == "run-real":
        result = run_real(
            fact_db=args.fact_db,
            market_cache_root=args.market_cache_root,
            output_root=args.output,
            run_id=args.run_id,
            registry_path=args.market_registry,
            publish_reports=args.publish_reports,
        )
    else:
        result = verify_artifacts(args.run_dir)
    print(_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
