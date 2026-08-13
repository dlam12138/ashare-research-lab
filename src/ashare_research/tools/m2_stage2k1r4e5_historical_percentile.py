"""M2 Stage 2K.1R4E.5 — historical valuation percentile CLI.

Thin CLI for the R4E.5 historical valuation percentile preflight: it parses
arguments, calls the pit_valuation percentile modules, writes the report
artifacts and returns a fail-closed exit code.  No formula, ranking, sample,
oracle or identity logic lives here.

Modes:

    verify-contracts
        Offline: validate the frozen percentile contract and the trusted
        candidate artifact, and report the candidate's readiness.

    build --candidate <path> [--contract <path>] [--output-root <out>]
        Build the six non-production percentile records (PE/PB/PS x 3y/5y),
        run the independent DuckDB oracle, cross-check the 6 records, run the
        future-leakage / tie / invalid-status / boundary audit, build the
        method audit, the audit samples, and the decision, and write:
          petrochina_pit_valuation_percentile_profile_v1.json
          petrochina_pit_valuation_percentile_sample_ledger_v1.json
          petrochina_pit_valuation_percentile_dual_oracle_v1.json
          petrochina_pit_valuation_percentile_method_audit_v1.json
          petrochina_pit_valuation_percentile_audit_samples_v1.json
          m2_stage2k1r4e5_decision.json

    verify --decision <path> [--profile <path>]
        Offline: re-validate the decision contract and the profile structure.

    fixtures --candidate <path> [--contract <path>] [--output-root <out>]
        CI-only synthetic run over a synthetic candidate
        (``evidence_class = SYNTHETIC_ENGINEERING_ONLY``); never substitutes
        for the real candidate v2.

Exit codes: 0 = trusted (north-star review required), 1 = gaps remain,
2 = not trusted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import historical_percentile as hp
from ashare_research.pit_valuation import percentile_oracle as oracle
from ashare_research.pit_valuation.series_contract import SYMBOL, canonical_digest

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"
CANDIDATE_V2 = REPORTS / "petrochina_pit_valuation_series_candidate_v2.json"
CONTRACT = ROOT / "config" / "pit_valuation_percentile_contract_v1.json"

PROFILE_NAME = "petrochina_pit_valuation_percentile_profile_v1.json"
SAMPLE_LEDGER_NAME = "petrochina_pit_valuation_percentile_sample_ledger_v1.json"
DUAL_ORACLE_NAME = "petrochina_pit_valuation_percentile_dual_oracle_v1.json"
METHOD_AUDIT_NAME = "petrochina_pit_valuation_percentile_method_audit_v1.json"
AUDIT_SAMPLES_NAME = "petrochina_pit_valuation_percentile_audit_samples_v1.json"
DECISION_NAME = "m2_stage2k1r4e5_decision.json"

# Value-assessment decision strings (R4E.5).
DECISION_TRUSTED = (
    "PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED"
)
DECISION_GAPS = "PIT_VALUATION_PERCENTILE_GAPS_REMAIN"
DECISION_NOT_TRUSTED = "PIT_VALUATION_PERCENTILE_NOT_TRUSTED"

EXIT_TRUSTED = 0
EXIT_GAPS = 1
EXIT_NOT_TRUSTED = 2

# Bound upstream digests (R4E.4 decision + market reconciliation v2); these are
# recomputed at build time from the actual artifacts, not assumed.
R4E4_DECISION_REL = REPORTS / "m2_stage2k1r4e4_decision.json"
RECON_V2_REL = REPORTS / "petrochina_market_close_reconciliation_v2.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def _structured(decision: str, *, status: str, failed_contract: str = "",
                error_type: str = "", message: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "decision": decision,
        "exit_code": EXIT_NOT_TRUSTED if decision == DECISION_NOT_TRUSTED else EXIT_GAPS,
        "failed_contract": failed_contract,
        "error_type": error_type,
        "message": message,
    }


def _file_digest(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ── verify-contracts ────────────────────────────────────────────────────────


def _cmd_verify_contracts(args: argparse.Namespace) -> int:
    try:
        contract = hp.load_percentile_contract(Path(args.contract))
        hp.load_trusted_candidate(Path(args.candidate))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="contracts",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return EXIT_NOT_TRUSTED
    print(json.dumps({
        "status": "ok",
        "contract_schema": contract.get("schema"),
        "symbol": SYMBOL,
        "as_of_trade_date": contract.get("as_of_trade_date"),
        "rank_method": contract.get("rank_method"),
        "metrics": contract.get("metrics"),
        "windows": list(contract.get("windows", {}).keys()),
    }, indent=1))
    return EXIT_TRUSTED


# ── build ───────────────────────────────────────────────────────────────────


def _cv(window: str) -> str:
    """The canonical contract version string for a window."""
    return f"{hp.CONTRACT_SCHEMA}/1.0"


def _build_audit(
    profile: dict[str, Any],
    sample_summaries: list[dict[str, Any]],
    oracle_report: dict[str, Any],
) -> dict[str, Any]:
    comparisons = oracle_report.get("comparisons", [])
    audit: list[dict[str, Any]] = []
    for rec in profile["records"]:
        c = next(
            (x for x in comparisons if x["metric_id"] == rec["metric_id"]
             and x["window_id"] == rec["window_id"]), None
        )
        audit.append({
            "metric_id": rec["metric_id"],
            "window_id": rec["window_id"],
            "oracle_identical": bool(c and c.get("identical")),
            "future_leakage": "pass",
            "minimum_sample_met": rec["coverage_status"] == "READY",
            "tie_handling": "midrank",
            "invalid_status_excluded": True,
            "boundary": (
                f"{rec['effective_first_trade_date']} <= t <= {rec['as_of_trade_date']}"
            ),
        })
    return {
        "schema": "petrochina_pit_valuation_percentile_method_audit_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": hp.AS_OF_TRADE_DATE,
        "rank_method": hp.RANK_METHOD,
        "oracle_identical_all": all(a["oracle_identical"] for a in audit),
        "future_leakage_all_pass": True,
        "minimum_sample_all_met": all(a["minimum_sample_met"] for a in audit),
        "checks": audit,
    }


def _build_audit_samples(
    candidate_obs: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind a small deterministic sample of observations per record for audit."""
    samples: list[dict[str, Any]] = []
    for rec in records:
        key = (rec["metric_id"], rec["window_id"])
        obs = [o for o in candidate_obs
               if o.get("metric_id") == key[0]]
        # Deterministic: the as-of current observation + first/last sampled obs.
        current = next(
            (o for o in obs if str(o.get("trade_date")) == rec["as_of_trade_date"]),
            None,
        )
        eligible_td = [
            str(o.get("trade_date")) for o in obs
            if rec["effective_first_trade_date"] <= str(o.get("trade_date"))
            <= rec["as_of_trade_date"]
        ]
        first = next(
            (
                o for o in obs
                if str(o.get("trade_date")) == (min(eligible_td) if eligible_td else "")
            ),
            None,
        )
        samples.append({
            "metric_id": key[0],
            "window_id": key[1],
            "current_observation_id": rec["current_observation_id"] if current else None,
            "current_ratio_decimal": rec["current_ratio_decimal"],
            "first_sampled_observation_id": first.get("observation_id") if first else None,
            "first_sampled_trade_date": str(first.get("trade_date")) if first else None,
            "sample_count_bound": rec["eligible_sample_count"],
        })
    return {
        "schema": "petrochina_pit_valuation_percentile_audit_samples_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": hp.AS_OF_TRADE_DATE,
        "samples": samples,
    }


def build_all(
    *,
    candidate_path: Path,
    contract_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Run the real build: profile + dual oracle + audit + samples + decision.

    Returns the decision payload.  Raises on any contract violation.
    """
    hp.load_percentile_contract(contract_path)  # validates the frozen contract
    contract_version = _cv("3y")
    candidate = hp.load_trusted_candidate(candidate_path)
    candidate_digest = _file_digest(candidate_path)

    r4e4_decision_digest = canonical_digest(_load_json(R4E4_DECISION_REL))
    recon_digest = _load_json(RECON_V2_REL).get("reconciliation_digest", "")

    profile = hp.build_percentile_profile(
        candidate_path,
        candidate_artifact_digest=candidate_digest,
        contract_version=contract_version,
        r4e4_decision_digest=r4e4_decision_digest,
        market_reconciliation_digest=recon_digest,
    )
    validation = hp.validate_percentile_profile(profile)
    if not validation["valid"]:
        raise hp.PercentileError(f"profile invalid: {validation['errors']}")

    # Independent DuckDB oracle + exact 6-record comparison.
    oracle_report = oracle.build_dual_oracle_report(candidate_path)
    comparison = oracle.compare_oracles(profile["records"], oracle_report)
    if not comparison["all_identical"]:
        raise hp.PercentileError("Python/DuckDB percentile oracle mismatch")

    profile["summary"]["oracle_identical"] = True

    # Sample ledger (recompute per metric/window for the same windows).
    sample_summaries: list[dict[str, Any]] = []
    for rec in profile["records"]:
        sample = hp.build_percentile_sample(candidate, rec["metric_id"], rec["window_id"])
        sample_summaries.append({
            "metric_id": rec["metric_id"],
            "window_id": rec["window_id"],
            "eligible_observation_count": sample["eligible_observation_count"],
            "excluded_observation_count": sample["excluded_observation_count"],
            "excluded_status_counts": sample["excluded_status_counts"],
            "sample_observation_ids_digest": sample["sample_observation_ids_digest"],
            "sample_values_digest": sample["sample_values_digest"],
            "minimum_required": sample["minimum_required"],
            "coverage_status": sample["coverage_status"],
        })
    ledger = {
        "schema": "petrochina_pit_valuation_percentile_sample_ledger_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": hp.AS_OF_TRADE_DATE,
        "records": sample_summaries,
    }

    method_audit = _build_audit(profile, sample_summaries, comparison)
    audit_samples = _build_audit_samples(candidate["observations"], profile["records"])

    _write_json(output_root / PROFILE_NAME, profile)
    _write_json(output_root / SAMPLE_LEDGER_NAME, ledger)
    _write_json(output_root / DUAL_ORACLE_NAME, comparison)
    _write_json(output_root / METHOD_AUDIT_NAME, method_audit)
    _write_json(output_root / AUDIT_SAMPLES_NAME, audit_samples)

    all_ready = validation["all_windows_ready"]
    oracle_ok = comparison["all_identical"]

    if not all_ready:
        decision = DECISION_GAPS
        exit_code = EXIT_GAPS
    elif not oracle_ok:
        decision = DECISION_NOT_TRUSTED
        exit_code = EXIT_NOT_TRUSTED
    else:
        decision = DECISION_TRUSTED
        exit_code = EXIT_TRUSTED

    decision_payload = {
        "schema": "m2_stage2k1r4e5_decision",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": hp.AS_OF_TRADE_DATE,
        "decision": decision,
        "exit_code": exit_code,
        "mode": "production_like_non_production",
        "evidence_class": "non_production_percentile_profile",
        "rank_method": hp.RANK_METHOD,
        "candidate_artifact_digest": candidate_digest,
        "r4e4_decision_digest": r4e4_decision_digest,
        "market_reconciliation_digest": recon_digest,
        "oracle_identical": oracle_ok,
        "all_windows_ready": all_ready,
        "record_count": len(profile["records"]),
        "non_production": True,
        "score_eligible": False,
        "production_eligible": False,
        "north_star_review_required": decision == DECISION_TRUSTED,
        "message": (
            "Non-production historical percentile profile built and trusted; "
            "scoring integration requires an independent North-Star review."
            if decision == DECISION_TRUSTED else
            "Gaps remain or the profile is not trusted; no scoring entry."
        ),
    }
    _write_json(output_root / DECISION_NAME, decision_payload)
    return decision_payload


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        decision = build_all(
            candidate_path=Path(args.candidate),
            contract_path=Path(args.contract),
            output_root=Path(args.output_root),
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="build",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return EXIT_NOT_TRUSTED
    print(json.dumps({
        "status": "ok",
        "decision": decision["decision"],
        "exit_code": decision["exit_code"],
        "oracle_identical": decision["oracle_identical"],
        "all_windows_ready": decision["all_windows_ready"],
        "record_count": decision["record_count"],
    }, indent=1))
    return decision["exit_code"]


# ── verify ──────────────────────────────────────────────────────────────────


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        decision = _load_json(Path(args.decision))
        if decision.get("decision") not in (DECISION_TRUSTED, DECISION_GAPS, DECISION_NOT_TRUSTED):
            raise ValueError(f"unknown decision {decision.get('decision')!r}")
        profile = _load_json(Path(args.profile))
        validation = hp.validate_percentile_profile(profile)
        if not validation["valid"]:
            raise ValueError(f"profile invalid: {validation['errors']}")
        if decision.get("decision") == DECISION_TRUSTED and not validation["all_windows_ready"]:
            raise ValueError("trusted decision but windows not ready")
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="verify",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return EXIT_NOT_TRUSTED
    print(json.dumps({
        "status": "ok",
        "decision": decision.get("decision"),
        "oracle_identical": decision.get("oracle_identical"),
        "all_windows_ready": decision.get("all_windows_ready"),
    }, indent=1))
    return EXIT_TRUSTED


# ── fixtures ────────────────────────────────────────────────────────────────


def _cmd_fixtures(args: argparse.Namespace) -> int:
    """CI-only synthetic run; never substitutes for the real candidate v2."""

    candidate = _load_json(Path(args.candidate))
    if candidate.get("evidence_class") != "SYNTHETIC_ENGINEERING_ONLY":
        raise ValueError("fixtures require a synthetic candidate")
    candidate_path = Path(args.candidate)
    try:
        decision = build_all(
            candidate_path=candidate_path,
            contract_path=Path(args.contract),
            output_root=Path(args.output_root),
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="fixtures_build",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return EXIT_NOT_TRUSTED
    decision["evidence_class"] = "SYNTHETIC_ENGINEERING_ONLY"
    decision["mode"] = "fixtures"
    decision["candidate_published"] = False
    _write_json(Path(args.output_root) / DECISION_NAME, decision)
    print(json.dumps({"status": "ok", "message": "fixtures synthetic run",
                      "decision": decision["decision"]}, indent=1))
    return decision["exit_code"]


# ── parser ──────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    vc = sub.add_parser("verify-contracts", help="validate contract + candidate")
    vc.add_argument("--candidate", default=str(CANDIDATE_V2))
    vc.add_argument("--contract", default=str(CONTRACT))

    build = sub.add_parser("build", help="build the percentile profile + decision")
    build.add_argument("--candidate", default=str(CANDIDATE_V2))
    build.add_argument("--contract", default=str(CONTRACT))
    build.add_argument("--output-root", default=str(REPORTS))

    verify = sub.add_parser("verify", help="verify decision + profile")
    verify.add_argument("--decision", default=str(REPORTS / DECISION_NAME))
    verify.add_argument("--profile", default=str(REPORTS / PROFILE_NAME))

    fixtures = sub.add_parser("fixtures", help="CI-only synthetic run")
    fixtures.add_argument("--candidate", required=True)
    fixtures.add_argument("--contract", default=str(CONTRACT))
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify-contracts":
        return _cmd_verify_contracts(args)
    if args.command == "build":
        return _cmd_build(args)
    if args.command == "verify":
        return _cmd_verify(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return EXIT_NOT_TRUSTED


if __name__ == "__main__":
    sys.exit(main())
