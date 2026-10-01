"""Acceptance coverage for the offline M4 synthetic demonstration CLI.

The module under test is ``python -m ashare_research.synthetic_demo``: a fixed, invented
24-row synthetic example driven through the frozen composed entry, with a readable text
summary by default and ``--json`` writing the existing canonical serialized bytes verbatim.

Every test is synthetic-only and offline.  The CLI is exercised through genuine child
processes with an explicit ``PYTHONPATH``, so byte determinism, exit codes and stream
separation are observed rather than assumed.  Nothing here reads real data, a provider, the
database, holdout, literature or M4-B state; nothing writes into the repository; no test
asserts a research, significance, economic-validity, tradability or A-share mechanism
conclusion.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ashare_research.mechanism.execution import INTERPRETATION_BOUNDARY
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.pipeline import (
    PIPELINE_SCHEMA_VERSION,
    PIPELINE_STATE,
    REGISTRY_BINDING_ABSENT,
    REQUIRED_STAGES_COMPLETED,
    SYNTHETIC_PIPELINE_MODE,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODULE_PATH = SRC / "ashare_research" / "synthetic_demo.py"
MODULE_SOURCE = MODULE_PATH.read_text(encoding="utf-8")
MODULE_NAME = "ashare_research.synthetic_demo"
ROW_COUNT = 24
ROLE_COUNT = 4
OBSERVATION_COUNT = ROW_COUNT * ROLE_COUNT
DIGEST_RE = re.compile(r"^pipeline_digest=([0-9a-f]{64})$", re.MULTILINE)

# The demonstration must stay dependency-free and side-effect-free: only the standard library
# names below plus the frozen project packages may appear at module level.
ALLOWED_STDLIB_IMPORTS = frozenset(
    {"__future__", "argparse", "collections", "dataclasses", "decimal", "re", "sys"}
)
PROJECT_ROOT_PACKAGE = "ashare_research"
BANNED_CALL_NAMES = frozenset({"open", "exec", "eval", "compile", "__import__"})
BANNED_ATTRIBUTES = frozenset({"system", "popen", "getenv", "environ", "putenv"})

# Child processes must import *this* worktree's package, not any ambient installation.
_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)

_VALIDATOR_SCRIPT = """
import sys

from ashare_research import synthetic_demo
from ashare_research.mechanism.pipeline import serialize_pipeline_result, validate_pipeline_result

request = synthetic_demo.build_demo_request()
result = synthetic_demo.run_demo()
validate_pipeline_result(result, request)
sys.stdout.buffer.write(serialize_pipeline_result(result))
"""

_FAILURE_SCRIPT = """
import io
import sys

from ashare_research import synthetic_demo
from ashare_research.mechanism.pipeline import PipelineError


class _Captured:
    def __init__(self):
        self.buffer = io.BytesIO()

    def write(self, text):
        self.buffer.write(text.encode("utf-8"))

    def flush(self):
        pass


def _coded(*args, **kwargs):
    raise PipelineError("PIPELINE_DIGEST_MISMATCH", "LEAK path=C:/secret value=0.5")


def _uncoded(*args, **kwargs):
    raise ValueError("LEAK plain value=0.25")


def _unsafe_code(*args, **kwargs):
    raise PipelineError("lower case path=C:/secret", "LEAK")


def _run(raiser):
    synthetic_demo.run_synthetic_pipeline = raiser
    captured = _Captured()
    real = sys.stdout
    sys.stdout = captured
    try:
        code = synthetic_demo.main(["--json"])
    finally:
        sys.stdout = real
    return code, captured.buffer.getvalue().decode("utf-8")


print("results=" + repr([_run(raiser) for raiser in (_coded, _uncoded, _unsafe_code)]))
"""

_NO_IO_SCRIPT = """
import builtins
import hashlib
import io
import os
import socket
import sys

from ashare_research import synthetic_demo


def _blocked(*args, **kwargs):
    raise AssertionError("blocked external access")


builtins.open = _blocked
os.getenv = _blocked
socket.socket = _blocked
socket.create_connection = _blocked


class _Captured:
    def __init__(self):
        self.buffer = io.BytesIO()

    def write(self, text):
        self.buffer.write(text.encode("utf-8"))

    def flush(self):
        pass


def _call(arguments):
    captured = _Captured()
    real = sys.stdout
    sys.stdout = captured
    try:
        code = synthetic_demo.main(arguments)
    finally:
        sys.stdout = real
    return code, captured.buffer.getvalue()


result = synthetic_demo.run_demo()
json_code, json_bytes = _call(["--json"])
text_code, text_bytes = _call([])
print(
    "no-io code=%d,%d json_sha256=%s text_bytes=%d"
    % (json_code, text_code, hashlib.sha256(json_bytes).hexdigest(), len(text_bytes))
)
"""


def _run_module(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *arguments],
        cwd=ROOT if cwd is None else cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _run_script(source: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _decode(completed: subprocess.CompletedProcess) -> str:
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout.decode("utf-8")


def _payload(completed: subprocess.CompletedProcess) -> dict:
    return json.loads(_decode(completed))


@pytest.fixture(scope="module")
def json_run() -> subprocess.CompletedProcess:
    return _run_module("--json")


# ==============================================================================================
# 1. Genuine subprocess execution: text, JSON, digest and determinism
# ==============================================================================================


def test_text_summary_reports_stages_rows_digest_and_verbatim_boundary():
    completed = _run_module()
    assert completed.returncode == 0
    assert completed.stderr == b""
    assert b"\r" not in completed.stdout

    text = _decode(completed)
    lines = text.splitlines()
    assert lines[0] == (
        f"M4 synthetic demonstration: invented {ROW_COUNT}-row daily example, "
        "synthetic-only, no real data"
    )
    assert "hypothesis_id=DEMO_INVENTED_DAILY_001" in lines
    assert f"mode={SYNTHETIC_PIPELINE_MODE}" in lines[2]
    assert f"rows={ROW_COUNT} observations={OBSERVATION_COUNT}" in lines[2]
    assert f"pipeline_state={PIPELINE_STATE}" in lines
    assert f"stages_completed={','.join(REQUIRED_STAGES_COMPLETED)}" in lines
    assert DIGEST_RE.search(text) is not None
    assert not text.startswith("{")

    # The executor's interpretation boundary is reproduced verbatim on its own line.
    assert lines[-2] == "interpretation_boundary:"
    assert lines[-1] == INTERPRETATION_BOUNDARY
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_json_output_is_the_existing_canonical_bytes_with_one_final_newline(json_run):
    assert json_run.returncode == 0
    assert json_run.stderr == b""
    encoded = json_run.stdout
    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert b"\r" not in encoded

    payload = json.loads(encoded.decode("utf-8"))
    # Exactly the frozen canonical projection and nothing else.
    assert sorted(payload) == ["contract", "execution", "matrix", "metadata", "plan", "preparation"]
    assert encoded == (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    # The envelope digest is recomputed from the emitted bytes with the public digest helper.
    body = {
        "metadata": {k: v for k, v in payload["metadata"].items() if k != "pipeline_digest"},
        "contract": payload["contract"],
        "plan": payload["plan"],
        "preparation": payload["preparation"],
        "matrix": payload["matrix"],
        "execution": payload["execution"],
    }
    assert canonical_digest(body) == payload["metadata"]["pipeline_digest"]
    assert re.fullmatch(r"[0-9a-f]{64}", payload["metadata"]["pipeline_digest"])

    metadata = payload["metadata"]
    assert metadata["pipeline_schema_version"] == PIPELINE_SCHEMA_VERSION
    assert metadata["pipeline_state"] == PIPELINE_STATE
    assert metadata["stages_completed"] == list(REQUIRED_STAGES_COMPLETED)
    assert metadata["interpretation_boundary"] == INTERPRETATION_BOUNDARY
    assert metadata["registry_binding"] is None
    assert metadata["registry_binding_digest"] == canonical_digest(
        {"binding_state": REGISTRY_BINDING_ABSENT}
    )


def test_json_bytes_are_deterministic_across_processes_and_working_directories(
    json_run, tmp_path
):
    assert json_run.returncode == 0
    first = json_run.stdout
    assert first

    repeat = _run_module("--json")
    assert repeat.returncode == 0 and repeat.stderr == b""
    assert repeat.stdout == first

    # A working directory outside the repository changes nothing.
    assert not tmp_path.is_relative_to(ROOT)
    elsewhere = _run_module("--json", cwd=tmp_path)
    assert elsewhere.returncode == 0 and elsewhere.stderr == b""
    assert elsewhere.stdout == first


def test_authoritative_validator_accepts_the_same_public_entry_and_bytes(json_run):
    assert json_run.returncode == 0
    child = _run_script(_VALIDATOR_SCRIPT)
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    assert child.stderr == b""
    # The CLI emits exactly the bytes produced by the public entry after the frozen
    # ``validate_pipeline_result(result, request)`` revalidation.
    assert child.stdout == json_run.stdout


# ==============================================================================================
# 2. Provenance, bounded demonstration configuration and no-IO probes
# ==============================================================================================


def test_demonstration_is_synthetic_only_with_disabled_bootstrap_and_no_registry_binding(json_run):
    payload = _payload(json_run)
    execution = payload["execution"]

    provenance = execution["provenance"]
    assert provenance["provenance_class"] == "SYNTHETIC_TEST_ONLY"
    assert provenance["synthetic_test_only"] is True
    assert provenance["dataset_mode"] == SYNTHETIC_PIPELINE_MODE
    assert provenance["real_data_used"] is False
    assert provenance["holdout_accessed"] is False

    assert execution["execution_authorized"] is False
    assert execution["statistics_computed"] is True
    assert execution["outcome_read"] is True
    assert payload["preparation"]["execution_authorized"] is False
    assert payload["matrix"]["execution_authorized"] is False

    # The fixed demonstration disables bootstrap and registers no robustness entry.
    assert payload["plan"]["bootstrap_plan"]["enabled"] is False
    assert payload["plan"]["bootstrap_plan"]["method_id"] == "DISABLED"
    assert execution["method_configuration"]["bootstrap_enabled"] is False
    assert execution["method_configuration"]["bootstrap_method_id"] == "DISABLED"
    assert execution["bootstrap"]["enabled"] is False
    assert execution["bootstrap"]["primary_effect_lower"] is None
    assert execution["bootstrap"]["primary_effect_upper"] is None
    assert payload["plan"]["robustness_plan"]["entries"] == []
    assert payload["contract"]["robustness_registry"] == []
    assert payload["plan"]["holdout_boundary"]["execution_authorized"] is False
    assert payload["plan"]["holdout_boundary"]["policy_id"] == "NO_HOLDOUT_AUTHORIZED"
    assert payload["contract"]["holdout_policy"] == "NO_HOLDOUT_AUTHORIZED_BY_THIS_CONTRACT"

    # One invented 24-row daily example: 24 complete rows and 24 x 4 observations.
    assert execution["sample"]["row_count"] == ROW_COUNT
    assert len(payload["preparation"]["complete_rows"]) == ROW_COUNT
    assert len(payload["matrix"]["rows"]) == ROW_COUNT
    assert len(payload["preparation"]["audit_rows"]) == ROW_COUNT
    assert all(len(row["cells"]) == ROLE_COUNT for row in payload["preparation"]["audit_rows"])
    assert execution["method_configuration"]["numeric_backend"] == "numpy.linalg.lstsq"


def test_module_import_surface_is_public_and_free_of_io_helpers():
    tree = ast.parse(MODULE_SOURCE)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules.add(node.module)
            for alias in node.names:
                assert not alias.name.startswith("_"), (node.module, alias.name)
                assert node.module != "__future__" or alias.name == "annotations"

    roots = {module.split(".")[0] for module in modules}
    assert roots <= ALLOWED_STDLIB_IMPORTS | {PROJECT_ROOT_PACKAGE}
    for module in modules:
        parts = module.split(".")
        assert "tests" not in parts and not any(part.startswith("test_") for part in parts)
        if parts[0] == PROJECT_ROOT_PACKAGE:
            assert module.startswith(f"{PROJECT_ROOT_PACKAGE}.mechanism.")

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in BANNED_CALL_NAMES, node.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in BANNED_ATTRIBUTES, node.attr


def test_runtime_probe_blocks_file_environment_and_network_access(json_run):
    assert json_run.returncode == 0
    child = _run_script(_NO_IO_SCRIPT)
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    assert child.stderr == b""

    text = child.stdout.decode("utf-8")
    assert text.startswith("no-io code=0,0 json_sha256=")
    # The blocked-IO process still produced the identical canonical bytes for both modes.
    assert hashlib.sha256(json_run.stdout).hexdigest() in text
    text_bytes = int(text.rsplit("text_bytes=", 1)[1])
    assert text_bytes > 0


# ==============================================================================================
# 3. Command surface: only help and --json, usage errors before execution, sanitized failures
# ==============================================================================================


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(("--seed", "7"), id="seed"),
        pytest.param(("--config", "config.yaml"), id="config"),
        pytest.param(("--output", "out.json"), id="output"),
        pytest.param(("--provider", "baostock"), id="provider"),
        pytest.param(("extra",), id="positional"),
    ],
)
def test_unsupported_arguments_fail_with_exit_code_two_and_no_result(arguments):
    completed = _run_module(*arguments)
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert b"usage:" in completed.stderr
    assert b"Traceback" not in completed.stderr


def test_help_exposes_only_json_and_help():
    completed = _run_module("--help")
    assert completed.returncode == 0
    assert completed.stderr == b""
    text = completed.stdout.decode("utf-8")
    assert "usage: python -m ashare_research.synthetic_demo [-h] [--json]" in text
    assert "--json" in text
    for absent in ("--seed", "--config", "--output", "--provider", "--db", "--input"):
        assert absent not in text


def test_known_validation_failures_are_sanitized_without_a_result():
    child = _run_script(_FAILURE_SCRIPT)
    assert child.returncode == 0, child.stderr.decode("utf-8", "replace")
    # No result was ever printed for any failure, and the exit code is the validation failure.
    assert child.stdout.decode("utf-8").strip() == "results=[(1, ''), (1, ''), (1, '')]"
    # Only the sanitized code is reported: no message text, no path, no value, no traceback.
    assert child.stderr.decode("utf-8") == (
        "SYNTHETIC_DEMO_FAILURE code=PIPELINE_DIGEST_MISMATCH\n"
        "SYNTHETIC_DEMO_FAILURE code=DEMO_VALIDATION_FAILED\n"
        "SYNTHETIC_DEMO_FAILURE code=DEMO_VALIDATION_FAILED\n"
    )
    assert b"LEAK" not in child.stderr
    assert b"C:/secret" not in child.stderr
    assert b"Traceback" not in child.stderr


def test_serialization_validation_failure_emits_no_partial_result(monkeypatch, capsys):
    from ashare_research import synthetic_demo
    from ashare_research.mechanism.pipeline import PipelineError

    def reject_serialization(result):
        raise PipelineError("PIPELINE_DIGEST_MISMATCH", "LEAK C:/secret")

    monkeypatch.setattr(synthetic_demo, "serialize_pipeline_result", reject_serialization)
    assert synthetic_demo.main(["--json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "SYNTHETIC_DEMO_FAILURE code=PIPELINE_DIGEST_MISMATCH\n"


@pytest.mark.parametrize("arguments", [["--input", "data.csv"], ["--j"], ["--help"]])
def test_parser_finishes_before_any_computation(arguments, monkeypatch, capsys):
    from ashare_research import synthetic_demo

    def forbid_execution():
        pytest.fail("parser attempted computation")

    monkeypatch.setattr(synthetic_demo, "run_demo", forbid_execution)
    with pytest.raises(SystemExit) as raised:
        synthetic_demo.main(arguments)
    assert raised.value.code == (0 if arguments == ["--help"] else 2)
    captured = capsys.readouterr()
    if raised.value.code == 2:
        assert captured.out == ""
