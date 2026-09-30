"""Output-boundary guards for ``build_test_capsule``.

The builder validates the supplied snapshot before creating the output
directory or any missing parent, refuses every caller-owned entry (including a
dangling symlink) before reading the input, and claims the output with an
exclusive ``mkdir`` so an entry appearing at that boundary is never adopted,
mutated or deleted.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ashare_research.reproducibility import capsule

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
SENTINEL = b"caller-owned output: do not adopt, overwrite or delete\n"


def _copied_snapshot(tmp_path: Path) -> Path:
    copied = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, copied)
    return copied


def test_missing_snapshot_leaves_no_output_or_parent(tmp_path: Path) -> None:
    out = tmp_path / "missing-parent" / "capsule"

    with pytest.raises(FileNotFoundError):
        capsule.build_test_capsule(out, committed_snapshot_dir=tmp_path / "absent-snapshot")

    assert not out.exists()
    assert not out.is_symlink()
    assert not out.parent.exists()
    assert list(tmp_path.iterdir()) == []


def test_bad_hash_snapshot_leaves_no_output_or_parent(tmp_path: Path) -> None:
    snapshot = _copied_snapshot(tmp_path)
    facts_path = snapshot / capsule.FACTS_FILE
    facts_path.write_bytes(facts_path.read_bytes() + b"\n")
    out = tmp_path / "missing-parent" / "capsule"

    with pytest.raises(ValueError, match="hash mismatch"):
        capsule.build_test_capsule(out, committed_snapshot_dir=snapshot)

    assert not out.exists()
    assert not out.parent.exists()
    assert [path.name for path in tmp_path.iterdir()] == ["snapshot"]


def test_corrected_snapshot_retries_same_output_without_cleanup(tmp_path: Path) -> None:
    snapshot = _copied_snapshot(tmp_path)
    facts_path = snapshot / capsule.FACTS_FILE
    original = facts_path.read_bytes()
    facts_path.write_bytes(original + b"\n")
    out = tmp_path / "missing-parent" / "capsule"

    with pytest.raises(ValueError, match="hash mismatch"):
        capsule.build_test_capsule(out, committed_snapshot_dir=snapshot)
    assert not out.exists()
    assert not out.parent.exists()

    facts_path.write_bytes(original)
    manifest = capsule.build_test_capsule(out, committed_snapshot_dir=snapshot)

    assert manifest["contract"] == capsule.CAPSULE_SCHEMA_VERSION
    assert capsule.verify_capsule_manifest(out)["logical_digest"] == manifest["logical_digest"]


@pytest.mark.parametrize("kind", ["file", "directory", "live_link", "dangling_link"])
def test_initial_output_rejected_before_input_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    out = tmp_path / "capsule"
    referent = tmp_path / "referent"
    if kind == "file":
        out.write_bytes(SENTINEL)
    elif kind == "directory":
        out.mkdir()
        (out / "sentinel").write_bytes(SENTINEL)
    else:
        if kind == "live_link":
            referent.write_bytes(SENTINEL)
        try:
            out.symlink_to(referent)
        except OSError:
            pytest.skip("symbolic links unavailable for this account")

    def forbidden_validation(_):
        pytest.fail("output must be rejected before the snapshot is read")

    monkeypatch.setattr(capsule, "validate_snapshot", forbidden_validation)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capsule.build_test_capsule(out, committed_snapshot_dir=tmp_path / "unused-input")

    if kind == "file":
        assert out.read_bytes() == SENTINEL
    elif kind == "directory":
        assert (out / "sentinel").read_bytes() == SENTINEL
    else:
        assert out.is_symlink()
        if kind == "live_link":
            assert referent.read_bytes() == SENTINEL
        else:
            assert not referent.exists()


def test_dangling_symlink_guard_without_platform_privileges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "capsule"
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == out)

    def forbidden_validation(_):
        pytest.fail("dangling symlink must be rejected before the snapshot is read")

    monkeypatch.setattr(capsule, "validate_snapshot", forbidden_validation)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capsule.build_test_capsule(out, committed_snapshot_dir=tmp_path / "unused-input")

    assert not out.exists()


@pytest.mark.parametrize("kind", ["directory", "file"])
def test_competing_output_at_mkdir_boundary_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    out = tmp_path / "capsule"
    real_mkdir = Path.mkdir
    real_validate = capsule.validate_snapshot
    events: list[str] = []

    def recording_validate(snapshot_dir):
        events.append("validate")
        return real_validate(snapshot_dir)

    def competing_mkdir(self: Path, *args, **kwargs):
        if self == out and "competing" not in events:
            events.append("competing")
            if kind == "directory":
                real_mkdir(out)
                (out / "sentinel").write_bytes(SENTINEL)
            else:
                out.write_bytes(SENTINEL)
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(capsule, "validate_snapshot", recording_validate)
    monkeypatch.setattr(Path, "mkdir", competing_mkdir)

    with pytest.raises(FileExistsError):
        capsule.build_test_capsule(out, committed_snapshot_dir=SNAPSHOT)

    assert events == ["validate", "competing"]
    if kind == "directory":
        assert (out / "sentinel").read_bytes() == SENTINEL
        assert [path.name for path in out.iterdir()] == ["sentinel"]
    else:
        assert out.read_bytes() == SENTINEL
