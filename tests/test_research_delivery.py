from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import package_archive, research_delivery, research_workflow

REQUEST = {
    "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023],
    "metrics": None, "scope": "consolidated",
}


def _bytes(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    root = tmp_path_factory.mktemp("legacy-workflow-delivery")
    research_workflow.export_workflow(REQUEST, root / "workflow")
    receipt = package_archive.export_archive(root / "workflow", root / "workflow.zip")
    return root, receipt


def test_real_cli_delivery_matches_legacy_bytes_and_selectors_in_process(
    reference, tmp_path, monkeypatch, capsys
):
    root, expected = reference
    before = _bytes(root)
    temporary = []
    original_temp = research_delivery.tempfile.TemporaryDirectory

    def track_temp(*args, **kwargs):
        runtime = original_temp(*args, **kwargs)
        temporary.append(Path(runtime.name))
        return runtime

    def forbidden(*args, **kwargs):
        pytest.fail("direct delivery must not initialize legacy services")

    monkeypatch.setattr(research_delivery.tempfile, "TemporaryDirectory", track_temp)
    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "--help"]) == 0
    assert "deliver" in capsys.readouterr().out
    output = tmp_path / "direct.zip"
    assert cli.main([
        "research", "deliver", "--as-of", REQUEST["as_of"],
        "--compare-with", REQUEST["compare_with"], "--year", "2023",
        "--scope", "consolidated", "--output", str(output), "--json",
    ]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == expected
    assert output.read_bytes() == (root / "workflow.zip").read_bytes()
    assert _bytes(root) == before
    assert sum(path.name.startswith("m2-direct-delivery-") for path in temporary) == 1
    assert all(not path.exists() for path in temporary)
    assert set(tmp_path.iterdir()) == {output}

    single = tmp_path / "single.zip"
    metrics = ["net_profit_attributable_to_parent_yoy", "operating_cash_flow_yoy"]
    result = subprocess.run(
        [sys.executable, "-m", "ashare_research.cli", "research", "deliver",
         "--as-of", "2024-03-31", "--year", "2022", "--year", "2023",
         "--metric", metrics[0], "--metric", metrics[1], "--scope", "consolidated",
         "--output", str(single), "--json"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        capture_output=True, check=False,
    )
    assert result.returncode == 0 and result.stderr == b""
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "archived" and receipt["verified_file_count"] == 80
    request = receipt["verification"]["request"]
    assert request["as_of"] == "2024-03-31" and request["compare_with"] is None
    assert request["years"] == [2022, 2023] and set(request["metrics"]) == set(metrics)
    assert request["scope"] == "consolidated"
    assert package_archive.verify_archive(single) == {**receipt, "status": "verified"}
    assert set(tmp_path.iterdir()) == {output, single}
    restored = tmp_path / "restored"
    assert package_archive.restore_archive(output, restored)["verified_file_count"] == 131
    assert _bytes(restored) == _bytes(root / "workflow")
    assert _bytes(root) == before


def test_early_guards_validation_tampering_and_late_write_no_foreign_mutation(
    reference, tmp_path, monkeypatch, capsys
):
    root, _ = reference
    foreign = tmp_path / "foreign.zip"
    foreign.write_bytes(b"preserve caller file")
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    def forbidden(*args, **kwargs):
        pytest.fail("output guards must reject before any workflow build")

    with monkeypatch.context() as patch:
        patch.setattr(research_workflow, "export_workflow", forbidden)
        for output in (foreign, existing_dir):
            with pytest.raises(research_delivery.DeliveryError, match="^OUTPUT_PATH_EXISTS$"):
                research_delivery.deliver_workflow(REQUEST, output)
        original_link = Path.is_symlink
        link = tmp_path / "link"
        patch.setattr(Path, "is_symlink", lambda path: path == link or original_link(path))
        with pytest.raises(research_delivery.DeliveryError, match="^OUTPUT_PATH_INVALID$"):
            research_delivery.deliver_workflow(REQUEST, link / "escape.zip")
    assert not (tmp_path / "link").exists()
    for args in ([], ["--as-of", "2024-03-31"],
                 ["--as-of", "2024-03-31", "--output", str(tmp_path / "year"),
                  "--year", "invalid"]):
        assert cli.main(["research", "deliver", *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    invalid = tmp_path / "invalid.zip"
    assert cli.main(["research", "deliver", "--as-of", "bad",
                     "--output", str(invalid), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_AS_OF_DATE\n"
    assert not invalid.exists()

    def failed_build(request, staged):
        raise research_workflow.WorkflowError("SOURCE_HASH_MISMATCH")

    with monkeypatch.context() as patch:
        patch.setattr(research_workflow, "export_workflow", failed_build)
        with pytest.raises(research_delivery.DeliveryError, match="^SOURCE_HASH_MISMATCH$"):
            research_delivery.deliver_workflow(REQUEST, tmp_path / "build-failed.zip")
    assert not (tmp_path / "build-failed.zip").exists()

    def copied_build(request, staged):
        shutil.copytree(root / "workflow", staged)

    def tampered_build(request, staged):
        copied_build(request, staged)
        (staged / "manifest.json").write_bytes(b"{}")

    with monkeypatch.context() as patch:
        patch.setattr(research_workflow, "export_workflow", tampered_build)
        assert cli.main(["research", "deliver", "--as-of", "2024-03-31",
                         "--output", str(tmp_path / "tampered.zip"), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: VERIFY_MANIFEST_INVALID\n"
    assert not (tmp_path / "tampered.zip").exists()

    late = tmp_path / "late.zip"
    original_open = Path.open

    class FailingWriter:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def write(self, raw):
            self.stream.write(raw[:3])
            raise OSError("private machine detail")

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

    def output_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return FailingWriter(stream) if path == late and args == ("xb",) else stream

    with monkeypatch.context() as patch:
        patch.setattr(research_workflow, "export_workflow", copied_build)
        patch.setattr(Path, "open", output_open)
        assert cli.main(["research", "deliver", "--as-of", "2024-03-31",
                         "--output", str(late), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: OUTPUT_WRITE_FAILED\n"
    assert late.read_bytes() == b"PK\x03"
    assert foreign.read_bytes() == b"preserve caller file" and existing_dir.is_dir()
    assert set(tmp_path.iterdir()) == {foreign, existing_dir, late}
