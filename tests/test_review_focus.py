"""Original review rows/comparisons from freshly verified directory and ZIP."""

import copy
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import (
    delivered_research,
    package_archive,
    research_review,
    research_session,
    review_focus,
)

METRIC = "cash_based_free_cash_flow_proxy"
YOY = "operating_cash_flow_yoy"


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("review-focus")
    session = root / "session"
    research_session.export_session({
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2025],
        "metrics": [METRIC, YOY], "scope": "consolidated",
    }, session)
    review = root / "review"
    research_review.export_review(session, review)
    archive = root / "review.zip"
    package_archive.export_archive(review, archive)
    original = delivered_research.read_report(archive, "review", archive=True)
    return review, archive, original


def test_original_rows_comparisons_missing_zero_empty_and_legacy(delivery, capsys):
    review, archive, original = delivery
    saved = copy.deepcopy(original)
    raw = archive.read_bytes()
    source = original["report"]
    args = ["research", "read", "--archive", str(archive), "--section", "review"]
    assert cli.main([*args, "--metric", METRIC, "--metric", METRIC,
                     "--year", "2023", "--year", "2023", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == review_focus.SCHEMA and report["source_read"] == original
    assert report["selection"] == {"metrics": [METRIC], "years": [2023],
                                   "missing_only": False}
    expected = [{**view, "rows": [row for row in view["rows"]
                                 if row["metric_id"] == METRIC and row["fiscal_year"] == 2023]}
                for view in source["views"]]
    assert report["review"]["views"] == expected and report["selected_row_count"] == 2
    comparison_entries = [
        row for row in source["comparison"]["entries"]
        if row["metric_id"] == METRIC and row["fiscal_year"] == 2023
    ]
    assert report["review"]["comparison"]["entries"] == comparison_entries
    assert report["review"]["comparison"]["states"] == {
        state: sum(row["state"] == state for row in comparison_entries)
        for state in source["comparison"]["states"]
    }
    missing = review_focus.build_report(original, years=[2025], missing_only=True)
    assert missing["selected_row_count"] == 4
    assert missing["selected_comparison_count"] == 2
    for view, full_view in zip(missing["review"]["views"], source["views"], strict=True):
        assert view["date"] == full_view["date"] and view["fact_count"] == full_view["fact_count"]
        assert view["rows"] == [row for row in full_view["rows"]
                                if row["fiscal_year"] == 2025 and row["value"] is None]
        assert all(row["missing_roles"] for row in view["rows"])
    assert missing["review"]["notes"] == source["notes"]
    assert missing["review"]["metric_limitations"] == source["metric_limitations"]
    empty = review_focus.build_report(original, metrics=[METRIC], years=[2023], missing_only=True)
    assert empty["selected_row_count"] == 0 and empty["review"]["comparison"]["entries"] == []
    assert not any(empty["review"]["comparison"]["states"].values())
    assert "当前选择没有匹配项" in review_focus.render_markdown(empty)
    # Pure projection edge case: null remains selected, zero is not classified as missing.
    edge = copy.deepcopy(original)
    left, right = edge["report"]["views"]
    left_row = next(row for row in left["rows"]
                    if row["metric_id"] == METRIC and row["fiscal_year"] == 2023)
    right_row = next(row for row in right["rows"]
                     if row["metric_id"] == METRIC and row["fiscal_year"] == 2023)
    left_row["value"] = None
    right_row["value"] = "0"
    selected = review_focus.build_report(edge, metrics=[METRIC], years=[2023], missing_only=True)
    assert selected["review"]["views"][0]["rows"] == [left_row]
    assert selected["review"]["views"][1]["rows"] == []
    assert selected["selected_comparison_count"] == 1
    assert selected["review"]["comparison"]["entries"][0] in source["comparison"]["entries"]
    single = copy.deepcopy(original)
    single["report"]["comparison"] = None
    single["report"]["views"] = single["report"]["views"][:1]
    assert review_focus.build_report(single)["review"]["comparison"] is None
    for extra in ([], ["--json"]):
        assert cli.main([*args, *extra]) == 0
        out = capsys.readouterr().out
        assert (json.loads(out) == original if extra
                else out == research_review.render_markdown(source))
    assert cli.main(["research", "read", "--package", str(review), "--section", "review",
                     "--metric", METRIC, "--year", "2023"]) == 0
    assert capsys.readouterr().out == review_focus.render_markdown(report)
    assert original == saved and archive.read_bytes() == raw


def test_invalid_unknown_outer_forgery_and_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    _, archive, _ = delivery
    for section, extra in (("review", ["--fact", "id"]), ("review", ["--gaps-only"]),
                           ("audit", ["--missing-only"]), ("compare", ["--missing-only"]),
                           ("review", ["--metric", " "]), ("review", ["--year", "0"]),
                           ("review", ["--year", "abc"])):
        assert cli.main(["research", "read", "--archive", "absent", "--section", section,
                         *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    args = ["research", "read", "--archive", str(archive), "--section", "review", "--json"]
    for extra, code in ((["--metric", "unknown"], "METRIC_NOT_SELECTED"),
                        (["--year", "1999", "--missing-only"], "YEAR_NOT_SELECTED")):
        assert cli.main([*args, *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["review.md"] += b"\nForged outer review\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, content in files.items():
            target.writestr(name, content)
    assert cli.main(["research", "read", "--archive", str(forged), "--section", "review",
                     "--missing-only"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def mutate_after_load(path):
        result = loader(path)
        calls.append(path)
        path.write_bytes(b"changed after verified map")
        return result

    monkeypatch.setattr(package_archive, "load_verified_archive", mutate_after_load)
    selected = ["research", "read", "--archive", str(handoff), "--section", "review",
                "--metric", METRIC, "--year", "2023", "--json"]
    assert cli.main(selected) == 0 and calls == [handoff]
    assert json.loads(capsys.readouterr().out)["selected_row_count"] == 2
    assert cli.main(selected) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
