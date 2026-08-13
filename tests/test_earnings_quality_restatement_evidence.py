"""Later-comparative review evidence for earnings-quality facts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "acceptance/fixtures/restatements/601857.SH"


def test_review_matrix_has_exactly_four_changed_concepts():
    changed = []
    for year in range(2021, 2025):
        path = REVIEWS / f"earnings_quality_{year}_reviewed_by_{year + 1}.json"
        review = json.loads(path.read_text(encoding="utf-8"))
        assert review["contract"] == "earnings_quality_restatement_evidence_v1"
        assert review["evidence_fiscal_year"] == year + 1
        assert len(review["concepts"]) == 3
        for item in review["concepts"]:
            computed = item["original_raw_value"] != item["later_comparative_raw_value"]
            assert item["changed"] is computed
            assert item["review_status"] == (
                "reviewed_changed" if computed else "reviewed_unchanged"
            )
            if computed:
                changed.append((year, item["concept_id"]))
    assert changed == [
        (2022, "net_profit_excluding_non_recurring"),
        (2023, "net_profit_excluding_non_recurring"),
        (2023, "operating_cost"),
        (2023, "operating_profit"),
    ]
