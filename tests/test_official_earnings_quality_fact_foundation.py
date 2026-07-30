"""Offline integration test for the 2021-2025 earnings-quality foundation."""

from __future__ import annotations

import json
from pathlib import Path

from ashare_research.tools.official_earnings_quality_fact_foundation import (
    EXPECTED_COUNTS,
    run_earnings_quality_foundation,
)


def test_complete_offline_foundation(tmp_path: Path):
    result = run_earnings_quality_foundation(tmp_path, run_id="test_run")
    assert result["status"] == "passed"
    assert result["transaction_committed"] is True
    assert result["R"] == 4
    assert result["counts"] == EXPECTED_COUNTS
    assert result["latest_pit_count"] == 35
    assert result["annual_cumulative_pit"] == [0, 7, 14, 21, 28, 35]
    assert result["upstream_fact_id_count"] == 84
    assert result["frozen_metric_results"]["count"] == 38
    assert len(result["new_fact_ids"]) == 48
    assert result["downloaded"] == 0
    assert result["network_access"] is False
    run_dir = Path(result["run_directory"])
    assert (run_dir / "earnings_quality.duckdb").is_file()
    assert {
        "evidence_manifest.json",
        "reconciliation_results.json",
        "restatement_results.json",
        "latest_fact_snapshot.json",
        "lineage_summary.json",
        "run_manifest.json",
        "acceptance_summary.md",
    } <= {path.name for path in run_dir.iterdir()}
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["default_db_sha256_before"] == manifest[
        "default_db_sha256_after"
    ]
