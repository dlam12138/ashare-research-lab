"""M2 Stage 2K.1R3/R4A composite tamper test.

Proves the validator recomputes from upstream and rejects any capsule that
self-reports inputs, source tiers, values, record digests, score_input_ids, or
the capsule digest. Since Stage 2K.1R4A, the capsule's resolved_records audit
snapshot must also match the authoritative recomputation
(capsule_snapshot_mismatch). Upstream artifacts are left untouched.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ashare_research.scoring import capsule as cap  # noqa: E402
from ashare_research.scoring import validator as v  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _load_upstream(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _write_upstream(path: str, data: dict) -> None:
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    fails = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    # sanest to build/validate against the real committed artifacts
    capsule = cap.build_capsule()
    base = v.validate_capsule(capsule)
    check("baseline validate passes", base["status"] == "pass", f"errors={base['errors']}")

    # --- tamper 1: transform_inputs + output value + score_input_id ---
    tampered = json.loads(json.dumps(capsule))
    comp = tampered["components"]["eq_gross_margin"]
    comp["transform_inputs"] = {"revenue": "999999", "operating_cost": "1"}
    comp["selected_value_decimal"] = "0.999999"
    comp["score_input_id"] = "0" * 64
    comp["resolved_source_tier"] = "canonical_fact_verified"
    tampered["capsule_digest"] = cap.capsule_digest(tampered)
    r = v.validate_capsule(tampered)
    check(
        "tamper inputs/value/id rejected",
        r["status"] == "fail",
        "errors=" + "; ".join(r["errors"][:4]),
    )
    check(
        "value mismatch detected",
        any("upstream_recomputed_value_mismatch" in e for e in r["errors"]),
    )
    check(
        "score_input_id mismatch detected",
        any("score_input_id_mismatch" in e for e in r["errors"]),
    )

    # --- tamper 2: capsule resolved_records snapshot mismatch is rejected ---
    # Stage 2K.1R4A (problem #3): the validator must require the capsule's
    # resolved_records audit snapshot to match the authoritative recomputation.
    # A tampered snapshot (wrong raw_value / record_digest) fails closed with
    # capsule_snapshot_mismatch even when the score_input_id is left correct.
    tampered2 = json.loads(json.dumps(capsule))
    rec = tampered2["components"]["eq_gross_margin"]["resolved_records"][0]
    rec["raw_value"] = "999999"
    rec["record_digest"] = "0" * 64
    tampered2["capsule_digest"] = cap.capsule_digest(tampered2)
    r2 = v.validate_capsule(tampered2)
    check(
        "tampered resolved_records snapshot rejected (audit snapshot mismatch)",
        r2["status"] == "fail",
        "errors=" + "; ".join(r2["snapshot_errors"][:4]),
    )
    check(
        "capsule_snapshot_mismatch detected",
        any("capsule_snapshot_mismatch" in e for e in r2["snapshot_errors"]),
    )
    check(
        "audit_snapshot_status=fail",
        r2["audit_snapshot_status"] == "fail",
    )
    # ...and if the capsule also claims a wrong score_input_id, it must fail.
    tampered2b = json.loads(json.dumps(tampered2))
    tampered2b["components"]["eq_gross_margin"]["score_input_id"] = "0" * 64
    tampered2b["capsule_digest"] = cap.capsule_digest(tampered2b)
    r2b = v.validate_capsule(tampered2b)
    check(
        "wrong score_input_id rejected even with tampered snapshot",
        r2b["status"] == "fail",
        "errors=" + "; ".join(r2b["errors"][:4]),
    )

    # --- tamper 3: source tier claim without touching upstream ---
    tampered3 = json.loads(json.dumps(capsule))
    tampered3["components"]["eq_roe"]["resolved_source_tier"] = "coverage_gap"
    tampered3["capsule_digest"] = cap.capsule_digest(tampered3)
    r3 = v.validate_capsule(tampered3)
    check(
        "tamper source tier rejected",
        r3["status"] == "fail",
        "errors=" + "; ".join(r3["errors"][:4]),
    )
    check(
        "source_tier_mismatch detected",
        any("source_tier_mismatch" in e for e in r3["errors"]),
    )

    # --- tamper 4: capsule digest only ---
    tampered4 = json.loads(json.dumps(capsule))
    tampered4["capsule_digest"] = "0" * 64
    r4 = v.validate_capsule(tampered4)
    check(
        "tamper capsule digest rejected",
        r4["status"] == "fail",
        "errors=" + "; ".join(r4["errors"][:4]),
    )
    check(
        "capsule_digest mismatch detected",
        any("capsule_digest_mismatch" in e for e in r4["errors"]),
    )

    # --- tamper 5: removed component (upstream registry untouched) ---
    tampered5 = json.loads(json.dumps(capsule))
    del tampered5["components"]["eq_roic"]
    tampered5["component_count"] = len(tampered5["components"])
    tampered5["capsule_digest"] = cap.capsule_digest(tampered5)
    r5 = v.validate_capsule(tampered5)
    check(
        "removed component rejected",
        r5["status"] == "fail",
        "errors=" + "; ".join(r5["errors"][:4]),
    )

    # --- tamper 6: coverage_gap count / observation count on a risk slot ---
    tampered6 = json.loads(json.dumps(capsule))
    tampered6["components"]["rk_gap_count"]["selected_value_decimal"] = "0"
    tampered6["components"]["rk_gap_count"]["resolved_records"] = []
    tampered6["capsule_digest"] = cap.capsule_digest(tampered6)
    r6 = v.validate_capsule(tampered6)
    check(
        "tamper gap count rejected",
        r6["status"] == "fail",
        "errors=" + "; ".join(r6["errors"][:4]),
    )

    print()
    if fails:
        print(f"RESULT: {len(fails)} FAILED")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
