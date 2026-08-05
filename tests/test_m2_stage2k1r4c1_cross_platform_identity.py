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
# 6. fingerprint envelope v2: provenance + identity + compare
# ---------------------------------------------------------------------------

def _envelope(runner_os: str, matrix_platform: str, github_sha: str | None = "deadbeef"):
    """Build an envelope with explicit provenance (tests are platform-agnostic)."""
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        ENVELOPE_SCHEMA,
        build_identity,
        identity_digest,
    )

    env = {
        "schema": ENVELOPE_SCHEMA,
        "version": "2.0",
        "provenance": {
            "runner_os": runner_os,
            "matrix_platform": matrix_platform,
            "github_sha": github_sha,
        },
        "identity": build_identity(),
    }
    env["identity_digest"] = identity_digest(env)
    return env


def test_envelope_schema_and_identity_determinism():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        ENVELOPE_SCHEMA,
        build_envelope,
        identity_digest,
    )

    env = build_envelope(matrix_platform="windows", github_sha="deadbeef")
    assert env["schema"] == ENVELOPE_SCHEMA
    identity = env["identity"]
    assert identity["capsule_schema"] == "petrochina_score_input_capsule_v4"
    assert identity["sensitivity_schema"] == "petrochina_dimension_scoring_sensitivity_v7"
    assert list(identity["components"].keys()) == sorted(identity["components"].keys())
    # no run time / absolute paths: identity is content-derived only
    text = json.dumps(env, ensure_ascii=False)
    assert "2026-08-04T" not in text
    assert "C:/" not in text and "D:/" not in text and "\\Users" not in text
    assert "tmp/" not in text and "\\Temp" not in text
    # identity_digest is canonical and stable across platforms
    ubuntu = build_envelope(matrix_platform="ubuntu", github_sha="deadbeef")
    assert identity_digest(env) == identity_digest(ubuntu)


def test_provenance_does_not_pollute_identity():
    env = _envelope("Linux", "ubuntu", "sha")
    assert set(env["identity"]) == {
        "symbol", "capsule_schema", "capsule_digest", "time_contract_digest",
        "registry_digest", "sensitivity_schema", "sensitivity_ledger_digest",
        "components", "scenario_ids",
    }
    assert {"runner_os", "matrix_platform", "github_sha"} <= set(env["provenance"])
    assert "runner_os" not in env["identity"] and "matrix_platform" not in env["identity"]


def test_different_provenance_identical_identity_passes():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    a = _envelope("Linux", "ubuntu")
    b = _envelope("Windows", "windows")
    r = compare_envelopes(a, b)
    assert r["identical"] is True
    assert r["gate"] == "ok"
    assert r["provenance_left"]["matrix_platform"] == "ubuntu"
    assert r["provenance_right"]["matrix_platform"] == "windows"


def test_compare_success_identity_digest_is_dynamic():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        compare_envelopes,
        identity_digest,
    )

    a = _envelope("Linux", "ubuntu")
    b = _envelope("Windows", "windows")
    r = compare_envelopes(a, b)
    assert r["identity_digest"] == identity_digest(a) == identity_digest(b)
    # NOT the old v1 flat-schema digest: the envelope identity_digest is a new value
    assert r["identity_digest"] != (
        "8186848b2505e29c92cd0732fa6f67427b11b555d2ba58589ba2b061aae7679f"
    )


def test_both_provenances_ubuntu_fails():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    a = _envelope("Linux", "ubuntu")
    r = compare_envelopes(a, a)
    assert r["identical"] is False
    assert r["gate"] == "provenance_right"


def test_both_provenances_windows_fails():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    b = _envelope("Windows", "windows")
    r = compare_envelopes(b, b)
    assert r["identical"] is False
    assert r["gate"] == "provenance_left"


def test_ubuntu_cannot_disguise_as_windows():
    # an ubuntu-built envelope can never be the windows side, and vice versa:
    # a single platform cannot satisfy both provenance gates simultaneously.
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    ubuntu = _envelope("Linux", "ubuntu")
    assert compare_envelopes(ubuntu, ubuntu)["gate"] == "provenance_right"
    windows = _envelope("Windows", "windows")
    assert compare_envelopes(windows, windows)["gate"] == "provenance_left"


def test_inconsistent_runner_platform_fails():
    # runner_os Windows but claims matrix_platform ubuntu -> cannot be the left side
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    a = _envelope("Windows", "ubuntu")
    b = _envelope("Windows", "windows")
    r = compare_envelopes(a, b)
    assert r["identical"] is False
    assert r["gate"] == "provenance_left"


def test_different_github_sha_fails():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    a = _envelope("Linux", "ubuntu", github_sha="sha-aaaa")
    b = _envelope("Windows", "windows", github_sha="sha-bbbb")
    r = compare_envelopes(a, b)
    assert r["identical"] is False
    assert r["gate"] == "github_sha"


def test_missing_github_sha_fails():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import compare_envelopes

    a = _envelope("Linux", "ubuntu", github_sha=None)
    b = _envelope("Windows", "windows", github_sha="sha")
    r = compare_envelopes(a, b)
    assert r["identical"] is False
    assert r["gate"] == "github_sha"


def test_identity_field_tamper_reports_first_mismatch():
    from ashare_research.tools.m2_stage2k1r4c1_identity_diagnose import (
        compare_envelopes,
        identity_digest,
    )

    a = _envelope("Linux", "ubuntu")
    b = _envelope("Windows", "windows")
    b["identity"]["capsule_digest"] = "0" * 64
    b["identity_digest"] = identity_digest(b)
    r = compare_envelopes(a, b)
    assert r["identical"] is False
    assert r["gate"] == "identity"
    assert r["first_mismatch_path"] == "identity.capsule_digest"

    b2 = _envelope("Windows", "windows")
    b2["identity"]["components"]["va_pe"]["records"][0]["sha256"] = "0" * 64
    b2["identity_digest"] = identity_digest(b2)
    r2 = compare_envelopes(a, b2)
    assert r2["identical"] is False
    assert r2["first_mismatch_path"] == "identity.components.va_pe.records[0].sha256"


# ---------------------------------------------------------------------------
# 6b. workflow matrix + artifact naming (cross-platform CI provenance)
# ---------------------------------------------------------------------------

def _workflow() -> dict:
    import yaml

    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "stage2g-reproducibility.yml").read_text(
            encoding="utf-8"
        )
    )


def test_ci_matrix_has_only_two_paired_include_entries():
    wf = _workflow()
    matrix = wf["jobs"]["clean-clone"]["strategy"]["matrix"]
    assert matrix["include"] == [
        {"os": "ubuntu-latest", "platform": "ubuntu"},
        {"os": "windows-latest", "platform": "windows"},
    ]
    # no cartesian list form (which produced 4 jobs)
    assert "os" not in matrix and "short" not in matrix


def test_ci_artifact_names_unique_and_sha_bound():
    wf = _workflow()
    clean = wf["jobs"]["clean-clone"]["steps"]
    upload = [s for s in clean if s.get("uses", "").startswith("actions/upload-artifact")]
    assert len(upload) == 1
    name = upload[0]["with"]["name"]
    assert name == "identity-fingerprint-${{ matrix.platform }}-${{ github.sha }}"

    compare = wf["jobs"]["identity-compare"]["steps"]
    downloads = [s for s in compare if s.get("uses", "").startswith("actions/download-artifact")]
    names = [s["with"]["name"] for s in downloads]
    assert names == [
        "identity-fingerprint-ubuntu-${{ github.sha }}",
        "identity-fingerprint-windows-${{ github.sha }}",
    ]
    # the ubuntu artifact name must differ from the windows artifact name
    assert names[0] != names[1]
    # both names are bound to the commit sha
    assert "github.sha" in names[0] and "github.sha" in names[1]


def test_ci_compare_job_has_hard_gate_and_sha_bound_paths():
    wf = _workflow()
    compare = wf["jobs"]["identity-compare"]["steps"]
    step_names = [s.get("name", "") for s in compare]
    assert "Hard gate - exactly two fingerprint artifacts" in step_names
    compare_step = next(s for s in compare if "Compare cross-platform" in s.get("name", ""))
    cmd = compare_step["run"]
    assert "identity-fingerprint-ubuntu-${{ github.sha }}.json" in cmd
    assert "identity-fingerprint-windows-${{ github.sha }}.json" in cmd


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
