"""M2 Stage 2K.1R4B Phase A tests: artifact manifest verifier + sensitivity ledger.

Covers two independent engineering patches:

  A. Artifact manifest verifier (true hash recomputation, LF-normalization,
     tamper detection, CLI exit semantics).
  B. Sensitivity v6 per-scenario ledger (six scenario classes, confidence
     scenarios counted, summary recomputable from ledger, digest validation).

No production scores, no peer acquisition, no M3.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from ashare_research.scoring import artifact_manifest as am
from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import validator as validator_mod
from ashare_research.tools import m2_stage2k1r3_closeout as closeout

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return cap.build_capsule()


def _lineage_report(capsule: dict) -> dict:
    rep = validator_mod.validate_capsule(capsule)
    rep["report_digest"] = cap._sha256_bytes(cap._canonical(rep))
    return rep


def _sensitivity_v6() -> dict:
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    return sensitivity_mod.build_sensitivity_v6(capsule, confidence)


def _run_cli(monkeypatch, *argv) -> int:
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    return closeout.main()


# ---------------------------------------------------------------------------
# manifest helpers
# ---------------------------------------------------------------------------

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write_manifest(tmp_path: Path, files_spec: list[dict]) -> Path:
    """files_spec: list of dicts with path/sha256/byte_size (or raw content)."""
    manifest = {
        "schema": "m2_stage2k1r4b_artifact_manifest_v1",
        "version": "1.0",
        "date": "2026-08-04",
        "stage": "2K.1R4B",
        "note": "sha256 over LF-normalized content; byte_size is LF-normalized length",
        "files": files_spec,
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return p


def _manifest_entry(rel: str, content: bytes) -> dict:
    norm = am.normalize_lf(content)
    return {
        "path": rel,
        "sha256": _sha(norm),
        "byte_size": len(norm),
    }


def _make_verified_manifest(tmp_path: Path) -> tuple[Path, list[dict]]:
    """Create a temp repo with 3 files and a correct manifest; return (manifest, entries)."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "a.py").write_bytes(b"line1\nline2\n")
    (repo / "b.py").write_bytes(b"data\n")
    (repo / "c.txt").write_bytes(b"x")
    entries = [
        _manifest_entry("a.py", b"line1\nline2\n"),
        _manifest_entry("b.py", b"data\n"),
        _manifest_entry("c.txt", b"x"),
    ]
    manifest = _write_manifest(tmp_path, entries)
    return manifest, entries


# ---------------------------------------------------------------------------
# A1. artifact manifest verifier (pure)
# ---------------------------------------------------------------------------

def test_normal_lf_consistency():
    # CRLF and LF with identical logical content normalize to the same bytes,
    # hence the same hash and size (contract for the current manifests).
    a = b"line1\r\nline2\r\n"
    b = b"line1\nline2\n"
    assert am.normalize_lf(a) == am.normalize_lf(b) == b"line1\nline2\n"
    assert _sha(am.normalize_lf(a)) == _sha(am.normalize_lf(b))
    assert len(am.normalize_lf(a)) == len(am.normalize_lf(b))


def test_normal_lf_preserves_other_bytes():
    # No UTF-8 decode/re-encode; non-LF bytes are preserved verbatim.
    data = b"a\r\nb\rc\x00d\xff"
    assert am.normalize_lf(data) == b"a\nb\nc\x00d\xff"


def test_manifest_pass(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "pass"
    assert v.verified_file_count == 3
    assert v.missing_files == []
    assert v.hash_mismatches == []
    assert v.size_mismatches == []
    assert v.errors == []


def test_manifest_modified_bytes_fail(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    (tmp_path / "repo" / "a.py").write_bytes(b"line1\nTAMPERED\n")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "a.py" in v.hash_mismatches


def test_manifest_modified_hash_fail(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    entries[0]["sha256"] = "0" * 64
    manifest.write_text(json.dumps({"schema": "m2_stage2k1r4b_artifact_manifest_v1",
                                    "version": "1.0", "files": entries}), encoding="utf-8")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "a.py" in v.hash_mismatches


def test_manifest_modified_byte_size_fail(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    entries[0]["byte_size"] = 9999
    manifest.write_text(json.dumps({"schema": "m2_stage2k1r4b_artifact_manifest_v1",
                                    "version": "1.0", "files": entries}), encoding="utf-8")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "a.py" in v.size_mismatches


def test_manifest_missing_file_fail(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    (tmp_path / "repo" / "c.txt").unlink()
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "c.txt" in v.missing_files


def test_manifest_duplicate_path_fail(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    entries.append(dict(entries[0]))
    manifest.write_text(json.dumps({"schema": "m2_stage2k1r4b_artifact_manifest_v1",
                                    "version": "1.0", "files": entries}), encoding="utf-8")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "a.py" in v.duplicate_paths


def test_manifest_absolute_path_fail(tmp_path):
    files_spec = [{"path": "/abs/escape.py", "sha256": "0" * 64, "byte_size": 1}]
    manifest = _write_manifest(tmp_path, files_spec)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "/abs/escape.py" in v.invalid_paths


def test_manifest_parent_traversal_fail(tmp_path):
    files_spec = [{"path": "../escape.py", "sha256": "0" * 64, "byte_size": 1}]
    manifest = _write_manifest(tmp_path, files_spec)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "../escape.py" in v.invalid_paths


def test_manifest_windows_drive_path_fail(tmp_path):
    files_spec = [{"path": "C:/escape.py", "sha256": "0" * 64, "byte_size": 1}]
    manifest = _write_manifest(tmp_path, files_spec)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert "C:/escape.py" in v.invalid_paths


def test_manifest_unsupported_schema_fail(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": "not_a_real_schema", "files": []}),
                        encoding="utf-8")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert v.unexpected_contract_errors


def test_manifest_not_json_object_fail(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[1,2,3]", encoding="utf-8")
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert v.unexpected_contract_errors


def test_manifest_digest_recomputable(tmp_path):
    manifest, entries = _make_verified_manifest(tmp_path)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert v.manifest_digest == am.manifest_digest(payload)
    # excluding manifest_digest must not change the digest
    assert am.manifest_digest(payload) == am.manifest_digest({**payload, "manifest_digest": "x"})


def test_manifest_missing_required_field_fail(tmp_path):
    files_spec = [{"path": "a.py", "sha256": "0" * 64}]  # missing byte_size
    manifest = _write_manifest(tmp_path, files_spec)
    v = am.verify_artifact_manifest(manifest, repository_root=tmp_path / "repo")
    assert v.status == "fail"
    assert v.unexpected_contract_errors or v.errors


# ---------------------------------------------------------------------------
# A2. CLI verify-artifacts exit semantics
# ---------------------------------------------------------------------------

def _real_repo_manifest(tmp_path: Path, *, tamper: str | None = None) -> Path:
    """Build a manifest referencing real repo files (relative to ROOT), so the
    CLI (which verifies against cap.ROOT) can verify it. Optionally tamper one
    entry's sha256."""
    rels = [
        "src/ashare_research/scoring/capsule.py",
        "src/ashare_research/scoring/validator.py",
        "src/ashare_research/scoring/confidence.py",
    ]
    entries = []
    for rel in rels:
        data = (ROOT / rel).read_bytes()
        entries.append(_manifest_entry(rel, data))
    if tamper:
        for e in entries:
            if e["path"] == tamper:
                e["sha256"] = "0" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"schema": "m2_stage2k1r4b_artifact_manifest_v1",
                    "version": "1.0", "files": entries}, indent=2),
        encoding="utf-8",
    )
    return manifest


def test_cli_verify_manifest_pass_exit_0(monkeypatch, tmp_path):
    manifest = _real_repo_manifest(tmp_path)
    out = tmp_path / "out.json"
    assert _run_cli(monkeypatch, "verify-artifacts", "--manifest", str(manifest),
                    "--output", str(out)) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["status"] == "pass"


def test_cli_verify_manifest_fail_exit_1(monkeypatch, tmp_path):
    manifest = _real_repo_manifest(tmp_path, tamper="src/ashare_research/scoring/capsule.py")
    assert _run_cli(monkeypatch, "verify-artifacts", "--manifest", str(manifest)) == 1


def test_cli_verify_manifest_output_preserves_failure(monkeypatch, tmp_path):
    manifest = _real_repo_manifest(tmp_path, tamper="src/ashare_research/scoring/capsule.py")
    out = tmp_path / "out.json"
    rc = _run_cli(monkeypatch, "verify-artifacts", "--manifest", str(manifest),
                  "--output", str(out))
    assert rc == 1
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["status"] == "fail"
    assert "src/ashare_research/scoring/capsule.py" in res["hash_mismatches"]


def test_cli_verify_manifest_missing_exit_2(monkeypatch, tmp_path):
    assert _run_cli(monkeypatch, "verify-artifacts", "--manifest",
                    str(tmp_path / "nope.json")) == 2


def test_cli_verify_manifest_uses_real_verifier(monkeypatch, tmp_path):
    # The CLI must NOT just return pass for a list of paths; tampering must fail.
    manifest = _real_repo_manifest(tmp_path, tamper="src/ashare_research/scoring/validator.py")
    assert _run_cli(monkeypatch, "verify-artifacts", "--manifest", str(manifest)) == 1


# ---------------------------------------------------------------------------
# B. sensitivity v6 ledger
# ---------------------------------------------------------------------------

def test_sensitivity_v6_schema_and_contract():
    s = _sensitivity_v6()
    assert s["schema"] == "petrochina_dimension_scoring_sensitivity_v6"
    assert s["scenario_contract_version"] == "1.0"
    assert s["non_production"] is True
    assert s["overall_score_prohibited"] is True
    assert s["recommendation_prohibited"] is True
    assert s["score_eligible"] is False
    assert s["ledger_digest"]


def test_sensitivity_six_scenario_classes_all_present():
    s = _sensitivity_v6()
    types = {sc["scenario_type"] for sc in s["scenarios"]}
    assert types == {
        "weight_perturbation",
        "leave_one_component_out",
        "coverage_threshold",
        "transform_alternative",
        "confidence_threshold",
        "missing_roic",
    }


def test_sensitivity_current_gap_roic_scenario_exists():
    s = _sensitivity_v6()
    modes = {
        sc["scenario_parameter_value"]
        for sc in s["scenarios"]
        if sc["scenario_type"] == "missing_roic"
    }
    assert {"current_gap", "synthetic_neutral", "no_roic_component"} <= modes


def test_sensitivity_confidence_scenarios_counted():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        d = s["dimensions"][dim]
        conf_in_ledger = sum(
            1
            for sc in s["scenarios"]
            if sc["dimension_id"] == dim and sc["scenario_type"] == "confidence_threshold"
        )
        assert conf_in_ledger == 3
        assert conf_in_ledger == d["scenario_type_counts"].get("confidence_threshold", 0)
        # confidence scenarios are part of scenario_count
        assert d["scenario_count"] == sum(d["scenario_type_counts"].values())
        # confidence_block_count matches the ledger
        assert d["confidence_block_count"] == sum(
            1
            for sc in s["scenarios"]
            if sc["dimension_id"] == dim
            and sc["scenario_type"] == "confidence_threshold"
            and not sc["release_allowed"]
        )


def test_sensitivity_scenario_type_counts_match_ledger():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        ledger_counts = {}
        for sc in s["scenarios"]:
            if sc["dimension_id"] == dim:
                ledger_counts[sc["scenario_type"]] = ledger_counts.get(sc["scenario_type"], 0) + 1
        assert s["dimensions"][dim]["scenario_type_counts"] == ledger_counts


def test_sensitivity_scenario_ids_unique():
    s = _sensitivity_v6()
    ids = [sc["scenario_id"] for sc in s["scenarios"]]
    assert len(ids) == len(set(ids))


def test_sensitivity_same_input_a_b_digest_same():
    a = _sensitivity_v6()
    b = _sensitivity_v6()
    assert a["ledger_digest"] == b["ledger_digest"]
    assert a["scenarios"] == b["scenarios"]


def test_sensitivity_tamper_fails_validation():
    s = _sensitivity_v6()
    s2 = json.loads(json.dumps(s))
    s2["scenarios"][0]["scenario_score"] = 999.0
    v = sensitivity_mod.validate_sensitivity_ledger(s2)
    assert v["status"] == "fail"
    assert v["errors"]


def test_sensitivity_digest_tamper_fails_validation():
    s = _sensitivity_v6()
    s2 = json.loads(json.dumps(s))
    s2["ledger_digest"] = "0" * 64
    v = sensitivity_mod.validate_sensitivity_ledger(s2)
    assert v["status"] == "fail"
    assert any("ledger_digest" in e for e in v["errors"])


def test_sensitivity_summary_recomputable_from_ledger():
    s = _sensitivity_v6()
    v = sensitivity_mod.validate_sensitivity_ledger(s)
    assert v["status"] == "pass", v["errors"]


def test_sensitivity_confidence_gate_does_not_change_coverage():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        base_cov = None
        for sc in s["scenarios"]:
            if sc["dimension_id"] == dim and sc["scenario_type"] == "confidence_threshold":
                assert sc["coverage"] == base_cov or base_cov is None
                base_cov = sc["coverage"]
        # confidence scenarios leave coverage equal to the base coverage
        assert base_cov is not None


def test_sensitivity_coverage_gate_does_not_change_confidence():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        grade = s["dimensions"][dim]["confidence_gate_sensitivity"]["grade"]
        for sc in s["scenarios"]:
            if sc["dimension_id"] == dim and sc["scenario_type"] == "coverage_threshold":
                assert sc["confidence_grade"] == grade


def test_sensitivity_synthetic_roic_flags_complete():
    s = _sensitivity_v6()
    synth = [
        sc for sc in s["scenarios"]
        if sc["scenario_type"] == "missing_roic"
        and sc["scenario_parameter_value"] == "synthetic_neutral"
    ]
    assert len(synth) == 1
    sc = synth[0]
    assert sc["is_synthetic"] is True
    assert sc["not_company_fact"] is True
    assert sc["not_publishable"] is True
    assert sc["excluded_from_base_result"] is True


def test_sensitivity_tolerance_still_one():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        assert s["dimensions"][dim]["stability_tolerance"] == 1.0


def test_sensitivity_stability_not_stable_preserved():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        assert s["dimensions"][dim]["stability_status"] == "NOT_STABLE"


def test_sensitivity_no_overall_rank_target():
    s = _sensitivity_v6()
    assert "overall_score" not in s
    assert "recommendation" not in s
    assert "ranking" not in s
    assert "target_price" not in s
    assert "position" not in s
    assert "signal" not in s


def test_sensitivity_module_does_not_mutate_registry():
    registry_before = _load(cap.REGISTRY_PATH)
    _sensitivity_v6()
    registry_after = _load(cap.REGISTRY_PATH)
    assert registry_before == registry_after
