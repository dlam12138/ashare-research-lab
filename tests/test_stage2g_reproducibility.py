"""Clean-clone and contract tests for Stage 2G.2."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ashare_research.reproducibility.artifacts import verify_artifacts
from ashare_research.reproducibility.capsule import (
    build_temp_fact_db,
    build_test_capsule,
    validate_snapshot,
)
from ashare_research.reproducibility.market import MarketSnapshotResolver
from ashare_research.tools.petrochina_valuation_and_value_profile import (
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
    capsule = tmp_path / "capsule"
    build_test_capsule(capsule, committed_snapshot_dir=SNAPSHOT)
    first = run_test_capsule(capsule)
    second = run_test_capsule(capsule)
    assert first["status"] == second["status"] == "pass"
    assert first["observation_count"] == second["observation_count"] == 8106
    assert first["artifact_verification"]["sha256"] == second["artifact_verification"]["sha256"]
    assert verify_artifacts(capsule / "runs" / "stage2g2_test_capsule")["status"] == "pass"


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


def test_verify_contracts_is_offline_and_explicitly_gap_aware() -> None:
    result = verify_contracts()
    assert result["status"] == "pass_with_explicit_gaps"
    assert result["market_registry"]["path_portable"] is True
    assert result["dividend_evidence"]["rule007_eligible_event_count"] == 1
