"""Existing caller outputs must survive attempted temporary database builds."""

from pathlib import Path

import duckdb
import pytest

from ashare_research.reproducibility import capsule

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


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


@pytest.mark.parametrize("failure", ["schema", "store", "validation"])
def test_build_failure_closes_and_cleans_owned_staging(tmp_path, monkeypatch, failure):
    target = tmp_path / "db" / "temporary.duckdb"
    closed = []
    original_close = capsule.DuckDBStore.close

    def close_and_record(store):
        original_close(store)
        closed.append(store)

    monkeypatch.setattr(capsule.DuckDBStore, "close", close_and_record)
    if failure == "schema":
        original_ensure_schema = capsule.FactRepository.ensure_schema_v2

        def fail_schema(*args, **kwargs):
            original_ensure_schema(*args, **kwargs)
            raise RuntimeError("injected schema failure")

        monkeypatch.setattr(capsule.FactRepository, "ensure_schema_v2", fail_schema)
    elif failure == "store":
        def fail_store(*args, **kwargs):
            raise RuntimeError("injected insertion failure")

        monkeypatch.setattr(capsule.FactRepository, "store_facts", fail_store)
    else:
        def fail_validation(*args, **kwargs):
            raise RuntimeError("injected validation failure")

        monkeypatch.setattr(capsule.VersionChainValidator, "validate", fail_validation)

    with pytest.raises(RuntimeError, match="injected"):
        capsule.build_temp_fact_db(SNAPSHOT, target)
    assert len(closed) == 1
    assert closed[0]._conn is None
    assert not target.exists()
    assert list(target.parent.iterdir()) == []


def test_competing_target_survives_publication_attempt(tmp_path, monkeypatch):
    target = tmp_path / "temporary.duckdb"
    original = b"caller-created during build"
    real_link = capsule.os.link

    def race(source, destination):
        target.write_bytes(original)
        return real_link(source, destination)

    monkeypatch.setattr(capsule.os, "link", race)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        capsule.build_temp_fact_db(SNAPSHOT, target)
    assert target.read_bytes() == original
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))


def test_unsupported_publication_fails_closed(tmp_path, monkeypatch):
    target = tmp_path / "temporary.duckdb"

    def unsupported(*args, **kwargs):
        raise OSError("hard links unsupported")

    monkeypatch.setattr(capsule.os, "link", unsupported)
    with pytest.raises(OSError, match="without overwrite"):
        capsule.build_temp_fact_db(SNAPSHOT, target)
    assert not target.exists()
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))


def test_successful_publication_is_readable_and_complete(tmp_path):
    target = tmp_path / "temporary.duckdb"
    result = capsule.build_temp_fact_db(SNAPSHOT, target)
    assert result == target
    with duckdb.connect(str(target), read_only=True) as connection:
        assert connection.sql("SELECT COUNT(*) FROM financial_facts").fetchone() == (33,)
        assert connection.sql("SELECT COUNT(*) FROM fact_contexts").fetchone() == (11,)
        assert connection.sql("SELECT COUNT(*) FROM fact_lineage").fetchone() == (33,)
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))
