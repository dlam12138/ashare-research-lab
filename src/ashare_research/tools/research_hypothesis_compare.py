"""Compare explicit hypotheses using the original compile-only plan envelopes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.tools.research_plan import PlanError, build_report

SCHEMA = "m4_compile_only_hypothesis_comparison_v1"
_DIGEST_KEYS = {
    "config": (),
    "contract": ("contract_digest", "source_config_digest"),
    "plan": ("plan_digest", "source_contract_digest"),
}


def _changes(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    if type(left) is dict and type(right) is dict:
        changes = []
        for key in sorted(left.keys() | right.keys()):
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in left or key not in right:
                entry = {
                    "path": pointer, "kind": "added" if key not in left else "removed",
                    "left_present": key in left, "right_present": key in right,
                }
                if key in left:
                    entry["left"] = left[key]
                if key in right:
                    entry["right"] = right[key]
                changes.append(entry)
            else:
                changes.extend(_changes(left[key], right[key], pointer))
        return changes
    # Lists are atomic ordered values: insertions cannot masquerade as moved fields.
    if type(left) is not type(right) or _json(left) != _json(right):
        return [{
            "path": path, "kind": "changed", "left_present": True, "right_present": True,
            "left": left, "right": right,
        }]
    return []


def build_comparison(left: Path, right: Path) -> dict[str, Any]:
    sources = {"left": build_report(left), "right": build_report(right)}
    changes = []
    identities = {}
    for section, excluded in _DIGEST_KEYS.items():
        original_left = sources["left"][section]
        original_right = sources["right"][section]
        identities[section] = _json(original_left) == _json(original_right)
        lhs = {key: value for key, value in original_left.items() if key not in excluded}
        rhs = {key: value for key, value in original_right.items() if key not in excluded}
        changes.extend({"section": section, **change} for change in _changes(lhs, rhs))
    return {
        "schema": SCHEMA,
        "status": "compiled_pre_execution",
        "source_bytes_equal": (
            sources["left"]["source_file_sha256"] == sources["right"]["source_file_sha256"]
        ),
        "canonical_equal": identities,
        "changes": changes,
        "excluded_derived_digest_fields": {key: list(value) for key, value in _DIGEST_KEYS.items()},
        "sources": sources,
        "boundary": dict(sources["left"]["boundary"]),
        "notes": [
            "Only canonical compiled content is compared; source byte identity is separate.",
            "Ordered lists are compared as complete values; paths use JSON pointer escaping.",
            "Derived digest fields are retained in sources, excluded from change rows.",
            "Changes do not imply improved evidence, readiness, or execution authorization.",
        ],
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    for char in ("\\", "`", "*", "_", "[", "]", "|"):
        text = text.replace(char, "\\" + char)
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ").replace("\r", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Hypothesis comparison (compile only)", "",
        f"Source bytes equal: {report['source_bytes_equal']}", "",
        f"Canonical equality: {_cell(report['canonical_equal'])}", "",
        "| Side | Source SHA256 | Contract digest | Plan digest |",
        "| --- | --- | --- | --- |",
    ]
    for side, source in report["sources"].items():
        values = (
            side, source["source_file_sha256"], source["contract"]["contract_digest"],
            source["plan"]["plan_digest"],
        )
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.extend([
        "", f"## Canonical changes ({len(report['changes'])})", "",
        "| Section | JSON pointer | Kind | Left | Right |",
        "| --- | --- | --- | --- | --- |",
    ])
    for change in report["changes"]:
        values = (change["section"], change["path"], change["kind"])
        cells = [_cell(value) for value in values]
        cells.extend(
            _cell(change[side]) if change[f"{side}_present"] else "(absent)"
            for side in ("left", "right")
        )
        lines.append("| " + " | ".join(cells) + " |")
    if not report["changes"]:
        lines.extend(["", "No canonical content changes."])
    lines.extend(["", "## Boundary", "", "```json", _json(report["boundary"]), "```", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="Compare two hypotheses without execution", allow_abbrev=False)
    parser.add_argument("--left", required=True, metavar="JSON")
    parser.add_argument("--right", required=True, metavar="JSON")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = build_comparison(Path(args.left), Path(args.right))
        text = _json(report) + "\n" if args.json else render_markdown(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - stable error, no partial result
        code = error.code if isinstance(error, (
            PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "HYPOTHESIS_COMPARISON_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
