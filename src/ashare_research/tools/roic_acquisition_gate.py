"""Generate the deterministic Stage 2I.1R2 acquisition coverage artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ashare_research.tools.roic_contracts import (
    DEPENDENCY_GRAPH_PATH,
    REGISTRY_PATH,
    load_dependency_graph,
    load_registry,
    validate_acquisition_plan,
)
from ashare_research.tools.roic_fact_readiness import build_readiness_report

ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = ROOT / "config" / "roic_official_fact_acquisition_plan_v3.json"


def build_acquisition_gate_report(
    *,
    plan_path: Path = PLAN_PATH,
    registry_path: Path = REGISTRY_PATH,
    dependency_graph_path: Path = DEPENDENCY_GRAPH_PATH,
    target_year: int = 2024,
    opening_year: int = 2023,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    graph = load_dependency_graph(dependency_graph_path)
    readiness = build_readiness_report(
        registry_path=registry_path,
        dependency_graph_path=dependency_graph_path,
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    return validate_acquisition_plan(
        registry,
        plan,
        graph,
        readiness,
        target_year=target_year,
        opening_year=opening_year,
    )


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# ROIC acquisition-plan v3 coverage validation",
            "",
            f"- Validation: **{report['validation_status']}**",
            f"- Plan digest: `{report['plan_digest']}`",
            f"- Registry digest: `{report['registry_sha256']}`",
            f"- Dependency graph digest: `{report['dependency_graph_sha256']}`",
            f"- Readiness report digest: `{report['readiness_report_sha256']}`",
            f"- Covered blocker cells: `{len(report['covered_blockers'])}`",
            f"- Uncovered: `{len(report['uncovered_blockers'])}`",
            f"- Orphan: `{len(report['orphan_items'])}`",
            f"- Mislayered: `{len(report['mislayered_items'])}`",
            f"- Duplicate contribution: `{len(report['duplicated_contributions'])}`",
            "",
            "The next-stage acquisition decision below is generated only from the",
            "validator result; it is not a manually asserted status.",
            "",
            f"Next-stage acquisition: **{report['next_stage_acquisition']}**",
            "",
        ]
    )


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "petrochina_roic_acquisition_plan_v3_coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "petrochina_roic_acquisition_plan_v3_coverage.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    report = build_acquisition_gate_report()
    write_report(report, args.output_dir)
    print(
        json.dumps(
            {
                "validation_status": report["validation_status"],
                "plan_digest": report["plan_digest"],
                "next_stage_acquisition": report["next_stage_acquisition"],
            }
        )
    )
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
