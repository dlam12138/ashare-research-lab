"""Inventory original compile-only plans and their declared series requirements."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.tools.research_plan import PlanError, build_report

SCHEMA = "m4_compile_only_hypothesis_inventory_v1"
MAX_HYPOTHESES = 16
MAX_OUTPUT_BYTES = 8_388_608


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def build_inventory(paths: Sequence[Path]) -> dict[str, Any]:
    if not 1 <= len(paths) <= MAX_HYPOTHESES:
        raise PlanError("INVALID_HYPOTHESIS_COUNT")
    sources = {}
    source_size = 0
    for path in paths:
        report = build_report(path)
        hypothesis_id = report["contract"]["hypothesis_id"]
        if hypothesis_id in sources:
            raise PlanError("DUPLICATE_HYPOTHESIS_ID")
        source_size += len(_json(report).encode("utf-8"))
        if source_size > MAX_OUTPUT_BYTES:
            raise PlanError("BATCH_TOO_LARGE")
        sources[hypothesis_id] = report
    sources = dict(sorted(sources.items()))
    groups = {}
    role_count = 0
    for hypothesis_id, report in sources.items():
        plan = report["plan"]
        for index, requirement in enumerate(plan["dataset_requirements"]["requirements"]):
            role_count += 1
            uses = groups.setdefault(requirement["series_id"], [])
            uses.append({
                "hypothesis_id": hypothesis_id,
                "requirement_index": index,
                "source_plan_digest": plan["plan_digest"],
                "requirement": requirement,
                "sample_plan": plan["sample_plan"],
                "universe_requirement": plan["dataset_requirements"]["universe_requirement"],
            })
    series = []
    for series_id, uses in sorted(groups.items()):
        hypotheses = sorted({use["hypothesis_id"] for use in uses})
        declarations = {
            _json({key: value for key, value in use["requirement"].items() if key != "role"})
            for use in uses
        }
        series.append({
            "series_id": series_id, "hypothesis_ids": hypotheses,
            "shared_declared_series": len(hypotheses) > 1,
            "role_independent_declarations_differ": len(declarations) > 1,
            "uses": uses,
        })
    result = {
        "schema": SCHEMA,
        "status": "compiled_pre_execution",
        "counts": {
            "hypotheses": len(sources), "role_requirements": role_count,
            "declared_series": len(series),
            "shared_declared_series": sum(item["shared_declared_series"] for item in series),
        },
        "series_groups": series,
        "sources": sources,
        "boundary": dict(next(iter(sources.values()))["boundary"]),
        "notes": [
            "Shared series IDs describe declared names, not verified shared or reusable data.",
            "Original roles, timing, transforms, quality gates, windows and universes "
            "stay separate.",
            "Different declarations are descriptive; no compatibility or readiness is established.",
            "Original compilers only; no acquisition, statistics, registry update "
            "or holdout access.",
            "Compiled identities are not independent seals, source evidence "
            "or execution permission.",
        ],
    }
    if len(_json(result).encode("utf-8")) + 1 > MAX_OUTPUT_BYTES:
        raise PlanError("BATCH_TOO_LARGE")
    return result


def _cell(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    for char in ("\\", "`", "*", "_", "[", "]", "|"):
        text = text.replace(char, "\\" + char)
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("\r", " ").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Hypothesis plan inventory (compile only)", "",
        f"Counts: {_cell(report['counts'])}", "",
        "## Original plan identities", "",
        "| Hypothesis | Source SHA256 | Contract digest | Plan digest |",
        "| --- | --- | --- | --- |",
    ]
    for hypothesis_id, source in report["sources"].items():
        values = (
            hypothesis_id, source["source_file_sha256"],
            source["contract"]["contract_digest"], source["plan"]["plan_digest"],
        )
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.extend([
        "", "## Declared series inventory", "",
        "| Series | Hypotheses | Shared declaration | Declarations differ (excluding role) |",
        "| --- | --- | --- | --- |",
    ])
    for group in report["series_groups"]:
        values = (
            group["series_id"], group["hypothesis_ids"], group["shared_declared_series"],
            group["role_independent_declarations_differ"],
        )
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    for hypothesis_id, source in report["sources"].items():
        plan = source["plan"]
        lines.extend([
            "", f"## Original requirements for {_cell(hypothesis_id)}", "",
            "| Index | Role | Series | Transform | Timing | Primary | Validity |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for index, requirement in enumerate(plan["dataset_requirements"]["requirements"]):
            values = [index, *(requirement[key] for key in (
                "role", "series_id", "transform_semantics", "observation_timing",
                "required_for_primary", "validity_requirement",
            ))]
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
        context = {
            "sample_plan": plan["sample_plan"],
            "universe_requirement": plan["dataset_requirements"]["universe_requirement"],
            "analysis_method_id": plan["analysis_method_id"],
            "holdout_boundary": plan["holdout_boundary"],
        }
        lines.extend(["", "```json", _json(context), "```"])
    lines.extend(["", "## Boundary", "", "```json", _json(report["boundary"]), "```", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="Compile multiple hypotheses and inventory declared inputs", allow_abbrev=False,
    )
    parser.add_argument("--hypothesis", required=True, action="append", metavar="JSON")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if any(not path for path in args.hypothesis):
            raise PlanError("INVALID_ARGUMENTS")
        report = build_inventory([Path(path) for path in args.hypothesis])
        text = _json(report) + "\n" if args.json else render_markdown(report)
        payload = text.encode("utf-8")
        if len(payload) > MAX_OUTPUT_BYTES:
            raise PlanError("BATCH_TOO_LARGE")
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "BATCH_COMPILATION_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
