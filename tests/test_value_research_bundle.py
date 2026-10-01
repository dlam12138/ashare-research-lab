"""Acceptance coverage for the M2 offline research bundle tool.

The four cases below cover: (1) the readable Markdown plus canonical JSON projection of the
nine fixed source reports, with original decimals and statuses preserved; (2) a genuine
subprocess export and portable verification run from an unrelated working directory, with
byte-stable source attachments and deterministic output; (3) rejection of a tampered package
even after the manifest is recomputed to match the tampered bytes; (4) rejection of a
pre-existing output path with the foreign artifacts left untouched.

Frozen manifest and known failures are never simulated: verify results and source bytes are
compared against the repository reports themselves.  Nothing here recomputes research, reads
the database or the network, or writes into the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from ashare_research.tools import value_research_bundle as bundle_module

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REPORTS = ROOT / "reports"
MODULE_NAME = "ashare_research.tools.value_research_bundle"

_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)

MANAGED_FILES = 11
TOTAL_FILES_WITH_MANIFEST = 12
INJECTED_MARKER = "TAMPERED_NOT_A_SOURCE_BYTE"


def _run_module(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *arguments],
        cwd=cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _stdout(completed: subprocess.CompletedProcess) -> str:
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout.decode("utf-8")


def _repo_bytes(name: str) -> bytes:
    return (REPORTS / name).read_bytes()


def _export(tmp_path: Path, name: str = "export") -> Path:
    """Run the real CLI export into a fresh subdirectory; return the directory."""
    target = tmp_path / name
    completed = _run_module("--output", str(target), cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return target


def test_projected_report_preserves_source_decimals_statuses_and_coherence(tmp_path: Path) -> None:
    reports = {
        name: json.loads(_repo_bytes(name).decode("utf-8"))
        for name in bundle_module.JSON_SOURCE_REPORTS
    }
    narratives = {
        name: _repo_bytes(name).decode("utf-8")
        for name in bundle_module.MARKDOWN_SOURCE_REPORTS
    }

    markdown = _stdout(_run_module(cwd=tmp_path))
    payload = json.loads(_stdout(_run_module("--json", cwd=tmp_path)))

    assert list(payload) == sorted(payload)
    assert payload["schema"] == bundle_module.SCHEMA_ID
    assert payload["symbol"] == "601857.SH"
    compilation = payload["compilation"]
    assert compilation["nature"] == "mixed_date_historical_compilation"
    assert compilation["unified_pit_as_of_query"] is False
    assert compilation["research_refresh"] is False
    assert compilation["new_metrics_computed"] is False
    assert compilation["overall_score"] is False
    assert compilation["ranking"] is False
    assert compilation["recommendation"] is False
    boundary = payload["nonproduction_boundary"]
    assert boundary["score_eligible"] is False
    assert boundary["production_eligible"] is False
    assert boundary["overall_score_prohibited"] is True
    assert boundary["recommendation_prohibited"] is True
    assert boundary["ranking_produced"] is False
    assert boundary["eligibility_assessed"] is False

    # The projection is the source, decoded: same key order, same bytes-level decimals.
    profile = reports["petrochina_value_profile.json"]
    assert list(payload["value_profile"]["latest_observations"]) == list(
        profile["latest_observations"]
    )
    assert payload["value_profile"]["capital_return"] == profile["capital_return"]
    assert payload["value_profile"]["integrated_layers"] == profile["integrated_layers"]
    mispriced = "12.89158710139375214555441126"
    assert payload["value_profile"]["latest_observations"][
        "a_share_price_to_latest_annual_parent_earnings"
    ]["value_decimal"] == profile["latest_observations"][
        "a_share_price_to_latest_annual_parent_earnings"
    ]["value_decimal"]
    assert mispriced in json.dumps(payload, ensure_ascii=False)
    dividend = payload["value_profile"]["latest_observations"]["trailing_12m_paid_dividend_yield"]
    assert dividend["status"] == "missing_input"
    assert dividend["value_decimal"] is None
    assert dividend["value"] is None
    assert dividend["lineage"]["missing_event_ids"] == profile["latest_observations"][
        "trailing_12m_paid_dividend_yield"
    ]["lineage"]["missing_event_ids"]
    assert payload["value_profile"]["capital_return"]["roic"]["status"] == (
        "not_computable_under_strict_evidence_contract"
    )
    assert payload["value_profile"]["integrated_layers"]["roic"] == (
        "not_computable_under_strict_evidence_contract"
    )
    assert payload["value_profile"]["integrated_layers"]["daily_market_mechanism"] == (
        "not_evaluated"
    )

    timeline = reports["petrochina_pit_financial_state_timeline_v2.json"]
    assert sorted(payload["timeline"]["timelines"]) == sorted(bundle_module.TIMELINE_METRIC_ORDER)
    assert payload["timeline"]["summary"] == timeline["summary"]
    for metric in bundle_module.TIMELINE_METRIC_ORDER:
        assert payload["timeline"]["timelines"][metric] == timeline["timelines"][metric]

    percentiles = reports["petrochina_pit_valuation_percentile_profile_v1.json"]
    assert payload["valuation_percentiles"]["records"] == percentiles["records"]
    assert [
        (record["metric_id"], record["window_id"]) for record in percentiles["records"]
    ] == [
        ("PE_A_TTM", "3y"),
        ("PE_A_TTM", "5y"),
        ("PB_A_MRQ", "3y"),
        ("PB_A_MRQ", "5y"),
        ("PS_A_TTM", "3y"),
        ("PS_A_TTM", "5y"),
    ]
    assert payload["valuation_percentiles"]["records"][0]["midrank_percentile_decimal"] == (
        "91.964286"
    )

    shadow = reports["petrochina_dimension_scoring_shadow_v6.json"]
    assert payload["shadow_dimensions"]["dimension_order"] == list(
        bundle_module.SHADOW_DIMENSION_ORDER
    )
    assert sorted(payload["shadow_dimensions"]["dimensions"]) == sorted(
        bundle_module.SHADOW_DIMENSION_ORDER
    )
    coverage = payload["shadow_dimensions"]["component_coverage"]
    assert [entry["dimension_id"] for entry in coverage] == list(
        bundle_module.SHADOW_DIMENSION_ORDER
    )
    assert payload["shadow_dimensions"]["non_production"] is True
    assert payload["shadow_dimensions"]["time_contract"] == shadow["time_contract"]
    assert payload["shadow_dimensions"]["score_eligible"] is False
    dimensions = payload["shadow_dimensions"]["dimensions"]
    assert dimensions["enterprise_quality"]["missing_component_ids"] == ["eq_roic"]
    assert dimensions["valuation_attractiveness"]["blocked_component_ids"] == ["va_pe"]
    assert shadow["overall_score_prohibited"] is True

    decision = reports["m2_stage2k1r4f4b_pe_disposition_decision_v1.json"]
    assert payload["pe_disposition"]["decision"] == (
        "PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE"
    )
    assert payload["pe_disposition"]["scoring_policy"] == decision["scoring_policy"]
    assert payload["pe_disposition"]["frozen_5y_evidence"] == decision["frozen_5y_evidence"]

    risk = reports["petrochina_risk_veto_report.json"]
    observations = payload["risk_observations"]["observations"]
    assert payload["risk_observations"]["risk_id_order"] == list(bundle_module.RISK_ID_ORDER)
    assert [record["risk_id"] for record in observations] == list(bundle_module.RISK_ID_ORDER)
    assert len(observations) == 8
    assert risk["expected_risk_count"] == 8
    for record, source in zip(observations, risk["observations"], strict=True):
        assert record["status"] == source["status"]
        assert record["observation_id"] == source["observation_id"]
        assert record["available_at"] == source["available_at"]
        assert record["lineage_status"] == source["lineage_status"]
        assert record["missing_reasons"] == source["missing_reasons"]
        assert record["all_evidence_ids"] == source["all_evidence_ids"]
        assert record["active_event_ids"] == source["active_event_ids"]
    missing = [record for record in observations if record["status"] == "missing_evidence"]
    assert len(missing) == 2
    assert [record["risk_id"] for record in missing] == list(risk["missing_evidence_risk_ids"])

    gaps = payload["explicit_gaps"]
    ledger = reports["m2_explicit_gap_ledger.json"]
    assert gaps["gap_count"] == 18 == len(ledger["gaps"])
    assert gaps["declared_current_gap_count"] == ledger["count_contract"]["current_gap_count"] == 18
    assert [row["gap_id"] for row in gaps["rows"]] == [row["gap_id"] for row in ledger["gaps"]]
    assert gaps["rows"] == ledger["gaps"]
    assert gaps["rows"][0]["exact_missing_reason"] == ledger["gaps"][0]["exact_missing_reason"]
    assert gaps["rows"][0]["consequence"] == ledger["gaps"][0]["consequence"]

    metadata = payload["sources"]
    assert [entry["name"] for entry in metadata] == list(bundle_module.SOURCE_REPORTS)
    for entry in metadata:
        raw = _repo_bytes(entry["name"])
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        assert entry["byte_count"] == len(raw)
        assert entry["sha256"] == bundle_module.PINNED_SOURCE_SHA256[entry["name"]]

    # Readable Markdown: Chinese sections, separate annual and TTM views, verbatim narratives.
    for section in (
        "## 汇编性质与边界",
        "## 一、固定来源与日期（混合日期历史汇编）",
        "## 二、原始价值画像（value_profile）",
        "## 三、PIT 财务状态时间线（period_end / effective_from / value / status）",
        "## 四、原始 TTM/MRQ 估值分位（与非 TTM 年度估值倍数分开）",
        "## 五、影子维度（非生产，不得作为评分或结论）",
        "## 六、PE 处置决定（数值评分已暂缓）",
        "## 七、风险观测（八个风险；缺失证据不是负面结论）",
        "## 八、显式缺口台账（全部 18 条，原样）",
        "## 九、非生产边界（无总体评分、无结论）",
        "## 十、原报告叙事附录",
    ):
        assert section in markdown
    assert "混合日期的历史汇编" in markdown
    assert "不是统一 as-of 时点的 PIT 查询" in markdown
    assert "not_computable_under_strict_evidence_contract" in markdown
    assert "missing_input" in markdown
    assert "PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE" in markdown
    assert "12.89158710139375214555441126" in markdown
    assert markdown.count("### 8.18 `M2G-ROIC-007`") == 1
    for gap in ledger["gaps"]:
        assert gap["gap_id"] in markdown
    for name, text in narratives.items():
        assert name in markdown
        assert bundle_module.SOURCES_REPORTS_DIR + "/" + name in markdown
        assert text.splitlines()[0] in markdown
    assert "ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT" in markdown

    # Original source dates only: no current timestamp, no absolute host path.
    today = date.today().isoformat()
    for rendered in (markdown, json.dumps(payload, ensure_ascii=False)):
        assert today not in rendered
        assert str(tmp_path) not in rendered
        assert str(ROOT) not in rendered
        assert "\\" not in rendered
        assert ":\\" not in rendered and ":/" not in rendered


def test_subprocess_export_and_verify_from_unrelated_cwd(tmp_path: Path) -> None:
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    first = _export(tmp_path, "first")
    second = _export(tmp_path, "second")

    assert sorted(path.name for path in first.iterdir()) == [
        bundle_module.MANIFEST_NAME,
        bundle_module.REPORT_JSON_NAME,
        bundle_module.REPORT_MARKDOWN_NAME,
        bundle_module.SOURCES_DIR,
    ]
    files = sorted(
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    )
    assert len(files) == TOTAL_FILES_WITH_MANIFEST
    assert set(files) == set(bundle_module.expected_managed_files()) | {bundle_module.MANIFEST_NAME}
    nested = first / bundle_module.SOURCES_REPORTS_DIR
    assert sorted(path.name for path in nested.iterdir()) == sorted(bundle_module.SOURCE_REPORTS)

    # Retained attachments are byte-exact copies of the repository reports.
    for name in bundle_module.SOURCE_REPORTS:
        retained = (nested / name).read_bytes()
        assert retained == _repo_bytes(name)
        assert hashlib.sha256(retained).hexdigest() == bundle_module.PINNED_SOURCE_SHA256[name]

    manifest = json.loads((first / bundle_module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["managed_file_count"] == MANAGED_FILES
    assert sorted(entry["path"] for entry in manifest["files"]) == sorted(
        bundle_module.expected_managed_files()
    )
    assert manifest["verification"]["current_timestamp_recorded"] is False
    assert not {"timestamp", "generated_at", "created_at"} & manifest.keys()

    verified = json.loads(_stdout(_run_module("--verify", str(first), cwd=unrelated)))
    assert verified["schema"] == bundle_module.SCHEMA_ID
    assert verified["status"] == "verified"
    assert verified["verified_file_count"] == MANAGED_FILES

    # Deterministic bytes, independent of the output location.
    for name in bundle_module.expected_managed_files():
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert (first / bundle_module.MANIFEST_NAME).read_bytes() == (
        second / bundle_module.MANIFEST_NAME
    ).read_bytes()

    # report links resolve inside the exported directory
    markdown = (first / bundle_module.REPORT_MARKDOWN_NAME).read_text(encoding="utf-8")
    for name in bundle_module.SOURCE_REPORTS:
        link = f"{bundle_module.SOURCES_REPORTS_DIR}/{name}"
        assert f"]({link})" in markdown
        assert (first / link).is_file()


def test_tampered_package_is_rejected_even_with_recomputed_manifest(tmp_path: Path) -> None:
    exported = _export(tmp_path, "tampered")
    assert _run_module("--verify", str(exported), cwd=tmp_path).returncode == 0

    # (a) rendered report tampered with, manifest recomputed to match the new bytes
    report = exported / bundle_module.REPORT_MARKDOWN_NAME
    report.write_bytes(
        report.read_bytes()
        .replace(b"# \xe4\xb8\xad\xe7\x9f\xb3\xe6\xb2\xb9", b"# \xe7\xaf\xa1\xe6\x94\xb9", 1)
    )
    manifest_path = exported / bundle_module.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        raw = (exported / entry["path"]).read_bytes()
        entry["byte_count"] = len(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["artifact_digest"] = hashlib.sha256(
        bundle_module.manifest_digest_bytes(manifest)
    ).hexdigest()
    manifest_path.write_bytes(bundle_module.canonical_manifest_bytes(manifest))

    tampered = _run_module("--verify", str(exported), cwd=tmp_path)
    assert tampered.returncode != 0
    assert tampered.stdout == b""
    assert b"VERIFY_RENDER_MISMATCH" in tampered.stderr

    # (b) retained source attachment tampered with, manifest again recomputed to match
    exported2 = _export(tmp_path, "tampered_source")
    source = exported2 / bundle_module.SOURCES_REPORTS_DIR / "petrochina_value_profile.json"
    raw = source.read_bytes()
    marker = (
        b'"contract": "petrochina_value_profile_v1",'
        b' "tampered_marker": "' + INJECTED_MARKER.encode("ascii") + b'",'
    )
    assert b'"contract": "petrochina_value_profile_v1",' in raw
    source.write_bytes(
        raw.replace(b'"contract": "petrochina_value_profile_v1",', marker, 1)
    )
    manifest2_path = exported2 / bundle_module.MANIFEST_NAME
    manifest2 = json.loads(manifest2_path.read_text(encoding="utf-8"))
    for entry in manifest2["files"]:
        raw = (exported2 / entry["path"]).read_bytes()
        entry["byte_count"] = len(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest2["artifact_digest"] = hashlib.sha256(
        bundle_module.manifest_digest_bytes(manifest2)
    ).hexdigest()
    manifest2_path.write_bytes(bundle_module.canonical_manifest_bytes(manifest2))

    tampered_source = _run_module("--verify", str(exported2), cwd=tmp_path)
    assert tampered_source.returncode != 0
    assert tampered_source.stdout == b""
    assert b"VERIFY_SOURCE_CORRUPT" in tampered_source.stderr

    # A manifest pointing outside the managed set is never accepted.
    exported3 = _export(tmp_path, "tampered_manifest")
    manifest3_path = exported3 / bundle_module.MANIFEST_NAME
    manifest3 = json.loads(manifest3_path.read_text(encoding="utf-8"))
    manifest3["files"].append({"path": "../outside.txt", "byte_count": 0, "sha256": "0" * 64})
    manifest3["artifact_digest"] = hashlib.sha256(
        bundle_module.manifest_digest_bytes(manifest3)
    ).hexdigest()
    manifest3_path.write_bytes(bundle_module.canonical_manifest_bytes(manifest3))
    rejected = _run_module("--verify", str(exported3), cwd=tmp_path)
    assert rejected.returncode != 0
    assert rejected.stdout == b""
    assert b"VERIFY_MANIFEST_INVALID" in rejected.stderr


def test_preexisting_output_is_rejected_and_left_untouched(tmp_path: Path, record_property) -> None:
    sentinel_dir = tmp_path / "existing"
    sentinel_dir.mkdir()
    sentinel = sentinel_dir / "sentinel.bin"
    sentinel_bytes = b"foreign artifact: not part of any bundle\n"
    sentinel.write_bytes(sentinel_bytes)

    completed = _run_module("--output", str(sentinel_dir), cwd=tmp_path)
    assert completed.returncode != 0
    assert completed.stdout == b""
    assert completed.stderr.startswith(b"error: ")
    assert b"OUTPUT_PATH_EXISTS" in completed.stderr
    assert sentinel.read_bytes() == sentinel_bytes
    assert sorted(path.name for path in sentinel_dir.iterdir()) == ["sentinel.bin"]
    assert not (sentinel_dir / bundle_module.MANIFEST_NAME).exists()
    assert not (sentinel_dir / bundle_module.SOURCES_DIR).exists()

    link = tmp_path / "existing_link"
    try:
        os.symlink(sentinel_dir, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        record_property("optional_symlink_probe", "unavailable; directory preservation verified")
        return
    linked = _run_module("--output", str(link), cwd=tmp_path)
    assert linked.returncode != 0
    assert linked.stdout == b""
    assert b"OUTPUT_PATH_EXISTS" in linked.stderr
    assert link.is_symlink()
    assert sorted(path.name for path in sentinel_dir.iterdir()) == ["sentinel.bin"]
    assert sentinel.read_bytes() == sentinel_bytes
