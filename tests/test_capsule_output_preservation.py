"""Existing caller outputs must survive attempted temporary database builds."""

import contextlib
import logging
import shutil
from pathlib import Path

import duckdb
import pytest

from ashare_research.reproducibility import capsule

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


@contextlib.contextmanager
def injected_staging_cleanup_failure(monkeypatch):
    """Make the real TemporaryDirectory cleanup of owned staging fail.

    Yields ``(attempted, retained)``: staging directories whose cleanup raised the
    injected ``PermissionError`` and those still present at that moment.  Leftovers
    are removed with the real ``rmtree`` once the injected failure is disabled.
    """

    real_rmtree = shutil.rmtree
    attempted: list[Path] = []
    retained: list[Path] = []
    active = True

    def deny_owned_staging(path, *args, **kwargs):
        candidate = Path(path)
        if active and candidate.name.startswith(".") and ".staging-" in candidate.name:
            attempted.append(candidate)
            if candidate.exists():
                retained.append(candidate)
            raise PermissionError(f"injected staging cleanup failure: {candidate}")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", deny_owned_staging)
    try:
        yield attempted, retained
    finally:
        active = False
        for candidate in attempted:
            if candidate.exists():
                real_rmtree(candidate)


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


def test_successful_publication_survives_cleanup_failure(tmp_path, monkeypatch, caplog):
    target = tmp_path / "temporary.duckdb"
    with (
        injected_staging_cleanup_failure(monkeypatch) as (attempted, retained),
        caplog.at_level(logging.WARNING, logger=capsule.__name__),
    ):
        result = capsule.build_temp_fact_db(SNAPSHOT, target)
        assert result == target
        assert attempted == retained
        assert len(retained) == 1
        assert (retained[0] / target.name).is_file()

    with duckdb.connect(str(target), read_only=True) as connection:
        assert connection.sql("SELECT COUNT(*) FROM financial_facts").fetchone() == (33,)
        assert connection.sql("SELECT COUNT(*) FROM fact_contexts").fetchone() == (11,)
        assert connection.sql("SELECT COUNT(*) FROM fact_lineage").fetchone() == (33,)
    assert len(attempted) == 1
    assert not retained[0].exists()
    assert target.is_file()
    assert f"retained owned staging directory {attempted[0]}" in caplog.text
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))


def test_build_failure_survives_cleanup_failure(tmp_path, monkeypatch, caplog):
    target = tmp_path / "temporary.duckdb"

    def fail_store(*args, **kwargs):
        raise RuntimeError("injected insertion failure")

    monkeypatch.setattr(capsule.FactRepository, "store_facts", fail_store)
    with (
        injected_staging_cleanup_failure(monkeypatch) as (attempted, retained),
        caplog.at_level(logging.WARNING, logger=capsule.__name__),
        pytest.raises(RuntimeError, match="injected insertion failure") as excinfo,
    ):
        capsule.build_temp_fact_db(SNAPSHOT, target)

    assert type(excinfo.value) is RuntimeError
    assert not target.exists()
    assert attempted == retained
    assert len(attempted) == 1
    assert f"retained owned staging directory {attempted[0]}" in caplog.text
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))


@pytest.mark.parametrize("publication_failure", ["competing_target", "link_unsupported"])
def test_publication_failure_survives_cleanup_failure(
    tmp_path, monkeypatch, caplog, publication_failure
):
    target = tmp_path / "temporary.duckdb"
    original = b"caller-created during build"
    if publication_failure == "competing_target":
        real_link = capsule.os.link

        def race(source, destination):
            target.write_bytes(original)
            return real_link(source, destination)

        monkeypatch.setattr(capsule.os, "link", race)
        expected = FileExistsError
        expected_message = "refusing to overwrite"
    else:
        def unsupported(*args, **kwargs):
            raise OSError("hard links unsupported")

        monkeypatch.setattr(capsule.os, "link", unsupported)
        expected = OSError
        expected_message = "without overwrite"

    with (
        injected_staging_cleanup_failure(monkeypatch) as (attempted, retained),
        caplog.at_level(logging.WARNING, logger=capsule.__name__),
        pytest.raises(expected, match=expected_message) as excinfo,
    ):
        capsule.build_temp_fact_db(SNAPSHOT, target)

    assert not isinstance(excinfo.value, PermissionError)
    assert attempted == retained
    assert len(attempted) == 1
    assert f"retained owned staging directory {attempted[0]}" in caplog.text
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))
    if publication_failure == "competing_target":
        assert target.read_bytes() == original
    else:
        assert not target.exists()


def test_non_oserror_cleanup_failure_is_not_swallowed(tmp_path, monkeypatch):
    target = tmp_path / "temporary.duckdb"
    real_rmtree = shutil.rmtree
    attempted: list[Path] = []
    active = True

    def explode_owned_staging(path, *args, **kwargs):
        candidate = Path(path)
        if active and ".staging-" in candidate.name:
            attempted.append(candidate)
            raise RuntimeError("injected cleanup programming error")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", explode_owned_staging)
    try:
        with pytest.raises(RuntimeError, match="injected cleanup programming error"):
            capsule.build_temp_fact_db(SNAPSHOT, target)
    finally:
        active = False
        for candidate in attempted:
            if candidate.exists():
                real_rmtree(candidate)

    assert target.is_file()
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))
