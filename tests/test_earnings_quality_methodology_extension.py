"""Methodology contract for the earnings-quality metric extension."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/value_evaluation_methodology_earnings_quality_v1.json"
BASE_CONFIG = ROOT / "config/value_evaluation_methodology_v1.json"
BASE_DOC = ROOT / "docs/value_evaluation_methodology_v1.md"


def test_methodology_has_four_non_scoring_transparent_metrics():
    methodology = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert methodology["schema_version"] == "1.0"
    assert methodology["version"] == "1"
    assert methodology["score_eligible"] is False
    assert methodology["decimal"] == {
        "precision": 28,
        "canonical_quantum": "0.000000000001",
        "rounding": "ROUND_HALF_EVEN",
    }
    assert len(methodology["metrics"]) == 4
    assert all(item["score_eligible"] is False for item in methodology["metrics"])
    required = {
        "display_name_zh",
        "formula",
        "input_concepts",
        "unit",
        "supports",
        "does_not_support",
        "industry_context_required",
        "multi_year_trend_required",
        "pit_required",
        "restatement_sensitive",
        "cyclical_company_limitation",
    }
    assert all(required <= item.keys() for item in methodology["metrics"])
    assert methodology["score_blockers"]


def test_base_methodology_files_remain_separate():
    assert BASE_CONFIG.is_file()
    assert BASE_DOC.is_file()
    methodology = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert methodology["extends"] == "value_evaluation_methodology_v1"
