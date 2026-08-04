"""M2 Stage 2K.1R4C.1 tests: cross-platform identity + ADR share-count correction.

Covers:

  1. Content digest contract (content_digest.py): LF-normalized text vs raw
     binary; CRLF/LF equivalence for text; fail-closed unknown algorithm;
     path-independent identity.
  2. Capsule v4 identity: simulated Windows/Linux working trees produce the
     same artifact digests, score-input ids and capsule digest; tampering with
     algorithm/size/SHA fails the validator.
  3. Sensitivity v7: fresh builds are deterministic (same scenario ids and
     ledger digest); NOT_STABLE preserved.
  4. Upstream digest contract: every resolved artifact path is registered with
     an algorithm; ResolvedRecord carries algorithm + byte_size.
  5. ADR share-count correction: 183,020,977,818 total ordinary shares ≈
     183.021 billion ≈ 1,830.21 亿股; the old wrong values are banned.
  6. Identity migration: capsule v4 / sensitivity v7 / migration report /
     manifest v2; economic values, scores, bands, coverage, confidence and
     stability are unchanged; v3/v6 preserved as history.
  7. Product boundaries: no quarterly facts, no PE/PB/PS series, no shadow
     update, no weight/threshold changes, no peer acquisition, no M3; default
     DB and fact baselines unchanged.

No production scores, no peer acquisition, no M3.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import content_digest as cd
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import validator as validator_mod

ROOT = Path(__file__).resolve().parents[1]

ADR = ROOT / "docs" / "decisions" / "ADR-VALUATION-002-a-share-per-share-convention.md"
MIGRATION = ROOT / "reports" / "petrochina_stage2k1r4c1_identity_migration.json"
CAPSULE_V4 = ROOT / "reports" / "petrochina_score_input_capsule_v4.json"
SENSITIVITY_V7 = ROOT / "reports" / "petrochina_dimension_scoring_sensitivity_v7.json"
CAPSULE_V3 = ROOT / "reports" / "petrochina_score_input_capsule_v3.json"
SENSITIVITY_V6 = ROOT / "reports" / "petrochina_dimension_scoring_sensitivity_v6.json"
VALUE_PROFILE = ROOT / "reports" / "petrochina_value_profile.json"
REGISTRY = ROOT / "config" / "value_dimension_scoring_upstream_registry_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return cap.build_capsule()


def _lineage_report(capsule: dict) -> dict:
    rep = validator_mod.validate_capsule(capsule)
    rep["report_digest"] = cap._sha256_bytes(cap._canonical(rep))
    return rep


def _sensitivity_v7() -> dict:
    return sensitivity_mod.build_sensitivity_v7(_capsule(), _confidence())


def _confidence() -> dict:
    from ashare_research.scoring import confidence as confidence_mod

    capsule = _capsule()
    return confidence_mod.build_confidence(capsule, _lineage_report(capsule))


# ---------------------------------------------------------------------------
# 1. content digest contract
# ---------------------------------------------------------------------------

def test_text_lf_and_crlf_same_digest():
    a = cd.digest_text_artifact(b'{"a": 1}\r\n')
    b = cd.digest_text_artifact(b'{"a": 1}\n')
    assert a == b
    assert a.algorithm == cd.ALGORITHM_LF_NORMALIZED_BYTES_V1
    assert a.byte_size == b.byte_size


def test_text_lone_cr_normalized():
    a = cd.digest_text_artifact(b"a\rb")
    b = cd.digest_text_artifact(b"a\nb")
    assert a == b


def test_binary_crlf_different_digest():
    a = cd.digest_binary_artifact(b'{"a": 1}\r\n')
    b = cd.digest_binary_artifact(b'{"a": 1}\n')
    assert a != b
    assert a.algorithm == cd.ALGORITHM_RAW_BYTES_V1
    assert a.byte_size != b.byte_size


def test_unknown_algorithm_fails_closed():
    with pytest.raises(cd.ContentDigestError):
        cd.digest_file(REGISTRY, algorithm="sha256_md5_v0")


def test_unknown_media_class_fails_closed():
    with pytest.raises(cd.ContentDigestError):
        cd.digest_for_media_class(b"x", "pdf")


def test_algorithm_part_of_identity():
    # a CRLF file hashes differently under the two algorithms: the algorithm
    # is part of the identity, so a contract change to a different algorithm
    # version would change every artifact identity.
    data = b'{\r\n}\r\n'
    text = cd.digest_text_artifact(data)
    raw = cd.digest_binary_artifact(data)
    assert text != raw
    # same bytes + same algorithm -> same identity (deterministic)
    assert cd.digest_text_artifact(data) == text


def test_digest_path_independent(tmp_path):
    # the digest is content-only (no path, no cwd): the same logical content
    # at different paths yields the same identity
    p1 = tmp_path / "a" / "x.json"
    p2 = tmp_path / "b" / "y.json"
    p1.parent.mkdir()
    p2.parent.mkdir()
    content = b'{"k": "v"}\n'
    p1.write_bytes(content)
    p2.write_bytes(content)
    d1 = cd.digest_file(p1, algorithm=cd.ALGORITHM_LF_NORMALIZED_BYTES_V1)
    d2 = cd.digest_file(p2, algorithm=cd.ALGORITHM_LF_NORMALIZED_BYTES_V1)
    assert d1 == d2
    assert d1.sha256 == cd.digest_text_artifact(content).sha256


# ---------------------------------------------------------------------------
# 2. upstream digest contract + ResolvedRecord
# ---------------------------------------------------------------------------

def test_registry_digest_contract_covers_all_resolved_paths():
    reg = _load(REGISTRY)
    contract = reg["artifact_digest_contract"]
    assert contract["schema"] == "artifact_content_digest_v1"
    entries = contract["entries"]
    capsule = _capsule()
    paths = set()
    for comp in capsule["components"].values():
        for r in comp.get("resolved_records", []):
            paths.add(r["artifact_logical_path"])
    for p in paths:
        assert p in entries, f"unregistered artifact path: {p}"
        assert entries[p]["algorithm"] == cd.ALGORITHM_LF_NORMALIZED_BYTES_V1
        assert entries[p]["media_class"] == cd.MEDIA_CLASS_TEXT


def test_resolved_records_carry_digest_algorithm_and_byte_size():
    capsule = _capsule()
    vt = validator_mod.validate_capsule(capsule)
    assert vt["status"] == "pass", vt["errors"]
    for comp in capsule["components"].values():
        for r in comp.get("resolved_records", []):
            assert r["artifact_digest_algorithm"] in (
                cd.ALGORITHM_LF_NORMALIZED_BYTES_V1,
                cd.ALGORITHM_RAW_BYTES_V1,
            )
            assert isinstance(r["artifact_byte_size"], int) and r["artifact_byte_size"] > 0


def test_value_profile_digest_is_lf_normalized():
    # the CRLF-on-Windows generated report must digest identically to its LF
    # committed blob (the cross-platform root-cause fix)
    capsule = _capsule()
    for comp in capsule["components"].values():
        for r in comp.get("resolved_records", []):
            if r["artifact_logical_path"] == "reports/petrochina_value_profile.json":
                expected = cd.digest_file(
                    VALUE_PROFILE, algorithm=cd.ALGORITHM_LF_NORMALIZED_BYTES_V1
                )
                assert r["artifact_sha256"] == expected.sha256
                assert r["artifact_byte_size"] == expected.byte_size
                return
    raise AssertionError("value_profile.json not found in resolved records")


# ---------------------------------------------------------------------------
# 3. capsule identity: simulated Windows / Linux
# ---------------------------------------------------------------------------

def test_capsule_simulated_windows_linux_identical_identity():
    """The Windows working tree (CRLF value_profile) and a Linux clean clone
    (LF value_profile) must produce identical score-input ids and capsule
    digest under the LF-normalized digest contract."""
    orig = VALUE_PROFILE.read_bytes()
    lf = orig.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    try:
        VALUE_PROFILE.write_bytes(lf)
        c_linux = _capsule()
    finally:
        VALUE_PROFILE.write_bytes(orig)
    c_windows = _capsule()
    assert c_windows["capsule_digest"] == c_linux["capsule_digest"]
    for cid in c_windows["components"]:
        assert (
            c_windows["components"][cid]["score_input_id"]
            == c_linux["components"][cid]["score_input_id"]
        ), cid


def test_capsule_algorithm_tamper_fails_validator():
    c = _capsule()
    comp = c["components"]["va_pe"]
    comp["resolved_records"][0]["artifact_digest_algorithm"] = "sha256_raw_bytes_v1"
    c["capsule_digest"] = cap.capsule_digest(c)
    result = validator_mod.validate_capsule(c)
    assert result["status"] == "fail"
    assert any("capsule_snapshot_mismatch" in e for e in result["snapshot_errors"])


def test_capsule_sha_tamper_fails_validator():
    c = _capsule()
    comp = c["components"]["va_pe"]
    comp["resolved_records"][0]["artifact_sha256"] = "0" * 64
    c["capsule_digest"] = cap.capsule_digest(c)
    result = validator_mod.validate_capsule(c)
    assert result["status"] == "fail"
    assert any("capsule_snapshot_mismatch" in e for e in result["snapshot_errors"])


def test_capsule_byte_size_tamper_fails_validator():
    c = _capsule()
    comp = c["components"]["va_pe"]
    comp["resolved_records"][0]["artifact_byte_size"] += 1
    c["capsule_digest"] = cap.capsule_digest(c)
    result = validator_mod.validate_capsule(c)
    assert result["status"] == "fail"
    assert any("capsule_snapshot_mismatch" in e for e in result["snapshot_errors"])


def test_capsule_v4_report_matches_fresh_build():
    report = _load(CAPSULE_V4)
    fresh = _capsule()
    assert report == fresh
    assert report["schema"] == "petrochina_score_input_capsule_v4"


# ---------------------------------------------------------------------------
# 4. sensitivity v7 identity
# ---------------------------------------------------------------------------

def test_sensitivity_v7_report_matches_fresh_build():
    report = _load(SENSITIVITY_V7)
    fresh = _sensitivity_v7()
    assert report == fresh
    assert report["schema"] == "petrochina_dimension_scoring_sensitivity_v7"


def test_sensitivity_v7_scenario_ids_deterministic():
    a = _sensitivity_v7()
    b = _sensitivity_v7()
    assert a["scenarios"][0]["scenario_id"] == b["scenarios"][0]["scenario_id"]
    assert [s["scenario_id"] for s in a["scenarios"]] == [
        s["scenario_id"] for s in b["scenarios"]
    ]
    assert a["ledger_digest"] == b["ledger_digest"]


def test_sensitivity_v7_not_stable_preserved():
    s = _sensitivity_v7()
    for dim in cap.SCORED_DIMENSIONS:
        assert s["dimensions"][dim]["stability_status"] == "NOT_STABLE"
        assert s["dimensions"][dim]["stability_tolerance"] == 1.0


def test_sensitivity_v7_validator_passes():
    v = sensitivity_mod.validate_sensitivity_ledger(_sensitivity_v7())
    assert v["status"] == "pass", v["errors"]


# ---------------------------------------------------------------------------
# 5. identity migration
# ---------------------------------------------------------------------------

def test_migration_report_economics_unchanged():
    m = _load(MIGRATION)
    assert m["schema"] == "petrochina_stage2k1r4c1_identity_migration_v1"
    s = m["summary"]
    assert s["economic_value_changed"] is False
    assert s["scores_changed"] is False
    assert s["bands_changed"] is False
    assert s["coverage_changed"] is False
    assert s["confidence_changed"] is False
    assert s["stability_status_changed"] is False
    assert s["score_input_id_changed_count"] == 24
    assert s["scenario_count_old"] == s["scenario_count_new"] == 87


def test_migration_all_score_input_ids_changed():
    # identity structure changed (artifact_digests) so every score-input id
    # changed, but the economic values did not
    m = _load(MIGRATION)
    for cid, row in m["components"].items():
        assert row["score_input_id_changed"] is True, cid
        assert row["economic_value_changed"] is False, cid
        assert row["old_selected_value_decimal"] == row["new_selected_value_decimal"], cid


def test_v3_v6_preserved_as_history():
    v3 = _load(CAPSULE_V3)
    v6 = _load(SENSITIVITY_V6)
    assert v3["schema"] == "petrochina_score_input_capsule_v3"
    assert v6["schema"] == "petrochina_dimension_scoring_sensitivity_v6"
    assert v6["ledger_digest"] == (
        "213cdba05c5d5664f199d73529de18d214b270a19147347eb7c0ff470efd6ccf"
    )


# ---------------------------------------------------------------------------
# 6. fingerprint + compare
# ---------------------------------------------------------------------------

def test_fingerprint_schema_and_determinism():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        build_fingerprint,
        compare_fingerprints,
        fingerprint_digest,
    )

    fp = build_fingerprint()
    assert fp["schema"] == "scoring_identity_fingerprint_v1"
    assert fp["capsule_schema"] == "petrochina_score_input_capsule_v4"
    assert fp["sensitivity_schema"] == "petrochina_dimension_scoring_sensitivity_v7"
    assert list(fp["components"].keys()) == sorted(fp["components"].keys())
    # no run time / absolute paths: the fingerprint is content-derived only
    text = json.dumps(fp, ensure_ascii=False)
    assert "2026-08-04T" not in text
    assert "C:/" not in text and "D:/" not in text and "\\Users" not in text
    assert "tmp/" not in text and "\\Temp" not in text
    # canonical JSON is stable
    assert fingerprint_digest(fp) == fingerprint_digest(build_fingerprint())
    # self-compare identical
    assert compare_fingerprints(fp, fp)["identical"] is True


def test_fingerprint_compare_reports_first_mismatch():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        build_fingerprint,
        compare_fingerprints,
    )

    fp = build_fingerprint()
    tampered = json.loads(json.dumps(fp))
    tampered["capsule_digest"] = "0" * 64
    r = compare_fingerprints(fp, tampered)
    assert r["identical"] is False
    assert r["first_mismatch_path"] == "fingerprint.capsule_digest"

    tampered2 = json.loads(json.dumps(fp))
    tampered2["components"]["va_pe"]["records"][0]["sha256"] = "0" * 64
    r2 = compare_fingerprints(fp, tampered2)
    assert r2["identical"] is False
    assert r2["first_mismatch_path"] == "fingerprint.components.va_pe.records[0].sha256"


# ---------------------------------------------------------------------------
# 7. ADR share-count correction
# ---------------------------------------------------------------------------

def test_adr_share_count_corrected():
    text = ADR.read_text(encoding="utf-8")
    assert "183,020,977,818" in text
    assert "183.021 billion" in text
    assert "1,830.21 亿股" in text


def test_adr_share_count_old_wrong_values_banned():
    text = ADR.read_text(encoding="utf-8")
    for banned in ("18.302 billion", "18,302,097,781", "18,302,097,782"):
        assert banned not in text, f"banned wrong share count present: {banned}"


def test_adr_share_count_is_factual_evidence_not_input():
    text = ADR.read_text(encoding="utf-8")
    assert "factual evidence" in text
    assert "not" in text and "hard-coded input" in text


# ---------------------------------------------------------------------------
# 8. product boundaries (business state unchanged)
# ---------------------------------------------------------------------------

def test_no_quarterly_facts_collected():
    for path in [
        "reports/pit_quarterly_facts.json",
        "reports/quarterly_financial_facts.json",
        "reports/petrochina_quarterly_facts.json",
    ]:
        assert not (ROOT / path).exists(), f"unexpected quarterly facts artifact: {path}"


def test_no_historical_series_generated():
    for path in [
        "reports/petrochina_historical_pe_pb_ps_series.json",
        "reports/pit_valuation_series.json",
        "reports/historical_valuation_series.json",
    ]:
        assert not (ROOT / path).exists(), f"unexpected series artifact: {path}"


def test_valuation_shadow_not_modified():
    out = subprocess.run(
        ["git", "status", "--short", "--", "src/ashare_research/scoring/shadow.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "shadow.py was modified"


def test_scoring_weights_thresholds_unchanged():
    out = subprocess.run(
        ["git", "status", "--short", "--",
         "config/value_dimension_scoring_registry_v1.json",
         "config/value_dimension_scoring_policy_v1.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "scoring registry/policy modified"


def test_no_peer_acquisition_started():
    for path in ["reports/peer_acquisition_plan.json", "reports/peer_database.json"]:
        assert not (ROOT / path).exists()
    assert "peer" not in _load(MIGRATION)["summary"]["new_capsule_schema"]


def test_no_m3_started():
    assert "M3" not in _load(MIGRATION)["summary"]["new_capsule_schema"]
    assert "M3" not in json.dumps(_load(MIGRATION))


def test_default_db_unchanged():
    from ashare_research.storage.default_db_guard import hash_optional_default_db

    # absent on clean clones (guarded baseline); present -> must match the
    # protected digest exactly. Constants inlined (tests/ is not a package, so
    # `from tests.conftest import ...` breaks bare `pytest` on CI).
    default_db = ROOT / "data" / "research.duckdb"
    protected_digest = "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
    assert hash_optional_default_db(default_db, protected_digest) == protected_digest


def test_fact_baseline_unchanged():
    # the 354-fact inventory baseline (ROIC readiness contract) must be intact
    inventory = ROOT / "reports" / "roic_fact_inventory.json"
    if inventory.exists():
        assert _load(inventory)["fact_count"] == 354


def test_no_pe_pb_ps_valuation_percentiles_promoted():
    capsule = _capsule()
    for cid in ("va_pe", "va_pb", "va_ps"):
        obs = capsule["components"][cid].get("observation_set") or {}
        assert obs.get("percentile_source") == "committed_manifest"


# ---------------------------------------------------------------------------
# 9. R4C.1 manifest v2
# ---------------------------------------------------------------------------

def test_r4c1_artifact_manifest_v2_verifies_and_is_default():
    from ashare_research.scoring import artifact_manifest as am
    from ashare_research.tools import m2_stage2k1r3_closeout as closeout

    manifest = ROOT / "reports" / "m2_stage2k1r4c1_artifact_manifest.json"
    assert manifest.exists()
    v = am.verify_artifact_manifest(manifest, repository_root=ROOT)
    assert v.status == "pass", v.errors
    assert manifest == closeout.DEFAULT_MANIFEST
    assert am.verify_artifact_manifest(
        closeout.DEFAULT_MANIFEST, repository_root=ROOT
    ).status == "pass"


def test_r4c1_manifest_entries_carry_digest_algorithm():

    manifest = _load(ROOT / "reports" / "m2_stage2k1r4c1_artifact_manifest.json")
    assert manifest["schema"] == "m2_stage2k1r4c1_artifact_manifest_v2"
    assert manifest["version"] == "2.0"
    for entry in manifest["files"]:
        assert entry["digest_algorithm"] == cd.ALGORITHM_LF_NORMALIZED_BYTES_V1
