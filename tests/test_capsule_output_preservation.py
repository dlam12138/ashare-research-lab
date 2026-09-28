"""Existing caller outputs must survive attempted temporary database builds."""

from pathlib import Path

import pytest

from ashare_research.reproducibility import capsule


@pytest.mark.parametrize("kind", ["file", "directory", "live_link", "dangling_link"])
def test_existing_output_rejected_before_snapshot_read(tmp_path, monkeypatch, kind):
    target = tmp_path / "existing.duckdb"
    original = b"caller-owned output: do not delete"
    referent = tmp_path / "referent"
    if kind == "file":
        target.write_bytes(original)
    elif kind == "directory":
        target.mkdir()
        (target / "sentinel").write_bytes(original)
    else:
        if kind == "live_link":
            referent.write_bytes(original)
        try:
            target.symlink_to(referent)
        except OSError:
            pytest.skip("symbolic links unavailable for this account")

    def forbidden_read(_):
        pytest.fail("existing output must be rejected before loading input")

    monkeypatch.setattr(capsule, "validate_snapshot", forbidden_read)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capsule.build_temp_fact_db(tmp_path / "unused-input", target)

    if kind == "file":
        assert target.read_bytes() == original
    elif kind == "directory":
        assert (target / "sentinel").read_bytes() == original
    else:
        assert target.is_symlink()
        if kind == "live_link":
            assert referent.read_bytes() == original
        else:
            assert not referent.exists()


def test_invalid_snapshot_does_not_create_fresh_output(tmp_path, monkeypatch):
    target = tmp_path / "new-parent" / "new.duckdb"

    def invalid_snapshot(_):
        raise ValueError("invalid snapshot")

    monkeypatch.setattr(capsule, "validate_snapshot", invalid_snapshot)
    with pytest.raises(ValueError, match="invalid snapshot"):
        capsule.build_temp_fact_db(Path("unused-input"), target)
    assert not target.parent.exists()


def test_dangling_symlink_guard_without_platform_privileges(tmp_path, monkeypatch):
    target = tmp_path / "dangling.duckdb"
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == target)

    def forbidden_read(_):
        pytest.fail("dangling symlink must be rejected before loading input")

    monkeypatch.setattr(capsule, "validate_snapshot", forbidden_read)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capsule.build_temp_fact_db(tmp_path / "unused-input", target)
