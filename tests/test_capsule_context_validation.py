"""Context ambiguity must fail before a temporary database is created."""

import json
import shutil
from pathlib import Path

import pytest

from ashare_research.reproducibility.capsule import build_temp_fact_db, validate_snapshot

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


@pytest.mark.parametrize(
    "mutation", ["duplicate", "conflicting_duplicate", "orphan", "empty", "numeric"]
)
def test_context_mutations_fail_before_import(tmp_path, mutation):
    snapshot = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, snapshot)
    path = snapshot / "contexts.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    extra = dict(rows[0])
    if mutation == "conflicting_duplicate":
        extra["accounting_standard"] = "CONFLICT"
    elif mutation == "orphan":
        extra["context_id"] = "unreferenced-context"
    elif mutation == "empty":
        extra["context_id"] = ""
    elif mutation == "numeric":
        extra["context_id"] = 42
    rows.append(extra)
    path.write_text(json.dumps(rows), encoding="utf-8")
    manifest_path = snapshot / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["context_count"] = len(rows)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "db" / "temporary.duckdb"
    with pytest.raises(ValueError, match="context"):
        build_temp_fact_db(snapshot, output)
    assert not output.parent.exists()


def test_existing_contexts_are_valid():
    assert validate_snapshot(SNAPSHOT)["status"] == "pass"
