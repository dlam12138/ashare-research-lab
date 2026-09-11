"""The main entry must expose usable capabilities and resolve its evidence links."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_capabilities_explain_entrypoints_and_limits():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    summary = text.split("## 当前可用能力", 1)[1].split("### 研究结论", 1)[0]
    for capability in (
        "M1",
        "M2",
        "M3",
        "M4-A.1",
        "M4-A.2",
        "M4-A.2D",
        "M4-A.2M",
        "M4-A.2E",
        "M4-B",
    ):
        assert f"| {capability} " in summary
    assert "如何使用" in summary and "限制" in summary and "证据" in summary
    assert "计划编译已实现" in summary
    assert "有界执行器尚未实现" in summary
    assert "统计执行尚未实现" in summary
    assert "holdout 始终不授权执行" in summary
    assert "build_analysis_plan(contract)" in text
    assert "ashare_research.mechanism.planning" in text
    assert "python -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py" in text
    assert "没有通用研究执行器" in summary
    assert "parse_hypothesis_config(document)" in text
    assert "compile_hypothesis_config(config)" in text
    assert "python -m pytest -q tests/test_m4_stage4a1_typed_contract.py" in text
    assert "真实验收命令另需显式" in text
    assert "历史停止与当前授权" in text


def test_entry_and_history_evidence_links_resolve():
    for relative in ("README.md", "docs/project-history.md", "agent/record/README.md"):
        path = ROOT / relative
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            assert (path.parent / target.split("#", 1)[0]).is_file(), (relative, target)
    assert "[README](../README.md)" in (ROOT / "docs/project-history.md").read_text(
        encoding="utf-8"
    )
    assert "[项目入口](../../README.md)" in (ROOT / "agent/record/README.md").read_text(
        encoding="utf-8"
    )
