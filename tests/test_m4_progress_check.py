"""Focused tests for the offline M4 progress check: deterministic, read-only, fail closed.

Mutation cases use pytest-owned fixture copies outside the repository; repository
evidence is only ever read.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "agent" / "tools"
TOOL = TOOLS / "check_m4_progress.py"
AUTHORIZATION = "evidence/m4/eia_direct_authorization_01.json"
GOAL = "agent/goals/2026-09-25_m4_eia_encrypted_probe.md"
LEDGER = "evidence/m4/eia_direct_run_01.json"

sys.path.insert(0, str(TOOLS))

import check_m4_progress as progress  # noqa: E402

SOURCE_FILES = (
    progress.DOSSIER,
    progress.REPORT,
    AUTHORIZATION,
    GOAL,
    LEDGER,
)


@pytest.fixture
def workdir(tmp_path):
    return tmp_path

def owned_root(workdir):
    root = workdir / "owned_repository"
    for relative in SOURCE_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    return root


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(root, relative, document):
    (root / relative).write_bytes(progress.canonical(document) + b"\n")


def resign(document, field):
    document[field] = progress.sha(
        progress.canonical({k: v for k, v in document.items() if k != field})
    )
    return document


def repin_dossier_to_authorization(root):
    dossier = read_json(root / progress.DOSSIER)
    dossier["authorization_file_sha256"] = hashlib.sha256(
        (root / AUTHORIZATION).read_bytes()
    ).hexdigest()
    write_json(root, progress.DOSSIER, resign(dossier, "dossier_digest"))


def run_cli(cwd, *arguments):
    return subprocess.run(
        [sys.executable, str(TOOL), *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def expect_failure(capsys, root, code):
    assert progress.main([], root=root) == 2
    captured = capsys.readouterr()
    assert captured.out == f"EVIDENCE_VALIDATION_FAILED: {code}\nexit_code: 2\n"
    assert "DIAGNOSTIC_COMPLETE" not in captured.out
    assert "reason_codes" not in captured.out
    assert progress.main(["--json"], root=root) == 2
    assert json.loads(capsys.readouterr().out) == {
        "schema_id": progress.SCHEMA_ID,
        "result": "EVIDENCE_VALIDATION_FAILED",
        "error_code": code,
        "exit_code": 2,
    }


def test_owned_fixture_copy_reproduces_repository_report(workdir, capsys):
    root = owned_root(workdir)
    assert progress.main([], root=root) == 0
    assert capsys.readouterr().out == progress.render_text(
        progress.build_progress_report(progress.REPOSITORY_ROOT)
    )


def test_real_cli_is_deterministic_from_unrelated_cwd(workdir):
    first_dir = workdir / "cwd-a"
    second_dir = workdir / "cwd-b"
    first_dir.mkdir()
    second_dir.mkdir()
    first = run_cli(first_dir, "--json")
    second = run_cli(second_dir, "--json")
    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout == second.stdout
    assert first.stdout == progress.canonical(progress.build_progress_report(ROOT)).decode() + "\n"
    text_a = run_cli(first_dir)
    text_b = run_cli(second_dir)
    assert text_a.returncode == 0 and text_b.returncode == 0
    assert text_a.stdout == text_b.stdout
    assert text_a.stdout == progress.render_text(progress.build_progress_report(ROOT))
    assert str(ROOT) not in text_a.stdout and str(ROOT) not in first.stdout


def test_report_exposes_explicit_false_authorization(workdir):
    text = run_cli(workdir).stdout
    payload = json.loads(run_cli(workdir, "--json").stdout)
    assert payload["assessment_scope"] == "FROZEN_EIA_TRANSPORT_DOSSIER_ONLY"
    assert payload["evidence_checks_passed"] is True
    assert payload["evidence_checks"]["passed"] is True
    assert payload["evidence_checks"]["retained_assessment_reproduced"] is True
    assert payload["research_blocked"] is True
    assert payload["research_ready"] is False
    assert payload["execution_authorized"] is False
    assert payload["research_state"] == "PIT_EVIDENCE_MISSING"
    assert payload["result"] == "DIAGNOSTIC_COMPLETE_RESEARCH_BLOCKED"
    for line in ("research_ready: false", "execution_authorized: false", "research_blocked: true"):
        assert line in text
    assert "a complete k2" in payload["scope_note"].lower()
    assert payload["limits"]["not_a_complete_k2_or_whole_project_readiness_assessment"] is True
    assert payload["limits"]["eia_frozen_dossier_metadata_only"] is True


def test_all_missing_reason_codes_and_supplements_are_reported(workdir):
    payload = json.loads(run_cli(workdir, "--json").stdout)
    assert payload["reason_codes"] == [
        "REAL_AVAILABLE_AT_MISSING",
        "REAL_PUBLISHED_AT_MISSING",
        "REAL_SOURCE_VERSION_MISSING",
    ]
    assert payload["missing_fields_in_verified_response_schema"] == [
        "available_at",
        "published_at",
        "revision_id",
        "vintage_id",
    ]
    assert sorted(payload["required_supplement"]) == ["availability", "publication", "version"]
    assert payload["next_task"] == progress.NEXT_TASK
    assert "first-party" in payload["next_task"]
    assert "before any new acquisition" in payload["next_task"]
    assert payload["limits"]["provider_has_no_archive_asserted"] is False
    assert payload["limits"]["monthly_to_daily_conversion_performed"] is False
    assert payload["limits"]["observations_read"] is False
    assert payload["limits"]["additional_api_requests"] == 0
    text = run_cli(workdir).stdout
    for code in payload["reason_codes"]:
        assert code in text


def test_output_contains_no_raw_proof_credentials_or_locators(workdir):
    dossier = read_json(ROOT / progress.DOSSIER)
    authorization = read_json(ROOT / AUTHORIZATION)
    combined = run_cli(workdir).stdout + run_cli(workdir, "--json").stdout
    for secret in (
        dossier["transport_proof"]["ciphertext_sha256"],
        dossier["transport_proof"]["raw_sha256"],
        dossier["transport_proof"]["encrypted_locator"],
        dossier["metadata_raw_sha256"][0],
        dossier["licence_evidence"]["encrypted_locator"],
        authorization["credential_source"],
        authorization["raw_namespace"],
    ):
        assert secret
        assert secret not in combined


def test_missing_dossier_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    (root / progress.DOSSIER).unlink()
    expect_failure(capsys, root, "EVIDENCE_FILE_MISSING")


def test_missing_linked_authorization_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    (root / AUTHORIZATION).unlink()
    expect_failure(capsys, root, "EVIDENCE_FILE_MISSING")


def test_missing_retained_assessment_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    (root / progress.REPORT).unlink()
    expect_failure(capsys, root, "EVIDENCE_FILE_MISSING")


def test_corrupt_dossier_digest_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.DOSSIER)
    document["retrieved_at"] = "2000-01-01T00:00:00.000Z"
    write_json(root, progress.DOSSIER, document)
    expect_failure(capsys, root, "DIGEST_MISMATCH")


def test_duplicate_key_metadata_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    path = root / progress.DOSSIER
    raw = path.read_bytes()
    mutated = raw.replace(b'"dossier_digest"', b'"dossier_id":"x","dossier_digest"', 1)
    assert mutated != raw
    path.write_bytes(mutated)
    expect_failure(capsys, root, "DUPLICATE_KEY")


def test_rehashed_fake_research_permission_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.DOSSIER)
    document["research_use_permitted"] = True
    write_json(root, progress.DOSSIER, resign(document, "dossier_digest"))
    expect_failure(capsys, root, "UNSUPPORTED_ADMISSION_CLAIM")


def test_rehashed_fake_pit_state_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.DOSSIER)
    document["state"] = "PIT_VERIFIED_VALUES_ALLOWED"
    write_json(root, progress.DOSSIER, resign(document, "dossier_digest"))
    expect_failure(capsys, root, "UNSUPPORTED_ADMISSION_CLAIM")


def test_rehashed_fake_pit_semantics_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.DOSSIER)
    document["pit_semantics"] = "PROVEN"
    write_json(root, progress.DOSSIER, resign(document, "dossier_digest"))
    expect_failure(capsys, root, "FROZEN_IDENTITY_MISMATCH")


def test_rehashed_fake_ready_retained_report_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.REPORT)
    document["research_ready"] = True
    write_json(root, progress.REPORT, document)
    expect_failure(capsys, root, "ASSESSMENT_NOT_REPRODUCIBLE")


def test_retained_report_byte_mismatch_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    path = root / progress.REPORT
    path.write_bytes(path.read_bytes() + b" ")
    expect_failure(capsys, root, "ASSESSMENT_NOT_REPRODUCIBLE")


def test_linked_path_escape_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    shutil.copyfile(ROOT / AUTHORIZATION, workdir / "outside.json")
    document = read_json(root / progress.DOSSIER)
    document["authorization_path"] = "../outside.json"
    write_json(root, progress.DOSSIER, resign(document, "dossier_digest"))
    expect_failure(capsys, root, "LINK_NOT_ALLOWLISTED")


def test_linked_digest_mismatch_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    path = root / AUTHORIZATION
    path.write_bytes(path.read_bytes() + b"\n")
    expect_failure(capsys, root, "LINK_DIGEST_MISMATCH")


def test_rehashed_authorization_admission_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    authorization = read_json(root / AUTHORIZATION)
    authorization["values_may_enter_research"] = True
    write_json(root, AUTHORIZATION, authorization)
    repin_dossier_to_authorization(root)
    expect_failure(capsys, root, "UNSUPPORTED_ADMISSION_CLAIM")


def test_rehashed_authorization_schema_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    authorization = read_json(root / AUTHORIZATION)
    authorization["schema_id"] = "M4_UNKNOWN_AUTHORIZATION"
    write_json(root, AUTHORIZATION, authorization)
    repin_dossier_to_authorization(root)
    expect_failure(capsys, root, "UNSUPPORTED_SCHEMA")


def test_rehashed_predecessor_identity_mismatch_fails_closed(workdir, capsys):
    root = owned_root(workdir)
    document = read_json(root / progress.DOSSIER)
    document["predecessor_dossier_ids"] = ["other_transport"]
    write_json(root, progress.DOSSIER, resign(document, "dossier_digest"))
    expect_failure(capsys, root, "FROZEN_IDENTITY_MISMATCH")


def test_repository_evidence_is_not_mutated_and_report_is_reproducible():
    watched = {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in SOURCE_FILES
    }
    listing = sorted(path.name for path in (ROOT / "evidence" / "m4").iterdir())
    assert progress.build_progress_report(ROOT) == progress.build_progress_report(
        progress.REPOSITORY_ROOT
    )
    assert {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in SOURCE_FILES
    } == watched
    assert sorted(path.name for path in (ROOT / "evidence" / "m4").iterdir()) == listing


def test_cli_rejects_root_or_path_arguments(workdir):
    for arguments in (["--root", str(workdir)], [str(workdir)], ["--dossier", "x"]):
        result = run_cli(workdir, *arguments)
        assert result.returncode == 2
        assert "unrecognized arguments" in result.stderr
    help_result = run_cli(workdir, "--help")
    assert help_result.returncode == 0
    assert "--json" in help_result.stdout
    assert "--root" not in help_result.stdout


def test_tool_source_has_no_network_write_or_runtime_reads():
    source = TOOL.read_text(encoding="utf-8")
    for banned in (
        "socket",
        "urllib",
        "httpx",
        "requests.",
        "import requests",
        "subprocess",
        "os.environ",
        "os.getenv",
        "datetime",
        "time.time",
        "write_text",
        "write_bytes",
        "unlink",
        "mkdir",
        "rmtree",
        "tempfile",
        "open(",
    ):
        assert banned not in source, banned
