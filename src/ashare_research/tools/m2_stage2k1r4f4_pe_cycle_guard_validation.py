"""M2 Stage 2K.1R4F.4 — thin CLI (build / verify / oracle / fixtures).

Argument parsing and orchestration only.  All validation logic lives in
``pe_cycle_guard_validation.py`` and the reused R4F.3 resolver.  Fully
offline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ashare_research.pit_valuation.pe_cycle_context_preflight import (  # noqa: E402
    merge_fact_bundles,
)
from ashare_research.pit_valuation.pe_cycle_guard_validation import (  # noqa: E402
    build_3y_series,
    build_decision,
    build_denominator_state_ledger,
    build_direction_audit,
    build_divergence,
    build_recurrence_audit,
    build_transition_audit,
    compute_midrank_percentile,
)

REPORTED_BUNDLE = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
BACKFILL_BUNDLE = (
    ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json"
)
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"

SERIES_OUT = ROOT / "reports" / "petrochina_pe_3y_normalized_pe_series_v1.json"
LEDGER_OUT = ROOT / "reports" / "petrochina_pe_3y_denominator_state_ledger_v1.json"
DIRECTION_OUT = ROOT / "reports" / "petrochina_pe_3y_cycle_guard_direction_audit_v1.json"
TRANSITION_OUT = (
    ROOT / "reports" / "petrochina_pe_3y_denominator_transition_audit_v1.json"
)
DIVERGENCE_OUT = (
    ROOT / "reports" / "petrochina_pe_3y_raw_vs_normalized_divergence_v1.json"
)
PERCENTILE_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_3y_percentile_profile_v1.json"
)
DECISION_OUT = ROOT / "reports" / "m2_stage2k1r4f4_decision.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_facts() -> list[dict]:
    reported = _load_json(REPORTED_BUNDLE).get("facts", [])
    reconciled = _load_json(RECONCILED_BUNDLE).get("facts", [])
    backfill = _load_json(BACKFILL_BUNDLE).get("facts", [])
    return merge_fact_bundles(reported, reconciled) + backfill


def _load_observations() -> list[dict]:
    return _load_json(CANDIDATE_V2).get("observations", [])


def _build_all(as_of: str) -> dict[str, dict]:
    facts = _load_facts()
    observations = _load_observations()
    series = build_3y_series(facts, observations)
    ledger = build_denominator_state_ledger(series)
    direction = build_direction_audit(series)
    recurrence = build_recurrence_audit(direction)
    transition = build_transition_audit(series)
    divergence = build_divergence(series, ledger)
    # current normalized PE (2026-07-31 observation)
    current = next(
        o
        for o in observations
        if o.get("metric_id") == "PE_A_TTM" and o.get("trade_date") == as_of
    )
    es = None
    from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
        build_normalized_earnings_state,
        build_normalized_pe_state,
        resolve_annual_roe_chain_as_of,
        resolve_current_bvps_as_of,
    )

    roe = resolve_annual_roe_chain_as_of(facts, as_of)
    bvps = resolve_current_bvps_as_of(facts, as_of)
    es = build_normalized_earnings_state(facts, as_of, roe_chain=roe, bvps=bvps)
    pe_state = build_normalized_pe_state(
        facts, as_of, current, earnings_state=es
    )
    values = [r["normalized_pe_decimal"] for r in series["rows"]]
    current_norm_pe = pe_state.get("normalized_pe_decimal")
    percentile = compute_midrank_percentile(values, current_norm_pe)
    percentile_profile = {
        "schema": "pe_normalized_3y_percentile_profile_v1",
        "symbol": "601857.SH",
        "as_of_trade_date": as_of,
        "window": {"start": series["window"]["start"], "end": series["window"]["end"]},
        "n": len(values),
        "current_normalized_pe_decimal": current_norm_pe,
        "current_raw_pe_decimal": current.get("ratio_decimal"),
        "current_raw_pe_3y_percentile": _raw_pe_3y_percentile(),
        "percentile": percentile,
        "comparison": "DESCRIPTIVE_DENOMINATOR_NORMALIZATION_COMPARISON",
        "no_buy_sell_interpretation": True,
        "not_scoring_input": True,
    }
    decision = build_decision(
        series=series,
        direction=direction,
        recurrence=recurrence,
        transition=transition,
        percentile_ok=True,  # oracle check runs separately
    )
    return {
        "series": series,
        "ledger": ledger,
        "direction": direction,
        "recurrence": recurrence,
        "transition": transition,
        "divergence": divergence,
        "percentile": percentile_profile,
        "decision": decision,
    }


def _raw_pe_3y_percentile() -> str:
    """Bind the committed R4E.5 raw PE 3y percentile record."""
    profile = _load_json(
        ROOT / "reports" / "petrochina_pit_valuation_percentile_profile_v1.json"
    )
    for r in profile.get("records", []):
        if r.get("metric_id") == "PE_A_TTM" and r.get("window_id") == "3y":
            return r["midrank_percentile_decimal"]
    return ""


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def cmd_build(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    _write(SERIES_OUT, out["series"])
    _write(LEDGER_OUT, out["ledger"])
    _write(DIRECTION_OUT, out["direction"])
    _write(TRANSITION_OUT, out["transition"])
    _write(DIVERGENCE_OUT, out["divergence"])
    _write(PERCENTILE_OUT, out["percentile"])
    _write(DECISION_OUT, out["decision"])
    print(f"decision: {out['decision']['decision']} ({out['decision']['verdict']})")
    print(
        f"series: {out['series']['trade_day_count']}/728 | "
        f"raw states: {out['ledger']['unique_raw_ttm_denominator_states']} | "
        f"norm states: {out['ledger']['unique_normalized_denominator_states']}"
    )
    print(
        f"direction violations: {out['direction']['direction_violation_count']} | "
        f"recurrence: {out['recurrence']['result']}"
    )
    print(
        f"current normalized PE: {out['percentile'].get('current_normalized_pe_decimal')} | "
        f"3y percentile: {out['percentile']['percentile']['midrank_percentile_decimal']}"
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    failures = 0
    for name, path in (
        ("series", SERIES_OUT),
        ("ledger", LEDGER_OUT),
        ("direction", DIRECTION_OUT),
        ("transition", TRANSITION_OUT),
        ("divergence", DIVERGENCE_OUT),
        ("percentile", PERCENTILE_OUT),
        ("decision", DECISION_OUT),
    ):
        committed = _load_json(path)
        rebuilt = out[name]
        if committed != rebuilt:
            print(f"FAIL: {name} differs from committed artifact ({path})")
            failures += 1
        else:
            print(f"pass: {name} byte-identical")
    return 1 if failures else 0


def cmd_oracle(args: argparse.Namespace) -> int:
    """Independent DuckDB midrank-percentile oracle."""
    import duckdb

    profile = _load_json(PERCENTILE_OUT)
    values = [float(v) for v in _series_normalized_pe_values()]
    current = float(profile["current_normalized_pe_decimal"])
    con = duckdb.connect()
    con.execute("CREATE TABLE t (v DOUBLE)")
    con.executemany("INSERT INTO t VALUES (?)", [(v,) for v in values])
    less = con.execute("SELECT count(*) FROM t WHERE v < ?", [current]).fetchone()[0]
    equal = con.execute("SELECT count(*) FROM t WHERE v = ?", [current]).fetchone()[0]
    greater = con.execute("SELECT count(*) FROM t WHERE v > ?", [current]).fetchone()[0]
    n = len(values)
    num = 2 * less + equal + 1
    den = 2 * n
    pct = 100.0 * num / den
    py = profile["percentile"]
    ok = (
        py["count_less"] == less
        and py["count_equal"] == equal
        and py["count_greater"] == greater
        and py["rank_numerator"] == num
        and py["rank_denominator"] == den
    )
    print(
        f"oracle: N={n} L={less} E={equal} G={greater} "
        f"rank={num}/{den} pct={pct:.6f} | python match: {ok}"
    )
    return 0 if ok else 1


def _series_normalized_pe_values() -> list[str]:
    series = _load_json(SERIES_OUT)
    return [r["normalized_pe_decimal"] for r in series["rows"]]


def cmd_fixtures(args: argparse.Namespace) -> int:
    """Write a deterministic synthetic later-restatement fixture for tests."""

    facts = _load_facts()
    later = []
    for i, f in enumerate(facts):
        if f.get("concept_id") == "equity_attributable_to_parent" and f.get(
            "period_end"
        ) == "2018-12-31":
            later.append(
                {
                    "concept_id": f["concept_id"],
                    "period_end": f["period_end"],
                    "value": 1214067000000.0,
                    "unit": f["unit"],
                    "fact_id": f"r4f4-synthetic-later-restate-{i}",
                    "available_at": "2025-06-01",
                    "effective_from": "2025-06-02",
                    "supersedes_fact_id": f["fact_id"],
                    "restatement_version": "restated_1",
                }
            )
    payload = {
        "schema": "r4f4_synthetic_later_restatement_bundle_v1",
        "facts": later,
    }
    out = ROOT / "tmp" / "r4f4_synthetic_later_restatement.json"
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"wrote {out} ({len(later)} synthetic facts)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="R4F4 cycle-guard validation CLI")
    sub = p.add_subparsers(dest="command", required=True)
    for name, fn in (
        ("build", cmd_build),
        ("verify", cmd_verify),
        ("oracle", cmd_oracle),
        ("fixtures", cmd_fixtures),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--as-of", default="2026-07-31")
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
