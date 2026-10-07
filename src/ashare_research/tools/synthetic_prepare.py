"""Prepare explicit invented synthetic inputs without statistical execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import (
    ContractCompilationError,
    compile_hypothesis_config,
    contract_to_canonical_dict,
)
from ashare_research.mechanism.datasets import (
    AdapterError,
    BoundDatasetInputsV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    validate_dataset,
)
from ashare_research.mechanism.hypothesis_config import (
    HypothesisConfigError,
    parse_hypothesis_config,
)
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict
from ashare_research.mechanism.planning.matrix import (
    MatrixError,
    materialize_design_matrix,
    serialize_matrix,
)
from ashare_research.tools import research_plan_archive, research_plan_package
from ashare_research.tools.research_plan import PlanError

SCHEMA = "m4_explicit_synthetic_preparation_view_v1"
MAX_INPUT_BYTES = 1_048_576
NOTES = (
    "仅检查调用者显式提供的虚构合成观测；SYNTHETIC 标签和行摘要不证明真实来源。",
    "仅读取显式提供的合成观测；未访问真实结果或 holdout，未执行回归、秩检查或 bootstrap。",
    "沿用原数据与矩阵适配器；不填补缺失、修补摘要、转换单位或裁剪窗口外观测。",
    "质量拒绝保留完整诊断且不生成矩阵；退出码 0 仅表示诊断报告成功生成。",
    "READY_SYNTHETIC 仅表示合成输入准备通过，不表示可估计、研究就绪或执行授权。",
)


class PrepareError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PrepareError("DUPLICATE_INPUT_JSON_KEY")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise PrepareError("NONFINITE_INPUT_JSON_NUMBER")


def _read_inputs(path: Path) -> tuple[dict[str, Any], str]:
    try:
        absolute = path.absolute()
        for candidate in (absolute, *absolute.parents):
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise PrepareError("LINKED_INPUT_PATH")
        if not stat.S_ISREG(absolute.lstat().st_mode):
            raise PrepareError("INVALID_INPUT_FILE")
        with path.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as error:
        raise PrepareError("INPUT_READ_FAILED") from error
    if len(payload) > MAX_INPUT_BYTES:
        raise PrepareError("INPUT_TOO_LARGE")
    try:
        document = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise PrepareError("INVALID_INPUT_JSON") from error
    if type(document) is not dict:
        raise PrepareError("INVALID_INPUT_ROOT")
    return document, hashlib.sha256(payload).hexdigest()


def build_report(package: Path, inputs: Path, *, archive: bool = False) -> dict[str, Any]:
    verified = (research_plan_archive.verify_archive(package)["verification"]["report"]
                if archive else research_plan_package.verify_package(package)["report"])
    parser_config = dict(verified["config"])
    # Canonical reports explicitly include an absent optional holdout as null;
    # the original input parser expresses absence by omitting this key.
    if parser_config.get("holdout_policy") is None:
        parser_config.pop("holdout_policy", None)
    contract = compile_hypothesis_config(parse_hypothesis_config(parser_config))
    plan = build_analysis_plan(contract)
    if (_json(contract_to_canonical_dict(contract)) != _json(verified["contract"])
            or _json(plan_to_canonical_dict(plan)) != _json(verified["plan"])):
        raise PrepareError("VERIFIED_PLAN_REBUILD_MISMATCH")
    document, source_hash = _read_inputs(inputs)
    bound = BoundDatasetInputsV1.from_dict(document)
    prepared = materialize_analysis_dataset(contract, plan, bound)
    validate_dataset(prepared, contract, plan, bound)
    matrix = None
    if prepared.status == "READY_SYNTHETIC":
        matrix = json.loads(serialize_matrix(
            materialize_design_matrix(prepared, contract, plan, bound)
        ))
    return {
        "schema": SCHEMA,
        "status": "verified_synthetic_preparation",
        "plan_identity": {
            "hypothesis_id": contract.hypothesis_id,
            "source_file_sha256": verified["source_file_sha256"],
            "contract_digest": contract.contract_digest,
            "plan_digest": plan.plan_digest,
        },
        "input_file_sha256": source_hash,
        "dataset": dataset_to_canonical_dict(prepared),
        "matrix": matrix,
        "boundary": {
            "synthetic_observations_read": bool(bound.observations),
            "outcome_read": any(row.role == "TARGET_OUTCOME" for row in bound.observations),
            "execution_authorized": False, "statistics_computed": False,
            "holdout_accessed": False, "source_evidence_validated": False,
            "research_ready": False,
        },
        "notes": list(NOTES),
    }


def render_markdown(report: dict[str, Any]) -> str:
    dataset, matrix = report["dataset"], report["matrix"]
    quality = dataset["quality"]
    dimensions = f"{len(matrix['rows'])} 行 × {len(matrix['columns'])} 列" if matrix else "未生成"
    lines = ["# 合成输入准备检查", "", f"准备状态：`{dataset['status']}`。",
             f"共同有效覆盖：{quality['coverage_numerator']}/{quality['coverage_denominator']}；"
             f"门槛：{quality['coverage_gate']}。", f"设计矩阵：{dimensions}。", "",
             "仅读取显式提供的虚构合成观测；未执行统计研究。", "", "## 输入身份", "",
             "```json", _json({"plan_identity": report["plan_identity"],
                              "input_file_sha256": report["input_file_sha256"]}), "```", "",
             "## 完整数据准备与质量诊断", "", "```json", _json(dataset), "```", "",
             "## 完整设计矩阵", "", "```json", _json(matrix), "```", "",
             "## 执行边界", "", "```json", _json(report["boundary"]), "```", "",
             "## 限制", "", *(f"- {note}" for note in report["notes"]), ""]
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PrepareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="显式合成输入的数据与矩阵准备检查", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", metavar="DIR")
    source.add_argument("--archive", metavar="ZIP")
    parser.add_argument("--inputs", required=True, metavar="JSON")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--role", action="append", default=[], metavar="ID")
    parser.add_argument("--gaps-only", action="store_true")
    try:
        args = parser.parse_args(argv)
        from ashare_research.tools import preparation_diagnostics

        preparation_diagnostics.validate_options(args.summary, args.role, args.gaps_only)
        report = build_report(
            Path(args.package if args.package is not None else args.archive),
            Path(args.inputs), archive=args.archive is not None,
        )
        renderer = render_markdown
        if args.summary:
            report = preparation_diagnostics.build_summary(
                report, roles=args.role, gaps_only=args.gaps_only,
            )
            renderer = preparation_diagnostics.render_markdown
        text = _json(report) + "\n" if args.json else renderer(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized fail-closed command boundary
        code = (error.code if isinstance(error, (
            PrepareError, PlanError, AdapterError, MatrixError,
            HypothesisConfigError, ContractCompilationError,
        )) else "SYNTHETIC_PREPARATION_FAILED")
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
