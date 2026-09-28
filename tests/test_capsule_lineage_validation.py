"""Reject structurally incomplete or misbound snapshot provenance."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from ashare_research.reproducibility.capsule import build_temp_fact_db, validate_snapshot

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


@pytest.mark.parametrize("mutation", ["truncate", "duplicate", "orphan", "rebind", "id_type"])
def test_invalid_lineage_rejected_before_db_creation(tmp_path, mutation):
    copied = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, copied)
    path = copied / "lineage.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "truncate":
        rows.pop()
    elif mutation == "duplicate":
        rows[1]["lineage_id"] = rows[0]["lineage_id"]
    elif mutation == "orphan":
        rows[0]["fact_id"] = "unknown-fact"
    elif mutation == "rebind":
        rows[0]["fact_id"] = next(r["fact_id"] for r in rows if r["fact_id"] != rows[0]["fact_id"])
    else:
        rows[0]["lineage_id"] = str(rows[0]["lineage_id"])
    path.write_text(json.dumps(rows), encoding="utf-8")
    target = tmp_path / "db" / "temporary.duckdb"
    with pytest.raises(ValueError, match="lineage"):
        build_temp_fact_db(copied, target)
    assert not target.parent.exists()


def test_original_snapshot_lineage_remains_valid():
    result = validate_snapshot(SNAPSHOT)
    assert result["lineage_count"] == result["manifest"]["lineage_count"]


@pytest.mark.parametrize("declared", [None, [], [True], [1, 1], ["3"]])
def test_invalid_declared_lineage_is_rejected(tmp_path, declared):
    copied = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, copied)
    path = copied / "facts.json"
    facts = json.loads(path.read_text(encoding="utf-8"))
    facts[0]["lineage_ids"] = declared
    data = json.dumps(facts).encode("utf-8")
    path.write_bytes(data)
    manifest_path = copied / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["facts_sha256"] = hashlib.sha256(data).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="lineage binding"):
        validate_snapshot(copied)
