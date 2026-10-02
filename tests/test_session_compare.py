"""Four acceptance cases using actual pinned archives and public comparison."""

import hashlib
import json
import shutil

import pytest

from ashare_research import cli
from ashare_research.tools import pit_metric_replay, research_session
from ashare_research.tools import session_compare as compare


def _archive(root, **overrides):
    research_session.export_session(
        {
            "as_of": "2024-03-31",
            "compare_with": "2025-03-31",
            "years": [2023],
            "metrics": None,
            "scope": "consolidated",
            **overrides,
        },
        root,
    )
    return root


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    return _archive(tmp_path_factory.mktemp("compare") / "archive")


def test_restatements_preserve_original_comparison_records_and_input_traces(archive):
    report = compare.build_comparison(archive, archive, right_view="compare_with")
    original = json.loads((archive / "metrics/report.json").read_bytes())
    assert report["original_common_comparison"] == original["comparison"]
    assert report["states"]["value_changed"] == 7
    assert report["compared_key_count"] == report["common_key_count"] == 7
    for entry in report["entries"]:
        for side, name in (("before", "as_of"), ("after", "compare_with")):
            expected = next(
                r for r in original[name]["records"] if r["metric_id"] == entry["metric_id"]
            )
            assert entry[side] == expected
            assert entry[side]["inputs"]
            assert any(i["missing_source_reference_fields"] for i in entry[side]["inputs"])
            assert all(i["parents"]["unresolved"] for i in entry[side]["inputs"])
    assert report["left"]["boundary"]["historical_metric_publication_proven"] is False
    text = compare.render_markdown(report)
    assert "17407700.000000000000" in text and "17433900.000000000000" in text
    assert "](left/" not in text and "没有计算差额" in text


def test_selector_changes_missing_values_equal_dates_and_incompatible_views(archive, tmp_path):
    original = json.loads((archive / "metrics/report.json").read_bytes())
    metric = original["as_of"]["records"][0]["metric_id"]
    subset = _archive(tmp_path / "subset", years=[2023, 2024], metrics=[metric])
    report = compare.build_comparison(archive, subset)
    assert report["states"]["removed"] == 6
    assert report["states"]["added"] == 1
    assert report["states"]["unchanged"] == 1
    added = next(e for e in report["entries"] if e["state"] == "added")
    assert added["before"] is None and added["after"]["value"] is None
    assert added["after"]["missing_roles"]
    assert report["left"]["request"] != report["right"]["request"]
    equal = compare.build_comparison(archive, archive)
    assert equal["states"]["unchanged"] == 7
    mixed = _archive(tmp_path / "mixed", years=[2024, 2025])
    changed = compare.build_comparison(mixed, mixed, right_view="compare_with")
    assert (
        changed["original_common_comparison"]
        == json.loads((mixed / "metrics/report.json").read_bytes())["comparison"]
    )
    assert changed["states"]["status_changed"] == 7
    assert changed["states"]["inputs_changed"] == 4
    assert changed["states"]["unchanged"] == 3
    single = _archive(tmp_path / "single", compare_with=None)
    with pytest.raises(compare.CompareError, match="VIEW_NOT_REQUESTED"):
        compare.build_comparison(archive, single, right_view="compare_with")
    other_scope = _archive(tmp_path / "parent", scope="parent_company")
    with pytest.raises(compare.CompareError, match="SCOPE_MISMATCH"):
        compare.build_comparison(archive, other_scope)
    with pytest.raises(compare.CompareError, match="INVALID_VIEW"):
        compare.build_comparison(archive, archive, right_view="unknown")
    reverse = compare.build_comparison(archive, archive, left_view="compare_with")
    assert reverse["states"]["value_changed"] == 7
    assert reverse["original_common_comparison"] == pit_metric_replay.build_comparison(
        original["compare_with"]["records"], original["as_of"]["records"]
    )


def test_portable_export_exact_evidence_hashes_and_moved_verification(archive, tmp_path):
    root = tmp_path / "export"
    manifest = compare.export_comparison(archive, archive, root, right_view="compare_with")
    assert manifest["managed_file_count"] == 50
    assert len([p for p in root.rglob("*") if p.is_file()]) == 51
    for entry in manifest["files"]:
        raw = (root / entry["path"]).read_bytes()
        assert len(raw) == entry["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    for side in ("left", "right"):
        for path in archive.rglob("*"):
            if path.is_file():
                assert (root / side / path.relative_to(archive)).read_bytes() == path.read_bytes()
    text = (root / "compare.md").read_text(encoding="utf-8")
    assert "](left/metrics/report.json)" in text and "](right/metrics/report.json)" in text
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    for side in ("left", "right"):
        assert research_session.verify_session(moved / side)["verified_file_count"] == 24
    assert json.loads((moved / "compare.json").read_bytes()) == compare.build_comparison(
        archive, archive, right_view="compare_with"
    )


def test_real_cli_tamper_invalid_args_and_foreign_output_safety(
    archive, tmp_path, monkeypatch, capsys
):
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy initialization")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    prefix = ["research", "compare", "--left", str(archive), "--right", str(archive)]
    assert cli.main(["research", "compare", "--help"]) == 0
    assert "--right-view" in capsys.readouterr().out
    assert cli.main([*prefix, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["states"]["unchanged"] == 7
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep").write_bytes(b"foreign")
    with pytest.raises(compare.CompareError, match="OUTPUT_PATH_EXISTS"):
        compare.export_comparison(archive, archive, foreign)
    assert (foreign / "keep").read_bytes() == b"foreign"
    assert sorted(p.name for p in foreign.iterdir()) == ["keep"]
    tampered = tmp_path / "tampered"
    shutil.copytree(archive, tampered)
    (tampered / "metrics/report.json").write_bytes(b"{}")
    absent = tmp_path / "absent-parent" / "export"
    assert (
        cli.main(
            [
                "research",
                "compare",
                "--left",
                str(archive),
                "--right",
                str(tampered),
                "--output",
                str(absent),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("error: VERIFY_")
    assert not absent.parent.exists()
    for options in (["--bad"], ["--output", ""], ["--json", "--output", str(absent)]):
        assert cli.main([*prefix, *options]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ")
