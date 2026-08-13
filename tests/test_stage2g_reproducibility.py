"""Clean-clone and contract tests for Stage 2G.2."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ashare_research.reproducibility.artifacts import (
    compare_artifact_runs,
    logical_artifact_digest,
    verify_artifacts,
)
from ashare_research.reproducibility.capsule import (
    build_temp_fact_db,
    build_test_capsule,
    compare_capsules,
    validate_snapshot,
)
from ashare_research.reproducibility.market import MarketSnapshotResolver
from ashare_research.reproducibility.rule007 import select_rule007_sources
from ashare_research.tools.petrochina_valuation_and_value_profile import (
    _build_rule007_facts,
    _reconcile_rule007_facts,
    validate_dividend_evidence,
)
from ashare_research.tools.stage2g_reproducibility import (
    run_test_capsule,
    verify_contracts,
)

ROOT = Path(__file__).parents[1]
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


def test_committed_snapshot_is_portable_and_lossless() -> None:
    result = validate_snapshot(SNAPSHOT)
    assert result["row_count"] == 33
    assert result["manifest"]["identity_validation"] == "pass"
    assert result["manifest"]["version_chain_validation"] == "pass"
    assert all(row["value_decimal"] for row in result["facts"])
    assert all("D:\\" not in json.dumps(row) for row in result["facts"])


def test_tampered_snapshot_hash_fails(tmp_path: Path) -> None:
    copied = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, copied)
    facts_path = copied / "facts.json"
    facts_path.write_text(facts_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_snapshot(copied)


def test_missing_context_fails_before_temporary_db_import(tmp_path: Path) -> None:
    copied = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, copied)
    contexts_path = copied / "contexts.json"
    contexts = json.loads(contexts_path.read_text(encoding="utf-8"))
    contexts.pop()
    contexts_path.write_text(json.dumps(contexts), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch|row count mismatch|missing contexts"):
        build_temp_fact_db(copied, tmp_path / "temp.duckdb")


def test_test_capsule_build_and_run_are_artifact_verified(tmp_path: Path) -> None:
    capsule_a = tmp_path / "capsule-a"
    capsule_b = tmp_path / "capsule-b"
    build_test_capsule(capsule_a, committed_snapshot_dir=SNAPSHOT)
    build_test_capsule(capsule_b, committed_snapshot_dir=SNAPSHOT)
    assert compare_capsules(capsule_a, capsule_b)["status"] == "pass"
    first = run_test_capsule(
        capsule_a,
        output_root=tmp_path / "run-a",
        run_id="stage2g2_test_capsule_a",
    )
    second = run_test_capsule(
        capsule_b,
        output_root=tmp_path / "run-b",
        run_id="stage2g2_test_capsule_a",
    )
    assert first["status"] == second["status"] == "pass"
    assert first["observation_count"] == second["observation_count"] == 8106
    run_a = tmp_path / "run-a" / "stage2g2_test_capsule_a"
    run_b = tmp_path / "run-b" / "stage2g2_test_capsule_a"
    assert verify_artifacts(run_a)["status"] == "pass"
    assert verify_artifacts(run_b)["status"] == "pass"
    comparison = compare_artifact_runs(run_a, run_b)
    assert comparison["status"] == "pass"
    assert comparison["left"]["logical_digest"] == comparison["right"]["logical_digest"]
    manifest = json.loads((run_a / "artifact_manifest.json").read_text(encoding="utf-8"))
    changed_run_id = {**manifest, "run_id": "different-run-id"}
    assert logical_artifact_digest(manifest) == logical_artifact_digest(changed_run_id)
    with pytest.raises(FileExistsError, match="overwrite"):
        run_test_capsule(
            capsule_a,
            output_root=tmp_path / "run-a",
            run_id="stage2g2_test_capsule_a",
        )
    with pytest.raises(FileExistsError, match="overwrite"):
        build_test_capsule(capsule_a, committed_snapshot_dir=SNAPSHOT)


def test_dual_run_tamper_and_delete_fail_artifact_integrity(tmp_path: Path) -> None:
    capsule = tmp_path / "capsule"
    build_test_capsule(capsule, committed_snapshot_dir=SNAPSHOT)
    run_test_capsule(capsule, output_root=tmp_path / "run", run_id="tamper-test")
    run_dir = tmp_path / "run" / "tamper-test"
    target = run_dir / "summary.json"
    target.write_text(target.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact integrity failure"):
        verify_artifacts(run_dir)
    target.unlink()
    with pytest.raises(ValueError, match="artifact integrity failure"):
        verify_artifacts(run_dir)


def test_market_registry_has_no_absolute_paths_and_resolves_only_explicit_root(
    tmp_path: Path,
) -> None:
    capsule = tmp_path / "capsule"
    build_test_capsule(capsule, committed_snapshot_dir=SNAPSHOT)
    registry = json.loads(
        (capsule / "market_data_snapshot_registry_v2.json").read_text(encoding="utf-8")
    )
    MarketSnapshotResolver.validate_registry_contract(registry)
    resolved, _ = MarketSnapshotResolver(
        capsule / "market_data_snapshot_registry_v2.json",
        mode="test_capsule",
        fixture_root=capsule / "market_test_capsule_v1",
    ).resolve()
    assert len(resolved) == 2
    with pytest.raises(ValueError, match="cannot use an external"):
        MarketSnapshotResolver(
            capsule / "market_data_snapshot_registry_v2.json",
            mode="test_capsule",
            cache_root=tmp_path / "external",
            fixture_root=capsule / "market_test_capsule_v1",
        ).resolve()


def test_real_market_mode_missing_cache_fails_closed(tmp_path: Path) -> None:
    registry = ROOT / "events" / "market_data_snapshot_registry.json"
    with pytest.raises(FileNotFoundError, match="missing_external_research_input"):
        MarketSnapshotResolver(registry, mode="real_research").resolve()


def test_rule007_designated_platform_is_not_exchange_side() -> None:
    events = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )["events"]
    sources = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )["entries"]
    designated = next(
        source for source in sources if source["source_evidence_id"] == "2024-interim-exchange"
    )
    designated["source_type"] = "designated_disclosure_platform"
    result = validate_dividend_evidence(events, sources)
    assert result["rule007_eligible_event_count"] == 0
    assert result["eligible"] == []
    assert any(
        gap["status"] == "issuer_plus_designated_platform_verified" for gap in result["gaps"]
    )


def _rule_source(source_id: str, source_type: str, *, value: str = "1.00") -> dict:
    return {
        "source_evidence_id": source_id,
        "source_type": source_type,
        "retrieval_status": "retrieved",
        "content_sha256": f"hash-{source_id}",
        "independently_extracted": True,
        "extracted_values": {
            "cash_dividend_total": value,
            "cash_dividend_per_share": value,
        "share_capital": "100",
            "currency": "CNY",
            "share_scope": "ordinary_total",
        },
    }


@pytest.mark.parametrize(
    ("sources", "expected"),
    [
        ([], "no_retrieved_official_source"),
        (
            [
                {
                    "source_evidence_id": "unretrieved",
                    "source_type": "issuer_official",
                    "retrieval_status": "not_retrieved",
                }
            ],
            "no_retrieved_official_source",
        ),
        ([_rule_source("issuer", "issuer_official")], "issuer_only"),
        ([_rule_source("exchange", "exchange_official")], "exchange_only"),
        (
            [_rule_source("designated", "designated_disclosure_platform")],
            "designated_platform_only",
        ),
        (
            [
                _rule_source("issuer", "issuer_official"),
                _rule_source("designated", "designated_disclosure_platform"),
            ],
            "issuer_plus_designated_platform_verified",
        ),
        (
            [
                _rule_source("exchange", "exchange_official"),
                _rule_source("designated", "designated_disclosure_platform"),
            ],
            "exchange_plus_designated_platform_verified",
        ),
        (
            [
                _rule_source("issuer", "issuer_official"),
                _rule_source("exchange", "exchange_official"),
            ],
            "issuer_exchange_rule007_eligible",
        ),
        ([{}], "incomplete_or_invalid_evidence"),
    ],
)
def test_rule007_source_state_boundaries(sources: list[dict], expected: str) -> None:
    pair, errors = select_rule007_sources(sources)
    assert pair["status"] == expected
    assert pair["rule007_eligible"] is (expected == "issuer_exchange_rule007_eligible")
    if expected == "no_retrieved_official_source":
        assert not errors


def test_rule007_three_sources_keep_designated_supplemental_out_of_fact_inputs() -> None:
    events = json.loads(
        (ROOT / "events" / "dividend_events_2021_2026_v2.json").read_text(encoding="utf-8")
    )["events"]
    sources = json.loads(
        (ROOT / "events" / "dividend_source_evidence_2021_2026.json").read_text(encoding="utf-8")
    )["entries"]
    event = next(
        item
        for item in events
        if item["source_fiscal_year"] == 2024 and item["event_type"] == "interim"
    )
    exchange = next(
        item for item in sources if item["source_evidence_id"] == "2024-interim-exchange"
    )
    designated = dict(exchange)
    designated["source_evidence_id"] = "2024-interim-designated-supplemental"
    designated["source_type"] = "designated_disclosure_platform"
    designated["content_sha256"] = "supplemental-hash"
    event["source_evidence_ids"] = [
        *event["source_evidence_ids"],
        designated["source_evidence_id"],
    ]
    result = validate_dividend_evidence(events, [*sources, designated])
    eligible = next(item for item in result["eligible"] if item["event"] is event)
    assert eligible["pair_contract"]["status"] == "issuer_exchange_rule007_eligible"
    assert eligible["pair_contract"]["supplemental_sources"] == [designated]
    raw = _build_rule007_facts({"eligible": [eligible]})
    reconciled = _reconcile_rule007_facts({"eligible": [eligible]}, raw)
    assert all(
        designated["source_evidence_id"] not in item["input_fact_ids"] for item in reconciled
    )


def test_verify_contracts_is_offline_and_explicitly_gap_aware() -> None:
    result = verify_contracts()
    assert result["status"] == "pass_with_explicit_gaps"
    assert result["market_registry"]["path_portable"] is True
    assert result["dividend_evidence"]["rule007_eligible_event_count"] == 1
