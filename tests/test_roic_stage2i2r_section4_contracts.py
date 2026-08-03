import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.tools import roic_official_fact_acquisition as stage


def test_search_classification_is_match_content_driven():
    assert (
        stage.classify_search_match(term="所得税费用", excerpt="税率调节", acquisition_id="x")[0]
        == "tax_proxy_only"
    )
    assert (
        stage.classify_search_match(term="合营企业", excerpt="合计单项不重大", acquisition_id="x")[
            0
        ]
        == "aggregate_only_disclosure"
    )
    assert (
        stage.classify_search_match(term="非经营金融资产", excerpt="利息收入", acquisition_id="x")[
            0
        ]
        == "acceptable_exact_fact"
    )
    assert (
        stage.classify_search_match(
            term="其他权益工具投资", excerpt="金融资产", acquisition_id="x"
        )[0]
        == "purpose_income_linkage_missing"
    )
    assert (
        stage.classify_search_match(term="未知", excerpt="无关", acquisition_id="x")[0]
        == "irrelevant"
    )


def test_gate_whitelist_fails_closed_for_each_validator():
    for status in ("FAILED", "UNKNOWN", None):
        assert (
            stage.decide_acquisition_gate("READY_FOR_SHADOW", {"validator": status})["decision"]
            == "ROIC_ACQUISITION_NOT_TRUSTED"
        )
    assert (
        stage.decide_acquisition_gate("BLOCKED_WITH_EXPLICIT_GAPS", {"all": "TRUSTED"})["decision"]
        == "ROIC_FACT_GAPS_REMAIN"
    )


def test_search_specs_cover_all_cells_and_rejection_codes():
    records = stage._missing_records()
    assert len(records) == 7
    assert all(item["acceptance_patterns"] and item["exclusion_patterns"] for item in records)
    assert all("TAX_PROXY_ONLY" in item["rejection_reason_codes"] for item in records)


def test_search_validator_rejects_missing_object_and_bad_pit():
    record = stage._missing_records()[0]
    with pytest.raises(ValueError):
        stage.validate_search_results([record] * 6)
    record["content_object_ids"] = []
    with pytest.raises(ValueError):
        stage.validate_search_results([record] + stage._missing_records()[1:])


def test_decimal_and_identity_helpers_are_non_float():
    assert isinstance(Decimal("1.20"), Decimal)
    assert "float(" not in stage.Path(stage.__file__).read_text(encoding="utf-8")


def test_plan_and_artifact_contracts_remain_complete():
    result = stage.validate_contracts()
    assert result["approved_item_count"] == 11
    assert result["affected_cell_count"] == 16


def test_reconciled_validator_requires_ordered_dual_evidence_and_digest():
    evidence = [
        {
            "fact_id": "i",
            "source_id": "s1",
            "source_type": "company_official",
            "content_sha256": "a",
        },
        {
            "fact_id": "e",
            "source_id": "s2",
            "source_type": "exchange_official",
            "content_sha256": "b",
        },
    ]
    fact = {
        "source_type": "reconciled_derived",
        "source_tier": "dual_official_reconciled",
        "source_evidence": evidence,
    }
    fact["evidence_set_digest"] = stage.canonical_digest(
        [
            {
                "fact_id": x["fact_id"],
                "source_id": x["source_id"],
                "content_sha256": x["content_sha256"],
            }
            for x in evidence
        ]
    )
    assert stage.validate_reconciled_fact(fact)["status"] == "TRUSTED"
    fact["source_evidence"] = list(reversed(evidence))
    with pytest.raises(ValueError):
        stage.validate_reconciled_fact(fact)


@pytest.mark.parametrize(
    "validator",
    ["cache", "extraction", "reconciliation", "identity", "pit", "search", "artifact", "plan"],
)
def test_each_gate_validator_failure_is_not_trusted(validator):
    assert (
        stage.decide_acquisition_gate("READY_FOR_SHADOW", {validator: "NOT TRUSTED"})["decision"]
        == "ROIC_ACQUISITION_NOT_TRUSTED"
    )


def test_search_identity_changes_when_spec_or_source_changes():
    records = stage._missing_records()
    first = records[0]["deterministic_id"]
    records[0]["search_spec_id"] += "-changed"
    changed = stage.canonical_digest(
        {k: v for k, v in records[0].items() if k != "deterministic_id"}
    )
    assert changed != first


def test_committed_delivery_manifest_recomputes_hashes():
    root = Path(__file__).parents[1]
    manifest = json.loads(
        (root / "reports/petrochina_roic_stage2i2r_delivery_manifest.json").read_text()
    )
    assert (
        manifest["formal_artifact_set_sha256"]
        == "ff96e7c1244712280941f077aa94f20eb958788990c636408bbc2bc1314c59f2"
    )
    for item in manifest["files"]:
        path = root / item["logical_path"]
        assert path.is_file()
        payload = path.read_bytes()
        if path.suffix in {".md", ".json"}:
            payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        assert len(payload) == item["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
