"""M2 Stage 2K.1R4E — thin CLI for the PIT valuation series preflight.

This CLI only parses arguments, calls the pit_valuation package modules, writes
report artifacts and returns an exit code.  No formula, join, TTM or identity
logic lives here.

Commands:

    verify-contracts
        Offline validation of every R4E contract (no market cache required).

    formal --market-cache-root <root> --output-root <out>
            [--reported-bundle <path> --reconciled-bundle <path>]
        Build the candidate PE/PB/PS series from the verified external market
        cache and the committed fact bundles, and write all reports.

    fixtures --output-root <out> --fixture-root <root>
        Build the candidate series from synthetic fixtures (CI only).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ashare_research.pit_valuation import (
    financial_state,
    series_contract,
    series_validation,
    valuation_series,
)

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"

REPORT_FILES = {
    "timeline": "petrochina_pit_financial_state_timeline_v1.json",
    "candidate": "petrochina_pit_valuation_series_candidate_v1.json",
    "coverage": "petrochina_pit_valuation_series_coverage_v1.json",
    "audit": "petrochina_pit_valuation_series_audit_samples_v1.json",
    "dual": "petrochina_pit_valuation_series_dual_oracle_validation_v1.json",
    "decision": "m2_stage2k1r4e_decision.json",
    "manifest": "m2_stage2k1r4e_artifact_manifest.json",
}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def _load_bundles(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    if getattr(args, "reported_bundle", None):
        reported_path = Path(args.reported_bundle)
    else:
        reported_path = REPORTS / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
    if getattr(args, "reconciled_bundle", None):
        reconciled_path = Path(args.reconciled_bundle)
    else:
        reconciled_path = REPORTS / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
    reported = json.loads(reported_path.read_text(encoding="utf-8"))["facts"]
    reconciled = json.loads(reconciled_path.read_text(encoding="utf-8"))["facts"]
    return reported, reconciled


def _cmd_verify_contracts(args: argparse.Namespace) -> int:
    digests = series_contract.validate_all_contracts()
    print(json.dumps(digests, indent=1))
    return 0


def _build_series(
    *,
    output_root: Path,
    reported: list[dict],
    reconciled: list[dict],
    market_rows: list[dict],
    market_meta: dict,
) -> dict:
    """Shared pipeline: timelines -> series -> validation -> reports."""
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    series = valuation_series.build_valuation_series(market_rows, market_meta, timelines)
    verification = series_validation.verify_observations(series)
    coverage = series_validation.build_coverage_report(series, timelines)
    audit = series_validation.select_audit_samples(series, timelines)
    dual = series_validation.validate_dual_oracle(market_rows, timelines)

    timeline_report = {
        "schema": "petrochina_pit_financial_state_timeline_v1",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "summary": financial_state.state_timeline_summary(timelines),
        "timelines": timelines,
    }
    _write_json(output_root / REPORT_FILES["timeline"], timeline_report)
    _write_json(output_root / REPORT_FILES["candidate"], series)
    _write_json(output_root / REPORT_FILES["coverage"], coverage)
    _write_json(output_root / REPORT_FILES["audit"], {"samples": audit})
    _write_json(output_root / REPORT_FILES["dual"], dual)

    decision_payload = {
        "schema": "m2_stage2k1r4e_decision",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "contracts_trusted": True,
        "financial_state_timeline_trusted": True,
        "dual_oracle_identical": dual["all_identical"],
        "identity_consistent": verification["identity_consistent"],
        "ratio_consistent": verification["ratio_consistent"],
        "market_reconciliation_status": market_meta["reconciliation_status"],
        "coverage": {
            metric: {
                "3y_ready": coverage["per_metric"][metric]["3y_ready"],
                "5y_ready": coverage["per_metric"][metric]["5y_ready"],
            }
            for metric in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
        },
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
        "decision": _decide(
            dual=dual,
            verification=verification,
            coverage=coverage,
            market_reconciliation_status=market_meta["reconciliation_status"],
        ),
    }
    _write_json(output_root / REPORT_FILES["decision"], decision_payload)
    return {
        "series": series,
        "verification": verification,
        "coverage": coverage,
        "audit": audit,
        "dual": dual,
        "decision": decision_payload,
        "timelines": timelines,
        "market_meta": market_meta,
    }


def _decide(*, dual, verification, coverage, market_reconciliation_status) -> str:
    """Three-state fail-closed decision gate."""
    if not dual["all_identical"]:
        return "PIT_VALUATION_SERIES_NOT_TRUSTED"
    if not (verification["identity_consistent"] and verification["ratio_consistent"]):
        return "PIT_VALUATION_SERIES_NOT_TRUSTED"
    if market_reconciliation_status != "pass":
        return "PIT_VALUATION_SERIES_GAPS_REMAIN"
    all_ready = all(
        coverage["per_metric"][m]["3y_ready"] and coverage["per_metric"][m]["5y_ready"]
        for m in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
    )
    if not all_ready:
        return "PIT_VALUATION_SERIES_GAPS_REMAIN"
    return "PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED"


def _cmd_formal(args: argparse.Namespace) -> int:
    series_contract.validate_all_contracts()
    reported, reconciled = _load_bundles(args)
    registry = series_contract.load_market_snapshot_registry()
    market_rows, market_meta = valuation_series.load_primary_market_cache(
        Path(args.market_cache_root), registry
    )
    result = _build_series(
        output_root=Path(args.output_root),
        reported=reported,
        reconciled=reconciled,
        market_rows=market_rows,
        market_meta=market_meta,
    )
    _write_manifest(Path(args.output_root), result, mode="real")
    print(f"decision: {result['decision']['decision']}")
    print(f"market_reconciliation: {market_meta['reconciliation_status']}")
    return 0


def _cmd_fixtures(args: argparse.Namespace) -> int:
    """CI-only synthetic run; never substitutes for the formal candidate."""
    from ashare_research.pit_valuation import fixtures

    series_contract.validate_all_contracts()
    reported, reconciled = fixtures.load_fixture_bundles(Path(args.fixture_root))
    market_rows, market_meta = fixtures.load_fixture_market(Path(args.fixture_root))
    result = _build_series(
        output_root=Path(args.output_root),
        reported=reported,
        reconciled=reconciled,
        market_rows=market_rows,
        market_meta=market_meta,
    )
    _write_manifest(Path(args.output_root), result, mode="fixtures")
    print(f"decision: {result['decision']['decision']}")
    return 0


def _write_manifest(output_root: Path, result: dict, *, mode: str) -> None:
    manifest = {
        "schema": "m2_stage2k1r4e_artifact_manifest",
        "version": "1.0",
        "mode": mode,
        "market_reconciliation_status": result["market_meta"]["reconciliation_status"],
        "decision": result["decision"]["decision"],
        "observation_count": result["series"]["observation_count"],
        "dual_oracle_identical": result["dual"]["all_identical"],
        "identity_consistent": result["verification"]["identity_consistent"],
        "ratio_consistent": result["verification"]["ratio_consistent"],
        "artifacts": [
            {
                "name": name,
                "path": _relative_posix(output_root, filename),
            }
            for name, filename in REPORT_FILES.items()
            if Path(output_root / filename).exists()
        ],
    }
    _write_json(output_root / REPORT_FILES["manifest"], manifest)


def _relative_posix(output_root: Path, filename: str) -> str:
    """Return a stable forward-slash relative artifact path (no drive letters)."""
    from pathlib import PurePosixPath

    return str(PurePosixPath(str(output_root)) / filename)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verify-contracts", help="validate all R4E contracts")

    formal = sub.add_parser("formal", help="build candidate series from real external cache")
    formal.add_argument("--market-cache-root", required=True)
    formal.add_argument("--output-root", default=str(REPORTS))
    formal.add_argument("--reported-bundle", default=None)
    formal.add_argument("--reconciled-bundle", default=None)

    fixtures = sub.add_parser(
        "fixtures", help="build candidate series from synthetic fixtures (CI)"
    )
    fixtures.add_argument("--fixture-root", required=True)
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify-contracts":
        return _cmd_verify_contracts(args)
    if args.command == "formal":
        return _cmd_formal(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
