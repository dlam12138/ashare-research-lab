"""M2 Stage 2K.1R scoring-input lineage, confidence, and sensitivity tests.

Covers: deterministic capsule identity under lineage tampering (artifact hash /
record / method change the identity; path does not), future percentile PIT
protection, score/coverage/confidence separation, non-compensatory risk vetoes,
complete sensitivity scenarios, recomputable machine-derived stability, and the
absence of every production output.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ashare_research.tools import m2_stage2k1r_capsule as capsule_mod
from ashare_research.tools import m2_stage2k1r_confidence as confidence_mod
from ashare_research.tools import m2_stage2k1r_sensitivity as sensitivity_mod
from ashare_research.tools import m2_stage2k1r_shadow as shadow_mod
from ashare_research.tools import m2_stage2k1r_validate as validate_mod

ROOT = Path(__file__).parents[1]

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]
FORBIDDEN = {
    "overall_score",
    "rank",
    "recommendation",
    "target_price",
    "buy",
    "sell",
    "upside_probability",
    "portfolio_weight",
}


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _walk_keys(value):
    if isinstance(value, dict):
        found = set(value)
        for child in value.values():
            found.update(_walk_keys(child))
        return found
    if isinstance(value, list):
        found = set()
        for child in value:
            found.update(_walk_keys(child))
        return found
    return set()


# --- Capsule determinism and lineage identity ---


def test_capsule_is_deterministic_and_marked_non_production():
    a = capsule_mod.build_capsule()
    b = capsule_mod.build_capsule()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["symbol"] == "601857.SH"
    assert a["score_date"] == "2026-07-31"
    assert a["non_production"] is True
    assert a["score_eligible"] is False
    assert a["overall_score_prohibited"] is True
    assert a["capsule_digest"] == capsule_mod.build_capsule()["capsule_digest"]


def test_score_input_id_changes_on_hash_record_method_value_unit_date():
    """Lineage tampering: any real input change alters the identity."""
    base = capsule_mod.build_capsule()
    comp = base["components"]["eq_gross_margin"]
    up = comp["upstream"]
    args = dict(
        component_id=comp["component_id"],
        upstream=up,
        value=comp["value"],
        unit=comp["unit"],
        date=comp["fiscal_year"],
        available_at=comp["available_at"],
        selection_method=comp["selection_method"],
    )
    base_id = capsule_mod._score_input_id(**args)

    # artifact hash change
    tampered = dict(**args)
    tampered["upstream"] = dict(up, artifact_sha256="deadbeef")
    assert capsule_mod._score_input_id(**tampered) != base_id

    # selection method change
    tampered = dict(**args)
    tampered["selection_method"] = "different method"
    assert capsule_mod._score_input_id(**tampered) != base_id

    # value change
    tampered = dict(**args)
    tampered["value"] = 0.0
    assert capsule_mod._score_input_id(**tampered) != base_id

    # unit change
    tampered = dict(**args)
    tampered["unit"] = "CNY"
    assert capsule_mod._score_input_id(**tampered) != base_id

    # date change (fiscal year / trade date)
    tampered = dict(**args)
    tampered["date"] = 2024
    assert capsule_mod._score_input_id(**tampered) != base_id

    # available_at change
    tampered = dict(**args)
    tampered["available_at"] = "2026-04-01"
    assert capsule_mod._score_input_id(**tampered) != base_id


def test_score_input_id_ignores_logical_path():
    """A path change must NOT alter the identity: the logical path is not part
    of the identity payload."""
    base = capsule_mod.build_capsule()
    comp = base["components"]["eq_gross_margin"]
    up = comp["upstream"]
    args = dict(
        component_id=comp["component_id"],
        upstream=up,
        value=comp["value"],
        unit=comp["unit"],
        date=comp["fiscal_year"],
        available_at=comp["available_at"],
        selection_method=comp["selection_method"],
    )
    base_id = capsule_mod._score_input_id(**args)
    # Same everything except the logical path string.
    moved = dict(**args)
    moved["upstream"] = dict(up, artifact="some/other/path.json")
    assert capsule_mod._score_input_id(**moved) == base_id
    # The artifact path is not in the identity payload.
    identity = {
        "component_id": comp["component_id"],
        "artifact_sha256": up.get("artifact_sha256"),
        "contract": up.get("contract"),
        "record_id": up.get("record_id"),
        "selection_method": comp["selection_method"],
        "value": comp["value"],
        "unit": comp["unit"],
        "date": comp["fiscal_year"],
        "available_at": comp["available_at"],
    }
    assert "artifact" not in identity


def test_every_component_binds_to_artifact_sha256_and_contract():
    capsule = capsule_mod.build_capsule()
    for cid, comp in capsule["components"].items():
        assert comp["upstream"]["artifact_sha256"], cid
        assert comp["upstream"]["contract"], cid
        assert comp["score_input_id"] == capsule_mod._score_input_id(
            comp["component_id"],
            comp["upstream"],
            comp["value"],
            comp["unit"],
            comp["fiscal_year"] or comp["trade_date"],
            comp["available_at"],
            comp["selection_method"],
        ), cid


def test_no_artifact_sha256_is_missing_or_tmp():
    capsule = capsule_mod.build_capsule()
    for cid, comp in capsule["components"].items():
        assert comp["upstream"]["artifact_sha256"] != "MISSING_ARTIFACT", cid
    assert "tmp/" not in json.dumps(capsule)


def test_missing_upstream_becomes_coverage_gap_never_zero():
    capsule = capsule_mod.build_capsule()
    eq_roic = capsule["components"]["eq_roic"]
    assert eq_roic["value"] is None
    assert eq_roic["status"] == "not_computable_under_strict_evidence_contract"
    assert "M2G-ROIC-001" in eq_roic["record_ids"]
    va_dy = capsule["components"]["va_dividend_yield"]
    assert va_dy["value"] is None
    assert va_dy["status"] == "coverage_gap"


# --- Future percentile leakage / PIT protection ---


def test_percentile_binds_to_observation_set_within_score_date():
    capsule = capsule_mod.build_capsule()
    # va_dividend_yield is a coverage gap (no PIT percentile); the four computed
    # valuation components must bind a percentile to an observation set.
    for cid in ("va_pe", "va_pb", "va_ps", "va_fcf_yield"):
        comp = capsule["components"][cid]
        assert comp["percentile_3y"] is not None, cid
        obs = comp["observation_set"]
        assert obs["provider_digest"], cid
        assert obs["provider_sha256"], cid
        assert obs["row_count"] > 0, cid
        # scope must end at or before the score date (no future observations)
        assert obs["scope"].split("..")[1] == "2026-07-31", cid
        # effective samples must meet the minimum per history window
        eff = comp["effective_samples"]
        mn = comp["minimum_samples"]
        for window in ("3y", "5y"):
            assert eff[window] >= mn[window], (cid, window)
    # the dividend-yield coverage gap has no percentile because it is not computed.
    va_dy = capsule["components"]["va_dividend_yield"]
    assert va_dy["percentile_3y"] is None
    assert va_dy["status"] == "coverage_gap"


def test_future_available_at_flagged_as_pit_finding_not_error():
    """Risk metrics are available at 2026-08-02 > score_date 2026-07-31. This
    must be surfaced as a PIT finding (lowers confidence) but not a hard error."""
    capsule = capsule_mod.build_capsule()
    errors, pit_findings = validate_mod.validate_capsule(capsule)
    assert errors == []
    assert any(f.startswith("available_at:rk_") for f in pit_findings)
    assert any("2026-08-02" in f for f in pit_findings)


def test_capsule_validation_status_pass_with_pit_findings():
    capsule = capsule_mod.build_capsule()
    errors, pit_findings = validate_mod.validate_capsule(capsule)
    assert errors == []
    assert len(pit_findings) == 4


# --- Score / coverage / confidence separation ---


def test_score_band_coverage_and_confidence_are_separate_per_dimension():
    shadow = shadow_mod.compute_shadow(capsule_mod.build_capsule())
    confidence = confidence_mod.compute_confidence(capsule_mod.build_capsule())
    for dim in DIMENSIONS:
        if dim == "risk_and_evidence_integrity":
            assert shadow["dimensions"][dim]["representation"] == "status_outputs"
            assert shadow["dimensions"][dim]["no_merged_numeric_score"] is True
            assert "score" not in shadow["dimensions"][dim]
        else:
            assert "score" in shadow["dimensions"][dim]
            assert "band" in shadow["dimensions"][dim]
            assert "coverage_ratio" in shadow["dimensions"][dim]
        assert confidence["dimensions"][dim]["grade"] in {
            "high",
            "medium",
            "low",
            "not_trusted",
        }
        assert "reasons" in confidence["dimensions"][dim]
        assert "supporting_ids" in confidence["dimensions"][dim]


def test_confidence_is_separate_from_score_and_never_zero():
    confidence = confidence_mod.compute_confidence(capsule_mod.build_capsule())
    assert confidence["confidence_separate_from_score"] is True
    for dim in DIMENSIONS:
        # ROIC absence lowers confidence but is never a zero or a "not_trusted"
        # due to the gap alone.
        assert confidence["dimensions"][dim]["grade"] != "not_trusted"
    eq = confidence["dimensions"]["enterprise_quality"]
    assert any("roic_gap" in r for r in eq["reasons"])
    assert any("M2G-ROIC" in sid for sid in eq["supporting_ids"])


def test_confidence_contract_is_versioned_and_frozen():
    conf = _load("config/value_dimension_scoring_confidence_v1.json")
    assert conf["schema"] == "value_dimension_scoring_confidence_v1"
    assert conf["confidence_grade_scale"] == ["high", "medium", "low", "not_trusted"]
    assert conf["roic_rule"]["effect"].startswith("lowers")
    # confidence must be explicitly separated from business quality.
    assert conf["confidence_not_quality"]  # non-empty statement
    assert "never be described as business quality" in conf["confidence_not_quality"]


# --- Non-compensatory risk veto ---


def test_risk_veto_is_non_compensatory_and_blocks_dimension():
    capsule = capsule_mod.build_capsule()
    # Force a triggered veto.
    modified = copy.deepcopy(capsule)
    modified["components"]["rk_veto_triggered"]["value"] = 1
    shadow = shadow_mod.compute_shadow(modified)
    risk = shadow["dimensions"]["risk_and_evidence_integrity"]
    assert risk["risk_veto_status"]["status"] == "blocked_by_risk_veto"
    assert risk["risk_veto_status"]["non_compensatory"] is True
    assert "score" not in risk  # no merged score to hide the veto


def test_risk_dimension_has_no_merged_numeric_score():
    capsule = capsule_mod.build_capsule()
    shadow = shadow_mod.compute_shadow(capsule)
    risk = shadow["dimensions"]["risk_and_evidence_integrity"]
    assert risk["no_merged_numeric_score"] is True
    assert risk["risk_veto_status"]["status"] == "clear"
    assert risk["evidence_integrity"]["grade"] == "medium"


# --- Sensitivity scenarios and stability ---


def test_sensitivity_runs_all_scenario_types_and_reports_metrics():
    result = sensitivity_mod.compute_sensitivity(capsule_mod.build_capsule())
    assert result["schema"] == "petrochina_dimension_scoring_sensitivity_v2"
    assert result["thresholds_frozen_before_rerun"] is True
    assert result["synthetic_values_are_not_company_facts"] is True
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        d = result["dimensions"][dim]
        for key in (
            "base_score",
            "min_score",
            "max_score",
            "max_score_delta",
            "band_flip_count",
            "insufficient_evidence_count",
            "veto_block_count",
            "scenario_count",
            "stability_status",
            "production_readiness_reason",
        ):
            assert key in d, (dim, key)
        assert d["stability_status"] in ("STABLE", "NOT_STABLE")
        assert d["scenario_count"] > 0


def test_sensitivity_is_deterministic_and_stability_machine_derived():
    a = sensitivity_mod.compute_sensitivity(capsule_mod.build_capsule())
    b = sensitivity_mod.compute_sensitivity(capsule_mod.build_capsule())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    for dim in a["dimensions"].values():
        delta = dim["max_score_delta"]
        tolerance = dim["stability_tolerance"]
        # stability_status must equal the machine-derived condition.
        expected = (
            "STABLE"
            if (
                delta is not None
                and delta <= tolerance
                and dim["band_flip_count"] == 0
                and dim["insufficient_evidence_count"] == 0
                and dim["veto_block_count"] == 0
            )
            else "NOT_STABLE"
        )
        assert dim["stability_status"] == expected


def test_sensitivity_synthetic_roic_is_not_a_company_fact():
    capsule = capsule_mod.build_capsule()
    mod = sensitivity_mod._capsule_with_roic(capsule, "synthetic_neutral")
    roic = mod["components"]["eq_roic"]
    assert roic["is_synthetic"] is True
    assert roic["status"] == "synthetic_neutral"
    assert "never a company fact" in roic["note"]
    # The base capsule's ROIC is never synthetic.
    assert "is_synthetic" not in capsule["components"]["eq_roic"]


def test_sensitivity_does_not_mutate_frozen_breakpoints():
    """The frozen-transform scenario must restore the pristine breakpoints so a
    later scenario is never contaminated."""
    from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

    snapshot = {
        cid: list(bp) for cid, bp in stage2k._ABSOLUTE_BREAKPOINTS.items()
    }
    sensitivity_mod.compute_sensitivity(capsule_mod.build_capsule())
    assert snapshot == stage2k._ABSOLUTE_BREAKPOINTS


# --- Absence of production outputs ---


def test_no_production_outputs_in_any_report():
    for path in (
        "reports/petrochina_score_input_capsule_v1.json",
        "reports/petrochina_dimension_scoring_shadow_v2.json",
        "reports/petrochina_dimension_scoring_confidence_v1.json",
        "reports/petrochina_dimension_scoring_sensitivity_v2.json",
    ):
        doc = _load(path)
        assert not FORBIDDEN & _walk_keys(doc), path
        assert doc["score_eligible"] is False, path
        assert doc["overall_score_prohibited"] is True, path
        assert doc["recommendation_prohibited"] is True, path


def test_shadow_has_exactly_four_dimensions_and_no_overall_score():
    shadow = shadow_mod.compute_shadow(capsule_mod.build_capsule())
    assert set(shadow["dimensions"].keys()) == set(DIMENSIONS)
    assert not FORBIDDEN & _walk_keys(shadow)


def test_engines_write_no_production_tables_or_metric_results():
    for name in (
        "m2_stage2k1r_capsule.py",
        "m2_stage2k1r_shadow.py",
        "m2_stage2k1r_sensitivity.py",
        "m2_stage2k1r_confidence.py",
    ):
        source = (ROOT / "src/ashare_research/tools" / name).read_text(encoding="utf-8")
        assert "CREATE TABLE" not in source, name
        assert "metric_results" not in source, name


def test_engines_are_offline_no_network_no_db_no_llm():
    for name in (
        "m2_stage2k1r_capsule.py",
        "m2_stage2k1r_shadow.py",
        "m2_stage2k1r_sensitivity.py",
        "m2_stage2k1r_confidence.py",
        "m2_stage2k1r_validate.py",
    ):
        source = (ROOT / "src/ashare_research/tools" / name).read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "urllib",
            "socket",
            "duckdb",
            "data/research.duckdb",
            "openai",
            "anthropic",
            "llm",
        ):
            assert forbidden not in source.lower(), (name, forbidden)


def test_canonical_production_value_profile_remains_score_free():
    profile = _load("reports/petrochina_value_profile.json")
    assert profile["score_eligible"] is False
    assert not FORBIDDEN & _walk_keys(profile)


# --- Artifact manifest ---


def test_stage2k1r_artifact_manifest_recomputes_every_deliverable():
    manifest = _load("reports/m2_stage2k1r_artifact_manifest.json")
    assert manifest["schema"] == "m2_stage2k1r_artifact_manifest_v1"
    assert manifest["stage2k1r_decision"] == "SCORING_CONTRACT_GAPS_REMAIN"
    paths = [item["logical_path"] for item in manifest["files"]]
    assert len(paths) == len(set(paths))
    for item in manifest["files"]:
        path = ROOT / item["logical_path"]
        payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        assert len(payload) == item["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
